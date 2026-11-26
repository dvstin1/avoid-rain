# copyright 2026 Dustin Massop, License: GPLv2
"""Unit tests for Playtest Polish Batch 3 Pass 1: Slug bite, Bat claw slash, death theme, dash vol & name save."""
# pylint: disable=wrong-import-position,wrong-import-order,no-member,protected-access

import json
import math
import os
from types import SimpleNamespace

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame
import pytest

import constants
import engine.stats
from engine.actor import ActorState
from engine.audio import AudioManager
from engine.enemy import BatEnemy, SlugEnemy
from engine.game_state import GameState
from engine.stats import StatisticsTracker
from engine.world import World
from rendering.renderer import Renderer


@pytest.fixture(scope="module", autouse=True)
def init_pygame():
    """Initialize and cleanly tear down pygame in headless dummy mode."""
    pygame.init()
    yield
    pygame.quit()


def test_slug_bite_hitbox_connects_and_draws_no_greatblade(monkeypatch):
    """Verify SlugEnemy 38x38 forward bite hitbox connects during STRIKE and never draws a tapered blade."""
    slug = SlugEnemy(100.0, 100.0)
    slug.facing = (1.0, 0.0)

    # Non-STRIKE falls back to 32x32 body rect
    slug.state = ActorState.IDLE
    assert slug.get_attack_hitbox() == (100.0, 100.0, 32, 32)

    # STRIKE returns 38x38 hitbox shifted 10px forward
    slug.state = ActorState.STRIKE
    hx, hy, hw, hh = slug.get_attack_hitbox()
    assert hw == constants.SLUG_ATTACK_HITBOX_SIZE == 38.0
    assert hh == constants.SLUG_ATTACK_HITBOX_SIZE == 38.0
    slug_cx, slug_cy = slug.get_center()
    assert math.isclose(hx + hw / 2.0, slug_cx + constants.SLUG_ATTACK_HITBOX_OFFSET, abs_tol=1e-4)
    assert math.isclose(hy + hh / 2.0, slug_cy, abs_tol=1e-4)

    # Contact/bite reaches player standing just ahead of the slug's 32x32 body
    state = GameState(auto_load=False)
    state.network_manager.stop_network()
    try:
        state.world = World("open_arena")
        state.world.load_from_prototype(["." * 12 for _ in range(12)])
        state.player.x = 138.0  # 6px gap outside slug's 32px body (100..132), inside 38px shifted bite (107..145)
        state.player.y = 96.0
        initial_hp = float(state.player.hp)
        assert slug.attempt_damage_player(state) is True
        assert state.player.hp < initial_hp
    finally:
        state.shutdown_save_worker(timeout=1.0)

    # Renderer must never draw a boss greatblade for SlugEnemy
    screen = pygame.Surface((320, 240))
    renderer = Renderer(screen)
    blade_calls = []
    monkeypatch.setattr(renderer, "_draw_tapered_blade", lambda *a, **k: blade_calls.append(a))
    slug.combat_timer = 0.15
    renderer.draw_actor_ghost(slug, 0, 0, SimpleNamespace(debug_text_enabled=False))
    renderer.draw_boss_weapon(slug, 0, 0)
    assert not blade_calls, "SlugEnemy should never swing a tapered greatblade"


def test_bat_white_claw_slash_rendering_and_tight_28x28_swoop(monkeypatch):
    """Verify BatEnemy uses tight 28x28 hitbox and renders 3 crisp white claw slash lines (~18px) without blade."""
    bat = BatEnemy(120.0, 120.0)
    bat.swoop_dir = (1.0, 0.0)
    bat._swoop_locked = True
    bat.facing = (1.0, 0.0)
    bat.state = ActorState.STRIKE
    bat.combat_timer = 0.1

    hb = bat.get_attack_hitbox()
    assert hb[2] == constants.BAT_SWOOP_HITBOX_SIZE == 28.0
    assert hb[3] == constants.BAT_SWOOP_HITBOX_SIZE == 28.0
    assert math.isclose(hb[0] + hb[2] / 2.0, bat.get_center()[0] + constants.BAT_SWOOP_HITBOX_OFFSET, abs_tol=1e-4)

    screen = pygame.Surface((320, 240))
    renderer = Renderer(screen)
    blade_calls = []
    line_lengths = []
    orig_line = pygame.draw.line

    def _spy_line(surf, color, start_pos, end_pos, width=1):
        if surf is screen and tuple(color)[:3] == constants.COLOR_WHITE:
            line_lengths.append(math.hypot(end_pos[0] - start_pos[0], end_pos[1] - start_pos[1]))
        return orig_line(surf, color, start_pos, end_pos, width)

    monkeypatch.setattr(renderer, "_draw_tapered_blade", lambda *a, **k: blade_calls.append(a))
    monkeypatch.setattr(pygame.draw, "line", _spy_line)

    renderer.draw_actor_ghost(bat, 0, 0, SimpleNamespace(debug_text_enabled=False))
    assert not blade_calls, "BatEnemy must never draw a tapered greatblade"
    assert len(line_lengths) == 3, f"Expected 3 crisp white claw slash lines, got {len(line_lengths)}"
    for length in line_lengths:
        assert 14.0 <= length <= 22.0, f"Expected ~18px claw slash line, got {length:.1f}px"


def test_death_screen_duration_and_death_theme_single_play_fade(monkeypatch):
    """Verify DEATH_SCREEN_DURATION >= 5.4s and death_theme.ogg plays with loops=0 and 250ms fade."""
    assert constants.DEATH_SCREEN_DURATION >= 5.4

    state = GameState(auto_load=False)
    state.network_manager.stop_network()
    try:
        state.player.hp = 0.0
        state.update(0.016, {})
        assert math.isclose(state.death_timer, constants.DEATH_SCREEN_DURATION - 0.016, abs_tol=1e-3)
    finally:
        state.shutdown_save_worker(timeout=1.0)

    audio = AudioManager()
    play_calls = []
    monkeypatch.setattr(pygame.mixer.music, "load", lambda _p: None)
    monkeypatch.setattr(pygame.mixer.music, "play", lambda **kw: play_calls.append(kw))

    audio._start_fade_transition("death_theme.ogg")
    assert play_calls[-1] == {"loops": 0, "fade_ms": 250}

    audio._start_fade_transition("sanctuary_hub.ogg")
    assert play_calls[-1] == {"loops": -1, "fade_ms": 2000}


def test_dash_sfx_volume_scaled_by_constants(monkeypatch):
    """Verify player_dash.ogg scales by SFX_VOLUME_SCALE (0.45x) while unscaled SFX retain full volume."""
    assert math.isclose(constants.SFX_VOLUME_SCALE["player_dash.ogg"], 0.45, abs_tol=1e-6)

    audio = AudioManager()
    volumes = []

    fake_channel = SimpleNamespace(set_volume=volumes.append)
    fake_sound = SimpleNamespace(get_num_channels=lambda: 0, play=lambda: fake_channel)

    monkeypatch.setattr(os.path, "exists", lambda _p: True)
    audio.sfx_cache["player_dash.ogg"] = fake_sound
    audio.sfx_cache["menu_confirm.ogg"] = fake_sound

    audio.play_sfx("player_dash.ogg", volume=1.0, pitch_jitter=0.0)
    audio.play_sfx("player_dash.ogg", volume=0.5, pitch_jitter=0.0)
    audio.play_sfx("menu_confirm.ogg", volume=1.0, pitch_jitter=0.0)

    assert len(volumes) == 3
    assert math.isclose(volumes[0], 0.45, abs_tol=1e-6)
    assert math.isclose(volumes[1], 0.225, abs_tol=1e-6)
    assert math.isclose(volumes[2], 1.0, abs_tol=1e-6)


def test_custom_player_name_persists_across_deallocate_save_and_hydrate(tmp_path):
    """Verify custom name persists across deallocate() -> save_stats() -> hydrate_from_disk() without reset."""
    save_file = tmp_path / "profile_save.json"
    # Verify conftest isolated engine.stats.DEFAULT_PATH away from live user home config
    assert str(engine.stats.DEFAULT_PATH).startswith(str(tmp_path.parent)) or (
        ".config/avoid_rain" not in str(engine.stats.DEFAULT_PATH)
    )

    state = GameState(stats=StatisticsTracker(), stats_path=str(save_file), auto_load=False)
    state.network_manager.stop_network()
    try:
        state.stats.data["run_state"] = None
        state.network_manager.identity = "Vellum"
        state.stats.data["player_name"] = "Vellum"

        # Simulate Quit-to-Title deallocation before editing/saving profile name
        state.deallocate()
        assert state.player is None and state.world is None

        state.network_manager.identity = "Inkweaver"
        state.stats.data["player_name"] = "Inkweaver"
        state.save_stats(wait=True, allow_incompatible=True)

        assert save_file.exists()
        saved_json = json.loads(save_file.read_text(encoding="utf-8"))
        assert saved_json["player_name"] == "Inkweaver"

        # Hydrating from disk (as Continue does from Title Screen) must retain "Inkweaver", not "Scholar"
        state.hydrate_from_disk()
        assert state.network_manager.identity == "Inkweaver"
        assert state.stats.data["player_name"] == "Inkweaver"
    finally:
        state.shutdown_save_worker(timeout=1.0)
