"""
Unit tests for Batch 5 Pass 1:
1. Pastoral Valley stratum tile variants (ruled ledger lines on Stratum 1, (1, 1) == s_base invariant)
   and floor details (tar stepping stones & meadow wildflower clusters).
2. Bespoke Pastoral Valley props (pastoral_shepherd_cairn.png & pastoral_hay_crate.png) generation,
   preloading, and Biome-aware dispatch for Structure & Barrel.
3. Sun-drenched golden pollen & sunbeam atmosphere (draw_pastoral_valley_atmosphere).
4. Non-overlapping HUD weapon slots (SLOT A / SLOT B), stacked Swap / Pickup buttons, and fitted text widths.
"""
# pylint: disable=wrong-import-position,wrong-import-order,no-member,protected-access

import os

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame
import pytest

import constants
from engine.game_state import GameState
from engine.world import GameObject, WeaponPickup, World
from generate_assets import generate_pastoral_hay_crate, generate_pastoral_shepherd_cairn
from rendering.renderer import Renderer


@pytest.fixture(scope="module", autouse=True)
def init_pygame():
    """Initialize and cleanly tear down pygame in headless dummy mode."""
    pygame.init()
    yield
    pygame.quit()


def test_pastoral_valley_stratum_variants_and_ledger_lines():
    """Verify _build_pastoral_valley_stratum_variant preserves (1, 1) == s_base and draws ruled ledger lines."""
    ts = constants.TILE_SIZE
    pal = constants.BIOME_PALETTES["pastoral_valley"]
    strata = pal["strata"]

    for s_idx, (s_base, _s_alt) in enumerate(strata):
        variants = [
            Renderer._build_pastoral_valley_stratum_variant(ts, s_idx, v_idx, s_base)
            for v_idx in range(4)
        ]
        # Exact (1, 1) == s_base invariant on v_idx == 0
        assert variants[0].get_at((1, 1))[:3] == s_base
        # Variants are textured (not flat fills) and distinct across indices
        raw_bytes = [pygame.image.tostring(v, "RGB") for v in variants]
        assert len(set(raw_bytes)) == 4

    # Stratum 1 (meadow turf) includes horizontal ruled parchment ledger lines (~10px spacing)
    meadow_base = strata[1][0]
    meadow_v0 = Renderer._build_pastoral_valley_stratum_variant(ts, 1, 0, meadow_base)
    ledger_expected = Renderer._shift_rgb_clamped(meadow_base, 14, -4, -10)
    ledger_hits = sum(1 for x in range(ts) if meadow_v0.get_at((x, 8))[:3] == ledger_expected)
    assert ledger_hits >= ts // 2, "Expected horizontal ruled parchment ledger line across Stratum 1 meadow tile"

    # _draw_pastoral_valley_floor_details draws tar stepping stones (s_idx=0, pat=1) and wildflowers (s_idx=1)
    tar_surf = pygame.Surface((ts, ts))
    tar_surf.fill(strata[0][0])
    Renderer._draw_pastoral_valley_floor_details(tar_surf, pal, 0, (0, 0, 0, 0, ts), pat=1)
    assert tar_surf.get_at((20, 28))[:3] != strata[0][0]

    meadow_surf = pygame.Surface((ts, ts))
    meadow_surf.fill(meadow_base)
    Renderer._draw_pastoral_valley_floor_details(meadow_surf, pal, 1, (0, 0, 0, 0, ts), pat=0)
    assert meadow_surf.get_at((10, 12))[:3] != meadow_base


def test_pastoral_valley_props_generate_preload_and_dispatch(monkeypatch):
    """Verify common meadow rock, rare shepherd cairn & hay crate sprites exist, preload, and dispatch."""
    rock_path = os.path.join("assets", "graphics", "pastoral_rock.png")
    cairn_path = os.path.join("assets", "graphics", "pastoral_shepherd_cairn.png")
    crate_path = os.path.join("assets", "graphics", "pastoral_hay_crate.png")
    assert os.path.exists(rock_path), f"Missing generated asset: {rock_path}"
    assert os.path.exists(cairn_path), f"Missing generated asset: {cairn_path}"
    assert os.path.exists(crate_path), f"Missing generated asset: {crate_path}"

    assert pygame.image.load(rock_path).get_size() == (40, 60)
    assert pygame.image.load(cairn_path).get_size() == (40, 60)
    assert pygame.image.load(crate_path).get_size() == (40, 40)

    gen_cairn = generate_pastoral_shepherd_cairn()
    gen_crate = generate_pastoral_hay_crate()
    assert gen_cairn.get_size() == (40, 60) and gen_cairn.get_at((0, 0)).a == 0
    assert gen_crate.get_size() == (40, 40) and gen_crate.get_at((0, 0)).a == 0

    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)
    assert "PastoralRock" in renderer.prop_cache
    assert renderer.prop_cache["PastoralRock"].get_size() == (40, 60)
    assert "PastoralShepherdCairn" in renderer.prop_cache
    assert renderer.prop_cache["PastoralShepherdCairn"].get_size() == (40, 60)
    assert "PastoralHayCrate" in renderer.prop_cache
    assert renderer.prop_cache["PastoralHayCrate"].get_size() == (40, 40)

    state = GameState(auto_load=False)
    state.network_manager.stop_network()
    try:
        state.world = World("pastoral_valley")
        state.world.load_from_prototype(["." * 12 for _ in range(12)])
        state.player.x = 120.0
        state.player.y = 120.0
        state.camera.instant_center((160.0, 160.0))

        # Pick deterministic rare-cairn tile and common-rock tile inside the 12x12 room
        rare_tile = next(
            (tx, ty) for tx in range(1, 10) for ty in range(1, 10) if renderer._is_pastoral_rare_cairn(tx, ty)
        )
        rock_tile = next(
            (tx, ty) for tx in range(1, 10) for ty in range(1, 10) if not renderer._is_pastoral_rare_cairn(tx, ty)
        )

        cairn_obj = GameObject((rare_tile[0] * 40, rare_tile[1] * 40), (40, 40))
        cairn_obj.name = "Structure"
        cairn_obj.is_solid = True

        rock_obj = GameObject((rock_tile[0] * 40, rock_tile[1] * 40), (40, 40))
        rock_obj.name = "Structure"
        rock_obj.is_solid = True

        crate_obj = GameObject((200, 160), (40, 40))
        crate_obj.name = "Barrel"
        crate_obj.is_solid = True
        crate_obj.is_breakable = True
        state.world.interactables = [cairn_obj, rock_obj, crate_obj]

        dispatched = []
        orig_rock = renderer._draw_pastoral_rock
        orig_cairn = renderer._draw_pastoral_shepherd_cairn
        orig_crate = renderer._draw_pastoral_hay_crate

        def _spy_rock(*args, **kwargs):
            dispatched.append("rock")
            return orig_rock(*args, **kwargs)

        def _spy_cairn(*args, **kwargs):
            dispatched.append("cairn")
            return orig_cairn(*args, **kwargs)

        def _spy_crate(*args, **kwargs):
            dispatched.append("crate")
            return orig_crate(*args, **kwargs)

        monkeypatch.setattr(renderer, "_draw_pastoral_rock", _spy_rock)
        monkeypatch.setattr(renderer, "_draw_pastoral_shepherd_cairn", _spy_cairn)
        monkeypatch.setattr(renderer, "_draw_pastoral_hay_crate", _spy_crate)

        renderer.render(state)
        assert "rock" in dispatched
        assert "cairn" in dispatched
        assert "crate" in dispatched
    finally:
        state.shutdown_save_worker(timeout=1.0)


def test_pastoral_valley_golden_pollen_atmosphere_and_biome_gating():
    """Verify draw_pastoral_valley_atmosphere caches sunbeams & pollen motes only on pastoral_valley."""
    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)
    state = GameState(auto_load=False)
    state.network_manager.stop_network()
    try:
        # Non-pastoral biome: must remain a no-op
        state.world = World("windy_ridge")
        state.world.load_from_prototype(["." * 8 for _ in range(8)])
        state.player.x, state.player.y = 80.0, 80.0
        renderer._fx_surface_cache.clear()
        renderer.draw_pastoral_valley_atmosphere(state, 0.0, 0.0, now=1.5)
        assert not any(k[0].startswith("pastoral_") for k in renderer._fx_surface_cache)

        # Pastoral Valley: renders & caches sunbeams and golden pollen motes
        state.world = World("pastoral_valley")
        state.world.load_from_prototype(["." * 8 for _ in range(8)])
        renderer.draw_pastoral_valley_atmosphere(state, 0.0, 0.0, now=1.5)
        keys = list(renderer._fx_surface_cache.keys())
        assert any(k[0] == "pastoral_sunbeam" for k in keys)
        assert any(k[0] == "pastoral_pollen_mote" for k in keys)
    finally:
        state.shutdown_save_worker(timeout=1.0)


def test_hud_weapon_slots_and_buttons_non_overlapping_and_text_fits():
    """Verify tall compact 252x148 HUD layout, side-by-side slots, status row, and floating pickup pill."""
    assert constants.HUD_PANEL_W == 252
    assert constants.HUD_PANEL_H == 148

    hp_rect = pygame.Rect(8, 10, 236, 15)
    icon_rect = pygame.Rect(8, 33, 236, 19)
    slot_a = pygame.Rect(8, 58, constants.HUD_SLOT_W, constants.HUD_SLOT_H)
    slot_b = pygame.Rect(130, 58, constants.HUD_SLOT_W, constants.HUD_SLOT_H)
    swap_rect = pygame.Rect(constants.HUD_SWAP_BTN_RECT)
    pickup_rect = pygame.Rect(constants.HUD_PICKUP_BTN_RECT)
    status_rect = pygame.Rect(8, 121, 236, 19)

    assert swap_rect == slot_b
    assert pickup_rect.y == -26 and pickup_rect.bottom < 0

    in_card_rects = (hp_rect, icon_rect, slot_a, slot_b, status_rect)
    for idx, r_a in enumerate(in_card_rects):
        assert r_a.left >= 0 and r_a.right <= constants.HUD_PANEL_W
        assert r_a.top >= 0 and r_a.bottom <= constants.HUD_PANEL_H
        for r_b in in_card_rects[idx + 1:]:
            assert not r_a.colliderect(r_b), f"HUD rects overlap: {r_a} vs {r_b}"

    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)

    # Verify "Initial Quill" fits completely inside SLOT A with slot_font
    quill_w, _ = renderer.slot_font.size("Initial Quill")
    assert 12 + quill_w <= slot_a.width, f"'Initial Quill' ({quill_w}px) exceeds SLOT A width ({slot_a.width}px)"

    # Verify clean contextual pickup pill text fits cleanly inside floating pill width
    pill_w, pill_h = renderer.slot_font.size("Pick Up Refined Quill")
    assert pill_w <= pickup_rect.width - 8 and pill_h <= pickup_rect.height

    # Smoke-render draw_hud while standing over a WeaponPickup so the floating pill renders cleanly
    state = GameState(auto_load=False)
    state.network_manager.stop_network()
    try:
        state.player.current_interactable = WeaponPickup((100, 100), {"name": "Refined Quill", "damage": 18})
        renderer.draw_hud(state)
    finally:
        state.shutdown_save_worker(timeout=1.0)
