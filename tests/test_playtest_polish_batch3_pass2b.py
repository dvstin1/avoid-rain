"""Unit tests for Playtest Polish Batch 3 Pass 2B: Sanctuary doorway open state, door_open.ogg & roof reveal."""
# pylint: disable=wrong-import-position,wrong-import-order,no-member,protected-access

import os
from types import SimpleNamespace

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame
import pytest

import constants
import generate_sfx
from engine.game_state import GameState
from rendering.renderer import Renderer


@pytest.fixture(scope="module", autouse=True)
def init_pygame():
    """Initialize and cleanly tear down pygame in headless dummy mode."""
    pygame.init()
    yield
    pygame.quit()


def test_door_open_sfx_recipe_and_generated_asset():
    """Verify door_open preset/recipe renders cleanly and assets/audio/sfx/door_open.ogg exists and verifies."""
    assert "door_open" in generate_sfx.PRESETS
    assert "door_open.ogg" in generate_sfx.SOUND_RECIPES

    sig = generate_sfx.render_preset("door_open", seed=42)
    assert len(sig) == generate_sfx.n_samples(0.35)
    pk = generate_sfx.peak(sig)
    assert 0.01 < pk <= 1.0

    ogg_path = os.path.join("assets", "audio", "sfx", "door_open.ogg")
    assert os.path.exists(ogg_path), f"Missing generated SFX asset: {ogg_path}"
    length = generate_sfx.verify_ogg(ogg_path)
    assert 0.25 <= length <= 0.50


def test_sanctuary_door_open_state_and_edge_triggered_sound():
    """Verify sanctuary_door_open edge-triggers door_open.ogg once on approach and resets when leaving or respawning."""
    state = GameState(auto_load=False)
    state.network_manager.stop_network()
    played_sfx = []
    fake_audio = SimpleNamespace(
        play_sfx=lambda name, **kw: played_sfx.append(name),
        update_enemy_sounds=lambda _s: None,
        update_rain_audio=lambda *_a, **_k: None,
    )
    try:
        ts = constants.TILE_SIZE
        assert state.world.name == "sanctuary"
        assert state.sanctuary_door_open is False

        # 1. Far from doorway [38, 21]: stays closed, no SFX
        state.player.x = 38.0 * ts
        state.player.y = 26.0 * ts
        state.update(0.016, {}, audio_manager=fake_audio)
        assert state.sanctuary_door_open is False
        assert not played_sfx

        # 2. Approach south threshold [38, 22]: transitions False -> True and plays door_open.ogg once
        state.player.x = 38.0 * ts
        state.player.y = 22.0 * ts
        state.update(0.016, {}, audio_manager=fake_audio)
        assert state.sanctuary_door_open is True
        assert played_sfx == [constants.SANCTUARY_DOOR_OPEN_SFX]

        # 3. Step directly into doorway [38, 21]: remains open without re-triggering SFX
        state.player.x = 38.0 * ts
        state.player.y = 21.0 * ts
        state.update(0.016, {}, audio_manager=fake_audio)
        assert state.sanctuary_door_open is True
        assert len(played_sfx) == 1

        # 4. Walk far away -> closes; return -> edge-triggers door_open.ogg a second time
        state.player.x = 30.0 * ts
        state.player.y = 26.0 * ts
        state.update(0.016, {}, audio_manager=fake_audio)
        assert state.sanctuary_door_open is False

        state.player.x = 38.0 * ts
        state.player.y = 21.0 * ts
        state.update(0.016, {}, audio_manager=fake_audio)
        assert state.sanctuary_door_open is True
        assert len(played_sfx) == 2

        # 5. Respawn resets sanctuary_door_open to False
        state.respawn_player()
        assert state.sanctuary_door_open is False
    finally:
        state.shutdown_save_worker(timeout=1.0)


def test_open_archway_does_not_occlude_player_and_closed_door_preserved():
    """Verify open doorway draws only jambs/lintel (transparent center) while closed doorway renders arch sprite."""
    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)
    state = GameState(auto_load=False)
    state.network_manager.stop_network()
    try:
        ts = constants.TILE_SIZE
        state.camera.instant_center((38 * ts, 16 * ts))
        ox, oy = state.camera.get_offset()
        dx_px = int(38 * ts - ox)
        dy_px = int(21 * ts - oy)

        # 1. Closed state (player far away): closed SanctuaryArchDoorway fills doorway center
        state.player.x = 38.0 * ts
        state.player.y = 14.0 * ts
        state.sanctuary_door_open = False
        renderer.sanctuary_interior_alpha = 0.0
        sentinel_bg = (240, 12, 220)
        screen.fill(sentinel_bg)
        renderer.draw_sanctuary_roofs_and_blackout(state, ox, oy)
        assert screen.get_at((dx_px + ts // 2, dy_px + ts // 2))[:3] != sentinel_bg

        # 2. Open state (player standing at [38, 21]): center remains unoccluded while jambs/lintel frame it
        state.player.x = 38.0 * ts
        state.player.y = 21.0 * ts
        state.sanctuary_door_open = True
        renderer.sanctuary_interior_alpha = 0.0
        screen.fill(sentinel_bg)
        renderer.draw_sanctuary_roofs_and_blackout(state, ox, oy)
        # Center of doorway tile preserves underlying player/canvas pixel (not overwritten by closed door)
        assert screen.get_at((dx_px + ts // 2, dy_px + ts // 2))[:3] == sentinel_bg
        # Left jamb & top lintel frame the open archway cleanly
        assert screen.get_at((dx_px + 2, dy_px + ts // 2))[:3] != sentinel_bg
        assert screen.get_at((dx_px + ts // 2, dy_px + 2))[:3] != sentinel_bg
    finally:
        state.shutdown_save_worker(timeout=1.0)


def test_scriptorium_roof_reveals_upon_stepping_into_row_20():
    """Verify interior=[29, 8, 20, 13] stays roofed at [38, 21] and fades open upon stepping into row 20."""
    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)
    state = GameState(auto_load=False)
    state.network_manager.stop_network()
    try:
        ts = constants.TILE_SIZE
        roofs = state.world.sanctuary_zones["roof_zones"]
        scriptorium = next(r for r in roofs if r["name"] == "scriptorium_roof")
        assert scriptorium["interior"] == [29, 8, 20, 13]

        # Standing in doorway [38, 21] does NOT trigger interior reveal yet
        state.player.x = 38.0 * ts
        state.player.y = 21.0 * ts
        assert renderer._is_player_inside_scriptorium(state) is False
        renderer.sanctuary_interior_alpha = 0.0
        renderer.update_sanctuary_interior_alpha(state, 0.5)
        assert renderer.sanctuary_interior_alpha == 0.0

        # Stepping north into row 20 ([38, 20]) triggers interior reveal and fades roof away
        state.player.x = 38.0 * ts
        state.player.y = 20.0 * ts
        assert renderer._is_player_inside_scriptorium(state) is True
        renderer.update_sanctuary_interior_alpha(state, 0.5)
        assert renderer.sanctuary_interior_alpha == 1.0
    finally:
        state.shutdown_save_worker(timeout=1.0)
