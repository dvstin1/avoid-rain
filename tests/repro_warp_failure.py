
import pytest
from engine.game_state import GameState
from engine.world import WarpPortal
from engine.maps import create_world

def test_sanctuary_to_macro_warp():
    """Simulate warping from Sanctuary to macro_world."""
    # 1. Start in Sanctuary
    state = GameState(auto_load=False)
    state.world = create_world("sanctuary")
    
    # 2. Find the Chronicle WarpPortal
    chronicle = next((obj for obj in state.world.interactables if obj.name == "The Chronicle"), None)
    assert chronicle is not None, "Chronicle not found in Sanctuary"
    assert chronicle.target_name == "macro_world"
    
    # 3. Execute interaction
    print("\n--- Starting Warp Interaction ---")
    chronicle.execute_interaction(state)
    print("--- Warp Interaction Finished ---\n")
    
    # 4. Verify results
    assert state.world.name == "world_map1", f"World name should be world_map1, got {state.world.name}"
    # Check if grid is populated (not a blank world)
    assert len(state.world.grid) > 0
    assert len(state.world.grid[0]) > 0
    
    print(f"Success: Warped to {state.world.name} at ({state.player.x}, {state.player.y})")

if __name__ == "__main__":
    test_sanctuary_to_macro_warp()
