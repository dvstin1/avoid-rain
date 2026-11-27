# copyright 2026 Dustin Massop, License: GPLv2
"""Unit tests for Step 1: Articulated Boss Rig, Gimmick Armor/Weak-Point Hooks & MarginWarden."""
# pylint: disable=wrong-import-position,wrong-import-order,no-member,protected-access

import os
from types import SimpleNamespace

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame
import pytest

import constants
import generate_sfx
from engine.enemy import ENEMY_REGISTRY, Boss, MarginWarden, Miniboss, NightBoss
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


def test_margin_warden_stats_isolation_lan_mapping_and_sprite_resolution():
    """Verify MarginWarden matches Miniboss scaling/lifecycle without NightBoss rewards, music, or locks."""
    # NightBoss remains untouched
    nb = NightBoss(100, 100)
    assert nb.name == "Night Boss"
    assert nb.max_hp == constants.NIGHT_BOSS_MAX_HP
    assert nb.loot_tier == 1

    # MarginWarden sibling class
    mw = MarginWarden(200, 200)
    assert isinstance(mw, Miniboss)
    assert not isinstance(mw, NightBoss)
    assert mw.name == "Margin Warden"
    assert mw.get_display_name() == "The Margin Warden"
    assert mw.max_hp == constants.MARGIN_WARDEN_MAX_HP == 480
    assert mw.speed == pytest.approx(constants.MINIBOSS_SPEED * 0.95)
    assert mw.loot_tier == 2
    assert ENEMY_REGISTRY["MarginWarden"] is MarginWarden

    state = GameState(stats=StatisticsTracker(), auto_load=False)
    state.network_manager.stop_network()
    try:
        state.world = World("windy_ridge")
        state.world.load_from_prototype(["." * 16 for _ in range(16)])
        state.in_sanctuary = False
        state.player.x = 200.0
        state.player.y = 200.0
        state.stats.data["margin_scraps"] = 0

        # Audio track plays miniboss_combat.ogg, NOT night_boss.ogg
        state.enemies = [mw]
        state._update_audio_track(0.016)
        assert state.player.active_track_name == "miniboss_combat.ogg"

        # Defeating MarginWarden must NOT grant Night Boss Margin Scraps
        mw.hp = 0
        state.update_combat(0.016, False, {}, audio_manager=None)
        assert state.stats.data["margin_scraps"] == 0

        # LAN Client enemy sync instantiates MarginWarden by name
        state.enemies = []
        state._sync_enemies_from_host([
            {"id": 77, "name": "Margin Warden", "x": 160.0, "y": 160.0, "hp": 420.0, "state": 1}
        ])
        assert len(state.enemies) == 1
        assert isinstance(state.enemies[0], MarginWarden)
        assert state.enemies[0].network_id == 77

        # Renderer maps MarginWarden to night_boss.png directional sprites cleanly
        screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
        renderer = Renderer(screen)
        resolved_keys = []
        orig_resolve = renderer._resolve_boss_directional_sprite

        def _spy_resolve(base_key, *args, **kwargs):
            resolved_keys.append(base_key)
            return orig_resolve(base_key, *args, **kwargs)

        renderer._resolve_boss_directional_sprite = _spy_resolve
        draw_rect = pygame.Rect(100, 100, 64, 64)
        drawn = renderer.draw_procedural_enemy(
            MarginWarden(100, 100),
            draw_rect,
            {"base": "IDLE", "facing": (0.0, 1.0), "anim_timer": 0.2},
            (255, 255, 255),
        )
        assert drawn is True
        assert resolved_keys == ["night_boss.png"]
    finally:
        state.shutdown_save_worker(timeout=1.0)


def test_articulated_boss_rig_z_order_quantized_cache_and_under_layer():
    """Verify _draw_articulated_boss_rig() Z-ordering, 5-deg rotation cache, and procedural under-layer."""
    screen = pygame.Surface((256, 256))
    renderer = Renderer(screen)

    # Register 2 synthetic colored part surfaces to verify strict Z-order draw layering
    back_part = pygame.Surface((24, 24), pygame.SRCALPHA)
    back_part.fill((20, 90, 220, 255))
    front_part = pygame.Surface((24, 24), pygame.SRCALPHA)
    front_part.fill((230, 60, 40, 255))
    renderer.prop_cache["TestRigBack"] = back_part
    renderer.prop_cache["TestRigFront"] = front_part

    boss = MarginWarden(100, 100)
    boss.phase = 2
    boss.armor_active = True
    draw_rect = pygame.Rect(96, 96, 64, 64)
    packet = {"facing": (1.0, 0.0), "base": "IDLE", "anim_timer": 0.5}

    under_called = []

    def _under_cb(surf, rect, actor, pkt):
        under_called.append((surf is screen, rect, actor, pkt))
        pygame.draw.circle(surf, (40, 220, 140), rect.center, 44, 2)

    parts = [
        {"sprite_key": "TestRigFront", "z_order": 10, "angle_deg": 11.0, "scale": 1.0},
        {"sprite_key": "TestRigBack", "z_order": -5, "angle_deg": 11.0, "scale": 1.0},
    ]

    screen.fill((0, 0, 0))
    renderer._fx_surface_cache.clear()
    order1 = renderer._draw_articulated_boss_rig(boss, draw_rect, packet, parts, under_shapes_fn=_under_cb)

    # Back part (z=-5) drawn before Front part (z=10); center pixel shows Front red over Back blue
    assert [entry[0] for entry in order1] == ["TestRigBack", "TestRigFront"]
    assert screen.get_at(draw_rect.center)[:3] == (230, 60, 40)
    assert len(under_called) == 1
    assert under_called[0][0] is True

    # Under-layer caches shadow, Phase 2 aura, and armor ring
    cache_tags = {k[0] for k in renderer._fx_surface_cache}
    assert "boss_rig_shadow" in cache_tags
    assert "boss_rig_phase2_aura" in cache_tags
    assert "boss_rig_armor_ring" in cache_tags

    # 5-degree quantization: 11.0 deg and 12.0 deg both quantize to 10 deg -> exact cache hit (no extra entry)
    part_entries_before = [k for k in renderer._fx_surface_cache if k[0] == "boss_rig_part"]
    parts_close_angle = [
        {"sprite_key": "TestRigFront", "z_order": 10, "angle_deg": 12.0, "scale": 1.0},
        {"sprite_key": "TestRigBack", "z_order": -5, "angle_deg": 12.0, "scale": 1.0},
    ]
    order2 = renderer._draw_articulated_boss_rig(boss, draw_rect, packet, parts_close_angle)
    part_entries_after = [k for k in renderer._fx_surface_cache if k[0] == "boss_rig_part"]
    assert order1 == order2
    assert len(part_entries_before) == len(part_entries_after) == 2

    # Weak-point exposed state switches under-layer indicator to weak_ring
    boss.weakpoint_exposed_timer = 2.0
    renderer._draw_articulated_boss_rig(boss, draw_rect, packet, parts)
    assert any(k[0] == "boss_rig_weak_ring" for k in renderer._fx_surface_cache)


def test_gimmick_armor_weakpoint_local_melee_lan_damage_and_timer_decay():
    """Verify check_gimmick_hit(), weakpoint_exposed_timer decay, local melee & Host LAN DAMAGE_EVENT scaling."""
    state = GameState(stats=StatisticsTracker(), auto_load=False)
    state.network_manager.stop_network()
    played_sfx = []
    audio_stub = SimpleNamespace(
        play_sfx=lambda name, **kw: played_sfx.append(name),
        calculate_spatial_volume=lambda _d: 1.0,
    )
    state.audio_manager = audio_stub
    try:
        state.world = World("windy_ridge")
        state.world.load_from_prototype(["." * 16 for _ in range(16)])
        state.in_sanctuary = False

        boss = Boss(240.0, 200.0, 64, 64, 500.0, name="Margin Warden")
        boss.network_id = 55
        boss.facing = (-1.0, 0.0)
        boss.armor_active = True
        boss.armor_front_only = True
        boss.armor_damage_mult = 0.25
        boss.weakpoint_damage_mult = 2.0
        state.enemies = [boss]

        # Directional front-armor check: attacker in front (-x) -> 'armor', behind (+x) -> 'normal'
        assert boss.check_gimmick_hit(180.0, 232.0) == "armor"
        assert boss.check_gimmick_hit(360.0, 232.0) == "normal"

        # 1. Local melee hit against armored front scales damage to 0.25x, plays armor_deflect & spawns metallic sparks
        state.player.x = 200.0
        state.player.y = 216.0
        state.player.facing = (1.0, 0.0)
        state.player.state = state.player.state.ATTACKING
        state.player.hit_entities_this_attack.clear()
        base_dmg = state.player.get_active_weapon().get("damage", constants.SWORD_DAMAGE)
        hp_before = boss.hp
        state.impact_sparks.clear()

        state.update_combat(0.016, False, {}, audio_manager=audio_stub)
        assert hp_before - boss.hp == pytest.approx(base_dmg * 0.25)
        assert constants.ARMOR_DEFLECT_SFX in played_sfx
        assert any(sp["color"] == constants.COLOR_ARMOR_DEFLECT_SPARK for sp in state.impact_sparks)

        # 2. Opening weakpoint plays boss_expose.ogg, scales hit to 2.0x, plays weakpoint_crit & triggers rumble
        played_sfx.clear()
        boss.expose_weakpoint(1.5, state=state)
        assert constants.BOSS_EXPOSE_SFX in played_sfx
        assert boss.weakpoint_exposed_timer == pytest.approx(1.5)
        assert boss.check_gimmick_hit(180.0, 232.0) == "weakpoint"

        state.player.hit_entities_this_attack.clear()
        state.pending_rumble_impulses.clear()
        hp_before = boss.hp
        state.update_combat(0.016, False, {}, audio_manager=audio_stub)
        assert hp_before - boss.hp == pytest.approx(base_dmg * 2.0)
        assert constants.WEAKPOINT_CRIT_SFX in played_sfx
        assert state.consume_rumble_impulse() is not None

        # 3. Boss.update(dt, state) decrements weakpoint_exposed_timer cleanly to 0.0
        boss.update(0.6, state)
        assert boss.weakpoint_exposed_timer == pytest.approx(0.9)
        boss.update(1.5, state)
        assert boss.weakpoint_exposed_timer == 0.0
        assert boss.check_gimmick_hit(180.0, 232.0) == "armor"

        # 4. Host LAN DAMAGE_EVENT resolves attacking peer position for armor deflection & weakpoint crit
        state.network_manager.network_mode = "HOST"
        state.network_manager.remote_players["peer_front"] = {"x": 180.0, "y": 212.0, "identity": "GuestA"}
        state.network_manager.remote_players["peer_back"] = {"x": 340.0, "y": 212.0, "identity": "GuestB"}
        state.pending_remote_sfx.clear()
        hp_before = boss.hp
        state.handle_remote_damage("enemy", 55, 40.0, attacker_peer_id="peer_front")
        state._process_pending_remote_actions()
        assert hp_before - boss.hp == pytest.approx(10.0)
        assert any(s[0] == constants.ARMOR_DEFLECT_SFX for s in state.pending_remote_sfx)

        # Attacking from behind bypasses front armor (full 40.0 damage)
        hp_before = boss.hp
        state.handle_remote_damage("enemy", 55, 40.0, attacker_peer_id="peer_back")
        state._process_pending_remote_actions()
        assert hp_before - boss.hp == pytest.approx(40.0)

        # Exposed weakpoint scales LAN DAMAGE_EVENT by 2.0x, queues weakpoint_crit SFX, and triggers rumble
        boss.weakpoint_exposed_timer = 2.0
        state.pending_remote_sfx.clear()
        state.pending_rumble_impulses.clear()
        hp_before = boss.hp
        state.handle_remote_damage("enemy", 55, 40.0, attacker_peer_id="peer_front")
        state._process_pending_remote_actions()
        assert hp_before - boss.hp == pytest.approx(80.0)
        assert any(s[0] == constants.WEAKPOINT_CRIT_SFX for s in state.pending_remote_sfx)
        assert state.consume_rumble_impulse() is not None
    finally:
        state.shutdown_save_worker(timeout=1.0)


def test_gimmick_sfx_ogg_files_exist_verify_and_zero_missing():
    """Verify armor_deflect.ogg, boss_expose.ogg, and weakpoint_crit.ogg decode cleanly with 0 missing SFX."""
    for fname in (
        constants.ARMOR_DEFLECT_SFX,
        constants.BOSS_EXPOSE_SFX,
        constants.WEAKPOINT_CRIT_SFX,
    ):
        path = os.path.join("assets", "audio", "sfx", fname)
        assert os.path.exists(path), f"Missing generated gimmick SFX: {path}"
        length = generate_sfx.verify_ogg(path)
        assert 0.15 <= length <= 1.0, f"Unexpected duration for {fname}: {length:.2f}s"

    assert generate_sfx.find_missing_sfx(".") == {}
