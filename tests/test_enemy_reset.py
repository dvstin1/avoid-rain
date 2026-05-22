"""
Regression test for the Enemy Population Reset Lifecycle Fix.
Ensures that enemies are re-instantiated fresh when a room is loaded via warp or run reset.
"""
from engine.game_state import GameState
from engine.maps import create_world

def test_enemy_repopulation_on_warp():
    # 1. Start in Sanctuary
    gs = GameState(auto_load=False)
    assert gs.world.name == "sanctuary"
    assert len(gs.enemies) == 0
    
    # 2. Warp to Chapter 1
    gs.world = create_world("chapter1")
    # According to our updated parse_map, enemies should be populated from the prototype
    gs.enemies = gs.world.enemies
    assert len(gs.enemies) > 0
    
    # 3. "Kill" an enemy (manually remove from active list)
    initial_enemy_count = len(gs.enemies)
    enemy_to_kill = gs.enemies[0]
    gs.enemies.remove(enemy_to_kill)
    assert len(gs.enemies) == initial_enemy_count - 1
    
    # 4. Warp back to Sanctuary (enemies should be cleared)
    gs.world = create_world("sanctuary")
    gs.enemies = gs.world.enemies
    assert len(gs.enemies) == 0
    
    # 5. Warp back to Chapter 1 (enemies should be FRESH)
    gs.world = create_world("chapter1")
    gs.enemies = gs.world.enemies
    assert len(gs.enemies) == initial_enemy_count
    # Verify they are fresh instances (not the same object ID as the one we "killed")
    for enemy in gs.enemies:
        assert enemy is not enemy_to_kill

def test_enemy_repopulation_on_respawn():
    gs = GameState(auto_load=False)
    # Start in Chapter 1
    gs.world = create_world("chapter1")
    gs.enemies = gs.world.enemies
    initial_count = len(gs.enemies)
    
    # Remove all enemies
    gs.enemies = []
    
    # Trigger respawn (which calls create_world("sanctuary"))
    gs.respawn_player()
    assert gs.world.name == "sanctuary"
    assert len(gs.enemies) == 0
    
    # Warp back to Chapter 1
    gs.world = create_world("chapter1")
    gs.enemies = gs.world.enemies
    assert len(gs.enemies) == initial_count
