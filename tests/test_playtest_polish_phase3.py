"""Unit tests for Phase 3 playtest polish: Sanctuary Y-sorting, pond wading, facades, and lively NPCs."""
# pylint: disable=wrong-import-position,wrong-import-order,no-member,protected-access,too-many-locals

import json
import math
import os

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame
import pytest

import constants
from engine.game_state import GameState
from engine.stats import StatisticsTracker
from engine.world import Binder, Chronicler, GameObject, PatrolPoint
from rendering.renderer import Renderer


@pytest.fixture(scope="module", autouse=True)
def init_pygame():
    """Initialize pygame in headless dummy mode for Phase 3 Sanctuary tests."""
    pygame.init()
    yield
    pygame.quit()


def _make_sanctuary_state():
    """Create an isolated Sanctuary GameState with networking stopped."""
    state = GameState(auto_load=False, stats=StatisticsTracker())
    state.network_manager.stop_network()
    return state


def test_sanctuary_tree_canopy_y_sorted_draw_order(monkeypatch):
    """Trees north of player draw before player; trees south of player draw after player and before roofs/blackout."""
    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)
    state = _make_sanctuary_state()
    try:
        ts = constants.TILE_SIZE
        state.player.x = 20.0 * ts
        state.player.y = 20.0 * ts

        north_tree = GameObject((20 * ts, 18 * ts), (ts, ts))
        north_tree.name = "SanctuaryTreeCanopy"
        north_tree.prop_type = "sanctuary_tree"
        north_tree.is_solid = True

        south_tree = GameObject((20 * ts, 22 * ts), (ts, ts))
        south_tree.name = "SanctuaryTreeCanopy"
        south_tree.prop_type = "sanctuary_tree"
        south_tree.is_solid = True

        state.world.interactables = [north_tree, south_tree]
        state.camera.instant_center((20 * ts, 20 * ts))

        order = []
        orig_tree = renderer._draw_sanctuary_tree_canopy
        orig_ghost = renderer.draw_actor_ghost
        orig_roofs = renderer.draw_sanctuary_roofs_and_blackout

        def _track_tree(obj, ox, oy, prop_cache):
            order.append("north_tree" if obj is north_tree else "south_tree")
            return orig_tree(obj, ox, oy, prop_cache)

        def _track_ghost(actor, ox, oy, st):
            if actor is state.player:
                order.append("player")
            return orig_ghost(actor, ox, oy, st)

        def _track_roofs(st, ox, oy):
            order.append("roofs_and_blackout")
            return orig_roofs(st, ox, oy)

        monkeypatch.setattr(renderer, "_draw_sanctuary_tree_canopy", _track_tree)
        monkeypatch.setattr(renderer, "draw_actor_ghost", _track_ghost)
        monkeypatch.setattr(renderer, "draw_sanctuary_roofs_and_blackout", _track_roofs)

        renderer.render(state)

        assert order.index("north_tree") < order.index("player")
        assert order.index("player") < order.index("south_tree")
        assert order.index("south_tree") < order.index("roofs_and_blackout")
    finally:
        state.shutdown_save_worker(timeout=1.0)


def test_sanctuary_pond_wading_slowdown_and_ripples():
    """World.is_in_sanctuary_pond() triggers 0.40x speed multiplier and foot-ripple rings without altering puddles."""
    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)
    state = _make_sanctuary_state()
    try:
        ts = constants.TILE_SIZE
        # Dry tile in courtyard path (21, 24)
        dry_rect = (21.0 * ts, 24.0 * ts, float(ts), float(ts))
        pond_rect = (12.0 * ts, 24.0 * ts, float(ts), float(ts))
        assert state.world.is_in_sanctuary_pond(dry_rect) is False
        assert state.world.is_in_sanctuary_pond(pond_rect) is True

        # Pond lily reeds still do not trigger Inkwell Puddle collision
        lily = next(o for o in state.world.interactables if getattr(o, "prop_type", None) == "pond_lily_reeds")
        assert state.world.has_puddle_collision(lily.rect) is False

        # Measure dry speed vs pond wading speed via GameState.update()
        state.player.x = 21.0 * ts
        state.player.y = 24.0 * ts
        state.update(0.05, {"move": (1, 0)})
        dry_vx = state.player.vx

        state.player.x = 12.0 * ts
        state.player.y = 24.0 * ts
        state.update(0.05, {"move": (1, 0)})
        pond_vx = state.player.vx

        assert dry_vx > 0.0
        assert pond_vx == pytest.approx(dry_vx * constants.SANCTUARY_POND_SPEED_MULTIPLIER, rel=1e-4)

        # Render courtyard atmosphere while player wades in the pond -> generates pond_wade_ripple
        state.camera.instant_center((12 * ts, 24 * ts))
        ox, oy = state.camera.get_offset()
        renderer.sanctuary_interior_alpha = 0.0
        renderer.draw_sanctuary_courtyard_atmosphere(state, ox, oy, now=1.25)
        assert any(k[0] == "pond_wade_ripple" for k in renderer._fx_surface_cache)
    finally:
        state.shutdown_save_worker(timeout=1.0)


def test_sanctuary_visible_facades_shed_door_and_chimney():
    """Verify shed door exposed below shed_roof, Scriptorium south windows/doorway + chimney, and inside cutout."""
    with open("maps/sanctuary.json", "r", encoding="utf-8") as handle:
        data = json.load(handle)

    zones = data["zones"]
    roofs = {r["name"]: r for r in zones["roof_zones"]}
    assert roofs["shed_roof"]["y"] == 4 and roofs["shed_roof"]["h"] == 4
    assert roofs["scriptorium_roof"]["y"] == 7 and roofs["scriptorium_roof"]["h"] == 14
    assert roofs["scriptorium_roof"]["footprint"] == [28, 7, 22, 15]
    assert roofs["scriptorium_roof"]["chimney"] == [46, 7]

    south_facade = zones["south_facade"]
    assert len(south_facade["windows"]) >= 4
    assert all(coord[1] == 21 for coord in south_facade["windows"])
    assert south_facade["doorway"] == [[38, 21]]

    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)
    state = _make_sanctuary_state()
    try:
        ts = constants.TILE_SIZE

        # 1. Shed roof covers (6, 6) while leaving LockedShedDoor at (6, 8) completely uncovered
        state.camera.instant_center((8 * ts, 8 * ts))
        ox, oy = state.camera.get_offset()
        screen.fill((210, 190, 170))
        renderer.sanctuary_interior_alpha = 0.0
        renderer.draw_sanctuary_roofs_and_blackout(state, ox, oy)
        shed_mid = screen.get_at((int(6 * ts + 20 - ox), int(6 * ts + 20 - oy)))[:3]
        shed_door_pt = screen.get_at((int(6 * ts + 20 - ox), int(8 * ts + 20 - oy)))[:3]
        assert shed_mid != (210, 190, 170), "shed_roof should cover (6, 6)"
        assert shed_door_pt == (210, 190, 170), "LockedShedDoor at (6, 8) must remain uncovered below shed_roof"

        # 2. Outside Scriptorium: south facade windows, arched doorway, roof, and chimney all render visibly
        state.camera.instant_center((38 * ts, 16 * ts))
        ox, oy = state.camera.get_offset()
        screen.fill((12, 14, 18))
        renderer.sanctuary_interior_alpha = 0.0
        renderer.draw_sanctuary_roofs_and_blackout(state, ox, oy)
        win_x, win_y = south_facade["windows"][0]
        win_px = screen.get_at((int(win_x * ts + 20 - ox), int(win_y * ts + 20 - oy)))[:3]
        door_px = screen.get_at((int(38 * ts + 20 - ox), int(21 * ts + 20 - oy)))[:3]
        assert win_px != (12, 14, 18), "SanctuaryWindowWall should render on south wall when outside"
        assert door_px != (12, 14, 18), "SanctuaryArchDoorway should render across south doorway when outside"

        # 2b. Verify chimney at [46, 7] renders cleanly on top of scriptorium_roof without clipping
        state.camera.instant_center((44 * ts, 10 * ts))
        ox_c, oy_c = state.camera.get_offset()
        screen.fill((12, 14, 18))
        renderer.draw_sanctuary_roofs_and_blackout(state, ox_c, oy_c)
        chim_px = screen.get_at((int(46 * ts + 20 - ox_c), int(6 * ts + 25 - oy_c)))[:3]
        assert chim_px != (12, 14, 18), "SanctuaryChimney should render atop scriptorium_roof without clipping"

        # 3. Inside Scriptorium: blackout cutout preserves the southern doorway threshold (38, 21) brightly lit
        state.camera.instant_center((38 * ts, 16 * ts))
        ox, oy = state.camera.get_offset()
        screen.fill((120, 110, 100))
        renderer.sanctuary_interior_alpha = 1.0
        renderer.draw_sanctuary_roofs_and_blackout(state, ox, oy)
        door_inside = screen.get_at((int(38 * ts + 20 - ox), int(21 * ts + 20 - oy)))[:3]
        outside_yard = screen.get_at((int(38 * ts + 20 - ox), int(23 * ts + 20 - oy)))[:3]
        assert door_inside == (120, 110, 100), "Blackout cutout must include southern wall/doorway threshold (y=21)"
        assert sum(outside_yard) < 60, "Exterior courtyard south of doorway must be darkened when inside"
    finally:
        state.shutdown_save_worker(timeout=1.0)


def test_sanctuary_npcs_patrol_autonomously_and_halt_during_dialogue():
    """Chronicler and Binder both link to Sanctuary patrol routes, move autonomously, and halt during dialogue."""
    state = _make_sanctuary_state()
    try:
        chronicler = next(o for o in state.world.interactables if isinstance(o, Chronicler))
        binder = next(o for o in state.world.interactables if isinstance(o, Binder))

        assert binder.is_stationary is False
        assert binder.patrol_speed_multiplier == pytest.approx(constants.BINDER_PATROL_SPEED_MULTIPLIER)
        assert len(chronicler.patrol_route) >= 2
        assert len(binder.patrol_route) >= 2
        assert any(
            isinstance(o, PatrolPoint) and o.route_id == "binder_work" for o in state.world.interactables
        )

        # Ensure neither NPC starts paused on a wait timer and step simulation with no dialogue
        chronicler.wait_timer = 0.0
        binder.wait_timer = 0.0
        c_start = (chronicler.x, chronicler.y)
        b_start = (binder.x, binder.y)

        for _ in range(15):
            state.update(0.05, {"move": (0, 0)})

        c_moved = math.hypot(chronicler.x - c_start[0], chronicler.y - c_start[1])
        b_moved = math.hypot(binder.x - b_start[0], binder.y - b_start[1])
        assert c_moved > 2.0, f"Expected Chronicler to patrol autonomously, moved {c_moved}"
        assert b_moved > 2.0, f"Expected Binder to patrol autonomously, moved {b_moved}"

        # Active dialogue halts both NPCs completely
        state.active_dialogue = {"speaker": "The Chronicler", "text": "Listen closely."}
        c_frozen = (chronicler.x, chronicler.y)
        b_frozen = (binder.x, binder.y)
        for _ in range(10):
            state.update(0.05, {"move": (0, 0)})
        assert (chronicler.x, chronicler.y) == c_frozen
        assert (binder.x, binder.y) == b_frozen

        # Binder Loom dialog also halts both NPCs
        state.active_dialogue = None
        state.binder_dialog = {"selection": 0, "status_msg": "Weave."}
        for _ in range(10):
            state.update(0.05, {"move": (0, 0)})
        assert (chronicler.x, chronicler.y) == c_frozen
        assert (binder.x, binder.y) == b_frozen
    finally:
        state.shutdown_save_worker(timeout=1.0)
