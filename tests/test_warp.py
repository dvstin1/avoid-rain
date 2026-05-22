"""Tests for warp tile behavior and map transition."""
from engine.game_state import GameState
from engine.world import World
from engine.maps import create_world
from constants import TILE_WARP, TILE_EMPTY, TILE_SIZE


def test_warp_transition_to_outside():
    gs = GameState(auto_load=False)
    # Find warp tile coordinates in the sanctuary
    warp_coord = None
    for y in range(len(gs.world.grid)):
        for x in range(len(gs.world.grid[0])):
            if gs.world.grid[y][x] == TILE_WARP:
                warp_coord = (x, y)
                break
        if warp_coord is not None:
            break
    assert warp_coord is not None, "No warp tile found in sanctuary"

    wx, wy = warp_coord
    # Place player centered on warp tile
    gs.player.x = wx * TILE_SIZE
    gs.player.y = wy * TILE_SIZE

    # Call update with zero movement to trigger warp check
    gs.update(0.016, {'move': (0, 0), 'attack': False})

    # After update, world should be an OutsideWorld (create_world('outside'))
    assert type(gs.world) is not World and gs.world is not None
    # Player should be at spawn coordinate set by the sanctuary (near right side)
    assert gs.player.x != wx * TILE_SIZE or gs.player.y != wy * TILE_SIZE
