"""Unit tests for Tech Tower Pass 2: cyber-archival props and Sky Citadel atmosphere."""
# pylint: disable=wrong-import-position,wrong-import-order,no-member,protected-access

import os

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame
import pytest

import constants
from engine.game_state import GameState
from engine.world import GameObject
from generate_assets import generate_tech_canister, generate_tech_server_pylon
from rendering.renderer import Renderer


@pytest.fixture(scope="module", autouse=True)
def init_pygame():
    """Initialize and cleanly tear down pygame in headless dummy mode."""
    pygame.init()
    yield
    pygame.quit()


def test_tech_tower_prop_assets_exist_and_preload():
    """Verify tech_server_pylon.png (40x60) & tech_canister.png (40x40) exist, generate cleanly, and preload."""
    pylon_path = os.path.join("assets", "graphics", "tech_server_pylon.png")
    canister_path = os.path.join("assets", "graphics", "tech_canister.png")
    assert os.path.exists(pylon_path), f"Missing generated asset: {pylon_path}"
    assert os.path.exists(canister_path), f"Missing generated asset: {canister_path}"

    assert pygame.image.load(pylon_path).get_size() == (40, 60)
    assert pygame.image.load(canister_path).get_size() == (40, 40)

    gen_pylon = generate_tech_server_pylon(40, 60)
    gen_canister = generate_tech_canister(40, 40)
    assert gen_pylon.get_size() == (40, 60)
    assert gen_canister.get_size() == (40, 40)
    assert gen_pylon.get_at((0, 0)).a == 0
    assert gen_canister.get_at((0, 0)).a == 0

    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)
    assert "TechServerPylon" in renderer.prop_cache
    assert renderer.prop_cache["TechServerPylon"].get_size() == (40, 60)
    assert "tech_server_pylon.png" in renderer.image_cache

    assert "TechCanister" in renderer.prop_cache
    assert renderer.prop_cache["TechCanister"].get_size() == (40, 40)
    assert "tech_canister.png" in renderer.image_cache


def test_tech_tower_structure_renders_server_pylon_and_preserves_ruins():
    """Verify 'T' Structure in tech_tower renders TechServerPylon at y-20 (with fallback) and ruins keeps rubble."""
    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)
    state = GameState(auto_load=False)
    state.network_manager.stop_network()
    try:
        ts = constants.TILE_SIZE
        state.world.name = "tech_tower"
        state.world.load_from_prototype(["........" for _ in range(8)])
        struct = GameObject((4 * ts, 4 * ts), (ts, ts))
        struct.name = "Structure"
        struct.is_solid = True
        state.world.interactables = [struct]
        state.player.x = 2.0 * ts
        state.player.y = 4.0 * ts
        state.camera.instant_center((4 * ts, 4 * ts))

        # 1. Sprite path in full render caches ground shadow and draws TechServerPylon
        renderer.render(state)
        assert any(k[0] == "tech_server_pylon_shadow" for k in renderer._fx_surface_cache)

        # Direct helper check: 40x60 monolith extends 20px above base tile (sy - 20)
        canvas = pygame.Surface((160, 160))
        canvas.fill((14, 18, 26))
        renderer.screen = canvas
        renderer._draw_tech_server_pylon(60, 60, renderer.prop_cache)
        upper_col = canvas.get_at((80, 48))[:3]  # Inside upper chassis (y = 60 - 20 + 8 = 48)
        assert upper_col != (14, 18, 26), "TechServerPylon should anchor 20px above base tile"

        # 2. Procedural fallback path when TechServerPylon PNG is absent
        canvas.fill((14, 18, 26))
        renderer._draw_tech_server_pylon(60, 60, {})
        fallback_upper = canvas.get_at((80, 50))[:3]
        assert fallback_upper != (14, 18, 26), "Procedural server pylon fallback should draw monolith"

        # 3. Ruins biome must keep routing 'T' Structure to RuinsRubble, not TechServerPylon
        renderer.screen = screen
        renderer._fx_surface_cache.clear()
        state.world.name = "ruins"
        rubble_sentinel = pygame.Surface((ts, ts), pygame.SRCALPHA)
        rubble_sentinel.fill((212, 64, 188, 255))
        renderer.prop_cache["RuinsRubble"] = rubble_sentinel
        renderer.render(state)
        assert not any(k[0] == "tech_server_pylon_shadow" for k in renderer._fx_surface_cache)
        ox, oy = state.camera.get_offset()
        px_check = int(struct.x - ox + ts // 2)
        py_check = int(struct.y - oy + ts // 2)
        assert screen.get_at((px_check, py_check))[:3] == (212, 64, 188)
    finally:
        state.shutdown_save_worker(timeout=1.0)


def test_tech_tower_barrel_renders_tech_canister_and_preserves_other_biomes():
    """Verify Barrel in tech_tower uses TechCanister (with fallback), while other biomes keep barrel_0.png."""
    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)
    state = GameState(auto_load=False)
    state.network_manager.stop_network()
    try:
        ts = constants.TILE_SIZE
        state.world.name = "tech_tower"
        state.world.load_from_prototype(["........" for _ in range(8)])
        barrel = GameObject((4 * ts, 4 * ts), (ts, ts))
        barrel.name = "Barrel"
        barrel.is_solid = True
        state.world.interactables = [barrel]
        state.player.x = 2.0 * ts
        state.player.y = 4.0 * ts
        state.camera.instant_center((4 * ts, 4 * ts))

        # Sentinel sprites distinguish TechCanister vs barrel_0.png
        canister_sentinel = pygame.Surface((ts, ts), pygame.SRCALPHA)
        canister_sentinel.fill((36, 210, 232, 255))
        barrel_sentinel = pygame.Surface((ts, ts), pygame.SRCALPHA)
        barrel_sentinel.fill((164, 108, 44, 255))
        renderer.prop_cache["TechCanister"] = canister_sentinel
        renderer.image_cache["barrel_0.png"] = barrel_sentinel

        # 1. tech_tower renders TechCanister
        renderer.render(state)
        ox, oy = state.camera.get_offset()
        cx = int(barrel.x - ox + ts // 2)
        cy = int(barrel.y - oy + ts // 2)
        # Check non-zero cyan dominance (atmosphere overlay may subtly tint over it)
        col_tech = screen.get_at((cx, cy))[:3]
        assert col_tech[2] > 180 and col_tech[0] < 100, f"Expected TechCanister sentinel, got {col_tech}"

        # 2. Procedural fallback path when TechCanister PNG is absent
        canvas = pygame.Surface((120, 120))
        canvas.fill((12, 16, 24))
        renderer.screen = canvas
        renderer._draw_tech_canister(40, 40, barrel, {})
        assert canvas.get_at((60, 58))[:3] != (12, 16, 24), "Procedural canister fallback should render gauge"

        # 3. Other biomes retain barrel_0.png
        renderer.screen = screen
        state.world.name = "windy_ridge"
        renderer.render(state)
        col_other = screen.get_at((cx, cy))[:3]
        assert col_other[0] > 130 and col_other[2] < 90, f"Expected barrel_0.png sentinel, got {col_other}"
    finally:
        state.shutdown_save_worker(timeout=1.0)


def test_tech_tower_atmosphere_draws_shimmer_and_data_dust_only_on_tech_tower():
    """Verify draw_tech_tower_atmosphere draws cached shimmer (alpha 22..36) & data motes only on tech_tower."""
    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)
    state = GameState(auto_load=False)
    state.network_manager.stop_network()
    try:
        ts = constants.TILE_SIZE
        state.world.name = "tech_tower"
        state.world.load_from_prototype(["......" for _ in range(6)])
        state.player.x = 2.0 * ts
        state.player.y = 2.0 * ts

        screen.fill((16, 22, 32))
        before = pygame.image.tobytes(screen, "RGB")
        renderer.draw_tech_tower_atmosphere(state, 0, 0, now=3.2)
        after = pygame.image.tobytes(screen, "RGB")
        assert after != before, "Expected shimmer beams and data-dust motes to draw on tech_tower"

        shimmer_keys = [k for k in renderer._fx_surface_cache if k[0] == "tech_tower_shimmer"]
        mote_keys = [k for k in renderer._fx_surface_cache if k[0] == "tech_tower_data_mote"]
        assert shimmer_keys, "Expected cached tech_tower_shimmer surfaces"
        assert mote_keys, "Expected cached tech_tower_data_mote surfaces"
        for _, _, _, alpha, _ in shimmer_keys:
            assert 22 <= alpha <= 36
        # Both pale cyan and muted magenta motes should be cached
        mote_colors = {k[1] for k in mote_keys}
        assert mote_colors == {False, True}

        # Non-tech_tower biomes must be a no-op
        for other_biome in ("windy_ridge", "sanctuary"):
            state.world.name = other_biome
            screen.fill((16, 22, 32))
            renderer.draw_tech_tower_atmosphere(state, 0, 0, now=3.2)
            assert pygame.image.tobytes(screen, "RGB") == before
    finally:
        state.shutdown_save_worker(timeout=1.0)
