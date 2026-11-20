"""
Unit and integration tests for Section 4: A* Pathfinding & Live Map Patrols.
Verifies corner-safe A* routing around walls and solid GameObjects, unreachable targets,
440x440 macro-world performance bounds, enemy chase/patrol/return-to-patrol behavior,
and socket-scoped patrol route generation in biome segment pools.
"""
# pylint: disable=protected-access,too-many-locals

import json
import time
from types import SimpleNamespace

from constants import (
    ACTOR_ACTIVE_SIMULATION_RADIUS_TILES,
    BIOME_SEGMENT_POOLS,
    TILE_EMPTY,
    TILE_SIZE,
    TILE_WALL,
)
from engine.actor import ActorState
from engine.enemy import (
    BatEnemy,
    FinalAuthor,
    FlutterEnemy,
    NightBoss,
    PunctuationWolfEnemy,
    SentryEnemy,
    SlugEnemy,
    SmearEnemy,
)
from engine.maps import create_world
from engine.pathfinding import find_path, get_solid_obstacle_tiles, has_line_of_sight
from engine.player import Player
from engine.world import GameObject, LevelLoader, PatrolPoint, World


def _build_world_from_lines(lines):
    """Create a headless World directly from ASCII prototype lines."""
    world = World("test_nav")
    world.load_from_prototype(lines)
    return world


def _make_minimal_state(world, player_pos, enemies=None):
    """Build a lightweight headless state namespace for actor update loops."""
    player = Player(float(player_pos[0]), float(player_pos[1]))
    net = SimpleNamespace(remote_players={})
    return SimpleNamespace(
        world=world,
        player=player,
        network_manager=net,
        enemies=enemies or [],
        active_dialogue=None,
        audio_manager=None,
        player_breadcrumbs=[],
        damage_numbers=[],
    )


def test_astar_routes_around_wall_barrier():
    """Verify A* computes a corner-safe detour around a solid wall barrier."""
    layout = [
        "############",
        "#..........#",
        "#....#.....#",
        "#....#.....#",
        "#....#.....#",
        "#....#.....#",
        "#....#.....#",
        "#..........#",
        "############",
    ]
    world = _build_world_from_lines(layout)
    start_px = (2.5 * TILE_SIZE, 4.5 * TILE_SIZE)
    goal_px = (8.5 * TILE_SIZE, 4.5 * TILE_SIZE)

    assert has_line_of_sight(world, start_px, goal_px) is False
    path = find_path(world, start_px, goal_px)
    assert len(path) >= 2

    # Every waypoint must land on a walkable non-wall tile
    for wx, wy in path:
        tx, ty = int(wx // TILE_SIZE), int(wy // TILE_SIZE)
        assert world.grid[ty][tx] != TILE_WALL

    # Final waypoint reaches the goal tile
    end_tx, end_ty = int(path[-1][0] // TILE_SIZE), int(path[-1][1] // TILE_SIZE)
    assert (end_tx, end_ty) == (8, 4)


def test_astar_avoids_solid_gameobjects_and_refreshes_cache():
    """Verify A* avoids solid props (Bookcases/Barrels) and updates when a prop is removed."""
    layout = [
        "##########",
        "#........#",
        "#........#",
        "#........#",
        "#........#",
        "##########",
    ]
    world = _build_world_from_lines(layout)

    # Block column x=4 across rows y=1..3 with solid props, leaving only y=4 open
    props = []
    for row in (1, 2, 3):
        prop = GameObject((4 * TILE_SIZE, row * TILE_SIZE), (TILE_SIZE, TILE_SIZE))
        prop.is_solid = True
        prop.name = "Heavy Bookcase"
        world.interactables.append(prop)
        props.append(prop)

    start_px = (2.5 * TILE_SIZE, 2.5 * TILE_SIZE)
    goal_px = (7.5 * TILE_SIZE, 2.5 * TILE_SIZE)

    blocked = get_solid_obstacle_tiles(world)
    assert {(4, 1), (4, 2), (4, 3)}.issubset(blocked)
    assert has_line_of_sight(world, start_px, goal_px) is False

    path = find_path(world, start_px, goal_px)
    assert len(path) >= 2
    for wx, wy in path:
        assert (int(wx // TILE_SIZE), int(wy // TILE_SIZE)) not in {(4, 1), (4, 2), (4, 3)}

    # Removing the middle solid prop invalidates the nav cache and restores direct LOS
    world.interactables.remove(props[1])
    assert (4, 2) not in get_solid_obstacle_tiles(world)
    assert has_line_of_sight(world, start_px, goal_px) is True


def test_astar_unreachable_target_returns_empty():
    """Verify provably unreachable targets inside sealed rooms return an empty path."""
    layout = [
        "##########",
        "#...#....#",
        "#...#....#",
        "#...#....#",
        "##########",
    ]
    world = _build_world_from_lines(layout)
    start_px = (1.5 * TILE_SIZE, 2.5 * TILE_SIZE)
    goal_px = (7.5 * TILE_SIZE, 2.5 * TILE_SIZE)
    assert find_path(world, start_px, goal_px) == []


def test_astar_performance_on_440x440_grid():
    """Verify bounded A* stays fast on a full 440x440 macro-world grid."""
    world = World("perf_macro")
    world.grid = [[TILE_EMPTY for _ in range(440)] for _ in range(440)]
    # Add a 10-tile vertical wall divider near the center
    for y in range(215, 226):
        world.grid[y][220] = TILE_WALL

    start_px = (210.5 * TILE_SIZE, 220.5 * TILE_SIZE)
    goal_px = (230.5 * TILE_SIZE, 220.5 * TILE_SIZE)

    t0 = time.perf_counter()
    for _ in range(20):
        path = find_path(world, start_px, goal_px)
        assert len(path) >= 2
    elapsed = time.perf_counter() - t0
    assert elapsed < 0.5, f"20 A* queries on 440x440 grid took too long: {elapsed:.3f}s"


def test_enemy_patrols_chases_around_wall_and_returns_to_patrol():
    """Verify an enemy patrols around a wall, chases the player around it, and returns to patrol."""
    layout = [
        "##############",
        "#............#",
        "#.....#......#",
        "#.....#......#",
        "#.....#......#",
        "#.....#......#",
        "#............#",
        "##############",
    ]
    world = _build_world_from_lines(layout)

    # Patrol markers on opposite sides of the interior wall
    p1 = PatrolPoint((2 * TILE_SIZE, 3 * TILE_SIZE), route_id="r_test", symbol_idx=1, wait_min=0.0, wait_max=0.0)
    p2 = PatrolPoint((9 * TILE_SIZE, 3 * TILE_SIZE), route_id="r_test", symbol_idx=2, wait_min=0.0, wait_max=0.0)
    world.interactables.extend([p1, p2])

    enemy = SlugEnemy(2 * TILE_SIZE, 3 * TILE_SIZE)
    enemy.speed = 160.0
    enemy.patrol_speed_multiplier = 0.6
    enemy.detect_radius = 2 * TILE_SIZE
    enemy.patrol_route = [p1, p2]
    enemy.patrol_idx = 1  # Head toward p2 around the wall

    # Place player far outside detect_radius initially
    state = _make_minimal_state(world, (30 * TILE_SIZE, 30 * TILE_SIZE), enemies=[enemy])

    # 1. Patrol around the wall from p1 -> p2
    reached_p2 = False
    for _ in range(360):
        enemy.update(0.05, state)
        if enemy.patrol_idx == 0:
            reached_p2 = True
            break
    assert reached_p2, f"Enemy failed to patrol around wall to p2 (pos=({enemy.x:.1f}, {enemy.y:.1f}))"

    # 2. Player enters detect_radius on the opposite side of the wall -> enemy chases around it
    enemy.x, enemy.y = 2.0 * TILE_SIZE, 4.0 * TILE_SIZE
    state.player.x, state.player.y = 7.0 * TILE_SIZE, 4.0 * TILE_SIZE
    enemy.detect_radius = 7 * TILE_SIZE
    for _ in range(180):
        enemy.update(0.05, state)
        if enemy.x > 6.0 * TILE_SIZE:
            break
    assert enemy.state in (ActorState.CHASE, ActorState.WIND_UP, ActorState.STRIKE)
    assert enemy.x > 6.0 * TILE_SIZE, "Enemy failed to pathfind around wall during CHASE"

    # 3. Player moves far away -> enemy breaks aggro and returns cleanly to patrol route
    state.player.x, state.player.y = 12.0 * TILE_SIZE, 6.0 * TILE_SIZE
    enemy.detect_radius = 2 * TILE_SIZE
    enemy.state = ActorState.CHASE
    enemy.x, enemy.y = 11.0 * TILE_SIZE, 1.0 * TILE_SIZE

    enemy.update(0.05, state)
    assert enemy.state == ActorState.PATROLLING
    assert enemy._returning_to_patrol is True

    returned = False
    for _ in range(300):
        enemy.update(0.05, state)
        if not enemy._returning_to_patrol:
            returned = True
            break
    assert returned, "Enemy failed to return to its patrol route after breaking aggro"


def test_specialized_enemies_use_astar_and_flutter_returns_to_patrol():
    """Verify Bat, Sentry, Wolf, and Flutter integrate cleanly with A* and patrol return."""
    layout = [
        "############",
        "#..........#",
        "#....#.....#",
        "#....#.....#",
        "#....#.....#",
        "#..........#",
        "############",
    ]
    world = _build_world_from_lines(layout)
    p1 = PatrolPoint((2 * TILE_SIZE, 2 * TILE_SIZE), route_id="flut_r", symbol_idx=1, wait_min=0.0, wait_max=0.0)
    p2 = PatrolPoint((8 * TILE_SIZE, 2 * TILE_SIZE), route_id="flut_r", symbol_idx=2, wait_min=0.0, wait_max=0.0)

    bat = BatEnemy(2 * TILE_SIZE, 3 * TILE_SIZE)
    sentry = SentryEnemy(2 * TILE_SIZE, 3 * TILE_SIZE)
    wolf = PunctuationWolfEnemy(2 * TILE_SIZE, 3 * TILE_SIZE)
    flutter = FlutterEnemy(2 * TILE_SIZE, 3 * TILE_SIZE)
    flutter.patrol_route = [p1, p2]
    flutter.patrol_idx = 0

    state = _make_minimal_state(world, (7 * TILE_SIZE, 3 * TILE_SIZE), enemies=[bat, sentry, wolf, flutter])

    for enemy in (bat, sentry, wolf):
        enemy.detect_radius = 10 * TILE_SIZE
        enemy.active_target = state.player.get_center()
        enemy.state = ActorState.CHASE
        enemy.update(0.05, state)
        assert enemy.state == ActorState.CHASE

    # Flutter flees when player is close, then returns to PATROLLING when player leaves
    flutter.detect_radius = 8 * TILE_SIZE
    flutter.update(0.05, state)
    assert flutter.state == ActorState.CHASE

    flutter.detect_radius = 2 * TILE_SIZE
    flutter.update(0.05, state)
    assert flutter.state == ActorState.PATROLLING
    assert flutter._returning_to_patrol is True


def test_generated_segments_have_patrols_and_macro_world_links_routes():
    """Verify all 7 biome segment pools include patrol markers and macro-world routes are socket-scoped."""
    for biome, pools in BIOME_SEGMENT_POOLS.items():
        has_patrol = False
        for room_path in pools["rooms"]:
            with open(room_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if any(
                isinstance(val, dict) and "route_id" in val
                for val in data.get("entities", {}).values()
            ):
                has_patrol = True
                break
        assert has_patrol, f"Expected patrol routes in {biome} room segments"

    world = create_world("macro_world")
    state = _make_minimal_state(world, world.player_start, enemies=list(world.enemies))
    LevelLoader.link_actors_to_routes(state)

    linked = [e for e in state.enemies if e.patrol_route]
    assert len(linked) > 0, "Expected enemies in macro_world to be linked to patrol routes"

    # Verify socket-scoped routes stay localized (no cross-map 200+ tile jumps between consecutive markers)
    for enemy in linked:
        pts = enemy.patrol_route
        for idx in range(len(pts) - 1):
            dx = abs(pts[idx + 1].x - pts[idx].x)
            dy = abs(pts[idx + 1].y - pts[idx].y)
            assert dx < 40 * TILE_SIZE and dy < 40 * TILE_SIZE, (
                f"Cross-room route collision detected for {enemy.name}: {pts[idx].route_id}"
            )


def test_active_simulation_radius_sleep_and_exemptions():
    """Verify distant actors sleep outside ACTOR_ACTIVE_SIMULATION_RADIUS_TILES while bosses,
    persistent_pursuit hunters, and active remote runners (excluding Waiting Scholars) work properly."""
    world = World("sim_cull_test")
    world.grid = [[TILE_EMPTY for _ in range(160)] for _ in range(160)]
    state = _make_minimal_state(world, (10 * TILE_SIZE, 10 * TILE_SIZE))
    state.in_sanctuary = False

    far_px = (10 + ACTOR_ACTIVE_SIMULATION_RADIUS_TILES + 25) * TILE_SIZE
    far_slug = SlugEnemy(far_px, far_px)
    far_smear = SmearEnemy(far_px + 40, far_px)
    far_smear._puddle_timer = 1.5
    p1 = PatrolPoint((far_px + 120, far_px), route_id="far_r", symbol_idx=1, wait_min=0.0, wait_max=0.0)
    far_slug.patrol_route = [p1]

    # 1. Distant standard enemies sleep and do not move or drop off-screen puddles
    assert far_slug.is_within_active_simulation(state) is False
    assert far_smear.is_within_active_simulation(state) is False
    initial_inter_count = len(world.interactables)
    far_slug.update(0.1, state)
    far_smear.update(0.1, state)
    assert far_slug.x == far_px
    assert len(world.interactables) == initial_inter_count

    # 2. A Waiting Scholar in Sanctuary at far_px does NOT wake macro-world enemies
    state.network_manager.remote_players["waiting_peer"] = {
        "x": far_px,
        "y": far_px,
        "in_sanctuary": True,
    }
    assert far_slug.is_within_active_simulation(state) is False

    # 3. An active remote runner in the macro-world at far_px DOES wake nearby enemies
    state.network_manager.remote_players["active_peer"] = {
        "x": far_px,
        "y": far_px,
        "in_sanctuary": False,
    }
    assert far_slug.is_within_active_simulation(state) is True
    state.network_manager.remote_players.clear()

    # 4. Exemptions: persistent_pursuit hunters and bosses never sleep even when far away
    far_hunter = SlugEnemy(far_px, far_px)
    far_hunter.persistent_pursuit = True
    far_night_boss = NightBoss(far_px, far_px)
    far_author = FinalAuthor(far_px, far_px)
    assert far_hunter.is_within_active_simulation(state) is True
    assert far_night_boss.is_within_active_simulation(state) is True
    assert far_author.is_within_active_simulation(state) is True

    # 5. Appending a non-solid Inkwell Puddle reuses the cached solid obstacle tile set
    solid_prop = GameObject((4 * TILE_SIZE, 4 * TILE_SIZE), (TILE_SIZE, TILE_SIZE))
    solid_prop.is_solid = True
    world.interactables.append(solid_prop)
    tiles_before = get_solid_obstacle_tiles(world)
    puddle = GameObject((5 * TILE_SIZE, 5 * TILE_SIZE), (TILE_SIZE, TILE_SIZE))
    puddle.is_solid = False
    puddle.name = "Inkwell Puddle"
    world.interactables.append(puddle)
    tiles_after = get_solid_obstacle_tiles(world)
    assert tiles_after is tiles_before
