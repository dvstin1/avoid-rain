"""Tests for warp tile behavior and map transition."""
from engine.game_state import GameState
from engine.world import World
from engine.maps import create_world
from constants import TILE_WARP, TILE_EMPTY, TILE_SIZE


def test_warp_interaction_required():
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
    # Place player near warp tile (within interaction margin)
    gs.player.x = wx * TILE_SIZE
    gs.player.y = wy * TILE_SIZE

    # Call update without attack: should NOT warp
    gs.update(0.016, {'move': (0, 0), 'attack': False})
    assert type(gs.world) is World # still sanctuary

    # Call update WITH attack: should warp
    gs.update(0.016, {'move': (0, 0), 'attack': True})
    assert type(gs.world) is not World
    # Player should be at spawn coordinate set by the sanctuary
    assert gs.player.x != wx * TILE_SIZE or gs.player.y != wy * TILE_SIZE

def test_combat_suppression_during_interaction():
    from engine.player import PlayerStateEnum
    gs = GameState(auto_load=False)
    # Move player to warp tile
    warp_x, warp_y = 0, 0
    for y, row in enumerate(gs.world.grid):
        for x, tile in enumerate(row):
            if tile == TILE_WARP:
                warp_x, warp_y = x * TILE_SIZE, y * TILE_SIZE
                break

    gs.player.x, gs.player.y = warp_x, warp_y

    # Update: player should have current_interactable
    gs.update(0.0, {'move': (0, 0), 'attack': False})
    assert gs.player.current_interactable is not None

    # Attack: should trigger interaction and NOT enter ATTACKING state
    gs.update(0.1, {'move': (0, 0), 'attack': True})
    assert gs.player.state != PlayerStateEnum.ATTACKING
