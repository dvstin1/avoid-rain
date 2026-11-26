# copyright 2026 Dustin Massop, License: GPLv2
"""Unit tests for Windy Ridge Pass 2: Highland Monolith, gale atmosphere, and dark-enemy contrast."""
# pylint: disable=wrong-import-position,wrong-import-order,no-member,protected-access

import os
from types import SimpleNamespace

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame
import pytest

import constants
from engine.enemy import SlugEnemy, SmearEnemy
from engine.game_state import GameState
from engine.world import GameObject
from rendering.renderer import Renderer


@pytest.fixture(scope="module", autouse=True)
def init_pygame():
    """Initialize and cleanly tear down pygame in headless dummy mode."""
    pygame.init()
    yield
    pygame.quit()


def test_highland_monolith_asset_exists_and_preloads():
    """Verify assets/graphics/highland_monolith.png exists at 40x60 SRCALPHA and preloads in Renderer."""
    path = os.path.join("assets", "graphics", "highland_monolith.png")
    assert os.path.exists(path), f"Missing generated asset: {path}"
    loaded = pygame.image.load(path)
    assert loaded.get_size() == (40, 60)

    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)
    assert "HighlandMonolith" in renderer.prop_cache
    assert renderer.prop_cache["HighlandMonolith"].get_size() == (40, 60)
    assert "highland_monolith.png" in renderer.image_cache


def test_windy_ridge_structure_renders_highland_monolith_and_fallback():
    """Verify 'T' Structure in windy_ridge renders HighlandMonolith at y-20 with shadow and procedural fallback."""
    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)
    state = GameState(auto_load=False)
    state.network_manager.stop_network()
    try:
        ts = constants.TILE_SIZE
        state.world.name = "windy_ridge"
        state.world.load_from_prototype(["........" for _ in range(8)])
        struct = GameObject((4 * ts, 4 * ts), (ts, ts))
        struct.name = "Structure"
        struct.is_solid = True
        state.world.interactables = [struct]
        state.player.x = 2.0 * ts
        state.player.y = 4.0 * ts
        state.camera.instant_center((4 * ts, 4 * ts))

        # 1. Sprite path: renders HighlandMonolith + caches ground contact shadow
        renderer.render(state)
        assert any(k[0] == "highland_monolith_shadow" for k in renderer._fx_surface_cache)

        # Verify direct helper anchors the 40x60 monolith cleanly above its 40x40 base tile (sy - 20)
        canvas = pygame.Surface((160, 160))
        canvas.fill((20, 30, 25))
        renderer.screen = canvas
        renderer._draw_highland_monolith(60, 60, renderer.prop_cache)
        upper_col = canvas.get_at((80, 48))[:3]  # Inside upper stone shaft (y = 60 - 20 + 8 = 48)
        assert upper_col != (20, 30, 25), "HighlandMonolith should extend 20px above base tile"

        # 2. Procedural fallback path when HighlandMonolith PNG is absent
        canvas.fill((20, 30, 25))
        renderer._draw_highland_monolith(60, 60, {})
        fallback_upper = canvas.get_at((80, 52))[:3]
        assert fallback_upper != (20, 30, 25), "Procedural monolith fallback should render standing stone"
    finally:
        state.shutdown_save_worker(timeout=1.0)


def test_windy_ridge_atmosphere_draws_wind_ribbons_and_pollen_only_on_ridge():
    """Verify draw_windy_ridge_atmosphere renders cached gale ribbons (alpha 28..44) & pollen only on windy_ridge."""
    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)
    state = GameState(auto_load=False)
    state.network_manager.stop_network()
    try:
        ts = constants.TILE_SIZE
        state.world.name = "windy_ridge"
        state.world.load_from_prototype(["......" for _ in range(6)])
        state.player.x = 2.0 * ts
        state.player.y = 2.0 * ts

        screen.fill((18, 42, 30))
        before = pygame.image.tobytes(screen, "RGB")
        renderer.draw_windy_ridge_atmosphere(state, 0, 0, now=3.2)
        after = pygame.image.tobytes(screen, "RGB")
        assert after != before, "Expected wind ribbons and pollen motes to draw on windy_ridge"

        gust_keys = [k for k in renderer._fx_surface_cache if k[0] == "windy_ridge_gust"]
        pollen_keys = [k for k in renderer._fx_surface_cache if k[0] == "windy_ridge_pollen"]
        assert gust_keys, "Expected cached windy_ridge_gust surfaces"
        assert pollen_keys, "Expected cached windy_ridge_pollen surfaces"
        for _, _, alpha in gust_keys:
            assert 28 <= alpha <= 44

        # Non-windy_ridge biome must be a no-op
        state.world.name = "swamp_mire"
        screen.fill((18, 42, 30))
        renderer.draw_windy_ridge_atmosphere(state, 0, 0, now=3.2)
        assert pygame.image.tobytes(screen, "RGB") == before
    finally:
        state.shutdown_save_worker(timeout=1.0)


def test_slug_and_smear_ground_shadow_and_rim_highlight_on_png_and_procedural_paths(monkeypatch):
    """Verify SlugEnemy and SmearEnemy draw contact shadow and 1px rim arc on both PNG and procedural paths."""
    screen = pygame.Surface((400, 400))
    renderer = Renderer(screen)
    state = SimpleNamespace(debug_text_enabled=False)

    arc_calls = []
    orig_arc = pygame.draw.arc

    def _spy_arc(surf, col, rect, start_ang, stop_ang, width=1):
        if surf is screen:
            arc_calls.append((tuple(col), tuple(rect), width))
        return orig_arc(surf, col, rect, start_ang, stop_ang, width)

    monkeypatch.setattr(pygame.draw, "arc", _spy_arc)

    slug = SlugEnemy(100, 100)
    smear = SmearEnemy(180, 100)
    smear_emp = SmearEnemy(260, 100)
    smear_emp.is_empowered = True

    # 1. Loaded PNG path
    for enemy in (slug, smear, smear_emp):
        arc_calls.clear()
        renderer._fx_surface_cache.clear()
        renderer.draw_actor_ghost(enemy, 0, 0, state)
        assert any(k[0] == "enemy_ground_shadow" for k in renderer._fx_surface_cache), (
            f"Missing ground shadow for PNG {enemy.name}"
        )
        assert any(w == 1 for _, _, w in arc_calls), f"Missing 1px top-rim arc for PNG {enemy.name}"

    # 2. Procedural fallback path (strip slug & smear PNGs from cache)
    for key in list(renderer.image_cache.keys()):
        if key.startswith(("slug", "smear")):
            renderer.image_cache.pop(key, None)

    for enemy in (slug, smear, smear_emp):
        arc_calls.clear()
        renderer._fx_surface_cache.clear()
        renderer.draw_actor_ghost(enemy, 0, 0, state)
        assert any(k[0] == "enemy_ground_shadow" for k in renderer._fx_surface_cache), (
            f"Missing ground shadow for procedural {enemy.name}"
        )
        assert any(w == 1 for _, _, w in arc_calls), f"Missing 1px top-rim arc for procedural {enemy.name}"
