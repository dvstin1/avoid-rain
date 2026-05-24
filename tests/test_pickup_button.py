
import pytest
from engine.game_state import GameState
from engine.player import Player
from engine.world import WeaponPickup
from constants import HUD_PICKUP_BTN_RECT, SCREEN_HEIGHT, HUD_PANEL_H

class MockWorld:
    def __init__(self, name="outside"):
        self.grid = [[0]]
        self.interactables = []
        self.enemies = []
        self.name = name
    def get_nearby_interactables(self, rect):
        return self.interactables
    def get_nearby_walls(self, rect):
        return []

def test_pickup_suppressed_from_space():
    """Verify that SPACE bar does NOT trigger a weapon pickup."""
    state = GameState(auto_load=False)
    state.world = MockWorld()
    state.player = Player(100, 100)
    
    weapon_data = {"name": "Test Weapon", "damage": 20}
    pickup = WeaponPickup((100, 100), weapon_data)
    state.world.interactables.append(pickup)
    
    # Simulate standing over the weapon and pressing SPACE
    actions = {'attack': True, 'move': (0,0)}
    state.update(0.1, actions)
    
    # Weapon should still be in the world (not picked up)
    assert pickup in state.world.interactables
    assert len(state.player.weapons) == 1

def test_pickup_triggered_by_button_click():
    """Verify that clicking the [PICK UP] HUD button triggers a pickup."""
    state = GameState(auto_load=False)
    state.world = MockWorld()
    state.player = Player(100, 100)
    
    weapon_data = {"name": "Test Weapon", "damage": 20}
    pickup = WeaponPickup((100, 100), weapon_data)
    state.world.interactables.append(pickup)
    
    # Calculate screen coordinates for the pickup button
    # bx, by = 10, SCREEN_HEIGHT - HUD_PANEL_H - 10
    # HUD_PICKUP_BTN_RECT = (180, 45, 80, 30)
    bx = 10 + HUD_PICKUP_BTN_RECT[0] + 5
    by = (SCREEN_HEIGHT - HUD_PANEL_H - 10) + HUD_PICKUP_BTN_RECT[1] + 5
    
    # Simulate clicking the button while standing over the weapon
    actions = {'mouse_click': (bx, by), 'move': (0,0)}
    state.update(0.1, actions)
    
    # Weapon should be in inventory and removed from world
    assert pickup not in state.world.interactables
    assert any(w["name"] == "Test Weapon" for w in state.player.weapons)
