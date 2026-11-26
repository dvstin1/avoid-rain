# copyright 2026 Dustin Massop, License: GPLv2
"""
Unit tests for Respite stability & root-cause fixes:
1. Opening a Respite puts non-boss idle/patrolling enemies to sleep (is_within_active_simulation == False).
2. Respite.execute_rest() respawns enemies from world.initial_enemy_spawns strictly on walkable floor tiles
   inside the existing world grid with current Act scaling, fresh network_ids, world.enemies parity,
   preserved active Night Boss, and defeated miniboss exclusion.
3. LevelLoader.link_actors_to_routes() does not chain 'default' patrol markers across TILE_WALL barriers.
"""
# pylint: disable=no-member,protected-access,too-many-locals,too-many-statements,duplicate-code
import pytest
import pygame

import constants
from engine.actor import ActorState
from engine.enemy import FinalAuthor, Miniboss, NightBoss, SlugBoss, SlugEnemy
from engine.game_state import GameState
from engine.physics import check_aabb_collision
from engine.stats import StatisticsTracker
from engine.world import GameObject, LevelLoader, Respite, World


def _make_state(tmp_path):
    """Create an offline GameState backed by a temporary stats path."""
    pygame.init()
    stats_path = str(tmp_path / "stats.json")
    stats = StatisticsTracker()
    state = GameState(auto_load=False, stats=stats, stats_path=stats_path)
    state.online_mode = False
    state.network_manager.stop_network()
    return state


def test_open_respite_sleeps_non_boss_idle_and_patrolling_enemies(tmp_path):
    """Verify opening a Respite puts non-boss idle/patrolling enemies to sleep while exempting bosses."""
    state = _make_state(tmp_path)
    prototype = [
        "####################",
        "#R............Z...1#",
        "#..................#",
        "####################",
    ]
    state.world = World("respite_sleep_test")
    state.world.load_from_prototype(prototype)
    state.enemies = list(state.world.enemies)
    state.in_sanctuary = False
    state.player.x = 1.0 * constants.TILE_SIZE
    state.player.y = 1.0 * constants.TILE_SIZE
    LevelLoader.link_actors_to_routes(state)

    idle_slug = state.enemies[0]
    patrolling_slug = SlugEnemy(15.0 * constants.TILE_SIZE, 2.0 * constants.TILE_SIZE)
    patrolling_slug.state = ActorState.PATROLLING
    patrolling_slug.patrol_route = list(idle_slug.patrol_route)
    night_boss = NightBoss(16.0 * constants.TILE_SIZE, 2.0 * constants.TILE_SIZE)
    slug_boss = SlugBoss(16.0 * constants.TILE_SIZE, 2.0 * constants.TILE_SIZE)
    final_author = FinalAuthor(16.0 * constants.TILE_SIZE, 2.0 * constants.TILE_SIZE)

    # Before opening Respite, nearby enemies (within 48 tiles) are within active simulation
    state.active_respite = None
    assert idle_slug.is_within_active_simulation(state) is True
    assert patrolling_slug.is_within_active_simulation(state) is True

    # Opening Respite removes the resting local player from active runners; non-boss enemies sleep
    respite = next(obj for obj in state.world.interactables if isinstance(obj, Respite))
    respite.execute_interaction(state)
    assert state.active_respite is respite

    assert idle_slug.is_within_active_simulation(state) is False
    assert patrolling_slug.is_within_active_simulation(state) is False
    assert night_boss.is_within_active_simulation(state) is True
    assert slug_boss.is_within_active_simulation(state) is True
    assert final_author.is_within_active_simulation(state) is True


def test_respite_execute_rest_respawns_walkable_scaled_enemies_and_excludes_defeated_miniboss(tmp_path):
    """Verify Respite.execute_rest() rebuilds from initial_enemy_spawns with Act scaling, walkable positions,
    sequential network_ids, world.enemies parity, defeated miniboss exclusion, and Night Boss preservation."""
    state = _make_state(tmp_path)
    prototype = [
        "############",
        "#R..Z...E..#",
        "#....##....#",
        "#..Z.##..E.#",
        "#..........#",
        "############",
    ]
    state.world = World("in_memory_respite_world")
    state.world.load_from_prototype(prototype)
    state.enemies = list(state.world.enemies)
    state.in_sanctuary = False

    # Verify initial_enemy_spawns captured the 2 Slugs ('Z') and 2 Minibosses ('E')
    assert len(state.world.initial_enemy_spawns) == 4

    # Add a solid prop on top of the first spawn coordinate and a corrupted wall spawn to test walkability snap
    first_spawn = state.world.initial_enemy_spawns[0]
    solid_block = GameObject((first_spawn["x"], first_spawn["y"]), (constants.TILE_SIZE, constants.TILE_SIZE))
    solid_block.is_solid = True
    state.world.interactables.append(solid_block)

    state.world.initial_enemy_spawns.append(
        {
            "cls": SlugEnemy,
            "type": "SlugEnemy",
            "x": 5.0 * constants.TILE_SIZE,
            "y": 2.0 * constants.TILE_SIZE,  # Directly on '#' wall tile (5, 2)
            "id": "wall_tile_slug",
            "is_miniboss": False,
            "is_stationary": True,
        }
    )

    # Mark one miniboss ('E') as defeated and add an active Night Boss that must be preserved across rest
    defeated_miniboss = next(e for e in state.enemies if isinstance(e, Miniboss))
    state.defeated_miniboss_ids.add(defeated_miniboss.id)

    active_boss = SlugBoss(8.0 * constants.TILE_SIZE, 4.0 * constants.TILE_SIZE)
    active_boss.hp = 450.0
    active_boss.network_id = 9000

    # Kill/damage existing enemies and set Act 3 saturation scaling
    state.enemies = [active_boss]
    state.current_act = 3
    state.player.hp = 12.0
    state.player.flask_charges = 0

    respite = next(obj for obj in state.world.interactables if isinstance(obj, Respite))
    respite.execute_rest(state)

    # 1. Player restored
    assert state.player.hp == pytest.approx(state.player.max_hp)
    assert state.player.flask_charges == constants.FLASK_MAX_CHARGES
    assert state.player.has_rested_this_session is True

    # 2. Defeated miniboss excluded; 3 Slugs + 1 surviving MinibossM2 + 1 preserved SlugBoss = 5 enemies
    assert len(state.enemies) == 5
    assert state.world.enemies == state.enemies
    assert all(getattr(e, "id", None) != defeated_miniboss.id for e in state.enemies)
    assert active_boss in state.enemies
    assert active_boss.hp == pytest.approx(450.0)

    # 3. Act 3 saturation scaling applied to respawned enemies + sequential network_ids (0..3)
    sat3 = constants.get_act_saturation(3)
    base_slug = SlugEnemy(0, 0)
    respawned_standard = [e for e in state.enemies if e is not active_boss]
    assert [e.network_id for e in respawned_standard] == [0, 1, 2, 3]

    respawned_slugs = [e for e in respawned_standard if isinstance(e, SlugEnemy)]
    assert len(respawned_slugs) == 3
    for slug in respawned_slugs:
        assert slug.max_hp == pytest.approx(base_slug.max_hp * sat3["hp_multiplier"])
        assert slug.damage == pytest.approx(base_slug.damage * sat3["damage_multiplier"])
        assert slug.speed == pytest.approx(base_slug.speed * sat3["speed_multiplier"])
        assert slug.is_empowered is True

    wall_slug = next(e for e in respawned_slugs if e.id == "wall_tile_slug")
    assert wall_slug.is_stationary is True

    # 4. Every respawned enemy sits strictly on walkable floor tiles avoiding walls and solid props
    for enemy in respawned_standard:
        e_rect = enemy.get_rect()
        assert not check_aabb_collision(e_rect, solid_block.rect)
        tx0 = int(enemy.x // constants.TILE_SIZE)
        ty0 = int(enemy.y // constants.TILE_SIZE)
        tx1 = int((enemy.x + enemy.width - 1e-4) // constants.TILE_SIZE)
        ty1 = int((enemy.y + enemy.height - 1e-4) // constants.TILE_SIZE)
        for ty in range(ty0, ty1 + 1):
            for tx in range(tx0, tx1 + 1):
                assert state.world.grid[ty][tx] != constants.TILE_WALL


def test_default_patrol_markers_do_not_chain_across_walls(tmp_path):
    """Verify LevelLoader.link_actors_to_routes() does not chain 'default' patrol markers across a wall."""
    state = _make_state(tmp_path)
    prototype = [
        "#############",
        "#Z.1..2#3..4#",
        "#......#....#",
        "#############",
    ]
    state.world = World("cross_wall_patrol_test")
    state.world.load_from_prototype(prototype)
    state.enemies = list(state.world.enemies)

    LevelLoader.link_actors_to_routes(state)

    slug = state.enemies[0]
    route_indices = [pt.symbol_idx for pt in slug.patrol_route]
    assert route_indices == [1, 2]
    for pt in slug.patrol_route:
        assert pt.x < 7 * constants.TILE_SIZE
