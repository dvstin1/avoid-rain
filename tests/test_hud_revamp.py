"""
Unit tests for Batch 8 — Tall Compact Visual HUD Revamp (252x148):
1. Panel geometry, side-by-side weapon cards, SLOT B swap rect, and floating pickup pill bounds.
2. Cached procedural HUD mini-icons (Flask full/empty, Scholar, Torn Page, Weapon) with zero per-frame churn.
3. Crimson HP bar + 4px icy-cyan Frost Exposure / Ice-Block sub-bar rendering.
4. Flask & Scholar icon counts (no text clutter / no keybind shortcut strings like 'Q / L1' or 'SPACE / A').
5. Contextual floating 'Pick Up <Weapon>' pill rendered directly on screen above the HUD card and clickable.
"""
# pylint: disable=wrong-import-position,wrong-import-order,no-member,protected-access

import os

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame
import pytest

import constants
from engine.game_state import GameState
from engine.world import WeaponPickup, World
from rendering.renderer import Renderer


@pytest.fixture(scope="module", autouse=True)
def init_pygame():
    """Initialize and cleanly tear down pygame in headless dummy mode."""
    pygame.init()
    yield
    pygame.quit()


def test_hud_compact_geometry_and_cached_mini_icons():
    """Verify 252x148 HUD panel geometry and cached SRCALPHA mini-icons reuse identical surfaces."""
    assert (constants.HUD_PANEL_W, constants.HUD_PANEL_H) == (252, 148)
    assert (constants.HUD_SLOT_W, constants.HUD_SLOT_H) == (114, 58)
    assert constants.HUD_SWAP_BTN_RECT == (130, 58, 114, 58)
    assert constants.HUD_PICKUP_BTN_RECT == (8, -26, 236, 22)

    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)

    full_1 = renderer._get_hud_mini_icon("hud_flask_full")
    full_2 = renderer._get_hud_mini_icon("hud_flask_full")
    empty_1 = renderer._get_hud_mini_icon("hud_flask_empty")
    scholar_1 = renderer._get_hud_mini_icon("hud_scholar_icon")
    page_1 = renderer._get_hud_mini_icon("hud_page_icon")

    assert full_1 is full_2
    assert full_1.get_size() == (16, 16)
    assert empty_1.get_size() == (16, 16)
    assert scholar_1.get_size() == (16, 16)
    assert page_1.get_size() == (14, 14)
    # Full flask and empty flask must be visually distinct
    assert pygame.image.tostring(full_1, "RGBA") != pygame.image.tostring(empty_1, "RGBA")


def test_hud_crimson_hp_bar_frost_subbar_and_zero_keybind_clutter(monkeypatch):
    """Verify crimson HP bar, conditional frost sub-bar, status pills, and zero keybind text labels."""
    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)
    state = GameState(auto_load=False)
    state.network_manager.stop_network()
    try:
        state.player.hp = 60.0
        state.player.flask_charges = 2
        state.player.frost_exposure = 0.65
        state.player.negation_timer = 2.0
        state.player.negation_amount = 5.0
        state.player.weapons.append({"name": "Refined Quill", "damage": 18})
        state.network_manager.remote_players = {"peer_2": {"x": 0, "y": 0}}
        state.player.current_interactable = WeaponPickup((100, 100), {"name": "Anomalous Blade", "damage": 24})

        rendered_strings = []
        orig_render = renderer.slot_font.render

        def _spy_render(text, antialias, color, *args, **kwargs):
            rendered_strings.append(str(text))
            return orig_render(text, antialias, color, *args, **kwargs)

        monkeypatch.setattr(renderer.slot_font, "render", _spy_render)

        screen.fill((0, 0, 0))
        renderer.draw_hud(state)

        # Zero keybind shortcut clutter or old text-counter clutter anywhere on HUD
        joined = " | ".join(rendered_strings)
        for forbidden in ("Q / L1", "SPACE / A", "(GP)", "[1]", "[SPACE]", "Scholars:", "Flasks:"):
            assert forbidden not in joined, f"Unexpected HUD clutter '{forbidden}' in {rendered_strings}"

        assert "SLOT A" in rendered_strings
        assert "SLOT B" in rendered_strings
        assert any(s.startswith("Pick Up Anomalous Blade") for s in rendered_strings)
        assert any(s.startswith("WARD") for s in rendered_strings)

        # Crimson HP bar pixels drawn in Row 1 inside hud_surf
        hud_surf = renderer._hud_surf
        assert hud_surf.get_size() == (252, 148)
        hp_col = hud_surf.get_at((24, 17))
        assert hp_col.r > 160 and hp_col.g < 80, f"Expected crimson HP fill, got {hp_col}"

        # 4px icy-cyan Frost sub-bar drawn at y=26..29 when frost_exposure > 0
        frost_col = hud_surf.get_at((24, 27))
        assert frost_col.b > 200 and frost_col.g > 200, f"Expected icy-cyan frost gauge, got {frost_col}"

        # Floating contextual pickup pill drawn directly on screen above the HUD card
        hud_x = 10
        hud_y = constants.SCREEN_HEIGHT - constants.HUD_PANEL_H - 10
        pill_sample = screen.get_at((hud_x + 12, hud_y - 20))
        assert pill_sample[:3] != (0, 0, 0), "Expected floating pickup pill drawn above HUD card"

        # Expanded Inspect View over a WeaponPickup renders cleanly without NameError
        state.inspect_active = True
        renderer.draw_hud(state)
    finally:
        state.shutdown_save_worker(timeout=1.0)


def test_hud_icon_counts_and_slot_click_interactions():
    """Verify Flask/Scholar icon rendering across counts and SLOT B / Pickup pill click hit-testing."""
    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)
    state = GameState(auto_load=False)
    state.network_manager.stop_network()
    try:
        state.world = World("sanctuary")
        state.world.load_from_prototype(["." * 8 for _ in range(8)])
        state.player.x, state.player.y = 120.0, 120.0
        state.player.weapons.append({"name": "Scriber's Blade", "damage": 21})

        # 1. Flask icon strip reflects 0 vs 3 charges visually
        state.player.flask_charges = 0
        renderer.draw_hud(state)
        empty_strip = pygame.image.tostring(renderer._hud_surf.subsurface((8, 34, 56, 16)), "RGBA")

        state.player.flask_charges = 3
        renderer.draw_hud(state)
        full_strip = pygame.image.tostring(renderer._hud_surf.subsurface((8, 34, 56, 16)), "RGBA")
        assert empty_strip != full_strip

        # 2. Scholar icon strip reflects 1 vs 3 scholars visually
        state.network_manager.remote_players = {}
        renderer.draw_hud(state)
        one_scholar_strip = pygame.image.tostring(renderer._hud_surf.subsurface((82, 34, 62, 16)), "RGBA")

        state.network_manager.remote_players = {"p2": {}, "p3": {}}
        renderer.draw_hud(state)
        three_scholar_strip = pygame.image.tostring(renderer._hud_surf.subsurface((82, 34, 62, 16)), "RGBA")
        assert one_scholar_strip != three_scholar_strip

        # 3. Clicking SLOT B (HUD_SWAP_BTN_RECT) swaps 0 -> 1, and clicking inactive SLOT A swaps 1 -> 0
        hx = 10
        hy = constants.SCREEN_HEIGHT - constants.HUD_PANEL_H - 10
        swr = constants.HUD_SWAP_BTN_RECT
        assert state.player.active_weapon_idx == 0
        state._handle_hud_interactions({"mouse_click": (hx + swr[0] + 20, hy + swr[1] + 20)})
        assert state.player.active_weapon_idx == 1
        state._handle_hud_interactions({"mouse_click": (hx + 20, hy + swr[1] + 20)})
        assert state.player.active_weapon_idx == 0

        # 4. Clicking floating Pickup pill above HUD card picks up / swaps standing WeaponPickup
        pickup = WeaponPickup((120, 120), {"name": "Glacier Quill", "damage": 26})
        state.world.interactables.append(pickup)
        state.player.current_interactable = pickup
        pkr = constants.HUD_PICKUP_BTN_RECT
        state._handle_hud_interactions({"mouse_click": (hx + pkr[0] + 20, hy + pkr[1] + 10)})
        assert any(w["name"] == "Glacier Quill" for w in state.player.weapons)
        assert pickup.weapon_data["name"] == "Initial Quill"
    finally:
        state.shutdown_save_worker(timeout=1.0)
