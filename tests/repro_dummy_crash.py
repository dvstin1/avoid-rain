
import pytest
from engine.game_state import GameState
from constants import SWORD_DAMAGE

def test_dummy_hit_crash():
    """Attempt to hit the training dummy to check for COLOR_WHITE crash."""
    state = GameState()
    # Move player near dummy
    from constants import DUMMY_X, DUMMY_Y
    state.player.x = DUMMY_X - 50
    state.player.y = DUMMY_Y
    state.player.facing = (1, 0) # Face dummy
    
    # Hit dummy
    state.update(0.016, {'attack': True, 'move': (0,0)})
    
    # If it didn't crash, we're good (or the bug isn't where I think it is)
    assert state.dummy_outline_timer > 0
