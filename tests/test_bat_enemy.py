import math
from engine.game_state import GameState
from engine.enemy import BatEnemy
from constants import BAT_MAX_HP, PLAYER_MAX_HP

def distance(a, b):
    return math.hypot(a[0]-b[0], a[1]-b[1])

def test_bat_enemy_movement():
    gs = GameState(auto_load=False)
    # Instantiate BatEnemy manually
    bat = BatEnemy(gs.player.x + 200, gs.player.y)
    gs.enemies = [bat]
    
    before = distance((bat.x, bat.y), gs.player.get_center())
    # Update for some time to see it moving towards player
    for _ in range(5):
        gs.update(0.1, {})
    after = distance((bat.x, bat.y), gs.player.get_center())
    
    # Bat should move closer
    assert after < before
    # Check if vx/vy is not just simple linear movement
    assert bat.vx != 0 or bat.vy != 0

def test_bat_enemy_damage():
    gs = GameState(auto_load=False)
    bat = BatEnemy(gs.player.x, gs.player.y) # Directly on top
    gs.enemies = [bat]
    
    gs.player.hp = PLAYER_MAX_HP
    gs.update(0.1, {})
    
    assert gs.player.hp < PLAYER_MAX_HP
    assert bat._damage_timer > 0

def test_bat_enemy_death():
    gs = GameState(auto_load=False)
    bat = BatEnemy(gs.player.x + 30, gs.player.y)
    gs.enemies = [bat]
    
    # Damage bat
    bat.take_damage(BAT_MAX_HP)
    assert bat.is_dead()
    
    # Update game state to remove dead enemies
    gs.update(0.1, {})
    assert bat not in gs.enemies
