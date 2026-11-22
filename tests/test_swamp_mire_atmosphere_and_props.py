"""Unit tests for Venomous Mire Pass 2: biomechanical spore pod prop and marsh miasma atmosphere."""
# pylint: disable=wrong-import-position,wrong-import-order,no-member,protected-access

import os

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame
import pytest

import constants
from engine.game_state import GameState
from engine.world import GameObject
from generate_assets import generate_swamp_spore_pod
from rendering.renderer import Renderer


@pytest.fixture(scope="module", autouse=True)
def init_pygame():
    """Initialize and cleanly tear down pygame in headless dummy mode."""
    pygame.init()
    yield
    pygame.quit()


def test_swamp_spore_pod_asset_exists_generates_and_preloads():
    """Verify swamp_spore_pod.png (40x40 SRCALPHA) exists, generates cleanly, preloads, and keeps existing Swamp*."""
    pod_path = os.path.join("assets", "graphics", "swamp_spore_pod.png")
    assert os.path.exists(pod_path), f"Missing generated asset: {pod_path}"
    assert pygame.image.load(pod_path).get_size() == (40, 40)

    gen_pod = generate_swamp_spore_pod(40, 40)
    assert gen_pod.get_size() == (40, 40)
    assert gen_pod.get_flags() & pygame.SRCALPHA != 0
    assert gen_pod.get_at((0, 0)).a == 0

    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)
    assert "SwampSporePod" in renderer.prop_cache
    assert renderer.prop_cache["SwampSporePod"].get_size() == (40, 40)
    assert "swamp_spore_pod.png" in renderer.image_cache

    # Existing Venomous Mire props must remain untouched
    for existing_key in ("SwampFungus", "SwampVent", "SwampThorns", "SwampFlora"):
        assert existing_key in renderer.prop_cache
        assert renderer.prop_cache[existing_key].get_size() == (40, 40)


def test_swamp_mire_barrel_renders_swamp_barrel_fallback_and_preserves_other_biomes():
    """Verify Barrel in swamp_mire renders SwampBarrel (with fallback) while other biomes keep barrel_0.png."""
    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)
    state = GameState(auto_load=False)
    state.network_manager.stop_network()
    try:
        ts = constants.TILE_SIZE
        state.world.name = "swamp_mire"
        state.world.load_from_prototype(["........" for _ in range(8)])
        barrel = GameObject((4 * ts, 4 * ts), (ts, ts))
        barrel.name = "Barrel"
        barrel.is_solid = True
        state.world.interactables = [barrel]
        state.player.x = 2.0 * ts
        state.player.y = 4.0 * ts
        state.camera.instant_center((4 * ts, 4 * ts))

        # Sentinel sprites distinguish SwampBarrel vs wooden barrel_0.png
        swamp_sentinel = pygame.Surface((ts, ts), pygame.SRCALPHA)
        swamp_sentinel.fill((148, 215, 68, 255))
        barrel_sentinel = pygame.Surface((ts, ts), pygame.SRCALPHA)
        barrel_sentinel.fill((176, 98, 42, 255))
        renderer.prop_cache["SwampBarrel"] = swamp_sentinel
        renderer.image_cache["barrel_0.png"] = barrel_sentinel

        # 1. swamp_mire renders SwampBarrel
        renderer.render(state)
        ox, oy = state.camera.get_offset()
        cx = int(barrel.x - ox + ts // 2)
        cy = int(barrel.y - oy + ts // 2)
        col_swamp = screen.get_at((cx, cy))[:3]
        assert col_swamp[1] > 180 and col_swamp[2] < 100, f"Expected SwampBarrel sentinel, got {col_swamp}"

        # 2. Procedural fallback paths when SwampBarrel / SwampSporePod PNGs are absent
        canvas = pygame.Surface((120, 120))
        canvas.fill((14, 10, 20))
        renderer.screen = canvas
        renderer._draw_swamp_barrel(40, 40, barrel, {})
        assert canvas.get_at((60, 58))[:3] != (14, 10, 20), "Procedural swamp barrel fallback should draw barrel"
        canvas.fill((14, 10, 20))
        renderer._draw_swamp_spore_pod(40, 40, barrel, {})
        assert canvas.get_at((60, 58))[:3] != (14, 10, 20), "Procedural spore pod fallback should draw sac"

        # 3. Non-swamp_mire biomes retain barrel_0.png
        renderer.screen = screen
        state.world.name = "windy_ridge"
        renderer.render(state)
        col_other = screen.get_at((cx, cy))[:3]
        assert col_other[0] > 140 and col_other[1] < 120, f"Expected barrel_0.png sentinel, got {col_other}"
    finally:
        state.shutdown_save_worker(timeout=1.0)


def test_swamp_mire_atmosphere_draws_miasma_and_spores_only_on_swamp_mire():
    """Verify draw_swamp_mire_atmosphere draws cached miasma (alpha 20..34) & spores only on swamp_mire."""
    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)
    state = GameState(auto_load=False)
    state.network_manager.stop_network()
    try:
        ts = constants.TILE_SIZE
        state.world.name = "swamp_mire"
        state.world.load_from_prototype(["......" for _ in range(6)])
        state.player.x = 2.0 * ts
        state.player.y = 2.0 * ts

        screen.fill((22, 12, 32))
        before = pygame.image.tobytes(screen, "RGB")
        renderer.draw_swamp_mire_atmosphere(state, 0, 0, now=3.2)
        after = pygame.image.tobytes(screen, "RGB")
        assert after != before, "Expected miasma wisps and rising spore motes to draw on swamp_mire"

        miasma_keys = [k for k in renderer._fx_surface_cache if k[0] == "swamp_mire_miasma"]
        spore_keys = [k for k in renderer._fx_surface_cache if k[0] == "swamp_mire_spore"]
        assert miasma_keys, "Expected cached swamp_mire_miasma surfaces"
        assert spore_keys, "Expected cached swamp_mire_spore surfaces"
        for _, _, _, alpha, _ in miasma_keys:
            assert 20 <= alpha <= 34
        # Both chartreuse and violet miasma wisps & both chartreuse and pale-lilac spores should be cached
        assert {k[4] for k in miasma_keys} == {False, True}
        assert {k[1] for k in spore_keys} == {False, True}

        # Non-swamp_mire biomes must be a no-op
        for other_biome in ("windy_ridge", "tech_tower", "sanctuary"):
            state.world.name = other_biome
            screen.fill((22, 12, 32))
            renderer.draw_swamp_mire_atmosphere(state, 0, 0, now=3.2)
            assert pygame.image.tobytes(screen, "RGB") == before
    finally:
        state.shutdown_save_worker(timeout=1.0)
