"""
Unit tests for the stylized "Ink & Fog Warp" cinematic transit sequence.
Tests verify the three-stage transition state machine (DEPARTURE, THE_VEIL, ARRIVAL),
fog puff expansion/evaporation, typographic glyph swirls/dispersal, player alpha fading,
coordinate re-anchoring, camera snapping, and input locking.
"""
# pylint: disable=redefined-outer-name,unused-variable,protected-access,no-member
import pytest
import pygame
from engine.game_state import GameState
from engine.warp_controller import WarpFogPuff, WarpGlyph
from engine.world import WarpPortal
from constants import (
    WARP_STAGE_IDLE,
    WARP_STAGE_DEPARTURE,
    WARP_STAGE_THE_VEIL,
    WARP_STAGE_ARRIVAL,
    WARP_DEPARTURE_FRAMES,
    WARP_VEIL_FRAMES,
    WARP_ARRIVAL_FRAMES,
    WARP_FOG_PUFF_COUNT,
    WARP_GLYPH_COUNT,
    WARP_GLYPH_POOL,
)
from rendering.renderer import Renderer


@pytest.fixture
def game_state():
    """Create a clean GameState without auto-loading save data."""
    gs = GameState(auto_load=False)
    return gs


@pytest.fixture
def mock_renderer():
    """Create a Renderer with a test surface."""
    pygame.init()
    surf = pygame.Surface((800, 600))
    return Renderer(surf)


def test_warp_initial_state(game_state):
    """Verify warp controller starts in IDLE and doesn't block gameplay."""
    wc = game_state.warp_controller
    assert wc.stage == WARP_STAGE_IDLE
    assert not wc.is_active()
    assert not wc.blocks_input()
    assert not wc.blocks_enemy_updates()
    assert wc.veil_alpha == 0
    assert len(wc.fog_puffs) == 0
    assert len(wc.glyph_particles) == 0


def test_warp_start_spawns_fog_and_glyphs(game_state):
    """Verify start_warp populates fog cloud puffs and manuscript glyph swirls."""
    wc = game_state.warp_controller
    portal = WarpPortal("sanctuary", 100, 200, (0, 0, 40, 40))

    success = wc.start_warp(game_state.player, portal)
    assert success is True
    assert wc.stage == WARP_STAGE_DEPARTURE
    assert wc.is_active() is True
    assert wc.blocks_input() is True
    assert wc.blocks_enemy_updates() is True

    # Fog cloud puffs
    assert len(wc.fog_puffs) == WARP_FOG_PUFF_COUNT
    for puff in wc.fog_puffs:
        assert isinstance(puff, WarpFogPuff)
        assert puff.base_radius > 0

    # Typographic manuscript glyph particles
    assert len(wc.glyph_particles) == WARP_GLYPH_COUNT
    for glyph in wc.glyph_particles:
        assert isinstance(glyph, WarpGlyph)
        assert glyph.glyph in WARP_GLYPH_POOL
        assert glyph.alpha == 255


def test_stage_1_departure_fading_and_blooming(game_state):
    """Verify player alpha fades to 0 and fog blooms during Stage 1: DEPARTURE."""
    wc = game_state.warp_controller
    portal = WarpPortal("sanctuary", 100, 200, (0, 0, 40, 40))
    wc.start_warp(game_state.player, portal)

    initial_alpha = game_state.player.alpha
    assert initial_alpha == 255

    # Advance halfway through Departure
    half_departure_dt = (WARP_DEPARTURE_FRAMES * 0.5) / 60.0
    wc.update(half_departure_dt, game_state)
    assert wc.stage == WARP_STAGE_DEPARTURE
    assert 0 < game_state.player.alpha < 255
    assert wc.veil_alpha == 0

    # Fog puffs should have expanded
    for puff in wc.fog_puffs:
        assert puff.radius > puff.base_radius * 0.2
        assert puff.alpha > 0

    # Advance to end of Departure -> transitions to THE_VEIL
    remaining_dt = (WARP_DEPARTURE_FRAMES * 0.55) / 60.0
    wc.update(remaining_dt, game_state)
    assert wc.stage == WARP_STAGE_THE_VEIL
    assert game_state.player.alpha == 0


def test_stage_2_the_veil_transfer_and_reanchoring(game_state):
    """Verify full-screen veil fade to 100%, map swap, camera snap, and particle re-anchoring."""
    wc = game_state.warp_controller
    start_x, start_y = game_state.player.get_center()

    dest_x, dest_y = 500.0, 700.0
    portal = WarpPortal("sanctuary", dest_x, dest_y, (0, 0, 40, 40))
    wc.start_warp(game_state.player, portal)

    # Step past Departure into The Veil
    dep_dt = (WARP_DEPARTURE_FRAMES + 1.0) / 60.0
    wc.update(dep_dt, game_state)
    assert wc.stage == WARP_STAGE_THE_VEIL

    # Advance through The Veil to trigger map transfer
    veil_step_dt = (WARP_VEIL_FRAMES * 0.6) / 60.0
    wc.update(veil_step_dt, game_state)

    assert wc.veil_alpha > 0
    assert wc.transfer_executed is True

    # Camera must snap to destination
    new_cx, new_cy = game_state.player.get_center()
    target_ox, target_oy = game_state.camera.get_target_offset((new_cx, new_cy))
    assert game_state.camera.offset_x == pytest.approx(target_ox, abs=2.0)
    assert game_state.camera.offset_y == pytest.approx(target_oy, abs=2.0)

    # Step past The Veil into Arrival
    for _ in range(int(WARP_VEIL_FRAMES) + 2):
        wc.update(0.016, game_state)
    assert wc.stage == WARP_STAGE_ARRIVAL


def test_stage_3_arrival_unveiling_and_restore(game_state):
    """Verify veil clearing, player alpha restoring to 100%, and input unlocking."""
    wc = game_state.warp_controller
    portal = WarpPortal("sanctuary", 100, 100, (0, 0, 40, 40))
    wc.start_warp(game_state.player, portal)

    # Step through Departure and The Veil into Arrival
    for _ in range(int(WARP_DEPARTURE_FRAMES + WARP_VEIL_FRAMES) + 4):
        wc.update(0.016, game_state)
    assert wc.stage == WARP_STAGE_ARRIVAL

    # In Arrival, player alpha restores
    for _ in range(int(WARP_ARRIVAL_FRAMES * 0.5)):
        wc.update(0.016, game_state)
    assert game_state.player.alpha > 0

    # Advance past Arrival -> complete transition
    for _ in range(int(WARP_ARRIVAL_FRAMES * 0.7)):
        wc.update(0.016, game_state)

    assert wc.stage == WARP_STAGE_IDLE
    assert not wc.is_active()
    assert not wc.blocks_input()
    assert game_state.player.alpha == 255
    assert len(wc.fog_puffs) == 0
    assert len(wc.glyph_particles) == 0


def test_game_state_update_locks_input_and_movement(game_state):
    """Verify GameState.update blocks player controls and pauses enemies during warp."""
    portal = WarpPortal("sanctuary", 300, 300, (0, 0, 40, 40))
    game_state.start_warp(portal)
    assert game_state.warp_controller.is_active()

    # Attempt to move, attack, and dash while warping
    actions = {'move': (1.0, 1.0), 'attack': True, 'dash': True, 'block': True}
    orig_x, orig_y = game_state.player.x, game_state.player.y

    game_state.update(0.016, actions)

    # Player position must not change from movement
    assert game_state.player.x == orig_x
    assert game_state.player.y == orig_y
    assert game_state.player.vx == 0
    assert game_state.player.vy == 0


def test_renderer_draw_warp_sequence_and_actor_fading(game_state, mock_renderer):
    """Verify renderer draws warp sequence elements and respects player alpha."""
    portal = WarpPortal("sanctuary", 200, 200, (0, 0, 40, 40))
    game_state.start_warp(portal)

    # Advance a few frames so fog blooms and gains alpha
    for _ in range(5):
        game_state.warp_controller.update(0.016, game_state)

    # Render with active warp: must execute and populate puff cache
    mock_renderer.draw_warp_sequence(game_state, 0, 0)
    assert len(mock_renderer._puff_cache) > 0

    # Test actor alpha rendering (dissolved vs partial alpha)
    game_state.player.alpha = 0
    mock_renderer.draw_actor_ghost(game_state.player, 0, 0, game_state)

    game_state.player.alpha = 128
    mock_renderer.draw_actor_ghost(game_state.player, 0, 0, game_state)

    game_state.player.alpha = 255
    mock_renderer.draw_actor_ghost(game_state.player, 0, 0, game_state)
