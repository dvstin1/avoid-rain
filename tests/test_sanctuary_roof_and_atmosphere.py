"""Unit tests for Pass 3: Roof Overhangs, Interior/Exterior Fade & Courtyard Micro-Animations.

Verifies sanctuary_interior_alpha interpolation and non-Sanctuary reset, Scriptorium roof
concealment outside vs. exterior blackout mask inside, permanently opaque locked shed roof,
independent per-prop candelabra flicker, and pond ripples / drifting courtyard fireflies.
"""
# pylint: disable=no-member,protected-access

import pygame

import constants
from engine.game_state import GameState
from engine.stats import StatisticsTracker
from rendering.renderer import Renderer


def _make_sanctuary_pair():
    """Create a real-surface Renderer and headless Sanctuary GameState."""
    pygame.init()
    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)
    state = GameState(auto_load=False, stats=StatisticsTracker())
    state.network_manager.stop_network()
    return screen, renderer, state


def test_sanctuary_interior_alpha_interpolation_and_non_sanctuary_reset():
    """Verify smooth dt interpolation when entering/exiting Scriptorium and reset outside Sanctuary."""
    _, renderer, state = _make_sanctuary_pair()
    try:
        assert renderer.sanctuary_interior_alpha == 0.0

        # Player spawns inside Scriptorium interior (38, 14)
        assert Renderer._is_player_inside_scriptorium(state) is True
        alpha_1 = renderer.update_sanctuary_interior_alpha(state, 0.1)
        assert abs(alpha_1 - constants.SANCTUARY_INTERIOR_FADE_SPEED * 0.1) < 1e-6

        # Stepping further clamps cleanly at 1.0
        alpha_full = renderer.update_sanctuary_interior_alpha(state, 1.0)
        assert alpha_full == 1.0

        # Move player out into west courtyard (15, 24) -> fades smoothly back to 0.0
        state.player.x = 15.0 * constants.TILE_SIZE
        state.player.y = 24.0 * constants.TILE_SIZE
        assert Renderer._is_player_inside_scriptorium(state) is False
        alpha_mid = renderer.update_sanctuary_interior_alpha(state, 0.1)
        assert abs(alpha_mid - (1.0 - constants.SANCTUARY_INTERIOR_FADE_SPEED * 0.1)) < 1e-6
        assert renderer.update_sanctuary_interior_alpha(state, 1.0) == 0.0

        # Move back inside to reach 1.0, then leave Sanctuary -> immediate reset to 0.0
        state.player.x = 38.0 * constants.TILE_SIZE
        state.player.y = 14.0 * constants.TILE_SIZE
        assert renderer.update_sanctuary_interior_alpha(state, 1.0) == 1.0
        state.world.name = "generated_world"
        assert renderer.update_sanctuary_interior_alpha(state, 0.016) == 0.0
        assert renderer.sanctuary_interior_alpha == 0.0
    finally:
        state.shutdown_save_worker(timeout=1.0)


def test_scriptorium_roof_outside_vs_exterior_blackout_inside():
    """Verify outside draws opaque Scriptorium roof + chimney and inside blacks out exterior courtyard."""
    screen, renderer, state = _make_sanctuary_pair()
    try:
        ts = constants.TILE_SIZE
        # Center camera on west Scriptorium wall (x=28, y=14) so both courtyard (x=22) and interior (x=35) are visible
        cam_x, cam_y = 28 * ts, 14 * ts
        state.camera.instant_center((cam_x, cam_y))
        ox, oy = state.camera.get_offset()

        # Sample screen positions: courtyard tile (22, 14) and interior floor tile (35, 14)
        ext_pt = (int(22 * ts + 20 - ox), int(14 * ts + 20 - oy))
        int_pt = (int(35 * ts + 20 - ox), int(14 * ts + 20 - oy))

        # 1. Outside (interior_alpha = 0.0): courtyard bright, Scriptorium interior concealed by slate roof
        screen.fill((120, 110, 100))
        renderer.sanctuary_interior_alpha = 0.0
        renderer.draw_sanctuary_roofs_and_blackout(state, ox, oy)
        ext_outside = screen.get_at(ext_pt)[:3]
        int_outside = screen.get_at(int_pt)[:3]
        assert ext_outside == (120, 110, 100), "Courtyard should not be blacked out when outside"
        assert int_outside != (120, 110, 100), "Scriptorium interior should be covered by roof when outside"
        assert int_outside[2] >= int_outside[0] and sum(int_outside) < 280, (
            f"Expected dark slate roof over Scriptorium, got {int_outside}"
        )

        # 2. Inside (interior_alpha = 1.0): Scriptorium interior unobstructed, courtyard blacked out
        screen.fill((120, 110, 100))
        renderer.sanctuary_interior_alpha = 1.0
        renderer.draw_sanctuary_roofs_and_blackout(state, ox, oy)
        ext_inside = screen.get_at(ext_pt)[:3]
        int_inside = screen.get_at(int_pt)[:3]
        assert int_inside == (120, 110, 100), "Scriptorium interior must stay brightly unobstructed when inside"
        assert sum(ext_inside) < 60, f"Expected exterior courtyard darkened by blackout mask, got {ext_inside}"
    finally:
        state.shutdown_save_worker(timeout=1.0)


def test_locked_shed_roof_stays_opaque():
    """Verify permanently locked northwest shed_roof renders opaque slate over its 5x5 footprint."""
    screen, renderer, state = _make_sanctuary_pair()
    try:
        ts = constants.TILE_SIZE
        state.camera.instant_center((8 * ts, 8 * ts))
        ox, oy = state.camera.get_offset()
        shed_center = (int(6 * ts + 20 - ox), int(6 * ts + 20 - oy))

        screen.fill((200, 180, 160))
        renderer.sanctuary_interior_alpha = 0.0
        renderer.draw_sanctuary_roofs_and_blackout(state, ox, oy)
        shed_px = screen.get_at(shed_center)[:3]
        assert shed_px != (200, 180, 160), "Locked shed roof was not rendered"
        assert shed_px[2] >= shed_px[0] and sum(shed_px) < 280, (
            f"Expected opaque dark slate over locked shed, got {shed_px}"
        )
    finally:
        state.shutdown_save_worker(timeout=1.0)


def test_independent_candelabra_flicker_and_courtyard_micro_animations():
    """Verify independent candelabra flicker phases and pond ripples + courtyard fireflies."""
    screen, renderer, state = _make_sanctuary_pair()
    try:
        # 1. Independent candelabra flicker across distinct positions and over time
        c1_t0 = Renderer._compute_candelabra_flicker(1.0, 32 * 40, 9 * 40)
        c2_t0 = Renderer._compute_candelabra_flicker(1.0, 38 * 40, 9 * 40)
        c1_t1 = Renderer._compute_candelabra_flicker(1.35, 32 * 40, 9 * 40)
        assert c1_t0 != c2_t0 or c1_t0 != c1_t1
        for rad, alpha in (c1_t0, c2_t0, c1_t1):
            assert 16 <= rad <= 48
            assert 20 <= alpha <= 140

        # 2. Pond ripples and courtyard fireflies draw when outside (interior_alpha < 0.95)
        ts = constants.TILE_SIZE
        state.player.x = 18.0 * ts
        state.player.y = 24.0 * ts
        state.camera.instant_center((12 * ts, 24 * ts))
        ox, oy = state.camera.get_offset()

        screen.fill((20, 40, 50))
        before_bytes = pygame.image.tobytes(screen, "RGB")
        renderer.sanctuary_interior_alpha = 0.0
        renderer.draw_sanctuary_courtyard_atmosphere(state, ox, oy, now=2.5)
        after_outside = pygame.image.tobytes(screen, "RGB")
        assert after_outside != before_bytes, "Expected pond ripples and fireflies to render in Sanctuary courtyard"
        assert any(k[0] == "pond_ripple" for k in renderer._fx_surface_cache)
        assert any(k[0] == "firefly_mote" for k in renderer._fx_surface_cache)

        # 3. Skipped when fully inside Scriptorium (interior_alpha >= 0.95)
        screen.fill((20, 40, 50))
        renderer.sanctuary_interior_alpha = 1.0
        renderer.draw_sanctuary_courtyard_atmosphere(state, ox, oy, now=2.5)
        after_inside = pygame.image.tobytes(screen, "RGB")
        assert after_inside == before_bytes

        # 4. Full render() integration smoke test (both inside and outside)
        renderer.sanctuary_interior_alpha = 0.0
        renderer.render(state)
        state.player.x = 38.0 * ts
        state.player.y = 14.0 * ts
        renderer.update_sanctuary_interior_alpha(state, 1.0)
        renderer.render(state)
    finally:
        state.shutdown_save_worker(timeout=1.0)
