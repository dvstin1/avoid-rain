# copyright 2026 Dustin Massop, License: GPLv2
"""
Unit tests for Playtest Polish Pass 3:
1. Single 40px Sanctuary Scriptorium doorway at [38, 21] with solid [37, 21] and [39, 21] walls and single arch blit.
2. GameState.respawn_player() recording/clearing last_death_event across active Marginalia events and new runs.
3. Chronicler.execute_interaction() selecting distinct event-specific death dialogue across all 9 Marginalia events.
"""
# pylint: disable=no-member,protected-access,duplicate-code
import json
import pygame

import constants
from engine.game_state import GameState
from engine.marginalia_events import MARGINALIA_EVENT_CATALOG, MarginaliaEvent
from engine.stats import StatisticsTracker
from engine.world import Chronicler
from generate_maps import SYMBOL_FLOOR, SYMBOL_WALL, generate_sanctuary
from rendering.renderer import Renderer


def _make_state(tmp_path):
    """Create an offline GameState backed by a temporary stats path."""
    pygame.init()
    stats_path = str(tmp_path / "stats.json")
    stats = StatisticsTracker()
    state = GameState(auto_load=False, stats=stats, stats_path=stats_path)
    state.online_mode = False
    state.network_manager.stop_network()
    return state


def test_sanctuary_single_40px_doorway_and_single_arch_blit(tmp_path):
    """Verify Sanctuary has a single 40px doorway at [38, 21] and blits SanctuaryArchDoorway once."""
    sanctuary_map = generate_sanctuary()
    assert sanctuary_map.grid[21][37] == SYMBOL_WALL
    assert sanctuary_map.grid[21][38] == SYMBOL_FLOOR
    assert sanctuary_map.grid[21][39] == SYMBOL_WALL
    assert sanctuary_map.zones["south_facade"]["doorway"] == [[38, 21]]

    with open("maps/sanctuary.json", "r", encoding="utf-8") as handle:
        on_disk = json.load(handle)
    assert on_disk["grid"][21][37] == SYMBOL_WALL
    assert on_disk["grid"][21][38] == SYMBOL_FLOOR
    assert on_disk["grid"][21][39] == SYMBOL_WALL
    assert on_disk["zones"]["south_facade"]["doorway"] == [[38, 21]]

    state = _make_state(tmp_path)
    assert state.world.grid[21][37] == constants.TILE_WALL
    assert state.world.grid[21][38] == constants.TILE_EMPTY
    assert state.world.grid[21][39] == constants.TILE_WALL

    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)
    ts = constants.TILE_SIZE
    state.camera.instant_center((38 * ts, 16 * ts))
    ox, oy = state.camera.get_offset()

    # Replace SanctuaryArchDoorway with a distinct magenta marker surface to verify single-tile blit at [38, 21]
    marker_color = (250, 20, 220)
    marker_surf = pygame.Surface((ts, ts), pygame.SRCALPHA)
    marker_surf.fill((*marker_color, 255))
    renderer.prop_cache["SanctuaryArchDoorway"] = marker_surf

    screen.fill((12, 14, 18))
    renderer.sanctuary_interior_alpha = 0.0
    renderer.draw_sanctuary_roofs_and_blackout(state, ox, oy)

    px_37 = screen.get_at((int(37 * ts + 20 - ox), int(21 * ts + 20 - oy)))[:3]
    px_38 = screen.get_at((int(38 * ts + 20 - ox), int(21 * ts + 20 - oy)))[:3]
    px_39 = screen.get_at((int(39 * ts + 20 - ox), int(21 * ts + 20 - oy)))[:3]
    assert px_38 == marker_color
    assert px_37 != marker_color
    assert px_39 != marker_color


def test_respawn_player_records_and_clears_last_death_event(tmp_path):
    """Verify respawn_player records last_death_event on active Marginalia death and clears it otherwise."""
    state = _make_state(tmp_path)

    # 1. Death during an active Marginalia event records last_death_event in story_flags and stats.data
    state.marginalia_engine.active_event = MarginaliaEvent(
        event_id="palimpsest_duel", act_variant=1, status="ACTIVE"
    )
    state.respawn_player()
    assert state.stats.data["last_run_result"] == "DEFEAT"
    assert state.stats.data["last_death_event"] == "palimpsest_duel"
    assert state.stats.data["story_flags"]["last_death_event"] == "palimpsest_duel"

    # 2. Death with no active Marginalia event clears last_death_event
    assert state.marginalia_engine.active_event is None
    state.respawn_player()
    assert state.stats.data["last_run_result"] == "DEFEAT"
    assert "last_death_event" not in state.stats.data
    assert "last_death_event" not in state.stats.data["story_flags"]

    # 3. reset_to_new_game clears any recorded last_death_event
    state.stats.data["last_death_event"] = "unbound_folio"
    state.stats.data["story_flags"]["last_death_event"] = "unbound_folio"
    state.reset_to_new_game()
    assert "last_death_event" not in state.stats.data
    assert "last_death_event" not in state.stats.data["story_flags"]


def test_chronicler_event_specific_death_dialogue_all_9_events(tmp_path):
    """Verify Chronicler selects a unique disappointed death line for each of the 9 Marginalia events."""
    state = _make_state(tmp_path)
    chronicler = next((obj for obj in state.world.interactables if isinstance(obj, Chronicler)), None)
    assert chronicler is not None

    generic_defeat_text = next(
        node["text"]
        for node in constants.DIALOGUE_MANIFEST["chronicler"]
        if node["id"] == "chr_defeat"
    )

    all_event_ids = (
        "unbound_folio",
        "running_errata",
        "censored_passage",
        "palimpsest_duel",
        "margin_toll",
        "barrel_mimic_cluster",
        "sunken_margin",
        "relentless_censor",
        "unblotted_margin",
    )
    assert set(all_event_ids) == set(MARGINALIA_EVENT_CATALOG.keys())

    seen_texts = set()
    for event_id in all_event_ids:
        state.marginalia_engine.active_event = MarginaliaEvent(
            event_id=event_id, act_variant=1, status="ACTIVE"
        )
        state.respawn_player()
        chronicler.execute_interaction(state)
        assert state.active_dialogue is not None
        assert state.active_dialogue["speaker"] == "The Chronicler"
        assert state.active_dialogue["emotion"] == "disappointed"
        text = state.active_dialogue["text"]
        assert text != generic_defeat_text
        assert text not in seen_texts
        seen_texts.add(text)

    assert len(seen_texts) == 9

    # Non-event death falls back to generic chr_defeat dialogue
    state.marginalia_engine.active_event = None
    state.respawn_player()
    chronicler.execute_interaction(state)
    assert state.active_dialogue["text"] == generic_defeat_text
