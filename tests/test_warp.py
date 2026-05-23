"""Tests for warp tile behavior and map transition."""
from engine.game_state import GameState
from engine.world import World
from engine.maps import create_world
from constants import TILE_WARP, TILE_EMPTY, TILE_SIZE


def test_warp_interaction_required():
    gs = GameState(auto_load=False)
    # Find warp interactable in the sanctuary
    warp_obj = None
    for obj in gs.world.interactables:
        if hasattr(obj, 'target_name'):
            warp_obj = obj
            break
    assert warp_obj is not None, "No warp portal found in sanctuary"

    # Move player to warp portal
    gs.player.x, gs.player.y = warp_obj.x, warp_obj.y

    # Call update without attack: should NOT warp
    gs.update(0.016, {'move': (0, 0), 'attack': False})
    assert gs.world.name == "sanctuary"

    # Call update WITH attack: should warp
    gs.update(0.016, {'move': (0, 0), 'attack': True})
    assert gs.world.name == "world_map1"

def test_combat_suppression_during_interaction():
    from engine.player import PlayerStateEnum
    gs = GameState(auto_load=False)
    # Find warp interactable in the sanctuary
    warp_obj = None
    for obj in gs.world.interactables:
        if hasattr(obj, 'target_name'):
            warp_obj = obj
            break
    assert warp_obj is not None

    # Move player to warp portal
    gs.player.x, gs.player.y = warp_obj.x, warp_obj.y

    # Update: player should have current_interactable
    gs.update(0.0, {'move': (0, 0), 'attack': False})
    assert gs.player.current_interactable is not None

    # Attack: should trigger interaction and NOT enter ATTACKING state
    gs.update(0.1, {'move': (0, 0), 'attack': True})
    assert gs.player.state != PlayerStateEnum.ATTACKING
