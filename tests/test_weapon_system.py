
import pytest
from engine.player import Player, PlayerStateEnum
from engine.enemy import Miniboss
from engine.loot import WeaponItem
from engine.game_state import GameState

class MockWorld:
    def __init__(self):
        self.player_start = (0, 0)
        self.grid = [[0]]
        self.interactables = []
        self.enemies = []
    def get_nearby_interactables(self, rect):
        return []
    def get_nearby_walls(self, rect):
        return []

def test_weapon_inventory_limit():
    """Verify player can only hold 2 weapons and swap works."""
    player = Player(0, 0)
    assert len(player.weapons) == 1
    
    # Manually add a second weapon
    player.weapons.append({"name": "Second Weapon", "damage": 20})
    assert len(player.weapons) == 2
    
    # Test Swap
    assert player.active_weapon_idx == 0
    player.swap_weapon()
    assert player.active_weapon_idx == 1
    player.swap_weapon()
    assert player.active_weapon_idx == 0

def test_weapon_pickup_swap_logic():
    """Verify picking up a weapon when full swaps it with the active one."""
    from engine.game_state import GameState
    state = GameState(auto_load=False)
    state.world = MockWorld()
    state.player = Player(0, 0)
    
    # Fill inventory
    weapon2 = {"name": "Weapon 2", "damage": 15}
    state.player.weapons.append(weapon2)
    state.player.active_weapon_idx = 0 # Active is "Initial Quill"
    
    # Pickup a third weapon
    weapon3 = {"name": "Weapon 3", "damage": 25}
    pickup = WeaponItem(100, 100, weapon3)
    state.loot.append(pickup)
    
    pickup.execute_pickup(state)
    
    # Inventory should still be 2
    assert len(state.player.weapons) == 2
    # Active weapon (index 0) should now be Weapon 3
    assert state.player.weapons[0]["name"] == "Weapon 3"
    # Old active weapon (Initial Quill) should be dropped in state.loot
    dropped = [item for item in state.loot if isinstance(item, WeaponItem) and item.name == "Initial Quill"]
    assert len(dropped) > 0

def test_full_cradle_rule():
    """Verify Miniboss drops anomalous weapon only when player is full."""
    state = GameState(auto_load=False)
    state.world = MockWorld()
    state.player = Player(0, 0)
    
    # Case 1: Player has 1 weapon (Not Full)
    miniboss1 = Miniboss(50, 50)
    miniboss1.on_death(state)
    
    standard_drops = [item for item in state.loot if isinstance(item, WeaponItem) and item.name == "Refined Quill"]
    assert len(standard_drops) == 1
    
    # Case 2: Player has 2 weapons (Full Cradle)
    state.player.weapons.append({"name": "Refined Quill", "damage": 15})
    state.loot = [] # Clear previous drops
    
    miniboss2 = Miniboss(50, 50)
    miniboss2.on_death(state)
    
    anomalous_drops = [item for item in state.loot if isinstance(item, WeaponItem) and "Anomalous" in item.name]
    assert len(anomalous_drops) == 1
    assert "modifiers" in anomalous_drops[0].weapon_data
