"""
Tests for the map design framework (string-grid parsing and GameObjects).
"""
import pytest
from engine.world import World, GameObject, WarpPortal, LevelLoader
from engine.room_definitions import ROOM_PROTOTYPES, ENTITY_MANIFEST
from constants import TILE_WALL, TILE_EMPTY, TILE_KEY, PLAYER_START_X, PLAYER_START_Y

def test_level_loader_player_start():
    prototype = [
        "...",
        ".P.",
        "..."
    ]
    grid, interactables, warp_tiles, p_start = LevelLoader.parse_map(prototype)
    
    # x=1, y=1 -> (TILE_SIZE, TILE_SIZE)
    from constants import TILE_SIZE
    assert p_start == (TILE_SIZE, TILE_SIZE)
    # Check that 'P' doesn't leave a wall or anything in the grid
    assert grid[1][1] == TILE_EMPTY

def test_game_object_initialization():
    pos = (100, 200)
    dim = (40, 40)
    obj = GameObject(pos, dim)
    
    assert obj.x == 100
    assert obj.y == 200
    assert obj.width == 40
    assert obj.height == 40
    assert obj.rect == (100, 200, 40, 40)
    assert obj.is_solid is True
    assert obj.is_breakable is False
    assert obj.is_interactive is False

def test_world_load_from_prototype():
    prototype = [
        "###",
        "#W#",
        "###"
    ]
    entity_data = {
        (1, 1): {"target": "outside", "name": "Test Portal"}
    }
    
    world = World(name='custom')
    world.load_from_prototype(prototype, entity_data)
    
    # Check grid
    assert world.grid[0][0] == TILE_WALL
    assert world.grid[1][1] == TILE_KEY['W']
    
    # Check interactables
    assert len(world.interactables) == 1
    portal = world.interactables[0]
    assert isinstance(portal, WarpPortal)
    assert portal.target_name == "outside"
    assert portal.name == "Test Portal"

def test_world_solid_game_objects_collision():
    prototype = [
        "...",
        ".T.",
        "..."
    ]
    world = World(name='custom')
    world.load_from_prototype(prototype)
    
    # Tree at (1, 1) -> (40, 40)
    player_rect = (45, 45, 30, 30) # Overlaps with (40, 40, 40, 40)
    
    walls = world.get_nearby_walls(player_rect)
    assert len(walls) == 1
    assert walls[0] == (40, 40, 40, 40)

def test_world_interactable_detection():
    prototype = [
        "...",
        ".R.",
        "..."
    ]
    world = World(name='custom')
    world.load_from_prototype(prototype)
    
    # Respite at (1, 1)
    player_rect = (45, 45, 30, 30)
    
    interactables = world.get_nearby_interactables(player_rect)
    assert len(interactables) == 1
    assert interactables[0].name == "Respite"

def test_room_prototypes_registry():
    assert "chapter1_start" in ROOM_PROTOTYPES
    assert len(ROOM_PROTOTYPES["chapter1_start"]) == 6
    assert ROOM_PROTOTYPES["chapter1_start"][0] == "##########"

@pytest.mark.parametrize("room_id", ROOM_PROTOTYPES.keys())
def test_all_prototypes_loadable(room_id):
    world = World(name='custom')
    world.load_from_prototype(ROOM_PROTOTYPES[room_id], ENTITY_MANIFEST.get(room_id, {}))
    # Basic sanity check: grid should be populated
    found_any = any(any(tile != TILE_EMPTY for tile in row) for row in world.grid)
    assert found_any
