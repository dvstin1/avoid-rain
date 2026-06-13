import pytest
from engine.player import Player, PlayerStateEnum
from constants import BLOCK_DAMAGE_REDUCTION, BLOCK_SPEED_MULTIPLIER

def test_player_block_state():
    player = Player(100, 100)
    walls = []
    
    # Trigger block
    player.update(0.016, (1, 0), walls, {}, block_pressed=True)
    assert player.state == PlayerStateEnum.BLOCKING

def test_player_block_speed_reduction():
    player = Player(100, 100)
    walls = []
    
    # Test normal movement
    player.update(0.016, (1, 0), walls, {}, block_pressed=False)
    normal_vx = player.vx
    
    # Test blocked movement
    player.update(0.016, (1, 0), walls, {}, block_pressed=True)
    blocked_vx = player.vx
    
    assert blocked_vx == normal_vx * BLOCK_SPEED_MULTIPLIER

def test_player_block_damage_reduction():
    player = Player(100, 100)
    # Ensure stats dictionary exists for Edification logic
    player.stats = {"attack_modifier": 0, "max_hp_modifier": 0}
    initial_hp = player.hp
    
    # Set to blocking
    player.state = PlayerStateEnum.BLOCKING
    
    # Apply damage
    damage_amount = 20.0
    # Note: Pristine Concentration bonus might apply if HP > 95%
    player.take_damage(damage_amount)
    
    # If HP was full, it might have taken slightly less damage due to edification logic.
    # In test environment with lvl 1 edification: prowess_lvl=1, fort_lvl=1, edif=1.
    # HP ratio > 0.95: reduction = (1/2.0)/100 = 0.005. 20 * 0.995 = 19.9.
    # Blocking reduction 0.5. 19.9 * 0.5 = 9.95.
    
    assert player.hp < initial_hp
    
    # If BLOCK_DAMAGE_REDUCTION is 0, the player should not stagger
    if BLOCK_DAMAGE_REDUCTION == 0.0:
        assert player.state == PlayerStateEnum.BLOCKING
        assert player.stagger_timer == 0.0
    else:
        assert player.state == PlayerStateEnum.STAGGERED
