"""
Unit tests for Playtest Polish Pass 2:
1. Biome & Connector Area Name Resolution (vitreous_basin, sunlit_aqueducts, connector fallbacks).
2. Walkable Enemy Spawns (World.find_nearest_walkable_spawn, Marginalia, Night Boss, LevelLoader oversized enemies).
3. Wellspring Single-Flask Cap During Night Boss (+1 flask total, then "WELLSPRING DRY").
4. Bat Swoop Lunge & 36x36 Shifted Hitbox Effectiveness against stationary player at aggro range.
"""
# pylint: disable=no-member,protected-access,duplicate-code
import json
import math
import pygame

import constants
from engine.actor import ActorState
from engine.enemy import BatEnemy, NightBoss, SlugEnemy
from engine.game_state import GameState
from engine.physics import check_aabb_collision
from engine.stats import StatisticsTracker
from engine.world import LevelLoader, Wellspring, World


def _make_state(tmp_path):
    """Create an offline GameState backed by a temporary stats path."""
    pygame.init()
    stats_path = str(tmp_path / "stats.json")
    stats = StatisticsTracker()
    state = GameState(auto_load=False, stats=stats, stats_path=stats_path)
    state.online_mode = False
    state.network_manager.stop_network()
    return state


def test_area_name_resolution_vitreous_basin_sunlit_aqueducts_and_connectors(tmp_path):
    """Verify vitreous_basin, sunlit_aqueducts, and fallback connectors never produce THE UNKNOWN MARGIN."""
    state = _make_state(tmp_path)
    state.world = World("macro_world")
    state.in_sanctuary = False
    state.current_act = 1
    state.run_biomes["act1"] = "vitreous_basin"

    state.world.module_sockets = [
        {
            "name": "Room_0_0",
            "active_plug": "maps/segments/vitreous_basin/vitreous_basin_room_1.json",
        },
        {
            "name": "Room_4_0",
            "active_plug": "maps/segments/sunlit_aqueducts/sunlit_aqueducts_room_2.json",
        },
        {
            "name": "Room_8_0",
            "active_plug": "maps/smallcave.json",
        },
        {
            "name": "Room_0_4",
            "active_plug": "maps/gantry_bridge.json",
        },
        {
            "name": "Room_4_4",
            "active_plug": "maps/mire_causeway.json",
        },
    ]

    assert state._resolve_room_area_name("Room_0_0") == "THE VITREOUS BASIN"
    assert state._resolve_room_area_name("Room_4_0") == "THE SUNLIT AQUEDUCTS"

    # Connector and unmapped sockets fall back to active biome's BIOME_DISPLAY_NAMES title uppercased
    for connector_room in ("Room_8_0", "Room_0_4", "Room_4_4", "Room_8_8"):
        resolved = state._resolve_room_area_name(connector_room)
        assert resolved == "THE VITREOUS BASIN"
        assert resolved != "THE UNKNOWN MARGIN"

    # Switch active biome to sunlit_aqueducts and verify live bloom trigger in _update_ui_and_menus
    state.run_biomes["act1"] = "sunlit_aqueducts"
    state.last_zone_id = None
    state.zone_cooldown_timer = 0.0
    # Place player inside Room_8_0 (unit x=8..10, unit y=0..2 -> pixel x = 8 * 40 * 40 + 80)
    state.player.x = float(8 * constants.TILE_SIZE * 40 + 80)
    state.player.y = float(0 * constants.TILE_SIZE * 40 + 80)
    state._update_ui_and_menus(0.016, {}, False, None)
    assert state.bloom_text == "THE SUNLIT AQUEDUCTS"
    assert state.bloom_text != "THE UNKNOWN MARGIN"


def _assert_rect_clear_of_walls_and_props(world, rect):
    """Assert that rect is within world bounds and overlaps no TILE_WALL or solid interactable."""
    rx, ry, rw, rh = rect
    assert rx >= 0.0 and ry >= 0.0
    assert rx + rw <= len(world.grid[0]) * constants.TILE_SIZE
    assert ry + rh <= len(world.grid) * constants.TILE_SIZE

    tx0 = int(rx // constants.TILE_SIZE)
    ty0 = int(ry // constants.TILE_SIZE)
    tx1 = int((rx + max(0.0, rw - 1e-4)) // constants.TILE_SIZE)
    ty1 = int((ry + max(0.0, rh - 1e-4)) // constants.TILE_SIZE)
    for ty in range(ty0, ty1 + 1):
        for tx in range(tx0, tx1 + 1):
            assert world.grid[ty][tx] != constants.TILE_WALL
    for wall_rect in world.get_nearby_walls(rect):
        assert not check_aabb_collision(rect, wall_rect)


def test_find_nearest_walkable_spawn_snaps_wall_overlapping_enemies(tmp_path):
    """Verify find_nearest_walkable_spawn snaps Marginalia, NightBoss, and oversized map spawns off walls."""
    state = _make_state(tmp_path)
    prototype = [
        "########",
        "#......#",
        "#..##..#",
        "#..##..#",
        "#......#",
        "#......#",
        "########",
    ]
    state.world = World("test_spawn_world")
    state.world.load_from_prototype(prototype)
    state.in_sanctuary = False

    # 1. Direct helper call on a wall tile (3, 2) -> (120, 80)
    wx, wy = state.world.find_nearest_walkable_spawn(120.0, 80.0, 40, 40)
    _assert_rect_clear_of_walls_and_props(state.world, (wx, wy, 40, 40))

    # 2. MarginaliaEventEngine._spawn_enemy inside wall tile (3, 3) -> (120, 120)
    marg_enemy = state.marginalia_engine._spawn_enemy(state, SlugEnemy, 120.0, 120.0, 1)
    _assert_rect_clear_of_walls_and_props(state.world, marg_enemy.get_rect())

    # 3. Night Boss (64x64) spawned at tile (2, 2) where right neighbor (3, 2) is a wall
    state.enemies.clear()
    state.world.boss_coords_list = [{"x": 2, "y": 2}]
    state.weather_manager.set_boss_coords_list(state.world.boss_coords_list)
    state.weather_manager.bleed_state = "CLAMPED"
    state.weather_manager.active_safe_radius = constants.WEATHER_MIN_RADIUS
    state.player.x = 2 * constants.TILE_SIZE
    state.player.y = 2 * constants.TILE_SIZE
    state._update_world_events(0.016)
    state._update_world_events(constants.BOSS_SUMMON_DURATION)
    night_boss = next((e for e in state.enemies if isinstance(e, NightBoss)), None)
    assert night_boss is not None
    _assert_rect_clear_of_walls_and_props(state.world, night_boss.get_rect())

    # 4. LevelLoader.load_json_map with oversized enemies ('E' 64x64, '!' 80x80, 's' 48x48) placed next to walls
    map_path = tmp_path / "oversized_test.json"
    map_data = {
        "map_id": "oversized_test",
        "dimensions": {"width": 9, "height": 9},
        "grid": [
            "#########",
            "#.......#",
            "#.......#",
            "#.....E.#",
            "#.......#",
            "#.....s.#",
            "#.......#",
            "#.....!.#",
            "#########",
        ],
        "entities": {},
        "module_sockets": [],
    }
    map_path.write_text(json.dumps(map_data), encoding="utf-8")
    grid, interactables, _, _, loaded_enemies, _, _ = LevelLoader.load_json_map(str(map_path))
    loaded_world = World("oversized_test")
    loaded_world.grid = grid
    loaded_world.interactables = interactables
    assert len(loaded_enemies) == 3
    for enemy in loaded_enemies:
        _assert_rect_clear_of_walls_and_props(loaded_world, enemy.get_rect())


def test_wellspring_single_flask_cap_during_night_boss(tmp_path):
    """Verify Wellspring grants at most +1 flask during Night Boss and then stays dry."""
    state = _make_state(tmp_path)
    wellspring = Wellspring((200, 200), (40, 40))
    assert wellspring.night_boss_used is False

    # Activate Night Boss encounter with 0 flasks on player
    state.night_boss_spawned = True
    state.enemies = [NightBoss(400, 400)]
    state.player.flask_charges = 0

    # First interaction: grants +1 flask (0 -> 1) and marks night_boss_used = True
    wellspring.execute_interaction(state)
    assert state.player.flask_charges == 1
    assert wellspring.night_boss_used is True
    assert state.bloom_text == "HYDRATION RESTORED"

    # Second interaction during Night Boss: remains at 1 flask and blooms WELLSPRING DRY
    wellspring.execute_interaction(state)
    assert state.player.flask_charges == 1
    assert state.bloom_text == "WELLSPRING DRY"


def test_bat_enemy_swoop_lunge_and_hitbox_damages_stationary_player_at_aggro_range(tmp_path):
    """Verify BatEnemy tracks, locks swoop vector, surges ~2.4x speed, and hits stationary player at aggro range."""
    state = _make_state(tmp_path)
    state.world = World("open_arena")
    state.world.load_from_prototype(["." * 16 for _ in range(16)])
    state.in_sanctuary = False

    # Place stationary player at (200, 200) and BatEnemy 160px to the east (within 280px detect radius)
    state.player.x = 200.0
    state.player.y = 200.0
    initial_hp = float(state.player.hp)

    bat = BatEnemy(360.0, 208.0)
    state.enemies = [bat]

    # Check 28x28 tight shifted swoop hitbox dimensions and forward shift
    bat.swoop_dir = (-1.0, 0.0)
    bat._swoop_locked = True
    hx, _hy, hw, hh = bat.get_attack_hitbox()
    assert hw == 28.0 and hh == 28.0
    bat_cx, _ = bat.get_center()
    hitbox_cx = hx + hw / 2.0
    assert hitbox_cx < bat_cx
    bat._swoop_locked = False

    observed_wind_up_lock = False
    observed_swoop_surge = False
    for _ in range(60):
        bat.update(0.03, state)
        if bat.state == ActorState.WIND_UP and bat._swoop_locked:
            observed_wind_up_lock = True
        if bat.state == ActorState.STRIKE:
            speed_mag = math.hypot(bat.vx, bat.vy)
            if speed_mag >= bat.speed * 2.0 or bat.has_hit_this_attack:
                observed_swoop_surge = True
        if state.player.hp < initial_hp:
            break

    assert observed_wind_up_lock is True
    assert observed_swoop_surge is True
    assert state.player.hp < initial_hp
