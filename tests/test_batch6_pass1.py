# copyright 2026 Dustin Massop, License: GPLv2
"""
Unit tests for Batch 6 Pass 1:
1. SmearEnemy walking Inkwell Puddle 10s lifetime, smooth fade rendering, spatial cache invalidation,
   and permanence of map-placed 'v' Inkwell Puddle tiles.
2. Frozen Peaks stratum tile variants (_build_frozen_peaks_stratum_variant) preserving (1, 1) == s_base.
3. Bespoke Frozen Peaks props (frozen_script_monolith.png & frozen_rime_cask.png) generation, preloading,
   and biome-aware dispatch for Structure & Barrel.
4. Snowfall atmosphere (draw_frozen_peaks_atmosphere) active in frozen_peaks strictly where rain is not falling.
"""
# pylint: disable=wrong-import-position,wrong-import-order,no-member,protected-access

import os
import random

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame
import pytest

import constants
from engine.enemy import SmearEnemy
from engine.game_state import GameState
from engine.world import GameObject, World
from generate_assets import generate_frozen_rime_cask, generate_frozen_script_monolith
from rendering.renderer import Renderer


@pytest.fixture(scope="module", autouse=True)
def init_pygame():
    """Initialize and cleanly tear down pygame in headless dummy mode."""
    pygame.init()
    yield
    pygame.quit()


def test_smear_walking_puddle_fades_and_expires_while_map_puddle_persists(monkeypatch):
    """SmearEnemy walking puddles fade over SMEAR_TRAIL_FADE_DURATION and expire at 10s; map 'v' puddles persist."""
    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)
    state = GameState(auto_load=False)
    state.network_manager.stop_network()
    try:
        # Row 2, col 2 has a permanent map-placed 'v' Inkwell Puddle at (80, 80)
        grid_lines = ["." * 12 for _ in range(12)]
        grid_lines[2] = "..v" + "." * 9
        state.world = World("swamp_mire")
        state.world.load_from_prototype(grid_lines)

        map_puddles = [o for o in state.world.interactables if o.name == "Inkwell Puddle"]
        assert len(map_puddles) == 1
        map_puddle = map_puddles[0]
        assert getattr(map_puddle, "lifetime", None) is None

        # Pad interactables above 64 so World.has_puddle_collision exercises the spatial bucket path
        for idx in range(70):
            filler = GameObject((400 + (idx % 5) * 40, 400 + (idx // 5) * 40), (40, 40))
            filler.name = "DecorFiller"
            filler.is_solid = False
            state.world.interactables.append(filler)

        # Spawn a walking puddle from SmearEnemy at (240, 200)
        state.player.x, state.player.y = 200.0, 200.0
        state.camera.instant_center((200.0, 200.0))
        smear = SmearEnemy(240.0, 200.0)
        smear._puddle_timer = 0.95
        monkeypatch.setattr(random, "random", lambda: 0.0)
        smear.update(0.1, state)

        timed_puddles = [
            o for o in state.world.interactables
            if o.name == "Inkwell Puddle" and getattr(o, "lifetime", None) is not None
        ]
        assert len(timed_puddles) == 1
        trail_puddle = timed_puddles[0]
        assert trail_puddle.lifetime == pytest.approx(constants.SMEAR_TRAIL_PUDDLE_LIFETIME)
        assert trail_puddle.max_lifetime == pytest.approx(constants.SMEAR_TRAIL_PUDDLE_LIFETIME)

        trail_rect = (trail_puddle.x + 4, trail_puddle.y + 4, 24, 24)
        map_rect = (map_puddle.x + 4, map_puddle.y + 4, 24, 24)
        assert state.world.has_puddle_collision(trail_rect) is True
        assert state.world.has_puddle_collision(map_rect) is True

        # Advance 8.5s -> 1.5s remaining (inside 2.5s fade window), still slows and renders faded surface
        state._update_shared_world(8.5)
        assert trail_puddle in state.world.interactables
        assert trail_puddle.lifetime == pytest.approx(1.5)
        assert state.world.has_puddle_collision(trail_rect) is True

        renderer._fx_surface_cache.clear()
        renderer.render(state)
        assert any(k[0] == "inkwell_puddle_fade" for k in renderer._fx_surface_cache)
        assert any(k[0] == "inkwell_puddle_ripple" for k in renderer._fx_surface_cache)

        # Advance another 1.6s (total 10.1s) -> trail expires & spatial buckets immediately clear
        state._update_shared_world(1.6)
        assert trail_puddle not in state.world.interactables
        assert state.world.has_puddle_collision(trail_rect) is False

        # Permanent map-placed 'v' puddle remains intact and active
        assert map_puddle in state.world.interactables
        assert state.world.has_puddle_collision(map_rect) is True
    finally:
        state.shutdown_save_worker(timeout=1.0)


def test_frozen_peaks_stratum_variants_preserve_base_pixel_and_texture():
    """Verify _build_frozen_peaks_stratum_variant preserves (1, 1) == s_base on v_idx == 0 and adds detail."""
    ts = constants.TILE_SIZE
    pal = constants.BIOME_PALETTES["frozen_peaks"]
    strata = pal["strata"]

    for s_idx, (s_base, _s_alt) in enumerate(strata):
        variants = [
            Renderer._build_frozen_peaks_stratum_variant(ts, s_idx, v_idx, s_base)
            for v_idx in range(4)
        ]
        assert variants[0].get_at((1, 1))[:3] == s_base
        raw_bytes = [pygame.image.tostring(v, "RGB") for v in variants]
        assert len(set(raw_bytes)) == 4

    # Stratum 0 (Deep Mirror-Glacier Ice) contains suspended dark script columns
    glacier_base = strata[0][0]
    glacier_v0 = Renderer._build_frozen_peaks_stratum_variant(ts, 0, 0, glacier_base)
    script_ink = Renderer._shift_rgb_clamped(glacier_base, -18, -32, -46)
    ink_hits = sum(
        1 for y in range(ts) for x in range(ts) if glacier_v0.get_at((x, y))[:3] == script_ink
    )
    assert ink_hits >= 10, "Expected suspended frozen Archivist script strokes in Stratum 0 mirror-glacier tile"


def test_frozen_peaks_props_generate_preload_and_dispatch(monkeypatch):
    """Verify glacier monolith & rime cask sprites exist, preload, and dispatch in frozen_peaks."""
    monolith_path = os.path.join("assets", "graphics", "frozen_script_monolith.png")
    cask_path = os.path.join("assets", "graphics", "frozen_rime_cask.png")
    assert os.path.exists(monolith_path), f"Missing generated asset: {monolith_path}"
    assert os.path.exists(cask_path), f"Missing generated asset: {cask_path}"

    assert pygame.image.load(monolith_path).get_size() == (40, 60)
    assert pygame.image.load(cask_path).get_size() == (40, 40)

    gen_monolith = generate_frozen_script_monolith()
    gen_cask = generate_frozen_rime_cask()
    assert gen_monolith.get_size() == (40, 60) and gen_monolith.get_at((0, 0)).a == 0
    assert gen_cask.get_size() == (40, 40) and gen_cask.get_at((0, 0)).a == 0

    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)
    assert "FrozenScriptMonolith" in renderer.prop_cache
    assert renderer.prop_cache["FrozenScriptMonolith"].get_size() == (40, 60)
    assert "FrozenRimeCask" in renderer.prop_cache
    assert renderer.prop_cache["FrozenRimeCask"].get_size() == (40, 40)

    state = GameState(auto_load=False)
    state.network_manager.stop_network()
    try:
        state.world = World("frozen_peaks")
        state.world.load_from_prototype(["." * 12 for _ in range(12)])
        state.player.x = 120.0
        state.player.y = 120.0
        state.camera.instant_center((160.0, 160.0))

        monolith_obj = GameObject((160, 160), (40, 40))
        monolith_obj.name = "Structure"
        monolith_obj.is_solid = True

        cask_obj = GameObject((200, 160), (40, 40))
        cask_obj.name = "Barrel"
        cask_obj.is_solid = True
        cask_obj.is_breakable = True
        state.world.interactables = [monolith_obj, cask_obj]

        dispatched = []
        orig_monolith = renderer._draw_frozen_script_monolith
        orig_cask = renderer._draw_frozen_rime_cask

        def _spy_monolith(*args, **kwargs):
            dispatched.append("monolith")
            return orig_monolith(*args, **kwargs)

        def _spy_cask(*args, **kwargs):
            dispatched.append("cask")
            return orig_cask(*args, **kwargs)

        monkeypatch.setattr(renderer, "_draw_frozen_script_monolith", _spy_monolith)
        monkeypatch.setattr(renderer, "_draw_frozen_rime_cask", _spy_cask)

        renderer.render(state)
        assert "monolith" in dispatched
        assert "cask" in dispatched
    finally:
        state.shutdown_save_worker(timeout=1.0)


def test_frozen_peaks_snow_atmosphere_masks_active_rain_zones():
    """Verify draw_frozen_peaks_atmosphere renders snow only on frozen_peaks and skips active rain zones."""
    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)
    state = GameState(auto_load=False)
    state.network_manager.stop_network()
    try:
        # 1. Non-frozen biome -> no-op
        state.world = World("pastoral_valley")
        state.world.load_from_prototype(["." * 10 for _ in range(10)])
        state.player.x, state.player.y = 80.0, 80.0
        state.bleed_state = "GRACE_PERIOD"
        renderer._fx_surface_cache.clear()
        renderer.draw_frozen_peaks_atmosphere(state, 0.0, 0.0, now=2.0)
        assert not any(k[0] == "frozen_snowflake" for k in renderer._fx_surface_cache)

        # Switch to frozen_peaks
        state.world = World("frozen_peaks")
        state.world.load_from_prototype(["." * 10 for _ in range(10)])
        state.player.x, state.player.y = 80.0, 80.0

        # 2. Global rain (DILUTION) -> skip snow completely
        state.bleed_state = "DILUTION"
        state.weather_manager.bleed_state = "DILUTION"
        renderer._fx_surface_cache.clear()
        screen.fill((0, 0, 0))
        renderer.draw_frozen_peaks_atmosphere(state, 0.0, 0.0, now=2.0)
        assert not any(k[0] == "frozen_snowflake" for k in renderer._fx_surface_cache)

        # 3. Storm rain active: viewport completely OUTSIDE safe circle -> zero snowflakes drawn
        state.bleed_state = "SHRINKING"
        state.weather_manager.bleed_state = "SHRINKING"
        state.weather_manager.paused = False
        state.world.boss_coords_list = [{"x": 500, "y": 500}]
        state.weather_manager.set_boss_coords_list([{"x": 500, "y": 500}])
        state.weather_manager.active_safe_radius = 120.0
        state.active_safe_radius = 120.0
        state.current_boss_coords = {"x": 500, "y": 500}
        renderer._fx_surface_cache.clear()
        screen.fill((0, 0, 0))
        renderer.draw_frozen_peaks_atmosphere(state, 0.0, 0.0, now=2.0)
        assert not any(k[0] == "frozen_snowflake" for k in renderer._fx_surface_cache)
        assert pygame.image.tostring(screen, "RGB") == b"\x00" * (
            constants.SCREEN_WIDTH * constants.SCREEN_HEIGHT * 3
        )

        # 4. Storm rain active: viewport INSIDE safe circle -> snowflakes render & cache
        state.world.boss_coords_list = [{"x": 10, "y": 8}]
        state.weather_manager.set_boss_coords_list([{"x": 10, "y": 8}])
        state.current_boss_coords = {"x": 10, "y": 8}
        state.weather_manager.active_safe_radius = 1200.0
        state.active_safe_radius = 1200.0
        renderer._fx_surface_cache.clear()
        screen.fill((0, 0, 0))
        renderer.draw_frozen_peaks_atmosphere(state, 0.0, 0.0, now=2.0)
        assert any(k[0] == "frozen_snowflake" for k in renderer._fx_surface_cache)
        assert pygame.image.tostring(screen, "RGB") != b"\x00" * (
            constants.SCREEN_WIDTH * constants.SCREEN_HEIGHT * 3
        )
    finally:
        state.shutdown_save_worker(timeout=1.0)
