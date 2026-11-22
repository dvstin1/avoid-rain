"""Unit tests for Phase 1 playtest polish: audio cleanup, debug gating, warding, boss balance, and Binder UX."""
# pylint: disable=wrong-import-position,wrong-import-order,no-member,protected-access
# pylint: disable=too-few-public-methods,too-many-locals,missing-function-docstring

import os

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame
import pytest

import constants
from engine.actor import ActorState
from engine.audio import AudioManager
from engine.enemy import FinalAuthor, Miniboss, MinibossM2, MinibossM3, NightBoss, SlugEnemy
from engine.game_state import GameState
from engine.player import Player, PlayerStateEnum
from engine.world import World
from rendering.renderer import Renderer, load_font_or_sysfont
from ui.menu import _wrap_text_lines, draw_binder_weave_menu


@pytest.fixture(scope="module", autouse=True)
def init_pygame():
    """Initialize pygame in headless dummy mode for the module."""
    pygame.init()
    yield
    pygame.quit()


class _FakeChannel:
    """Minimal channel stub tracking stop() calls."""

    def __init__(self):
        self.stopped = False

    def stop(self):
        """Record channel stop."""
        self.stopped = True


class _FakeAudio:
    """Minimal audio stub recording played SFX names."""

    def __init__(self):
        self.played = []

    def play_sfx(self, name, volume=1.0):
        """Record SFX playback."""
        self.played.append((name, volume))


def test_audio_stop_enemy_move_sounds_clears_channels():
    """AudioManager.stop_enemy_move_sounds() stops and clears all looping movement channels."""
    audio = AudioManager.__new__(AudioManager)
    ch1, ch2 = _FakeChannel(), _FakeChannel()
    audio.active_move_sounds = {101: ch1, 202: ch2}

    audio.stop_enemy_move_sounds()

    assert ch1.stopped is True
    assert ch2.stopped is True
    assert not audio.active_move_sounds


def test_minimap_enemy_dots_stealth_vs_debug(monkeypatch):
    """Minimap enemy dots use muted slate-grey normally and red only when debug_text_enabled is True."""
    state = GameState(auto_load=False)
    state.network_manager.stop_network()
    world = World("chapter1")
    world.grid = [[constants.TILE_EMPTY for _ in range(10)] for _ in range(10)]
    state.world = world
    state.player.x = 120.0
    state.player.y = 120.0
    state.enemies = [SlugEnemy(160.0, 160.0)]

    screen = pygame.Surface((800, 600))
    renderer = Renderer(screen)
    recorded = []

    def _capture_rect(_surf, color, rect, *_args, **_kwargs):
        recorded.append((color, tuple(rect)))

    monkeypatch.setattr(pygame.draw, "rect", _capture_rect)

    state.debug_text_enabled = False
    renderer.draw_minimap(state)
    assert any(pygame.Color(c) == pygame.Color(constants.MINIMAP_ENEMY_STEALTH_COLOR) for c, _ in recorded)
    assert not any(pygame.Color(c) == pygame.Color(constants.MINIMAP_ENEMY_COLOR) for c, _ in recorded)

    recorded.clear()
    state.debug_text_enabled = True
    renderer.draw_minimap(state)
    assert any(pygame.Color(c) == pygame.Color(constants.MINIMAP_ENEMY_COLOR) for c, _ in recorded)


def test_dash_cyan_and_parry_window_gated_by_debug(monkeypatch):
    """Dash cyan fill and 4px PARRY_WINDOW box outline are suppressed unless debug_text_enabled is True."""
    state = GameState(auto_load=False)
    state.network_manager.stop_network()
    state.player.x = 200.0
    state.player.y = 200.0
    state.player.state = PlayerStateEnum.DASHING
    state.player.dash_timer = constants.DASH_DURATION
    state.player.parry_timer = constants.PARRY_WINDOW

    screen = pygame.Surface((800, 600))
    renderer = Renderer(screen)
    drawn_rects = []
    orig_rect = pygame.draw.rect

    def _spy_rect(surf, color, rect, *args, **kwargs):
        width = args[0] if args else kwargs.get("width", 0)
        drawn_rects.append((tuple(color), width))
        return orig_rect(surf, color, rect, *args, **kwargs)

    monkeypatch.setattr(pygame.draw, "rect", _spy_rect)

    # Normal play: no solid cyan dash fill and no 4px parry debug border
    state.debug_text_enabled = False
    renderer.draw_actor_ghost(state.player, 0, 0, state)
    assert not any(col[:3] == constants.COLOR_CYAN for col, _ in drawn_rects)
    assert not any(col[:3] == (200, 255, 255) and w == 4 for col, w in drawn_rects)

    # Debug mode: both cyan dash fill and 4px parry border are drawn
    drawn_rects.clear()
    state.debug_text_enabled = True
    renderer.draw_actor_ghost(state.player, 0, 0, state)
    assert any(col[:3] == constants.COLOR_CYAN for col, _ in drawn_rects)
    assert any(col[:3] == (200, 255, 255) and w == 4 for col, w in drawn_rects)


def test_warding_rain_damage_reduction_vs_melee_block():
    """Blocking reduces storm rain ticks by 20% (no block SFX) while melee hits stay at 50%."""
    # Use mid-HP so Pristine Concentration (>95%) and Desperate Synthesis (<30%) do not alter exact ratios
    p_rain = Player(100, 100)
    p_rain.hp = 60.0
    p_rain.state = PlayerStateEnum.BLOCKING
    audio_rain = _FakeAudio()
    p_rain.take_damage(10.0, bypass_stagger=True, audio_manager=audio_rain)
    expected_rain_dmg = 10.0 * (1.0 - constants.WARDING_RAIN_DAMAGE_REDUCTION)
    assert p_rain.hp == pytest.approx(60.0 - expected_rain_dmg, abs=1e-4)
    assert p_rain.state == PlayerStateEnum.BLOCKING
    assert not audio_rain.played

    p_melee = Player(100, 100)
    p_melee.hp = 60.0
    p_melee.state = PlayerStateEnum.BLOCKING
    audio_melee = _FakeAudio()
    p_melee.take_damage(10.0, bypass_stagger=False, audio_manager=audio_melee)
    expected_melee_dmg = 10.0 * constants.BLOCK_DAMAGE_REDUCTION
    assert p_melee.hp == pytest.approx(60.0 - expected_melee_dmg, abs=1e-4)
    assert any(name == "player_block.ogg" for name, _ in audio_melee.played)


def test_boss_speeds_timings_and_anti_cheese_ink_bolt():
    """Bosses use updated speed/timing constants and fire anti-cheese ink-bolts when cover blocks LOS."""
    mb = Miniboss(0, 0)
    mb2 = MinibossM2(0, 0)
    mb3 = MinibossM3(0, 0)
    nb = NightBoss(0, 0)
    fa = FinalAuthor(0, 0)

    assert mb.speed == pytest.approx(constants.MINIBOSS_SPEED)
    assert mb.attack_cooldown == pytest.approx(constants.MINIBOSS_DAMAGE_COOLDOWN)
    assert mb.wind_up_duration == pytest.approx(constants.BOSS_WIND_UP_DURATION)
    assert mb2.speed == pytest.approx(constants.MINIBOSS_M2_SPEED)
    assert mb3.speed == pytest.approx(constants.MINIBOSS_M3_SPEED)
    assert nb.speed == pytest.approx(constants.MINIBOSS_SPEED * 0.9)
    assert fa.speed == pytest.approx(constants.MINIBOSS_SPEED * 0.8)
    assert fa.wind_up_duration == pytest.approx(constants.FINAL_AUTHOR_WIND_UP_DURATION)

    # Set up a world with a wall pillar at tile (4, 3) between boss at tile (2, 3) and player at tile (6, 3)
    state = GameState(auto_load=False)
    state.network_manager.stop_network()
    world = World("arena")
    grid = [[constants.TILE_EMPTY for _ in range(12)] for _ in range(8)]
    grid[3][4] = constants.TILE_WALL
    world.grid = grid
    state.world = world
    state.audio_manager = None  # Explicitly verify None audio safety

    ts = constants.TILE_SIZE
    boss = Miniboss(2 * ts, 3 * ts)
    boss.state = ActorState.CHASE
    state.enemies = [boss]
    state.player.x = 6 * ts
    state.player.y = 3 * ts
    state.player.hp = 60.0

    # One update should detect blocked LOS within anti-cheese range and spawn an ink-bolt
    boss.update(0.05, state)
    assert len(boss.ink_bolts) == 1
    assert boss.ranged_cooldown_timer == pytest.approx(constants.BOSS_RANGED_COOLDOWN)

    # Advance frames so the bolt arcs across the pillar and damages the player
    for _ in range(40):
        boss.update(0.05, state)
        if state.player.hp < 60.0:
            break
    assert state.player.hp < 60.0

    # Verify CLIENT network mode does not fire authoritative boss bolts
    client_boss = Miniboss(2 * ts, 3 * ts)
    state.network_manager.network_mode = "CLIENT"
    fired = client_boss._fire_ink_bolt(100.0, 120.0, 240.0, 120.0, state)
    assert fired is False
    assert not client_boss.ink_bolts


def test_binder_consult_wraps_without_truncation_or_overlap():
    """Consult The Binder dialogue wraps across multiple lines with no truncation or option overlap."""
    state = GameState(auto_load=False)
    state.network_manager.stop_network()
    fallback_entry = next(
        entry for entry in constants.DIALOGUE_MANIFEST["binder"] if entry["id"] == "binder_fallback"
    )
    fallback_text = fallback_entry["text"]
    assert "Margin Scraps" in fallback_text
    assert "Hemming -> Serif -> Gloss" in fallback_text
    assert "True Stitch" in fallback_text

    state.binder_dialog = {"mode": "consult", "selection": 0, "status_msg": fallback_text}

    screen = pygame.Surface((1280, 720))
    font = load_font_or_sysfont("ink_sans", 2, "Arial", 24)

    wrapped = _wrap_text_lines(font, fallback_text, 720 - 48)
    assert 2 <= len(wrapped) <= 6
    assert " ".join(wrapped) == " ".join(fallback_text.split())

    blitted = []
    surf_to_text = {}

    class _TrackingFont:
        def __init__(self, inner):
            self._inner = inner

        def size(self, text):
            return self._inner.size(text)

        def get_height(self):
            return self._inner.get_height()

        def render(self, text, antialias, color):
            surf = self._inner.render(text, antialias, color)
            surf_to_text[id(surf)] = text
            return surf

    orig_draw_rect = pygame.draw.rect

    class _BlitProxy:
        def __init__(self, real_surf):
            self._surf = real_surf

        def get_size(self):
            return self._surf.get_size()

        def blit(self, surf, pos):
            blitted.append((surf_to_text.get(id(surf), ""), pos, surf.get_height()))
            return self._surf.blit(surf, pos)

    proxy = _BlitProxy(screen)
    pygame.draw.rect = lambda s, *a, **k: orig_draw_rect(s._surf if isinstance(s, _BlitProxy) else s, *a, **k)
    try:
        draw_binder_weave_menu(proxy, _TrackingFont(font), state)
    finally:
        pygame.draw.rect = orig_draw_rect

    status_blits = [item for item in blitted if item[0] in wrapped]
    option_blits = [item for item in blitted if item[0].startswith(("> ", "  "))]
    footer_blits = [item for item in blitted if "Close" in item[0]]

    assert len(status_blits) == len(wrapped)
    assert not any("..." in item[0] for item in status_blits)
    assert not option_blits, "Consult view should display only dialogue prose without upgrade options"
    assert footer_blits, "Expected footer close hint to be rendered"

    lowest_status_bottom = max(pos[1] + h for _, pos, h in status_blits)
    footer_top = min(pos[1] for _, pos, _ in footer_blits)
    assert footer_top > lowest_status_bottom
