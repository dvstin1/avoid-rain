"""
Unit tests for gated Respite activation on forest and ruins maps,
and Respite deactivation/auto-closure under rain weather conditions.
"""
# pylint: disable=wrong-import-position,wrong-import-order,no-member

import os
# Ensure headless execution before importing pygame
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pytest
import pygame

from constants import RESPITE_HOSTILE_BLOCK_RADIUS
from engine.actor import ActorState
from engine.enemy import FlutterEnemy, NightBoss, SlugEnemy
from engine.game_state import GameState
from engine.world import Respite, LevelLoader
from engine.maps import create_world
from engine.weather import WeatherManager


@pytest.fixture(scope="module", autouse=True)
def init_pygame():
    """Initializes pygame in headless mode for the test suite."""
    pygame.init()
    yield
    pygame.quit()


def test_respite_gating_on_forest_and_ruins():
    """
    Verifies that on forest and ruins maps, the Respite starts inactive
    if the miniboss is alive, and becomes active once the miniboss is defeated.
    """
    # 1. Test Forest Map
    state = GameState(auto_load=False)
    state.world = create_world("forest")
    state.enemies = state.world.enemies

    # Verify we have at least one Respite and a Miniboss
    respites = [obj for obj in state.world.interactables if isinstance(obj, Respite)]
    minibosses = [e for e in state.enemies if getattr(e, 'is_miniboss', False)]

    assert len(respites) > 0, "No respite found on forest map."
    assert len(minibosses) > 0, "No miniboss found on forest map."

    # Initially, respite should be inactive because the miniboss is alive
    for r in respites:
        assert r.is_active is False, "Respite should be inactive while miniboss is alive."

    # Remove all minibosses to simulate defeating them
    for e in minibosses:
        state.defeated_miniboss_ids.add(e.id)
    state.enemies = [e for e in state.enemies if not getattr(e, 'is_miniboss', False)]

    # Update game state to run the activation logic
    state.update(0.1, {"move": (0, 0)})

    # Now respite should be active
    for r in respites:
        assert r.is_active is True, "Respite should be active after miniboss is defeated."


def test_respite_active_on_other_maps():
    """
    Verifies that on maps other than forest/ruins, the Respite is active
    regardless of whether there are minibosses or not.
    """
    state = GameState(auto_load=False)
    state.world = create_world("sanctuary")
    state.enemies = state.world.enemies

    # Create respite programmatically
    respite = Respite((0, 0), (40, 40))
    state.world.interactables.append(respite)

    assert respite.is_active is True, "Respite on sanctuary should always be active."


def test_respite_rain_interaction_denial():
    """
    Verifies that interacting with a Respite exposed to rain returns a lore accurate
    dialogue message and does not open the Respite level-up UI.
    """
    state = GameState(auto_load=False)
    state.world = create_world("sanctuary")

    # Setup weather manager with rain at Respite location
    state.weather_manager = WeatherManager()
    state.weather_manager.boss_coords_list = [{'x': 0, 'y': 0}]
    state.weather_manager.current_boss_idx = 0
    state.weather_manager.active_safe_radius = 50.0  # Very small safe zone
    state.weather_manager.bleed_state = "SHRINKING"
    state.weather_manager.damage_enabled = True

    # Create respite far away from safe zone (e.g. at 500, 500)
    respite = Respite((500, 500), (40, 40))
    state.world.interactables.append(respite)

    # Verify it is considered rained on
    rx = respite.x + respite.width / 2
    ry = respite.y + respite.height / 2
    assert state.weather_manager.is_pos_safe(rx, ry) is False, "Respite should be outside safe zone."

    # Try interacting with it
    respite.execute_interaction(state)

    # Should show dialogue and not set active_respite
    assert state.active_respite is None, "Respite menu should not open when rained on."
    assert state.active_dialogue is not None, "Lore accurate dialogue should be set."
    # pylint: disable=unsubscriptable-object
    assert "liquid ink" in state.active_dialogue["text"], "Dialogue should contain lore explanation."


def test_respite_rain_auto_closure():
    """
    Verifies that if a Respite starts getting rained on while the player is using it,
    it closes instantly.
    """
    state = GameState(auto_load=False)
    state.world = create_world("sanctuary")

    # Setup weather manager
    state.weather_manager = WeatherManager()
    state.weather_manager.boss_coords_list = [{'x': 0, 'y': 0}]
    state.weather_manager.current_boss_idx = 0
    state.weather_manager.active_safe_radius = 1000.0  # Initially large/safe
    state.weather_manager.bleed_state = "SHRINKING"
    state.weather_manager.damage_enabled = True

    # Create respite inside safe zone
    respite = Respite((100, 100), (40, 40))
    state.world.interactables.append(respite)

    # Interact and open menu
    respite.execute_interaction(state)
    assert state.active_respite == respite, "Respite menu should be open."

    # Shrink safe circle to expose Respite
    state.weather_manager.active_safe_radius = 50.0  # Respite at 100, 100 is now outside

    # Run update
    state.update(0.1, {"move": (0, 0)})

    # Menu should be closed instantly
    assert state.active_respite is None, "Respite menu should close instantly when rained on."
    assert state.active_dialogue is None, "Dialogue should close as well."


def test_respite_gating_modular_proximity():
    """
    Verifies that proximity-based Respite gating works correctly on a custom/stitched map.
    """

    # 1. Define a prototype array where 'R' and 'E' (miniboss) are placed near each other (distance = 2)
    grid_proto = [
        "..........",
        "....R.E...",
        ".........."
    ]

    # 2. Parse the map using a custom/modular name
    _, interactables, _, _, _ = LevelLoader.parse_map(
        grid_proto, map_name="modular_world_test", defeated_ids=set()
    )

    # 3. Find the Respite and verify its gated_by_miniboss_id is set
    respites = [obj for obj in interactables if isinstance(obj, Respite)]
    assert len(respites) == 1
    respite = respites[0]

    # Expected gating miniboss coordinate is (6, 1) since E is at x=6, y=1
    assert respite.gated_by_miniboss_id == "modular_world_test:6,1"
    assert respite.is_active is False, "Respite should start inactive because miniboss is not defeated."

    # 4. If we parse with the miniboss already in defeated_ids
    _, interactables_def, _, _, _ = LevelLoader.parse_map(
        grid_proto, map_name="modular_world_test", defeated_ids={"modular_world_test:6,1"}
    )
    respite_def = [obj for obj in interactables_def if isinstance(obj, Respite)][0]
    assert respite_def.is_active is True, "Respite should start active if the gating miniboss was defeated."


def test_respite_multiplayer_defeated_sync():
    """
    Verifies that a Host's defeated miniboss set is correctly serialized
    and applied on the Client, which then activates the gated Respite.
    """
    # 1. Setup Host
    host = GameState(auto_load=False)
    host.network_manager.network_mode = "HOST"
    host.world = create_world("forest")
    host.defeated_miniboss_ids.add("forest:10,20") # Simulate a defeated boss

    # 2. Get local state payload (simulating host send)
    payload = host.get_local_state()
    assert "defeated_miniboss_ids" in payload
    assert "forest:10,20" in payload["defeated_miniboss_ids"]

    # 3. Setup Client
    client = GameState(auto_load=False)
    client.network_manager.network_mode = "CLIENT"
    client.world = create_world("forest")

    # Verify client respite is initially inactive
    respites = [obj for obj in client.world.interactables if isinstance(obj, Respite)]
    for r in respites:
        r.gated_by_miniboss_id = "forest:10,20" # Gate it by our boss
        r.is_active = False

    # 4. Apply remote state on client (simulating client receive)
    client.apply_remote_state("127.0.0.1", payload)
    assert "forest:10,20" in client.defeated_miniboss_ids

    # 5. Run client update loop to trigger Respite activation update
    client.update(0.1, {"move": (0, 0)})
    for r in respites:
        assert r.is_active is True, "Client Respite should activate after receiving sync data from Host."


def test_respite_blocked_when_hostiles_nearby_or_aggroed():
    """Verify Respite blocks interaction when alive enemies are within radius or actively aggroed."""
    state = GameState(auto_load=False)
    try:
        state.world = create_world("sanctuary")
        state.player.x, state.player.y = 200.0, 200.0
        respite = Respite((200, 200), (40, 40))
        state.world.interactables.append(respite)

        # 1. Nearby idle enemy inside RESPITE_HOSTILE_BLOCK_RADIUS blocks opening
        slug = SlugEnemy(200.0 + RESPITE_HOSTILE_BLOCK_RADIUS * 0.5, 200.0)
        state.enemies = [slug]
        respite.execute_interaction(state)
        assert state.active_respite is None
        assert isinstance(state.active_dialogue, dict)
        assert state.active_dialogue.get("speaker") == "Respite Anchor"
        assert "Hostile" in state.active_dialogue.get("text", "")

        # 2. Far enemy outside radius but actively chasing still blocks opening
        slug.x = 200.0 + RESPITE_HOSTILE_BLOCK_RADIUS + 200.0
        slug.state = ActorState.CHASE
        respite.execute_interaction(state)
        assert state.active_respite is None

        # 3. Far idle enemy allows Respite to open cleanly
        slug.state = ActorState.IDLE
        respite.execute_interaction(state)
        assert state.active_respite is respite

        # 4. Dead enemy right next to player does not block opening
        state.close_respite_menu()
        slug.x, slug.y = 210.0, 200.0
        slug.hp = 0
        respite.execute_interaction(state)
        assert state.active_respite is respite
    finally:
        state.shutdown_save_worker(timeout=1.0)


def test_respite_disabled_during_and_after_night_boss():
    """Verify Respite locks out during/after Night Boss across flag, active boss, and bleed_state."""
    state = GameState(auto_load=False)
    try:
        state.world = create_world("sanctuary")
        state.in_sanctuary = False
        state.player.x, state.player.y = 100.0, 100.0
        respite = Respite((100, 100), (40, 40))
        state.world.interactables.append(respite)

        # 1. Locked when night_boss_spawned flag is True (even with enemies cleared)
        state.enemies = []
        state.night_boss_spawned = True
        respite.execute_interaction(state)
        assert state.active_respite is None
        assert isinstance(state.active_dialogue, dict)
        assert "Night Boss" in state.active_dialogue.get("text", "")

        # 2. Locked when an alive NightBoss exists in state.enemies (even far away)
        state.night_boss_spawned = False
        boss = NightBoss(2000.0, 2000.0)
        state.enemies = [boss]
        respite.execute_interaction(state)
        assert state.active_respite is None

        # 3. Locked when bleed_state is BOSS_PHASE, DILUTION, or APPENDIX
        state.enemies = []
        for locked_phase in ("BOSS_PHASE", "DILUTION", "APPENDIX"):
            state.weather_manager.bleed_state = locked_phase
            respite.execute_interaction(state)
            assert state.active_respite is None

        # 4. Spawning NightBoss via _update_world_events sets night_boss_spawned and closes open Respite
        state.weather_manager.bleed_state = "GRACE_PERIOD"
        respite.execute_interaction(state)
        assert state.active_respite is respite

        state.world.boss_coords_list = [{"x": 5, "y": 5}]
        state.weather_manager.current_boss_idx = 0
        state.weather_manager.bleed_state = "CLAMPED"
        state._update_world_events(0.016)  # pylint: disable=protected-access
        assert state.night_boss_spawned is True
        assert state.active_respite is None

        # 5. on_enter_sanctuary() and reset_to_new_game() clear night_boss_spawned
        state.on_enter_sanctuary()
        assert state.night_boss_spawned is False
        state.night_boss_spawned = True
        state.reset_to_new_game()
        assert state.night_boss_spawned is False
    finally:
        state.shutdown_save_worker(timeout=1.0)


def test_start_warp_auto_closes_respite_menu():
    """Verify GameState.start_warp() clears open Respite UI and staged session flags."""
    state = GameState(auto_load=False)
    try:
        state.world = create_world("sanctuary")
        respite = Respite((100, 100), (40, 40))
        state.world.interactables.append(respite)
        respite.execute_interaction(state)
        state.respite_upgrades = {1: 2, 2: 1}
        state.respite_selection_idx = 2
        state.respite_marked_idx = 1
        state.player.has_rested_this_session = True
        assert state.active_respite is respite

        state.start_warp("sanctuary")
        assert state.active_respite is None
        assert state.active_dialogue is None
        assert state.respite_upgrades == {1: 0, 2: 0}
        assert state.respite_selection_idx == 5
        assert state.respite_marked_idx == -1
        assert state.player.has_rested_this_session is False
    finally:
        state.shutdown_save_worker(timeout=1.0)


def test_respite_defers_enemy_aggro_and_damage_until_closed():
    """Verify enemies ignore the resting local player while active_respite is open, preserve LAN peer targeting,
    and resume aggro once the Respite menu closes."""
    state = GameState(auto_load=False)
    try:
        state.world = create_world("sanctuary")
        state.in_sanctuary = False
        state.player.x, state.player.y = 200.0, 200.0
        respite = Respite((200, 200), (40, 40))
        state.world.interactables.append(respite)
        respite.execute_interaction(state)
        assert state.active_respite is respite

        # Enemies spawned right next to player stay non-hostile while Respite menu is open
        slug = SlugEnemy(210.0, 200.0)
        flutter = FlutterEnemy(220.0, 200.0)
        state.enemies = [slug, flutter]

        slug._update_state_logic(0.016, state)  # pylint: disable=protected-access
        flutter._update_state_logic(0.016, state)  # pylint: disable=protected-access
        assert slug.state not in (ActorState.CHASE, ActorState.WIND_UP, ActorState.STRIKE)
        assert slug.active_target is None
        assert flutter.state != ActorState.CHASE
        assert flutter.active_target is None

        # Even if overlapping during STRIKE, resting local player takes no damage
        hp_before = state.player.hp
        slug.state = ActorState.STRIKE
        assert slug.attempt_damage_player(state) is False
        assert state.player.hp == hp_before

        # LAN Co-op safety: non-resting remote peer remains targetable and damageable
        state.network_manager.remote_players["peer_1"] = {
            "x": 210.0,
            "y": 200.0,
            "hp": 100.0,
            "in_sanctuary": False,
            "identity": "Ally",
        }
        slug.state = ActorState.IDLE
        slug._update_state_logic(0.016, state)  # pylint: disable=protected-access
        assert slug.active_target == (230.0, 220.0)
        assert slug.state in (ActorState.CHASE, ActorState.WIND_UP)
        assert slug.attempt_damage_player(state) is True
        assert state.network_manager.remote_players["peer_1"]["hp"] < 100.0
        assert state.player.hp == hp_before

        # Closing Respite menu restores normal aggro and damage against local player
        state.network_manager.remote_players.clear()
        state.close_respite_menu()
        slug.state = ActorState.IDLE
        slug.cooldown_timer = 0.0
        slug._update_state_logic(0.016, state)  # pylint: disable=protected-access
        flutter._update_state_logic(0.016, state)  # pylint: disable=protected-access
        assert slug.state in (ActorState.CHASE, ActorState.WIND_UP)
        assert flutter.state == ActorState.CHASE
        assert slug.attempt_damage_player(state) is True
        assert state.player.hp < hp_before
    finally:
        state.shutdown_save_worker(timeout=1.0)
