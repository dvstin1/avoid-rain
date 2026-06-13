
import pytest
from engine.game_state import GameState
from engine.enemy import SlugEnemy
from constants import SLUG_MAX_HP, PLAYER_MAX_HP

def test_slug_damage_player_and_respawn_on_death():
    gs = GameState(auto_load=False)
    # Ensure stats exist
    from engine.stats import StatisticsTracker
    gs.stats = StatisticsTracker()
    
    # Move away from Sanctuary interactables and walls
    # sanctuary is 40x30 tiles. 1000, 1000 is likely inside the map?
    # Actually, 1000 // 40 = 25. 1000 // 40 = 25.
    # Tile (25, 25) in sanctuary might be a wall or empty.
    
    # Let's put them at a guaranteed safe spot or mock the world
    gs.player.x, gs.player.y = 400, 400
    
    # Place an enemy directly on top of the player
    slug = SlugEnemy(gs.player.x, gs.player.y)
    gs.enemies = [slug]
    
    # Ensure player's HP exists
    gs.player.hp = PLAYER_MAX_HP
    
    # Run multiple updates to cycle from IDLE -> WIND_UP -> STRIKE
    found_damage = False
    for _ in range(50): # More frames to be safe
        # Force positions to stay together in case physics pushes them
        gs.player.x, gs.player.y = 400, 400
        slug.x, slug.y = 400, 400
        
        gs.update(0.1, {})
        if gs.player.hp < PLAYER_MAX_HP:
            found_damage = True
            break
            
    assert found_damage is True
    
    # Kill player to test respawn
    gs.player.hp = 0
    # Update to start death timer
    gs.update(0.1, {})
    assert gs.death_timer > 0
    
    # Fast forward death timer
    gs.update(2.1, {})
    
    # Should be back in sanctuary with full health
    assert gs.world.name == "sanctuary"
    assert gs.player.hp == gs.player.max_hp
