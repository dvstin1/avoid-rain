# copyright 2026 Dustin Massop, License: GPLv2
"""Unit tests for the Bottom-Center Boss Name & Health Bar HUD."""
# pylint: disable=no-member,protected-access
import pygame
import pytest

import constants
from engine.enemy import (
    FinalAuthor,
    MeadowCensorBoss,
    Miniboss,
    MinibossM2,
    MinibossM3,
    NightBoss,
    RimecrestArbiterBoss,
    SlugBoss,
    SlugEnemy,
)
from engine.game_state import GameState
from engine.stats import StatisticsTracker
from engine.world import World
from rendering.renderer import Renderer


def _make_state():
    """Create a headless offline GameState with disk writes stubbed."""
    pygame.init()
    state = GameState(stats=StatisticsTracker(), auto_load=False, offline_only=True)
    state.network_manager.stop_network()
    state.save_stats = lambda wait=False: None
    state.in_sanctuary = False
    return state


def test_boss_display_names_across_all_boss_classes():
    """Verify every boss subclass resolves a clean player-facing HUD display name."""
    assert Miniboss(0, 0).get_display_name() == "Miniboss"
    assert Miniboss(0, 0, name="Overwritten Elite").get_display_name() == "Overwritten Elite"
    assert MinibossM2(0, 0).get_display_name() == "Bleeding Scribe"
    assert MinibossM3(0, 0).get_display_name() == "Forgotten Binder"
    assert NightBoss(0, 0).get_display_name() == "Night Boss"
    assert FinalAuthor(0, 0).get_display_name() == "The Final Author"

    slug = SlugBoss(0, 0)
    meadow = MeadowCensorBoss(0, 0)
    rime = RimecrestArbiterBoss(0, 0)
    assert slug.name == "Night Boss" and slug.get_display_name() == "The Crowned Slug"
    assert meadow.name == "Night Boss" and meadow.get_display_name() == "The Meadow Censor"
    assert rime.name == "Night Boss" and rime.get_display_name() == "The Rimecrest Arbiter"


def test_boss_hud_hidden_during_summoning_shown_on_emergence_updates_and_clears():
    """Boss HUD stays hidden during idle/erupting/emerging phases, appears on completion, tracks HP, clears on death."""
    state = _make_state()
    state.world = World("swamp_mire")
    state.world.load_from_prototype(["." * 16 for _ in range(16)])
    state.world.boss_coords_list = [{"x": 8, "y": 8}]
    state.current_act = 1
    state.run_biomes["act1"] = "swamp_mire"
    state.player.x = 1 * constants.TILE_SIZE
    state.player.y = 1 * constants.TILE_SIZE
    state.enemies = []
    state.weather_manager.set_boss_coords_list(state.world.boss_coords_list)
    state.weather_manager.bleed_state = "CLAMPED"

    # 1. Idle ground circle (player far away): hidden
    state._update_world_events(0.50)
    assert len(state.active_boss_summons) == 1
    assert state.get_active_boss_hud_info() is None

    # 2. Player walks close -> Stage 1 erupting (0.50s): still hidden
    ritual = state.active_boss_summons[0]
    state.player.x = ritual["cx"] - 60.0
    state.player.y = ritual["cy"]
    state._update_world_events(0.50)
    assert state.active_boss_summons[0]["erupting"] is True
    assert state.get_active_boss_hud_info() is None

    # 3. Stage 2 emerging behind veil (1.75s total, boss in enemies with summoning_emerge_timer > 0): still hidden
    state._update_world_events(1.25)
    assert len(state.enemies) == 1
    boss = state.enemies[0]
    assert isinstance(boss, SlugBoss)
    assert boss.summoning_emerge_timer > 0.0
    assert state.get_active_boss_hud_info() is None

    # 4. Summoning completes (>= 2.35s): HUD appears with full HP and canonical display name
    state._update_world_events(0.70)
    assert not state.active_boss_summons
    assert boss.summoning_emerge_timer == pytest.approx(0.0)
    info = state.get_active_boss_hud_info()
    assert info is not None
    assert info["boss"] is boss
    assert info["name"] == "The Crowned Slug"
    assert info["hp"] == pytest.approx(boss.max_hp)
    assert info["hp_ratio"] == pytest.approx(1.0)

    # 5. Boss takes damage -> HUD updates dynamically
    boss.take_damage(boss.max_hp * 0.4)
    updated = state.get_active_boss_hud_info()
    assert updated is not None
    assert updated["hp"] == pytest.approx(boss.max_hp * 0.6)
    assert updated["hp_ratio"] == pytest.approx(0.6)

    # 6. Boss defeated -> HUD clears automatically
    boss.hp = 0.0
    assert state.get_active_boss_hud_info() is None
    state.enemies.clear()
    assert state.get_active_boss_hud_info() is None


def test_boss_hud_dormant_miniboss_priority_proximity_and_sanctuary_gating():
    """Verify non-boss exclusion, dormant/proximity rules, priority ordering, and Sanctuary/death gating."""
    state = _make_state()
    state.player.x = 200.0
    state.player.y = 200.0

    # Regular enemies never trigger the boss HUD
    state.enemies = [SlugEnemy(220.0, 200.0)]
    assert state.get_active_boss_hud_info() is None

    # Dormant Miniboss stays hidden until emerged
    scribe = MinibossM2(260.0, 200.0)
    scribe.dormant_boss_summon = True
    state.enemies = [scribe]
    assert state.get_active_boss_hud_info() is None

    # Emerged Miniboss shows when within proximity, hides if player moves far away
    scribe.dormant_boss_summon = False
    info = state.get_active_boss_hud_info()
    assert info is not None and info["name"] == "Bleeding Scribe"

    state.player.x = 260.0 + constants.BOSS_HUD_PROXIMITY_RADIUS + 120.0
    assert state.get_active_boss_hud_info() is None

    # Priority: FinalAuthor (3) > NightBoss/Biome Boss (2) > Miniboss (1)
    state.player.x = 200.0
    meadow = MeadowCensorBoss(1600.0, 1600.0)
    state.enemies = [scribe, meadow]
    assert state.get_active_boss_hud_info()["name"] == "The Meadow Censor"

    author = FinalAuthor(1800.0, 1800.0)
    state.enemies = [scribe, meadow, author]
    assert state.get_active_boss_hud_info()["name"] == "The Final Author"

    # Hidden in Sanctuary or during player death sequence
    state.in_sanctuary = True
    assert state.get_active_boss_hud_info() is None
    state.in_sanctuary = False
    state.death_timer = 1.0
    assert state.get_active_boss_hud_info() is None


def test_boss_hud_headless_rendering_outline_fill_and_clear():
    """Verify headless bottom-center rendering (outline legibility, HP bar fill update, and clear on defeat)."""
    state = _make_state()
    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)

    bg_color = (235, 240, 245)  # Bright snow-like backdrop to verify dark outline contrast
    sw, sh = screen.get_size()
    bar_w = constants.BOSS_HUD_BAR_WIDTH
    bar_h = constants.BOSS_HUD_BAR_HEIGHT
    bar_x = (sw - bar_w) // 2
    bar_y = sh - constants.BOSS_HUD_BOTTOM_MARGIN - bar_h

    # 1. No active boss -> bottom-center stays clean
    state.enemies = []
    screen.fill(bg_color)
    renderer.draw_boss_hud(state)
    assert screen.get_at((sw // 2, bar_y + bar_h // 2))[:3] == bg_color

    # 2. Emerged RimecrestArbiterBoss at 100% HP -> draws dark outline + parchment name and full crimson bar
    boss = RimecrestArbiterBoss(300.0, 300.0)
    state.enemies = [boss]
    screen.fill(bg_color)
    renderer.draw_boss_hud(state)

    # Full bar has crimson fill near both left and right interior
    left_px = screen.get_at((bar_x + 20, bar_y + bar_h // 2))[:3]
    right_px = screen.get_at((bar_x + bar_w - 20, bar_y + bar_h // 2))[:3]
    assert left_px[0] > 150 and left_px[1] < 80
    assert right_px[0] > 150 and right_px[1] < 80

    # Name band directly above bar contains crisp dark outline pixels for contrast on bright backgrounds
    dark_outline_pixels = 0
    for y in range(max(0, bar_y - 44), bar_y - 2):
        for x in range(bar_x, bar_x + bar_w, 2):
            r, g, b = screen.get_at((x, y))[:3]
            if r < 40 and g < 40 and b < 40:
                dark_outline_pixels += 1
    assert dark_outline_pixels >= 30, "Boss name should render with a crisp dark outline/drop-shadow"

    # 3. Boss damaged to 25% HP -> left quarter crimson, right side empty dark track
    boss.hp = boss.max_hp * 0.25
    screen.fill(bg_color)
    renderer.draw_boss_hud(state)
    left_px_low = screen.get_at((bar_x + 20, bar_y + bar_h // 2))[:3]
    right_px_low = screen.get_at((bar_x + bar_w - 40, bar_y + bar_h // 2))[:3]
    assert left_px_low[0] > 150 and left_px_low[1] < 80
    assert right_px_low[0] < 60 and right_px_low[1] < 60

    # 4. Boss defeated -> HUD clears completely
    boss.hp = 0.0
    screen.fill(bg_color)
    renderer.draw_boss_hud(state)
    assert screen.get_at((sw // 2, bar_y + bar_h // 2))[:3] == bg_color
