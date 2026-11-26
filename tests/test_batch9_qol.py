# copyright 2026 Dustin Massop, License: GPLv2
"""
Unit tests for Batch 9 — Combat, Interaction, Audio & Minimap QoL:
1. Hostile interactable lockout (blocks LoreFragment/Respite/WarpPortal while allowing WeaponPickup/ExitLadder
   and allowing combat swings) + floating cancel icon rendering.
2. Minimap off-screen safe-circle amber/gold edge beacon dot (hidden once safe-circle center enters minimap).
3. SentryEnemy true 360-degree omnidirectional telegraph corridor and point-to-segment laser hitbox alignment.
4. Sunlit Aqueducts Stratum 0 shallow-water slow, wading ripples, and quiet water_step.ogg cadence.
5. Player hurt SFX (player_hurt.ogg), Flask heal (flask_use.ogg) vs. empty/full (flask_empty.ogg) wired live,
   and softened door_open.ogg generation.
6. Unblotted Margin +5% damage_mitigation reduction, non-pulsing LostPassage, and removed Binder/Dialogue footers.
"""
# pylint: disable=wrong-import-position,wrong-import-order,no-member,protected-access

import math
import os

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame
import pytest

import constants
import generate_sfx
from engine.actor import ActorState
from engine.enemy import SentryEnemy, SlugEnemy
from engine.game_state import GameState
from engine.player import PlayerStateEnum
from engine.world import ExitLadder, LoreFragment, Respite, WeaponPickup, World
from rendering.renderer import Renderer
from ui.menu import draw_binder_weave_menu


@pytest.fixture(scope="module", autouse=True)
def init_pygame():
    """Initialize and cleanly tear down pygame in headless dummy mode."""
    pygame.init()
    yield
    pygame.quit()


class _AudioSpy:
    """Minimal audio manager recording all play_sfx calls."""

    def __init__(self):
        self.played = []

    def play_sfx(self, name, **_kwargs):
        """Record an SFX filename."""
        self.played.append(name)


def test_hostile_interactable_lockout_allows_combat_and_draws_cancel_icon():
    """Hostiles near non-combat interactables block interaction, let attack swing, and draw cancel icon."""
    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)
    state = GameState(auto_load=False)
    state.network_manager.stop_network()
    try:
        state.world = World("windy_ridge")
        state.world.load_from_prototype(["." * 14 for _ in range(14)])
        state.in_sanctuary = False
        state.player.x, state.player.y = 200.0, 200.0

        passage = LoreFragment((200.0, 200.0), (40, 40), "windy_ridge_chronicle", name="Lost Passage")
        respite = Respite((200.0, 200.0), (40, 40))
        pickup = WeaponPickup((200.0, 200.0), {"name": "Refined Quill", "damage": 18})
        ladder = ExitLadder((200.0, 200.0), (40, 40))
        state.world.interactables = [passage]

        slug = SlugEnemy(250.0, 200.0)
        state.enemies = [slug]

        assert state.is_interactable_blocked_by_hostiles(passage) is True
        assert state.is_interactable_blocked_by_hostiles(respite) is True
        # WeaponPickup and ExitLadder remain unblocked mid-fight
        assert state.is_interactable_blocked_by_hostiles(pickup) is False
        assert state.is_interactable_blocked_by_hostiles(ladder) is False

        # Pressing attack does NOT open Lost Passage dialogue and DOES start a player sword swing
        state.update(0.016, {"move": (0.0, 0.0), "attack": True})
        assert state.active_dialogue is None
        assert state.player.state == PlayerStateEnum.ATTACKING

        # draw_interaction_prompt draws a red/amber cancel icon above the blocked target instead of text
        screen.fill((0, 0, 0))
        state.player.current_interactable = passage
        renderer.draw_interaction_prompt(state.player, 0.0, 0.0, state=state)
        cancel_px = screen.get_at((int(passage.x + 20), int(passage.y - 16)))
        assert cancel_px[:3] != (0, 0, 0)

        # Once enemy is dead, interaction unlocks cleanly
        slug.hp = 0
        assert state.is_interactable_blocked_by_hostiles(passage) is False
    finally:
        state.shutdown_save_worker(timeout=1.0)


def test_minimap_safe_circle_edge_beacon_dot():
    """Verify minimap draws an amber edge beacon when safe-circle center is off-minimap and hides it inside."""
    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)
    state = GameState(auto_load=False)
    state.network_manager.stop_network()
    try:
        state.world = World("windy_ridge")
        state.world.load_from_prototype(["." * 120 for _ in range(120)])
        state.player.x, state.player.y = 400.0, 400.0
        state.active_safe_radius = 120.0

        # 1. Safe-circle center far east (off minimap) -> amber beacon dot on right border (x ~ mw - 5)
        state.current_boss_coords = {"x": 110, "y": 10}
        renderer.draw_minimap(state)
        mm = renderer._minimap_surf
        mw, mh = constants.MINIMAP_WIDTH, constants.MINIMAP_HEIGHT
        amber_hits_off = [
            (x, y)
            for x in range(mw - 10, mw)
            for y in range(mh)
            if mm.get_at((x, y)).r > 230 and mm.get_at((x, y)).g > 170 and mm.get_at((x, y)).b < 190
        ]
        assert amber_hits_off, "Expected amber/gold edge beacon dot on right minimap border"

        # 2. Safe-circle center right beside player (inside minimap) -> NO edge beacon dot on right border
        state.current_boss_coords = {"x": 10, "y": 10}
        renderer.draw_minimap(state)
        amber_hits_on = [
            (x, y)
            for x in range(mw - 10, mw)
            for y in range(mh)
            if mm.get_at((x, y)).r > 230 and mm.get_at((x, y)).g > 170 and mm.get_at((x, y)).b < 190
        ]
        assert not amber_hits_on, "Edge beacon dot must hide once safe-circle center enters minimap bounds"
    finally:
        state.shutdown_save_worker(timeout=1.0)


def test_sentry_omnidirectional_telegraph_and_diagonal_hitbox():
    """Verify SentryEnemy uses true 360-degree point-to-segment collision and oriented WIND_UP telegraph."""
    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)
    state = GameState(auto_load=False)
    state.network_manager.stop_network()
    try:
        state.world = World("tech_tower")
        state.world.load_from_prototype(["." * 14 for _ in range(14)])
        state.in_sanctuary = False

        sentry = SentryEnemy(120.0, 120.0)
        diag = 1.0 / math.sqrt(2.0)
        sentry.facing = (diag, diag)  # 45-degree southeast diagonal
        sentry.state = ActorState.STRIKE
        sentry.combat_timer = 0.2

        # Player standing directly along the 45-degree diagonal beam MUST be hit
        state.player.x, state.player.y = 210.0, 210.0
        state.player.hp = state.player.max_hp
        assert sentry.attempt_damage_player(state) is True
        assert state.player.hp < state.player.max_hp

        # Player standing strictly east (where old cardinal AABB snapped) must NOT be hit by a 45-deg beam
        state.player.x, state.player.y = 240.0, 120.0
        state.player.hp = state.player.max_hp
        state.player.state = PlayerStateEnum.IDLE
        sentry.cooldown_timer = 0.0
        assert sentry.attempt_damage_player(state) is False
        assert state.player.hp == state.player.max_hp

        # WIND_UP renders oriented diagonal corridor polygon along (diag, diag) without cardinal grey AABB
        sentry.state = ActorState.WIND_UP
        sentry.combat_timer = 0.4
        screen.fill((0, 0, 0))
        renderer.draw_boss_weapon(sentry, 0.0, 0.0)
        diag_px = screen.get_at((210, 210))
        east_px = screen.get_at((240, 138))
        assert diag_px[:3] != (0, 0, 0), "Expected oriented cyan telegraph corridor along 45-deg diagonal"
        assert east_px[:3] == (0, 0, 0), "Cardinal east tile must remain clear during diagonal WIND_UP"
    finally:
        state.shutdown_save_worker(timeout=1.0)


def test_sunlit_aqueducts_water_slow_ripples_and_splash_sfx():
    """Verify sunlit_aqueducts Stratum 0 applies AQUEDUCT_WATER_SPEED_MULTIPLIER, ripples, and water_step.ogg."""
    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)
    state = GameState(auto_load=False)
    state.network_manager.stop_network()
    audio = _AudioSpy()
    try:
        state.world = World("sunlit_aqueducts")
        state.world.load_from_prototype(["." * 30 for _ in range(30)])
        state.in_sanctuary = False

        # Find a deterministic 2-tile-wide Stratum 0 water run and a non-Stratum-0 dry tile
        water_tile = next(
            (tx, ty)
            for ty in range(2, 26)
            for tx in range(2, 25)
            if constants.get_tile_stratum(tx, ty) == 0 and constants.get_tile_stratum(tx + 1, ty) == 0
        )
        dry_tile = next(
            (tx, ty)
            for ty in range(2, 26)
            for tx in range(2, 26)
            if constants.get_tile_stratum(tx, ty) != 0
        )

        water_rect = (water_tile[0] * 40.0, water_tile[1] * 40.0, 40.0, 40.0)
        dry_rect = (dry_tile[0] * 40.0, dry_tile[1] * 40.0, 40.0, 40.0)
        assert state.world.is_in_aqueduct_water(water_rect) is True
        assert state.world.is_in_shallow_water(water_rect) is True
        assert state.world.is_in_aqueduct_water(dry_rect) is False

        # Measure displacement over 0.1s on water vs dry ground -> slowed by AQUEDUCT_WATER_SPEED_MULTIPLIER
        state.player.x, state.player.y = water_tile[0] * 40.0, water_tile[1] * 40.0
        start_x = state.player.x
        state._update_player_lifecycle(
            0.1, {"move": (1.0, 0.0), "flask": False, "dash": False, "block": False, "swap": False}, False, audio
        )
        water_dx = state.player.x - start_x
        assert water_dx == pytest.approx(state.player.speed * constants.AQUEDUCT_WATER_SPEED_MULTIPLIER * 0.1, rel=0.05)

        # Continuing to move past WATER_STEP_INTERVAL (0.34s) triggers water_step.ogg
        state._update_player_lifecycle(
            0.26, {"move": (1.0, 0.0), "flask": False, "dash": False, "block": False, "swap": False}, False, audio
        )
        assert constants.WATER_STEP_SFX in audio.played

        # Wading ripples cache & render on sunlit_aqueducts water
        state.player.x, state.player.y = water_tile[0] * 40.0, water_tile[1] * 40.0
        renderer._fx_surface_cache.clear()
        renderer._draw_player_water_ripples(state, 0.0, 0.0, t_now=1.0, vis=1.0)
        assert any(k[0] == "pond_wade_ripple" for k in renderer._fx_surface_cache)
    finally:
        state.shutdown_save_worker(timeout=1.0)


def test_player_hurt_flask_sfx_door_open_and_unblotted_mitigation():
    """Verify player_hurt.ogg, flask_use.ogg, flask_empty.ogg, door_open.ogg, and +5% mitigation math."""
    for sfx_name in (constants.WATER_STEP_SFX, constants.PLAYER_HURT_SFX, constants.FLASK_EMPTY_SFX, "door_open.ogg"):
        path = os.path.join("assets", "audio", "sfx", sfx_name)
        assert os.path.exists(path), f"Missing SFX asset: {path}"
        assert os.path.getsize(path) > 512
    assert generate_sfx.find_missing_sfx(".") == {}

    state = GameState(auto_load=False)
    state.network_manager.stop_network()
    audio = _AudioSpy()
    try:
        state.world = World("windy_ridge")
        state.world.load_from_prototype(["." * 10 for _ in range(10)])
        state.player.x, state.player.y = 120.0, 120.0

        # Flask at full HP -> plays flask_empty.ogg without consuming a charge
        initial_charges = state.player.flask_charges
        state._update_player_lifecycle(
            0.05, {"move": (0.0, 0.0), "flask": True, "dash": False, "block": False, "swap": False}, False, audio
        )
        assert state.player.flask_charges == initial_charges
        assert constants.FLASK_EMPTY_SFX in audio.played

        # Unlatch flask, take unblocked combat damage -> plays player_hurt.ogg
        state._update_player_lifecycle(
            0.05, {"move": (0.0, 0.0), "flask": False, "dash": False, "block": False, "swap": False}, False, audio
        )
        state.player.take_damage(20.0, bypass_stagger=False, audio_manager=audio)
        assert constants.PLAYER_HURT_SFX in audio.played

        # Clear stagger & drink flask while injured -> plays flask_use.ogg via live player.update()
        state.player.state = PlayerStateEnum.IDLE
        state.player.stagger_timer = 0.0
        state._update_player_lifecycle(
            0.05, {"move": (0.0, 0.0), "flask": True, "dash": False, "block": False, "swap": False}, False, audio
        )
        assert "flask_use.ogg" in audio.played
        assert state.player.flask_charges == initial_charges - 1

        # Empty flask charges -> plays flask_empty.ogg
        audio.played.clear()
        state.player.flask_charges = 0
        state.player.hp = 40.0
        assert state.player.use_flask(audio_manager=audio) is False
        assert constants.FLASK_EMPTY_SFX in audio.played

        # +5% persistent damage_mitigation reduces incoming damage cleanly
        state.player.hp = 50.0
        state.player.damage_mitigation = 0.05
        state.player.take_damage(20.0, bypass_stagger=True)
        assert state.player.hp == pytest.approx(50.0 - 19.0)
    finally:
        state.shutdown_save_worker(timeout=1.0)


def test_non_pulsing_lost_passage_and_removed_ui_footers(monkeypatch):
    """Verify LostPassage renders without pulsing gold circle and Binder/Dialogue footers are removed."""
    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)
    state = GameState(auto_load=False)
    state.network_manager.stop_network()
    try:
        state.world = World("sunlit_aqueducts")
        state.world.load_from_prototype(["." * 10 for _ in range(10)])
        state.player.x, state.player.y = 80.0, 80.0
        state.camera.instant_center((120.0, 120.0))

        # 1. LostPassage / LoreFragment pixels are identical across different timestamps (no pulsing circle)
        frag = LoreFragment((160.0, 120.0), (40, 40), "windy_ridge_chronicle", name="Lost Passage")
        state.world.interactables = [frag]
        state.enemies = []

        import time as _time
        ox, oy = state.camera.get_offset()
        frag_rect = pygame.Rect(int(frag.x - ox), int(frag.y - oy), 40, 40)
        monkeypatch.setattr(_time, "time", lambda: 0.0)
        renderer.render(state)
        sub0 = screen.subsurface(frag_rect).copy()
        snap_t0 = pygame.image.tostring(sub0, "RGB")
        monkeypatch.setattr(_time, "time", lambda: 0.4)
        renderer.render(state)
        sub1 = screen.subsurface(frag_rect).copy()
        snap_t1 = pygame.image.tostring(sub1, "RGB")
        assert snap_t0 == snap_t1, "LostPassage should render statically without a pulsing ring"
        gold_ring_hits = sum(
            1 for y in range(40) for x in range(40) if sub0.get_at((x, y))[:3] == (215, 180, 95)
        )
        assert gold_ring_hits == 0, "Expected pulsing golden outline ring to be removed from LostPassage"

        # 2. Dialogue box & Binder Loom menus do not render obsolete shortcut footer lines
        rendered = []
        orig_render = renderer.font.render

        def _spy_render(text, aa, col, *args, **kwargs):
            rendered.append(str(text))
            return orig_render(text, aa, col, *args, **kwargs)

        monkeypatch.setattr(renderer.font, "render", _spy_render)
        state.active_dialogue = {"speaker": "The Chronicler", "text": "The ink remembers."}
        renderer.draw_dialogue_box(state)
        assert not any("Press [SPACE] to continue" in s for s in rendered)

        for mode in ("prompt", "consult", "weave"):
            rendered.clear()
            state.binder_dialog = {"mode": mode, "selection": 0, "prompt_selection": 0, "status_msg": "Ready."}
            draw_binder_weave_menu(screen, renderer.font, state)
            assert not any("Weave / Toggle Stitch" in s for s in rendered)
            assert not any("[UP/DOWN] Select" in s for s in rendered)
            assert not any("[X / Circle] Close" in s for s in rendered)
    finally:
        state.shutdown_save_worker(timeout=1.0)
