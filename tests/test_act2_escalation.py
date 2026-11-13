"""Unit tests for Act 2 difficulty escalation, stat scaling, empowered visuals, and co-op sync."""
import os
from unittest.mock import MagicMock

import pygame

import constants
from engine.enemy import BatEnemy, FinalAuthor, NightBoss, SlugEnemy
from engine.game_state import GameState
from engine.stats import StatisticsTracker
from engine.world import WarpPortal
from rendering.renderer import Renderer


def _make_state(tmp_path):
    """Create a headless GameState backed by a temporary stats file."""
    pygame.init()
    stats = StatisticsTracker()
    state = GameState(auto_load=False, stats=stats, stats_path=str(tmp_path / "stats.json"))
    state.network_manager.stop_network()
    return state


def test_act1_vs_act2_enemy_scaling_and_banner_cue(tmp_path, monkeypatch):
    """Act 1 uses 1.0x stats; Act 2 scales enemies/NightBoss 2.0x and triggers banner + audio cue."""
    gen_path = str(tmp_path / "generated_world.json")
    monkeypatch.setattr(constants, "get_generated_world_path", lambda: gen_path)
    monkeypatch.setattr("engine.world_generator.get_generated_world_path", lambda: gen_path)

    state = _make_state(tmp_path)
    mock_audio = MagicMock()
    state.audio_manager = mock_audio

    state.start_two_act_run("pastoral_valley", "swamp_mire")
    assert state.empowered_act is False
    base_slug = SlugEnemy(0, 0)
    for enemy in state.enemies:
        assert enemy.is_empowered is False
        if isinstance(enemy, SlugEnemy):
            assert enemy.max_hp == base_slug.max_hp
            assert enemy.damage == base_slug.damage

    assert state.transition_to_act2() is True
    assert state.empowered_act is True
    assert state.bloom_text == constants.ACT2_ESCALATION_BANNER
    assert state.bloom_timer > 0.0
    mock_audio.play_sfx.assert_any_call(constants.ACT2_ESCALATION_SFX)

    # Movement is NOT blocked during the escalation banner
    assert state.chronicle_dialog is None
    assert not state.active_dialogue

    for enemy in state.enemies:
        assert enemy.is_empowered is True
        if isinstance(enemy, SlugEnemy):
            assert enemy.max_hp == base_slug.max_hp * constants.ACT2_HP_MULTIPLIER
            assert enemy.damage == base_slug.damage * constants.ACT2_DAMAGE_MULTIPLIER

    # Act 2 NightBoss spawns with 2.0x stats
    state.enemies = []
    state.weather_manager.bleed_state = "CLAMPED"
    state._update_world_events(0.016)
    boss = next(e for e in state.enemies if isinstance(e, NightBoss))
    base_boss = NightBoss(0, 0)
    assert boss.is_empowered is True
    assert boss.max_hp == base_boss.max_hp * constants.ACT2_HP_MULTIPLIER
    assert boss.damage == base_boss.damage * constants.ACT2_DAMAGE_MULTIPLIER


def test_final_boss_arena_inherits_act2_scaling(tmp_path):
    """Warping into night_boss_arena from Act 2 scales The Final Author by 2.0x."""
    state = _make_state(tmp_path)
    state.current_act = 2
    state.empowered_act = True

    portal = WarpPortal("night_boss_arena", 36, 59, (0, 0, 40, 40), name="Arena Warp")
    portal.apply_transfer(state)

    base_author = FinalAuthor(0, 0)
    author = next(e for e in state.world.enemies if isinstance(e, FinalAuthor))
    assert author.is_empowered is True
    assert author.max_hp == base_author.max_hp * constants.ACT2_HP_MULTIPLIER
    assert author.damage == base_author.damage * constants.ACT2_DAMAGE_MULTIPLIER


def test_empowered_visual_variants_and_banner_render(tmp_path):
    """Verify cached empowered Slug tints, procedural PNG swaps, and banner rendering."""
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.init()
    screen = pygame.display.set_mode((1280, 720))
    renderer = Renderer(screen)

    # Hand-crafted Slug empowered sprites cached without overwriting disk assets
    assert "slug_1.png" in renderer.image_cache
    assert "slug_1_empowered.png" in renderer.image_cache
    std_px = renderer.image_cache["slug_1.png"].get_at((24, 24))
    emp_px = renderer.image_cache["slug_1_empowered.png"].get_at((24, 24))
    assert std_px != emp_px or renderer.image_cache["slug_1.png"] is not renderer.image_cache["slug_1_empowered.png"]

    # Procedural empowered sprites pre-loaded for all 6 procedural enemy archetypes
    for kind in ("bat", "flutter", "bindling", "smear", "sentry", "boss"):
        assert f"{kind}_empowered.png" in renderer.image_cache

    bat = BatEnemy(100, 100)
    bat.apply_act_scaling(2.0, 2.0)
    packet = {"facing": (1.0, 0.0), "base": "IDLE", "posture": "NORMAL", "anim_timer": 0.0}
    assert renderer.draw_procedural_enemy(bat, pygame.Rect(100, 100, 40, 40), packet, (200, 100, 0)) is True

    # Escalation banner renders cleanly
    state = _make_state(tmp_path)
    state.trigger_bloom(constants.ACT2_ESCALATION_BANNER, priority=3)
    renderer.draw_bloom_overlay(state)


def test_multiplayer_sync_carries_empowered_flag(tmp_path):
    """Host UDP payload carries empowered_act and per-enemy empowered flags to Client."""
    host = _make_state(tmp_path)
    host.network_manager.network_mode = "HOST"
    host.network_manager.identity = "Host"
    host.empowered_act = True
    bat = BatEnemy(200, 200)
    bat.network_id = 77
    bat.apply_act_scaling(2.0, 2.0)
    host.enemies = [bat]

    payload = host.get_local_state()
    assert payload["empowered_act"] is True
    assert payload["enemies"][0]["empowered"] is True

    client = _make_state(tmp_path)
    client.network_manager.network_mode = "CLIENT"
    client.network_manager.identity = "Client1"
    client.enemies = []
    client.apply_remote_state(("127.0.0.1", 55555), payload)

    assert client.empowered_act is True
    assert len(client.enemies) == 1
    assert client.enemies[0].is_empowered is True
