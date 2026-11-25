# copyright 2026 Dustin Massop, License: GPLv2
"""Unit tests for Item #17: 8-Direction Steep-Overhead Player Rig & Visible Equipped Weapons."""
# pylint: disable=no-member,protected-access,too-many-locals

import math
import os

import pygame
import pytest

import constants
from engine.game_state import GameState
from engine.player import Player, PlayerStateEnum
from engine.stats import StatisticsTracker
from generate_assets import generate_player_hood_sprite
from rendering.renderer import Renderer


def _ensure_pygame():
    if "SDL_VIDEODRIVER" not in os.environ and not pygame.display.get_init():
        os.environ["SDL_VIDEODRIVER"] = "dummy"
    pygame.init()


def test_8_direction_angle_mapping_and_mirror_specs():
    """Verify exact 8-way compass quantization, boundary behavior, and horizontal mirror specs."""
    cardinal_and_diag = [
        ((1.0, 0.0), "e"),
        ((1.0, 1.0), "se"),
        ((0.0, 1.0), "s"),
        ((-1.0, 1.0), "sw"),
        ((-1.0, 0.0), "w"),
        ((-1.0, -1.0), "nw"),
        ((0.0, -1.0), "n"),
        ((1.0, -1.0), "ne"),
    ]
    for vec, expected in cardinal_and_diag:
        assert constants.facing_to_direction_8(vec) == expected

    # Near-octant boundary angles (+/- 15 deg from each axis stay in that octant)
    for deg_center, expected in (
        (0.0, "e"),
        (45.0, "se"),
        (90.0, "s"),
        (135.0, "sw"),
        (180.0, "w"),
        (-135.0, "nw"),
        (-90.0, "n"),
        (-45.0, "ne"),
    ):
        for offset in (-15.0, 0.0, 15.0):
            rad = math.radians(deg_center + offset)
            assert constants.facing_to_direction_8((math.cos(rad), math.sin(rad))) == expected

    # Degenerate zero/None facing defaults safely to 's'
    assert constants.facing_to_direction_8((0.0, 0.0)) == "s"
    assert constants.facing_to_direction_8(None) == "s"

    # Mirror map: 5 unique unflipped + 3 mirrored west directions
    assert constants.resolve_player_rig_sprite_spec("n") == ("n", False)
    assert constants.resolve_player_rig_sprite_spec("ne") == ("ne", False)
    assert constants.resolve_player_rig_sprite_spec("e") == ("e", False)
    assert constants.resolve_player_rig_sprite_spec("se") == ("se", False)
    assert constants.resolve_player_rig_sprite_spec("s") == ("s", False)
    assert constants.resolve_player_rig_sprite_spec("nw") == ("ne", True)
    assert constants.resolve_player_rig_sprite_spec("w") == ("e", True)
    assert constants.resolve_player_rig_sprite_spec("sw") == ("se", True)

    # Player helper & visual packet expose quantized facing_dir and walk anim_timer
    player = Player(100, 100)
    player.facing = (-1.0, -1.0)
    assert player.get_facing_direction_8() == "nw"
    player.update(0.25, (-1.0, 0.0), [], {})
    pkt = player.get_visual_packet()
    assert pkt["facing_dir"] == "w"
    assert pkt["anim_timer"] == pytest.approx(0.25, abs=1e-4)
    assert pkt["weapon"]["name"] == "Initial Quill"


def test_player_hood_sprite_generation_and_preloading():
    """Verify all 20 hood-and-shoulder PNGs exist, are distinct, and preload into all 32 8-dir slots."""
    _ensure_pygame()
    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)

    disk_signatures = {}
    for p_dir in constants.PLAYER_RIG_UNIQUE_DIRECTIONS:
        for p_pose in constants.PLAYER_RIG_POSES:
            fname = f"player_hood_{p_dir}_{p_pose}.png"
            fpath = os.path.join("assets", "graphics", fname)
            assert os.path.exists(fpath), f"Missing generated player rig asset: {fpath}"
            assert fname in renderer.image_cache, f"{fname} not preloaded in image_cache"
            assert (p_dir, p_pose) in renderer.player_rig_sprites

            surf = renderer.player_rig_sprites[(p_dir, p_pose)]
            assert surf.get_size() == (
                constants.PLAYER_RIG_SPRITE_WIDTH,
                constants.PLAYER_RIG_SPRITE_HEIGHT,
            )
            raw = pygame.image.tobytes(surf, "RGBA")
            alphas = raw[3::4]
            assert any(a == 255 for a in alphas), f"{fname} has no opaque pixels"
            assert any(a == 0 for a in alphas), f"{fname} has no transparent background"
            disk_signatures[(p_dir, p_pose)] = raw

    # All 20 canonical (5 dirs x 4 poses) PNGs must be visually distinct
    assert len(set(disk_signatures.values())) == 20

    # All 32 (8 dirs x 4 poses) slots preloaded, with NW/W/SW equal to horizontal flips of NE/E/SE
    assert len(renderer.player_rig_sprites) == 32
    for west_dir, east_dir in (("nw", "ne"), ("w", "e"), ("sw", "se")):
        for p_pose in constants.PLAYER_RIG_POSES:
            west_surf = renderer.player_rig_sprites[(west_dir, p_pose)]
            east_flipped = pygame.transform.flip(renderer.player_rig_sprites[(east_dir, p_pose)], True, False)
            assert pygame.image.tobytes(west_surf, "RGBA") == pygame.image.tobytes(east_flipped, "RGBA")

    # Direct generator check: North/NE sprites have no glowing cyan eyes; S/SE/E sprites do
    eye_rgb = constants.COLOR_PLAYER_EYE
    for d_back in ("n", "ne"):
        back_surf = generate_player_hood_sprite(direction=d_back, pose="idle")
        pixels = {
            back_surf.get_at((x, y))[:3]
            for x in range(back_surf.get_width())
            for y in range(back_surf.get_height())
            if back_surf.get_at((x, y)).a > 0
        }
        assert eye_rgb not in pixels, f"Back-facing direction {d_back!r} should not render forward eyes"

    for d_front in ("s", "se", "e"):
        front_surf = generate_player_hood_sprite(direction=d_front, pose="idle")
        pixels = {
            front_surf.get_at((x, y))[:3]
            for x in range(front_surf.get_width())
            for y in range(front_surf.get_height())
            if front_surf.get_at((x, y)).a > 0
        }
        assert eye_rgb in pixels, f"Forward/side direction {d_front!r} should render glowing eyes"


def test_weapon_layer_depth_ordering_north_vs_south():
    """Verify weapon renders behind the body when facing north (N/NE/NW) and in front otherwise."""
    _ensure_pygame()
    screen = pygame.Surface((200, 200), pygame.SRCALPHA)
    renderer = Renderer(screen)

    for north_dir in ("n", "ne", "nw"):
        assert constants.get_player_weapon_layer(north_dir) == "behind"
    for front_dir in ("s", "se", "sw", "e", "w"):
        assert constants.get_player_weapon_layer(front_dir) == "front"

    rect = pygame.Rect(80, 80, 40, 40)
    bleed_wpn = {"name": "Anomalous Ink-Bleed", "damage": 24, "modifiers": {"bleed": 5.0}}

    # North-facing draw order: weapon_behind strictly before body_sprite
    north_layers = []
    renderer.draw_player_rig(
        rect,
        facing=(0.0, -1.0),
        base_state="IDLE",
        weapon_data=bleed_wpn,
        anim_time=0.0,
        record_layers=north_layers,
    )
    assert "weapon_behind" in north_layers
    assert "weapon_front" not in north_layers
    assert north_layers.index("weapon_behind") < north_layers.index("body_sprite")

    # NE / NW also layer behind body
    for vec in ((1.0, -1.0), (-1.0, -1.0)):
        diag_layers = []
        renderer.draw_player_rig(
            rect, facing=vec, base_state="RUN", weapon_data=bleed_wpn, anim_time=0.1, record_layers=diag_layers
        )
        assert diag_layers.index("weapon_behind") < diag_layers.index("body_sprite")

    # South-facing draw order: weapon_front strictly after body_sprite
    south_layers = []
    renderer.draw_player_rig(
        rect,
        facing=(0.0, 1.0),
        base_state="IDLE",
        weapon_data=bleed_wpn,
        anim_time=0.0,
        record_layers=south_layers,
    )
    assert "weapon_front" in south_layers
    assert "weapon_behind" not in south_layers
    assert south_layers.index("body_sprite") < south_layers.index("weapon_front")

    # Pixel-level occlusion verification with a synthetic bright-magenta weapon at the body center
    magenta = (255, 0, 220, 255)
    test_wpn_surf = pygame.Surface((40, 40), pygame.SRCALPHA)
    test_wpn_surf.fill(magenta)
    renderer.prop_cache["TestOcclusionWeapon"] = test_wpn_surf
    try:
        surf_north = pygame.Surface((160, 160), pygame.SRCALPHA)
        renderer.screen = surf_north
        renderer.draw_player_rig(
            pygame.Rect(60, 60, 40, 40),
            facing=(0.0, -1.0),
            base_state="IDLE",
            weapon_key="TestOcclusionWeapon",
            anim_time=0.0,
        )
        # Body hood center (80, 74) must NOT be magenta when facing north (body occludes weapon)
        north_center = surf_north.get_at((80, 74))
        assert (north_center.r, north_center.g, north_center.b) != (255, 0, 220)

        surf_south = pygame.Surface((160, 160), pygame.SRCALPHA)
        renderer.screen = surf_south
        renderer.draw_player_rig(
            pygame.Rect(60, 60, 40, 40),
            facing=(0.0, 1.0),
            base_state="IDLE",
            weapon_key="TestOcclusionWeapon",
            anim_time=0.0,
        )
        # Weapon sits in front of the lower-left body region (around hand anchor (71, 87)) when facing south
        south_hand = surf_south.get_at((71, 87))
        assert south_hand.r > 200 and south_hand.b > 160 and south_hand.g < 40
    finally:
        renderer.prop_cache.pop("TestOcclusionWeapon", None)


def test_equipped_weapon_visuals_rotation_and_headless_rendering():
    """Verify visible equipped weapon changes with loadout, rotation math, and headless rendering."""
    _ensure_pygame()

    # Rotation math aligns NE-tip blades and SW-nib quills to East (0 rad)
    assert constants.compute_player_weapon_rotation_deg(0.0, "WeaponScriberBlade") == pytest.approx(-45.0)
    assert constants.compute_player_weapon_rotation_deg(0.0, "WeaponQuillStandard") == pytest.approx(135.0)

    # Rendering different equipped floor-pickup weapons yields visibly distinct output
    surf_a = pygame.Surface((160, 160), pygame.SRCALPHA)
    renderer = Renderer(surf_a)
    rect = pygame.Rect(60, 60, 40, 40)

    renderer.draw_player_rig(
        rect,
        facing=(1.0, 0.0),
        base_state="IDLE",
        weapon_data={"name": "Initial Quill", "damage": 10},
        anim_time=0.0,
    )
    bytes_quill = pygame.image.tobytes(surf_a, "RGBA")

    surf_b = pygame.Surface((160, 160), pygame.SRCALPHA)
    renderer.screen = surf_b
    renderer.draw_player_rig(
        rect,
        facing=(1.0, 0.0),
        base_state="IDLE",
        weapon_data={"name": "Anomalous Ink-Bleed", "damage": 24, "modifiers": {"bleed": 5.0}},
        anim_time=0.0,
    )
    bytes_bleed = pygame.image.tobytes(surf_b, "RGBA")
    assert bytes_quill != bytes_bleed

    # Reusable remote-player style call (#19 contract): explicit weapon_key + Cyan/Magenta trim + attack sweep
    surf_remote = pygame.Surface((160, 160), pygame.SRCALPHA)
    renderer.screen = surf_remote
    remote_layers = []
    assert renderer.draw_player_rig(
        rect,
        facing=(0.7, 0.7),
        base_state="ATTACK",
        weapon_key="WeaponAnomalousRegen",
        anim_time=0.2,
        attack_progress=0.5,
        trim_color=constants.COLOR_CYAN,
        record_layers=remote_layers,
    ) is True
    assert "body_sprite" in remote_layers
    assert "weapon_front" in remote_layers

    # Full headless GameState render sweep across all 8 directions & states (IDLE, MOVING, ATTACKING, DASHING, BLOCKING)
    full_screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    full_renderer = Renderer(full_screen)
    state = GameState(auto_load=False, stats=StatisticsTracker())
    try:
        state.player.weapons = [
            {"name": "Anomalous Ink-Bleed", "damage": 24, "modifiers": {"bleed": 5.0}},
            {"name": "Scriber Blade", "damage": 16},
        ]
        for facing_vec in (
            (0, -1), (1, -1), (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1)
        ):
            state.player.facing = facing_vec
            state.player.state = PlayerStateEnum.MOVING
            state.player.walk_anim_timer += 0.15
            full_renderer.render(state)

        for p_state in (
            PlayerStateEnum.IDLE,
            PlayerStateEnum.ATTACKING,
            PlayerStateEnum.DASHING,
            PlayerStateEnum.BLOCKING,
        ):
            state.player.state = p_state
            state.player.attack_timer = constants.SWORD_DURATION * 0.5 if p_state == PlayerStateEnum.ATTACKING else 0.0
            full_renderer.render(state)
    finally:
        state.shutdown_save_worker(timeout=1.0)
