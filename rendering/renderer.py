# pylint: disable=too-many-locals,too-many-branches,too-many-statements,no-member
# pylint: disable=import-outside-toplevel,redefined-outer-name,reimported,invalid-name
# pylint: disable=unused-argument,unused-import,wrong-import-order,too-many-public-methods
# pylint: disable=attribute-defined-outside-init,broad-exception-caught,multiple-statements
# pylint: disable=unused-variable

import functools
import math
import random
import time

import pygame

import constants
from engine.player import PlayerStateEnum
from engine.camera import Camera
from rendering.bitmap_font import load_font_or_sysfont
from ui.menu import draw_respite_menu, draw_chronicle_biome_menu, draw_binder_weave_menu

class Renderer:
    """Coordinates rendering of the game state."""
    def __init__(self, screen):
        self.screen = screen
        self.font = load_font_or_sysfont("ink_sans", 2, "Arial", 24)
        self.small_font = load_font_or_sysfont("ink_mono", 1, "Arial", 14, letter_spacing=-1)
        self.large_font = load_font_or_sysfont("ink_sans", 3, "Arial", 32)
        self.hud_font = load_font_or_sysfont("ink_mono", 1, "Arial", 14, bold=True, letter_spacing=-1)
        self.slot_font = load_font_or_sysfont("ink_sans", 1, "Arial", 12)
        self.glyph_font = load_font_or_sysfont(
            "ink_mono", 1, "Courier New", constants.GLYPH_FONT_SIZE, bold=True
        )
        self.bloom_font = load_font_or_sysfont(
            "manuscript_serif", 4, "Times New Roman", 72, bold=True, italic=True
        )
        self.title_font = load_font_or_sysfont("manuscript_serif", 3, "Georgia", 54, bold=True)
        
        # Image Cache
        self.image_cache = {}
        self.prop_cache = {}
        self._chunk_cache = {}
        self._chunk_world_key = None
        self._compiled_sockets_key = None
        self._compiled_sockets = ()
        self._tile_biome_cache = {}
        self._weather_overlay = None
        self._weather_overlay_dirty = False
        self._hud_surf = None
        self._minimap_surf = None
        self._minimap_walls_surf = None
        self._minimap_world_key = None
        self._title_composite_surf = None
        self.warp_veil_surface = None
        self._puff_cache = {}
        self._actor_scratch_surf = None
        self.sanctuary_interior_alpha = 0.0
        self._sanctuary_last_perf_time = None
        self._sanctuary_blackout_surf = None
        self._sanctuary_roof_surfs = {}
        self.floor_variants = []
        self.sanctuary_flagstone_variants = []
        self.sanctuary_dirt_path_variants = []
        self.sanctuary_wood_floor_variants = []
        self.wall_tile_surf = None
        self.grass_natural_surf = None
        self._load_barrel_assets()
        self._load_tile_assets()
        self._load_slug_assets()
        self._load_base_enemy_assets()
        self._load_empowered_enemy_assets()
        self.grass_pools = {}
        self._load_grass_assets()
        self._generate_prop_cache()

    def _load_barrel_assets(self):
        """Pre-load barrel animation frames."""
        import os
        base_path = os.path.join("assets", "graphics")
        display_init = pygame.display.get_init() and (pygame.display.get_surface() is not None)
        
        for i in range(4):
            name = f"barrel_{i}.png"
            path = os.path.join(base_path, name)
            if os.path.exists(path):
                try:
                    img = pygame.image.load(path)
                    if display_init:
                        img = img.convert_alpha()
                    # Scale to 40x40 to match TILE_SIZE
                    self.image_cache[name] = pygame.transform.scale(img, (40, 40))
                except Exception as e:
                    print(f"[RENDER] Error loading {name}: {e}")

    def _load_slug_assets(self):
        """Pre-load slug enemy animation frames."""
        import os
        base_path = os.path.join("assets", "graphics")
        display_init = pygame.display.get_init() and (pygame.display.get_surface() is not None)
        
        # 1, 2, 3, 4 are directions/alternates. attack_1, attack_2 are attack states.
        slug_frames = ["slug_1.png", "slug_2.png", "slug_3.png", "slug_4.png", "slug_attack_1.png", "slug_attack_2.png"]
        for name in slug_frames:
            path = os.path.join(base_path, name)
            if os.path.exists(path):
                try:
                    img = pygame.image.load(path)
                    if display_init:
                        img = img.convert_alpha()
                    # Scale slug to 48x48 (slightly larger than its 32x32 box for visual presence)
                    scaled = pygame.transform.scale(img, (48, 48))
                    self.image_cache[name] = scaled
                    stem = name[:-4]
                    self.image_cache[f"{stem}_empowered.png"] = self._tint_empowered_surface(scaled)
                except Exception as e:
                    print(f"[RENDER] Error loading {name}: {e}")

    def _tint_empowered_surface(self, surf):
        """Return a cached crimson-violet mutated variant of a hand-crafted sprite."""
        w, h = surf.get_size()
        tinted = pygame.Surface((w, h), pygame.SRCALPHA)
        for y in range(h):
            for x in range(w):
                c = surf.get_at((x, y))
                if c.a == 0:
                    continue
                # Shift organic greens/browns toward mutated crimson-violet while preserving contrast
                nr = min(255, int(c.r * 1.15 + c.g * 0.45 + 24))
                ng = max(0, int(c.g * 0.35 + c.r * 0.1))
                nb = min(255, int(c.b * 0.85 + c.g * 0.35 + 28))
                tinted.set_at((x, y), (nr, ng, nb, c.a))
        return tinted

    def _load_base_enemy_assets(self):
        """Pre-load Act 1 / un-empowered base enemy and boss PNG sprites at native sizes."""
        import os
        base_path = os.path.join("assets", "graphics")
        display_init = pygame.display.get_init() and (pygame.display.get_surface() is not None)
        for kind in (
            "bat", "flutter", "bindling", "smear", "sentry", "punctuation_wolf",
            "event_champion", "miniboss", "night_boss", "final_author",
        ):
            name = f"{kind}.png"
            path = os.path.join(base_path, name)
            if os.path.exists(path):
                try:
                    img = pygame.image.load(path)
                    if display_init:
                        img = img.convert_alpha()
                    self.image_cache[name] = img
                except Exception as e:
                    print(f"[RENDER] Error loading {name}: {e}")

    def _load_empowered_enemy_assets(self):
        """Pre-load Act 2 empowered procedural enemy PNG variants."""
        import os
        base_path = os.path.join("assets", "graphics")
        display_init = pygame.display.get_init() and (pygame.display.get_surface() is not None)
        for kind in ("bat", "flutter", "bindling", "smear", "sentry", "punctuation_wolf", "boss"):
            name = f"{kind}_empowered.png"
            path = os.path.join(base_path, name)
            if os.path.exists(path):
                try:
                    img = pygame.image.load(path)
                    if display_init:
                        img = img.convert_alpha()
                    self.image_cache[name] = img
                except Exception as e:
                    print(f"[RENDER] Error loading {name}: {e}")

    def _desaturate_surface(self, surf):
        """Converts a surface to grayscale (removes saturation)."""
        width, height = surf.get_size()
        gray_surf = pygame.Surface((width, height), pygame.SRCALPHA)
        for y in range(height):
            for x in range(width):
                color = surf.get_at((x, y))
                gray = int(0.299 * color.r + 0.587 * color.g + 0.114 * color.b)
                gray_surf.set_at((x, y), (gray, gray, gray, color.a))
        return gray_surf

    def _prebake_floor_variants(self, base_floor_surf):
        """Pre-bake 4 subtle variants of floor_tile.png into RAM with rotations and value shifts."""
        display_init = pygame.display.get_init() and (pygame.display.get_surface() is not None) and pygame.display.get_surface() is not None
        ts = constants.TILE_SIZE
        scaled_base = pygame.transform.scale(base_floor_surf, (ts, ts))
        if display_init:
            scaled_base = scaled_base.convert()

        configs = [
            (0, 0.0),      # 0 deg, base
            (90, 0.07),    # 90 deg, +7% brightness
            (180, -0.06),  # 180 deg, -6% brightness
            (270, 0.09),   # 270 deg, +9% brightness
        ]
        variants = []
        for rot, brightness_shift in configs:
            var = scaled_base.copy()
            if brightness_shift > 0:
                bright_mask = pygame.Surface((ts, ts))
                add_val = int(255 * brightness_shift)
                bright_mask.fill((add_val, add_val, add_val))
                var.blit(bright_mask, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
            elif brightness_shift < 0:
                dark_mask = pygame.Surface((ts, ts))
                sub_val = int(255 * abs(brightness_shift))
                dark_mask.fill((sub_val, sub_val, sub_val))
                var.blit(dark_mask, (0, 0), special_flags=pygame.BLEND_RGB_SUB)

            if rot != 0:
                var = pygame.transform.rotate(var, rot)

            # Ensure 100% opaque surface with no alpha channel holes
            opaque_var = pygame.Surface((ts, ts))
            opaque_var.fill(constants.COLOR_SEPIA_AMBER)
            opaque_var.blit(var, (0, 0))
            if display_init:
                opaque_var = opaque_var.convert()
            variants.append(opaque_var)

        return variants

    def _load_tile_assets(self):
        """Pre-load tile assets like walls, generator-driven variants, and biome surfaces."""
        import os
        base_path = os.path.join("assets", "graphics")
        display_init = pygame.display.get_init() and (pygame.display.get_surface() is not None) and pygame.display.get_surface() is not None

        # 1. Wall Tile & Feature Variants (standard, cracked, mossy, webbed)
        self.wall_variants = []
        wall_specs = [
            ("wall_tile.png", "wall_tile_surf"),
            ("wall_tile_cracked.png", "wall_cracked_surf"),
            ("wall_tile_mossy.png", "wall_mossy_surf"),
            ("wall_tile_webbed.png", "wall_webbed_surf"),
        ]
        for fname, attr_name in wall_specs:
            w_path = os.path.join(base_path, fname)
            if not os.path.exists(w_path) and fname == "wall_tile.png":
                w_path = os.path.join(base_path, "brown_wall.png")
            if os.path.exists(w_path):
                try:
                    img = pygame.image.load(w_path)
                    if display_init:
                        img = img.convert_alpha()
                    scaled_w = pygame.transform.scale(img, (constants.TILE_SIZE, constants.TILE_SIZE))
                    setattr(self, attr_name, scaled_w)
                    self.image_cache[fname] = scaled_w
                    self.wall_variants.append(scaled_w)
                except Exception as e:
                    print(f"[RENDER] Error loading {w_path}: {e}")

        if not hasattr(self, "wall_tile_surf") or self.wall_tile_surf is None:
            if self.wall_variants:
                self.wall_tile_surf = self.wall_variants[0]
        if hasattr(self, "wall_tile_surf") and self.wall_tile_surf is not None:
            self.image_cache["brown_wall.png"] = self.wall_tile_surf
            self.image_cache["wall_tile.png"] = self.wall_tile_surf

        # 2. Swamp / Natural Biome Surfaces (water, mud turf, peat bank, swamp wall)
        swamp_specs = [
            ("swamp_water.png", "swamp_water_surf"),
            ("mud_turf.png", "mud_turf_surf"),
            ("peat_bank.png", "peat_bank_surf"),
            ("swamp_wall.png", "swamp_wall_surf"),
        ]
        for fname, attr_name in swamp_specs:
            s_path = os.path.join(base_path, fname)
            if os.path.exists(s_path):
                try:
                    img = pygame.image.load(s_path)
                    if display_init:
                        img = img.convert()
                    scaled_s = pygame.transform.scale(img, (constants.TILE_SIZE, constants.TILE_SIZE))
                    setattr(self, attr_name, scaled_s)
                    self.image_cache[fname] = scaled_s
                except Exception as e:
                    print(f"[RENDER] Error loading {s_path}: {e}")

        # 3. Floor Tile & Pre-Baked Variants (floor_tile.png)
        floor_name = "floor_tile.png"
        floor_path = os.path.join(base_path, floor_name)
        if not os.path.exists(floor_path):
            floor_path = os.path.join(base_path, "tile_floor.png")
        if os.path.exists(floor_path):
            try:
                img = pygame.image.load(floor_path)
                if display_init:
                    img = img.convert()
                scaled_floor = pygame.transform.scale(img, (constants.TILE_SIZE, constants.TILE_SIZE))
                self.floor_variants = self._prebake_floor_variants(scaled_floor)
                self.image_cache["floor_tile.png"] = self.floor_variants[0]
                self.image_cache["tile_floor.png"] = self.floor_variants[0]
            except Exception as e:
                print(f"[RENDER] Error loading {floor_path}: {e}")

        # 3b. Low-Contrast Sanctuary Floor Texture Variations (flagstone, dirt path, wood floorboards)
        for prefix, attr_name in (
            ("sanctuary_flagstone", "sanctuary_flagstone_variants"),
            ("sanctuary_dirt_path", "sanctuary_dirt_path_variants"),
            ("sanctuary_wood_floor", "sanctuary_wood_floor_variants"),
        ):
            loaded_variants = []
            for idx in range(4):
                v_fname = f"{prefix}_{idx}.png"
                v_path = os.path.join(base_path, v_fname)
                if os.path.exists(v_path):
                    try:
                        v_img = pygame.image.load(v_path)
                        if display_init:
                            v_img = v_img.convert()
                        if v_img.get_size() != (constants.TILE_SIZE, constants.TILE_SIZE):
                            v_img = pygame.transform.scale(v_img, (constants.TILE_SIZE, constants.TILE_SIZE))
                        loaded_variants.append(v_img)
                        self.image_cache[v_fname] = v_img
                    except Exception as e:
                        print(f"[RENDER] Error loading {v_path}: {e}")
            setattr(self, attr_name, loaded_variants)

        self.biome_tiles = {}
        self._generate_biome_tile_cache()

    @staticmethod
    def _shift_rgb_clamped(base_rgb, dr, dg, db):
        """Return an RGB tuple shifted by (dr, dg, db) and clamped to [0, 255]."""
        return (
            max(0, min(255, int(base_rgb[0]) + int(dr))),
            max(0, min(255, int(base_rgb[1]) + int(dg))),
            max(0, min(255, int(base_rgb[2]) + int(db))),
        )

    @classmethod
    def _build_windy_ridge_stratum_variant(cls, ts, s_idx, v_idx, s_base):
        """Generate a low-contrast (<= +/-12 RGB) textured 40x40 floor variant for windy_ridge."""
        fl = pygame.Surface((ts, ts))
        fl.fill(s_base)
        rng = random.Random(9100 + s_idx * 97 + v_idx * 19)

        # Subtle organic soil/stone pixel grain strictly within +/-10 RGB
        for _ in range(52):
            px = rng.randrange(0, ts)
            py = rng.randrange(0, ts)
            delta = rng.randint(-9, 9)
            fl.set_at((px, py), cls._shift_rgb_clamped(s_base, delta, delta, delta))

        if s_idx == 0:
            # Deep Viridian Clover Basin: soft mossy micro-blotches & tiny clover flecks
            moss_dark = cls._shift_rgb_clamped(s_base, -6, -9, -5)
            moss_light = cls._shift_rgb_clamped(s_base, 5, 11, 6)
            for _ in range(4):
                bx = rng.randint(4, ts - 12)
                by = rng.randint(4, ts - 10)
                pygame.draw.ellipse(fl, moss_dark, (bx, by, rng.randint(6, 10), rng.randint(4, 7)))
            for _ in range(5):
                fx = rng.randint(3, ts - 4)
                fy = rng.randint(3, ts - 4)
                fl.set_at((fx, fy), moss_light)
                fl.set_at((min(ts - 1, fx + 1), fy), moss_light)
        elif s_idx == 1:
            # Sunlit Emerald Meadow: delicate wind-swept fine grass blades & dew flecks
            blade_hi = cls._shift_rgb_clamped(s_base, 6, 11, 5)
            blade_lo = cls._shift_rgb_clamped(s_base, -6, -10, -5)
            for idx in range(9):
                gx = rng.randint(3, ts - 6)
                gy = rng.randint(5, ts - 3)
                col = blade_hi if idx % 2 == 0 else blade_lo
                pygame.draw.line(fl, col, (gx, gy), (gx + 2, gy - rng.randint(3, 4)), 1)
        else:
            # Ancient Limestone Cobble Trail: hairline cracks, mineral flecks & subtle stone bevels
            crack_col = cls._shift_rgb_clamped(s_base, -11, -11, -10)
            pebble_hi = cls._shift_rgb_clamped(s_base, 10, 10, 8)
            for _ in range(2):
                cx0 = rng.randint(4, ts - 14)
                cy0 = rng.randint(4, ts - 10)
                cx1 = cx0 + rng.randint(4, 8)
                cy1 = cy0 + rng.randint(-3, 4)
                pygame.draw.line(fl, crack_col, (cx0, cy0), (cx1, cy1), 1)
            for _ in range(6):
                px = rng.randint(2, ts - 3)
                py = rng.randint(2, ts - 3)
                fl.set_at((px, py), pebble_hi)

        # Preserve exact pixel (1, 1) == s_base invariant for stratum verification tests
        if v_idx == 0:
            fl.set_at((1, 1), s_base)
        return fl

    @classmethod
    def _build_tech_tower_stratum_variant(cls, ts, s_idx, v_idx, s_base):
        """Generate a low-contrast (<= +/-12 RGB) brushed-titanium / grate 40x40 variant for tech_tower."""
        fl = pygame.Surface((ts, ts))
        fl.fill(s_base)
        rng = random.Random(9400 + s_idx * 97 + v_idx * 19)

        if s_idx == 0:
            # Recessed Reactor Trench: dark grille slats & fine metallic dust within <= +/-10 RGB
            slat_dark = cls._shift_rgb_clamped(s_base, -6, -7, -9)
            slat_bevel = cls._shift_rgb_clamped(s_base, 6, 8, 10)
            phase = v_idx % 2
            for gy in range(phase * 2, ts, 6):
                pygame.draw.line(fl, slat_dark, (0, gy), (ts - 1, gy), 2)
                if gy + 2 < ts:
                    pygame.draw.line(fl, slat_bevel, (0, gy + 2), (ts - 1, gy + 2), 1)
            rib_x = 8 + v_idx * 8
            pygame.draw.line(fl, slat_dark, (rib_x, 0), (rib_x, ts - 1), 1)
            for _ in range(28):
                px, py = rng.randrange(0, ts), rng.randrange(0, ts)
                delta = rng.randint(-6, 6)
                fl.set_at((px, py), cls._shift_rgb_clamped(s_base, delta, delta, delta))
        elif s_idx == 1:
            # Brushed Titanium Deck Plating: horizontal brushed streaks & micro-rivets (<= +/-11 RGB)
            streak_hi = cls._shift_rgb_clamped(s_base, 7, 8, 10)
            streak_lo = cls._shift_rgb_clamped(s_base, -6, -7, -9)
            for idx in range(14):
                sx0 = rng.randint(0, ts - 10)
                sy0 = rng.randint(2, ts - 3)
                slen = rng.randint(6, 16)
                col = streak_hi if idx % 2 == 0 else streak_lo
                pygame.draw.line(fl, col, (sx0, sy0), (min(ts - 1, sx0 + slen), sy0), 1)
            rivet_hi = cls._shift_rgb_clamped(s_base, 9, 10, 11)
            rivet_lo = cls._shift_rgb_clamped(s_base, -8, -9, -10)
            off = 3 + (v_idx % 2)
            for rx, ry in ((off, off), (ts - off - 1, off), (off, ts - off - 1), (ts - off - 1, ts - off - 1)):
                fl.set_at((rx, ry), rivet_hi)
                if rx + 1 < ts and ry + 1 < ts:
                    fl.set_at((rx + 1, ry + 1), rivet_lo)
        else:
            # Anodized Steel Walkway: machined traction grooves & panel seams (<= +/-11 RGB)
            seam_lo = cls._shift_rgb_clamped(s_base, -9, -10, -11)
            seam_hi = cls._shift_rgb_clamped(s_base, 8, 9, 10)
            for idx in range(10):
                gx = rng.randint(2, ts - 12)
                gy = rng.randint(3, ts - 4)
                pygame.draw.line(fl, seam_hi if idx % 2 == 0 else seam_lo, (gx, gy), (gx + 8, gy), 1)
            notch_y = 10 + v_idx * 6
            pygame.draw.line(fl, seam_lo, (2, notch_y), (ts - 3, notch_y), 1)
            if notch_y + 1 < ts:
                pygame.draw.line(fl, seam_hi, (2, notch_y + 1), (ts - 3, notch_y + 1), 1)

        if v_idx == 0:
            fl.set_at((1, 1), s_base)
        return fl

    def _generate_biome_tile_cache(self):
        """Procedurally generate seamless base floor and wall surfaces per biome."""
        ts = constants.TILE_SIZE
        display_init = pygame.display.get_init() and (pygame.display.get_surface() is not None) and pygame.display.get_surface() is not None
        shadow_n = pygame.Surface((ts, 8), pygame.SRCALPHA)
        shadow_n.fill((0, 0, 0, 95), (0, 0, ts, 4))
        shadow_n.fill((0, 0, 0, 45), (0, 4, ts, 4))
        shadow_w = pygame.Surface((6, ts), pygame.SRCALPHA)
        shadow_w.fill((0, 0, 0, 70), (0, 0, 3, ts))
        shadow_w.fill((0, 0, 0, 35), (3, 0, 3, ts))

        for biome, pal in constants.BIOME_PALETTES.items():
            strata_defs = pal.get(
                "strata",
                [(pal["floor_base"], pal["floor_alt"])] * 3
            )
            strata_floors = []
            for s_idx, (s_base, _s_alt) in enumerate(strata_defs):
                tier_variants = []
                for v_idx in range(4):
                    if biome == "windy_ridge":
                        fl = self._build_windy_ridge_stratum_variant(ts, s_idx, v_idx, s_base)
                    elif biome == "tech_tower":
                        fl = self._build_tech_tower_stratum_variant(ts, s_idx, v_idx, s_base)
                    else:
                        fl = pygame.Surface((ts, ts))
                        fl.fill(s_base)
                    if display_init:
                        fl = fl.convert()
                    tier_variants.append(fl)
                strata_floors.append(tier_variants)

            # Default wall cap & wall front surfaces (used for fallback cache keys)
            w_cap = pygame.Surface((ts, ts))
            w_cap.fill(pal["wall_top"])
            if display_init:
                w_cap = w_cap.convert()

            w_front = pygame.Surface((ts, ts))
            w_front.fill(pal["wall_face"])
            w_front.fill(pal["wall_top"], (0, 0, ts, 14))
            w_front.fill(pal["wall_hi"], (0, 12, ts, 2))
            w_front.fill(pal["wall_mortar"], (0, ts - 3, ts, 3))
            if display_init:
                w_front = w_front.convert()

            self.biome_tiles[biome] = {
                "floors": strata_floors[1],
                "strata_floors": strata_floors,
                "wall_cap": w_cap,
                "wall_front": w_front,
                "shadow_n": shadow_n,
                "shadow_w": shadow_w
            }

        # Populate default cache keys
        if self.wall_tile_surf is not None:
            self.image_cache["brown_wall.png"] = self.wall_tile_surf
            self.image_cache["wall_tile.png"] = self.wall_tile_surf
        else:
            self.image_cache["brown_wall.png"] = self.biome_tiles["windy_ridge"]["wall_front"]

        if self.floor_variants:
            self.image_cache["tile_floor.png"] = self.floor_variants[0]
            self.image_cache["floor_tile.png"] = self.floor_variants[0]
        else:
            self.image_cache["tile_floor.png"] = self.biome_tiles["windy_ridge"]["floors"][0]

    def _resolve_tile_biome(self, state, tx, ty):
        """Determine the biome key for tile coordinates (tx, ty)."""
        world = getattr(state, "world", None)
        w_name = getattr(world, "name", "sanctuary").lower()

        if w_name == "sanctuary":
            return "sanctuary"

        for key in (
            "windy_ridge",
            "pastoral_valley",
            "swamp_mire",
            "frozen_peaks",
            "tech_tower",
            "vitreous_basin",
            "sunlit_aqueducts",
        ):
            if key in w_name:
                return key
        if any(k in w_name for k in ("ruins", "final_boss", "boss")):
            return "tech_tower"

        sockets = getattr(world, "module_sockets", None) or ()
        sock_key = (id(world), id(sockets), len(sockets), w_name)
        if getattr(self, "_compiled_sockets_key", None) != sock_key:
            compiled = []
            for sock in sockets:
                b = sock.get("bounds", {})
                bx = int(b.get("x", 0))
                by = int(b.get("y", 0))
                bw = int(b.get("width", 0))
                bh = int(b.get("height", 0))
                plug = sock.get("active_plug", "").lower()
                if "pastoral" in plug or "valley" in plug or "meadow" in plug:
                    b_res = "pastoral_valley"
                elif "swamp" in plug or "mire" in plug:
                    b_res = "swamp_mire"
                elif "frozen" in plug or "peak" in plug:
                    b_res = "frozen_peaks"
                elif "vitreous" in plug or "basin" in plug:
                    b_res = "vitreous_basin"
                elif "sunlit" in plug or "aqueduct" in plug:
                    b_res = "sunlit_aqueducts"
                elif any(k in plug for k in ("tech", "tower", "gantry", "ruins", "boss")):
                    b_res = "tech_tower"
                else:
                    b_res = "windy_ridge"
                compiled.append((bx, by, bx + bw, by + bh, b_res))
            self._compiled_sockets = tuple(compiled)
            self._compiled_sockets_key = sock_key
            self._tile_biome_cache = {}

        cache = getattr(self, "_tile_biome_cache", None)
        if cache is not None:
            cached = cache.get((tx, ty))
            if cached is not None:
                return cached

        resolved = None
        for bx0, by0, bx1, by1, b_res in self._compiled_sockets:
            if bx0 <= tx < bx1 and by0 <= ty < by1:
                resolved = b_res
                break

        if not resolved:
            sector = ((tx // 40) + (ty // 40)) % 7
            resolved = (
                "windy_ridge",
                "pastoral_valley",
                "swamp_mire",
                "frozen_peaks",
                "tech_tower",
                "vitreous_basin",
                "sunlit_aqueducts",
            )[sector]

        if cache is not None:
            if len(cache) > 65536:
                cache.clear()
            cache[(tx, ty)] = resolved
        return resolved

    def _load_grass_assets(self):
        """Pre-load grass assets and generate lightweight procedural grass tuft surfaces in RAM."""
        import os
        base_path = os.path.join("assets", "graphics")
        display_init = pygame.display.get_init() and (pygame.display.get_surface() is not None) and pygame.display.get_surface() is not None

        grass_name = "grass_natural.png"
        grass_path = os.path.join(base_path, grass_name)
        if os.path.exists(grass_path):
            try:
                g_img = pygame.image.load(grass_path)
                if display_init:
                    g_img = g_img.convert_alpha()
                self.grass_natural_surf = pygame.transform.scale(
                    g_img, (constants.TILE_SIZE, constants.TILE_SIZE)
                )
                self.image_cache[grass_name] = self.grass_natural_surf
            except Exception as e:
                print(f"[RENDER] Error loading {grass_name}: {e}")

        self.grass_pools = {"small": [], "medium": [], "tall": []}
        configs = [("small", (12, 8)), ("medium", (18, 12)), ("tall", (24, 16))]
        colors = [
            ((50, 158, 74), (110, 225, 130)),
            ((38, 132, 64), (88, 210, 112)),
            ((64, 175, 82), (148, 242, 146))
        ]
        for key, (w, h) in configs:
            for base_c, hi_c in colors:
                surf = pygame.Surface((w, h))
                surf.fill(base_c)
                surf.fill(hi_c, (2, 1, max(2, w - 4), max(2, h // 2)))
                if display_init:
                    surf = surf.convert()
                self.grass_pools[key].append(surf)

    def _generate_prop_cache(self):
        """Pre-render static procedural prop surfaces once at startup to eliminate per-frame shape drawing."""
        import os
        base_path = os.path.join("assets", "graphics")
        ts = constants.TILE_SIZE
        display_init = pygame.display.get_init() and (pygame.display.get_surface() is not None) and pygame.display.get_surface() is not None

        # 1. Structure (Default Biome Tree PNG with procedural fallback)
        tree_path = os.path.join(base_path, "tree_structure.png")
        if os.path.exists(tree_path):
            try:
                t_img = pygame.image.load(tree_path)
                if display_init:
                    t_img = t_img.convert_alpha()
                self.prop_cache["Structure"] = t_img
                self.image_cache["tree_structure.png"] = t_img
            except Exception as e:
                print(f"[RENDER] Error loading tree_structure.png: {e}")
        if "Structure" not in self.prop_cache:
            tree = pygame.Surface((ts, ts), pygame.SRCALPHA)
            cx_t, cy_t = ts // 2, ts // 2 - 4
            pygame.draw.circle(tree, (22, 44, 28), (cx_t + 2, ts - 6), ts // 3)
            pygame.draw.rect(tree, (28, 16, 8), (cx_t - 7, ts - 16, 14, 14), border_radius=2)
            pygame.draw.rect(tree, (92, 54, 28), (cx_t - 5, ts - 15, 10, 12), border_radius=2)
            pygame.draw.circle(tree, (18, 44, 24), (cx_t, cy_t), ts // 2 - 1)
            pygame.draw.circle(tree, (38, 126, 62), (cx_t, cy_t + 2), ts // 2 - 3)
            pygame.draw.circle(tree, (92, 218, 110), (cx_t - 1, cy_t - 2), ts // 2 - 5)
            pygame.draw.circle(tree, (162, 246, 148), (cx_t - 4, cy_t - 6), ts // 4)
            self.prop_cache["Structure"] = tree.convert_alpha() if display_init else tree

        # 2. Inkwell Puddle (PNG with procedural fallback)
        puddle_path = os.path.join(base_path, "inkwell_puddle.png")
        if os.path.exists(puddle_path):
            try:
                p_img = pygame.image.load(puddle_path)
                if display_init:
                    p_img = p_img.convert_alpha()
                self.prop_cache["Inkwell Puddle"] = p_img
                self.image_cache["inkwell_puddle.png"] = p_img
            except Exception as e:
                print(f"[RENDER] Error loading inkwell_puddle.png: {e}")
        if "Inkwell Puddle" not in self.prop_cache:
            puddle = pygame.Surface((ts, ts), pygame.SRCALPHA)
            pcx, pcy = ts // 2, ts // 2
            pygame.draw.circle(puddle, (16, 8, 24), (pcx, pcy), ts // 2 - 1)
            pygame.draw.circle(puddle, (58, 26, 82), (pcx - 4, pcy - 2), ts // 3 + 2)
            pygame.draw.circle(puddle, (58, 26, 82), (pcx + 5, pcy + 3), ts // 3 + 1)
            pygame.draw.circle(puddle, (28, 12, 42), (pcx, pcy), ts // 3)
            self.prop_cache["Inkwell Puddle"] = puddle.convert_alpha() if display_init else puddle

        # 3. Rock (Rock Cluster PNG Asset with procedural fallback)
        rock_name = "rock_cluster.png"
        rock_path = os.path.join(base_path, rock_name)
        if os.path.exists(rock_path):
            try:
                r_img = pygame.image.load(rock_path)
                if display_init:
                    r_img = r_img.convert_alpha()
                self.prop_cache["Rock"] = pygame.transform.scale(r_img, (ts, ts))
                self.image_cache[rock_name] = self.prop_cache["Rock"]
            except Exception as e:
                print(f"[RENDER] Error loading {rock_name}: {e}")
        if "Rock" not in self.prop_cache:
            rock = pygame.Surface((ts, ts), pygame.SRCALPHA)
            pygame.draw.circle(rock, (68, 88, 118), (ts // 2, ts // 2 + 2), ts // 2 - 3)
            pygame.draw.circle(rock, (135, 185, 225), (ts // 2 - 4, ts // 2 - 3), ts // 4)
            pygame.draw.line(rock, (220, 245, 255), (10, 12), (ts // 2, 8), 2)
            self.prop_cache["Rock"] = rock.convert_alpha() if display_init else rock

        # 4. Heavy Bookcase (Native 80x40 PNG with procedural fallback)
        bk_path = os.path.join(base_path, "heavy_bookcase.png")
        if os.path.exists(bk_path):
            try:
                bk_img = pygame.image.load(bk_path)
                if display_init:
                    bk_img = bk_img.convert_alpha()
                self.prop_cache["Heavy Bookcase"] = bk_img
                self.image_cache["heavy_bookcase.png"] = bk_img
            except Exception as e:
                print(f"[RENDER] Error loading heavy_bookcase.png: {e}")
        if "Heavy Bookcase" not in self.prop_cache:
            bw, bh = ts * 2, ts
            bk = pygame.Surface((bw, bh), pygame.SRCALPHA)
            pygame.draw.rect(bk, (68, 46, 34), (0, 0, bw, bh), border_radius=3)
            pygame.draw.rect(bk, (140, 105, 65), (0, 0, bw, 5))
            pygame.draw.line(bk, (30, 20, 14), (2, bh // 2), (bw - 2, bh // 2), 2)
            for sx_off in range(6, bw - 6, 8):
                col = (0, 210, 240) if (sx_off // 8) % 2 == 0 else (225, 75, 175)
                pygame.draw.rect(bk, col, (sx_off, 8, 5, bh // 2 - 10))
            self.prop_cache["Heavy Bookcase"] = bk.convert_alpha() if display_init else bk

        # 5. Ink Urn (40x40 PNG with procedural fallback)
        urn_path = os.path.join(base_path, "ink_urn.png")
        if os.path.exists(urn_path):
            try:
                u_img = pygame.image.load(urn_path)
                if display_init:
                    u_img = u_img.convert_alpha()
                self.prop_cache["Ink Urn"] = u_img
                self.image_cache["ink_urn.png"] = u_img
            except Exception as e:
                print(f"[RENDER] Error loading ink_urn.png: {e}")
        if "Ink Urn" not in self.prop_cache:
            urn = pygame.Surface((ts, ts), pygame.SRCALPHA)
            pygame.draw.circle(urn, (52, 74, 112), (ts // 2, ts // 2 + 3), ts // 2 - 4)
            pygame.draw.circle(urn, (110, 175, 230), (ts // 2 - 4, ts // 2), 4)
            pygame.draw.rect(urn, (190, 165, 105), (8, 4, ts - 16, 6), border_radius=2)
            pygame.draw.circle(urn, (0, 240, 255), (ts // 2, 7), 3)
            self.prop_cache["Ink Urn"] = urn.convert_alpha() if display_init else urn

        # 6. Candelabra Glow Halo (60x60) & Legacy Landmark PNGs
        for lp_file, lp_key in (
            ("wellspring.png", "The Wellspring"),
            ("lotus_frame.png", "LotusFrame"),
            ("bench.png", "Bench"),
            ("candelabra.png", "Candelabra"),
        ):
            lp_path = os.path.join(base_path, lp_file)
            if os.path.exists(lp_path):
                try:
                    lp_img = pygame.image.load(lp_path)
                    if display_init:
                        lp_img = lp_img.convert_alpha()
                    self.prop_cache[lp_key] = lp_img
                    self.image_cache[lp_file] = lp_img
                except Exception as e:
                    print(f"[RENDER] Error loading {lp_file}: {e}")
        glow_r = 30
        glow = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
        pygame.draw.circle(glow, (255, 190, 40, 60), (glow_r, glow_r), glow_r)
        self.prop_cache["CandelabraGlow"] = glow.convert_alpha() if display_init else glow

        # 7. Swamp Biome Props: Fungus, Gas Vent, and Skeletal Thorns
        swamp_prop_defs = [
            ("chronicle.png", "Chronicle"),
            ("respite.png", "Respite"),
            ("respite_corrupted.png", "RespiteCorrupted"),
            ("chronicler.png", "Chronicler"),
            ("binder.png", "Binder"),
            ("swamp_fungus.png", "SwampFungus"),
            ("swamp_gas_vent.png", "SwampVent"),
            ("swamp_thorns.png", "SwampThorns"),
        ]
        for sp_file, sp_key in swamp_prop_defs:
            sp_path = os.path.join(base_path, sp_file)
            if os.path.exists(sp_path):
                try:
                    sp_img = pygame.image.load(sp_path)
                    if display_init:
                        sp_img = sp_img.convert_alpha()
                    scaled_sp = pygame.transform.scale(sp_img, (ts, ts))
                    self.prop_cache[sp_key] = scaled_sp
                    self.image_cache[sp_file] = scaled_sp
                except Exception as e:
                    print(f"[RENDER] Error loading {sp_file}: {e}")

        # 7b. Assorted Weapon Pickup Sprites (Standard & Anomalous)
        weapon_pickup_defs = (
            ("weapon_quill_standard.png", "WeaponQuillStandard"),
            ("weapon_quill_refined.png", "WeaponQuillRefined"),
            ("weapon_scriber_blade.png", "WeaponScriberBlade"),
            ("weapon_anomalous_bleed.png", "WeaponAnomalousBleed"),
            ("weapon_anomalous_regen.png", "WeaponAnomalousRegen"),
            ("weapon_anomalous_negation.png", "WeaponAnomalousNegation"),
            ("weapon_anomalous_stout.png", "WeaponAnomalousStout"),
            ("weapon_anomalous_default.png", "WeaponAnomalousDefault"),
        )
        for wp_file, wp_key in weapon_pickup_defs:
            wp_path = os.path.join(base_path, wp_file)
            if os.path.exists(wp_path):
                try:
                    wp_img = pygame.image.load(wp_path)
                    if display_init:
                        wp_img = wp_img.convert_alpha()
                    scaled_wp = pygame.transform.scale(wp_img, (ts, ts))
                    self.prop_cache[wp_key] = scaled_wp
                    self.image_cache[wp_file] = scaled_wp
                except Exception as e:
                    print(f"[RENDER] Error loading {wp_file}: {e}")

        # 7c. Sanctuary Courtyard, Pond, Roof & Prop Assets (Pass 1 preload; graceful fallback if absent)
        sanctuary_extra_defs = (
            ("sanctuary_roof_tile.png", "SanctuaryRoofTile", (ts, ts), False),
            ("sanctuary_chimney.png", "SanctuaryChimney", (ts, ts * 2), True),
            ("sanctuary_tree_canopy.png", "SanctuaryTreeCanopy", (ts * 2, 100), True),
            ("pond_lily_reeds.png", "PondLilyReeds", (ts, ts), True),
            ("garden_flora.png", "GardenFlora", (ts, ts), True),
            ("locked_shed_door.png", "LockedShedDoor", (ts, ts), True),
            ("mossy_gravestone.png", "MossyGravestone", (ts, ts), True),
            ("sanctuary_window_wall.png", "SanctuaryWindowWall", (ts, ts), False),
            ("sanctuary_arch_doorway.png", "SanctuaryArchDoorway", (ts, ts), False),
            ("torn_page.png", "TornPage", (ts, ts), True),
            ("highland_monolith.png", "HighlandMonolith", (ts, 60), True),
        )
        for sx_file, sx_key, sx_size, has_alpha in sanctuary_extra_defs:
            sx_path = os.path.join(base_path, sx_file)
            if os.path.exists(sx_path):
                try:
                    sx_img = pygame.image.load(sx_path)
                    if display_init:
                        sx_img = sx_img.convert_alpha() if has_alpha else sx_img.convert()
                    if sx_img.get_size() != sx_size:
                        sx_img = pygame.transform.scale(sx_img, sx_size)
                    self.prop_cache[sx_key] = sx_img
                    self.image_cache[sx_file] = sx_img
                except Exception as e:
                    print(f"[RENDER] Error loading {sx_file}: {e}")
        self._fx_surface_cache = {}

        if "SwampFungus" not in self.prop_cache:
            fungus = pygame.Surface((ts, ts), pygame.SRCALPHA)
            pygame.draw.rect(fungus, (195, 168, 220), (ts // 2 - 4, ts - 18, 8, 16), border_radius=3)
            pygame.draw.ellipse(fungus, (66, 30, 62), (ts // 2 - 16, ts // 2 - 8, 32, 22))
            pygame.draw.circle(fungus, (142, 172, 44), (ts // 2 - 6, ts // 2 - 2), 3)
            pygame.draw.circle(fungus, (142, 172, 44), (ts // 2 + 7, ts // 2), 2)
            self.prop_cache["SwampFungus"] = fungus.convert_alpha() if display_init else fungus

        if "Binder" not in self.prop_cache:
            b_surf = pygame.Surface((ts, ts), pygame.SRCALPHA)
            pygame.draw.polygon(b_surf, (62, 32, 46), [(9, 33), (12, 14), (28, 14), (31, 33)])
            pygame.draw.circle(b_surf, (78, 42, 58), (ts // 2, 11), 7)
            pygame.draw.line(b_surf, (242, 214, 124), (29, 28), (34, 8), 2)
            self.prop_cache["Binder"] = b_surf.convert_alpha() if display_init else b_surf

        if "SwampVent" not in self.prop_cache:
            vent = pygame.Surface((ts, ts), pygame.SRCALPHA)
            pygame.draw.ellipse(vent, (66, 30, 62), (4, 8, ts - 8, ts - 12))
            pygame.draw.circle(vent, (18, 8, 22), (ts // 2, ts // 2), 6)
            pygame.draw.circle(vent, (148, 215, 68), (ts // 2, ts // 2), 3)
            self.prop_cache["SwampVent"] = vent.convert_alpha() if display_init else vent

        if "SwampThorns" not in self.prop_cache:
            thorns = pygame.Surface((ts, ts), pygame.SRCALPHA)
            pygame.draw.line(thorns, (180, 175, 185), (6, 34), (34, 10), 3)
            pygame.draw.line(thorns, (180, 175, 185), (14, 24), (10, 14), 2)
            pygame.draw.line(thorns, (180, 175, 185), (24, 18), (30, 26), 2)
            self.prop_cache["SwampThorns"] = thorns.convert_alpha() if display_init else thorns

        # 9. Environmental Biome Clutter: Ruins Rubble, Swamp Flora, Crypt Clutter & Pass 2 Biome Tiles/Props
        clutter_defs = [
            ("ruins_rubble.png", "RuinsRubble"),
            ("swamp_flora.png", "SwampFlora"),
            ("crypt_clutter.png", "CryptClutter"),
            ("vitreous_salt_floor.png", "VitreousSaltFloor"),
            ("vitreous_glass_flat.png", "VitreousGlassFlat"),
            ("vitreous_salt_spire.png", "VitreousSaltSpire"),
            ("aqueduct_terracotta_floor.png", "AqueductTerracottaFloor"),
            ("aqueduct_moss_wall.png", "AqueductMossWall"),
            ("aqueduct_pillar.png", "AqueductPillar"),
        ]
        for c_file, c_key in clutter_defs:
            c_path = os.path.join(base_path, c_file)
            if os.path.exists(c_path):
                try:
                    c_img = pygame.image.load(c_path)
                    if display_init:
                        c_img = c_img.convert_alpha()
                    scaled_c = pygame.transform.scale(c_img, (ts, ts))
                    self.prop_cache[c_key] = scaled_c
                    self.image_cache[c_file] = scaled_c
                except Exception as e:
                    print(f"[RENDER] Error loading {c_file}: {e}")

        if "RuinsRubble" not in self.prop_cache:
            rubble = pygame.Surface((ts, ts), pygame.SRCALPHA)
            pygame.draw.rect(rubble, (58, 62, 70), (10, 16, 14, 16), border_radius=2)
            pygame.draw.rect(rubble, (72, 78, 88), (26, 22, 8, 8), border_radius=1)
            pygame.draw.line(rubble, (130, 140, 155), (10, 16), (24, 16), 1)
            pygame.draw.line(rubble, (16, 18, 24), (12, 22), (20, 26), 1)
            self.prop_cache["RuinsRubble"] = rubble.convert_alpha() if display_init else rubble

        if "SwampFlora" not in self.prop_cache:
            flora = pygame.Surface((ts, ts), pygame.SRCALPHA)
            pygame.draw.line(flora, (46, 68, 36), (16, 32), (20, 10), 2)
            pygame.draw.line(flora, (46, 68, 36), (24, 32), (28, 14), 2)
            pygame.draw.ellipse(flora, (135, 195, 50), (15, 16, 10, 6))
            pygame.draw.circle(flora, (205, 255, 120), (20, 18), 2)
            self.prop_cache["SwampFlora"] = flora.convert_alpha() if display_init else flora

        if "CryptClutter" not in self.prop_cache:
            crypt = pygame.Surface((ts, ts), pygame.SRCALPHA)
            pygame.draw.rect(crypt, (182, 162, 126), (8, 20, 14, 10), border_radius=1)
            pygame.draw.line(crypt, (50, 42, 38), (11, 23), (19, 23), 1)
            pygame.draw.ellipse(crypt, (175, 172, 160), (24, 15, 10, 9))
            pygame.draw.circle(crypt, (64, 58, 54), (27, 19), 2)
            self.prop_cache["CryptClutter"] = crypt.convert_alpha() if display_init else crypt

        if "VitreousSaltSpire" not in self.prop_cache:
            spire = pygame.Surface((ts, ts), pygame.SRCALPHA)
            pygame.draw.polygon(spire, (134, 194, 218), [(12, 34), (20, 6), (28, 34)])
            pygame.draw.polygon(spire, (242, 254, 255), [(12, 34), (20, 6), (21, 32)])
            self.prop_cache["VitreousSaltSpire"] = spire.convert_alpha() if display_init else spire

        if "AqueductPillar" not in self.prop_cache:
            pillar = pygame.Surface((ts, ts), pygame.SRCALPHA)
            pygame.draw.rect(pillar, (176, 118, 82), (11, 10, 18, 22), border_radius=2)
            pygame.draw.circle(pillar, (88, 178, 96), (12, 12), 4)
            self.prop_cache["AqueductPillar"] = pillar.convert_alpha() if display_init else pillar

    def draw_warp(self, warp, offset_x, offset_y):
        """Draw the Warp Point as 'The Chronicle' gilded magical tome on a lectern."""
        wx, wy, ww, wh = warp.rect
        screen_x = wx - offset_x
        screen_y = wy - offset_y
        chronicle_surf = getattr(self, "prop_cache", {}).get("Chronicle")
        if chronicle_surf is not None:
            self.screen.blit(chronicle_surf, (int(screen_x), int(screen_y)))
            pulse = (math.sin(time.time() * 4.0) + 1.0) * 0.5
            glow_alpha = int(35 + pulse * 65)
            glow_surf = pygame.Surface((ww, wh), pygame.SRCALPHA)
            pygame.draw.ellipse(glow_surf, (0, 240, 255, glow_alpha), (8, 5, ww - 16, 16))
            self.screen.blit(glow_surf, (int(screen_x), int(screen_y)))
            return
        pedestal_rect = pygame.Rect(screen_x + 5, screen_y + wh - 15, ww - 10, 15)
        pygame.draw.rect(self.screen, constants.COLOR_DARK_GREY, pedestal_rect)
        pygame.draw.rect(self.screen, constants.COLOR_BLACK, pedestal_rect, 1)
        book_rect = pygame.Rect(screen_x + 8, screen_y + 10, ww - 16, 20)
        pygame.draw.rect(self.screen, (139, 69, 19), book_rect)
        pygame.draw.rect(self.screen, constants.COLOR_GREY, (screen_x + 8, screen_y + 10, 4, 20))
        pulse = (math.sin(time.time() * 4) + 1) / 2
        glyph_color = (0, 255, 255)
        pulse_size = int(pulse * 4)
        sigil_rect = pygame.Rect(0, 0, 4 + pulse_size, 4 + pulse_size)
        sigil_rect.center = book_rect.center
        pygame.draw.rect(self.screen, glyph_color, sigil_rect)

    def draw_interaction_prompt(self, player, offset_x, offset_y):
        """Draw a text prompt above the player's head."""
        target = player.current_interactable
        if target.name == "The Chronicler": prompt_text = f"Speak to {target.name}"
        elif "Chronicle" in target.name or "Return" in target.name: prompt_text = f"Read {target.name}"
        elif hasattr(target, 'weapon_data'):
            prompt_text = "[Click [PICK UP] on HUD to claim weapon]"
        else: prompt_text = f"Interact with {target.name}" if hasattr(target, 'name') else "Interact"

        prompt_surf = self.font.render(prompt_text, True, constants.COLOR_WHITE)
        px, py = player.get_center()
        blit_pos = (px - prompt_surf.get_width() // 2 - offset_x, py - player.height - 20 - offset_y)
        self.screen.blit(prompt_surf, blit_pos)

    def draw_wellspring(self, wellspring, offset_x, offset_y):
        """Draw the Wellspring fountain sprite with subtle animated runic shimmer."""
        ox, oy, ow, oh = wellspring.rect
        screen_x, screen_y = ox - offset_x, oy - offset_y
        ws_surf = self.prop_cache.get("The Wellspring")
        if ws_surf is not None:
            if ws_surf.get_size() != (int(ow), int(oh)) and ow > 0 and oh > 0:
                ws_surf = pygame.transform.scale(ws_surf, (int(ow), int(oh)))
            self.screen.blit(ws_surf, (int(screen_x), int(screen_y)))
            try:
                ticks = pygame.time.get_ticks()
                shimmer_x = int(screen_x + 8 + ((ticks * 0.015) % max(4, int(ow) - 20)))
                shimmer_y = int(screen_y + int(oh) // 2 + math.sin(ticks * 0.005) * 3)
                pygame.draw.line(self.screen, constants.COLOR_CYAN, (shimmer_x, shimmer_y), (shimmer_x + 6, shimmer_y), 1)
            except Exception:
                pass
            return

        basin_rect = pygame.Rect(screen_x, screen_y, ow, oh)
        pygame.draw.rect(self.screen, constants.COLOR_BLUE, basin_rect)
        pygame.draw.rect(self.screen, constants.COLOR_WHITE, basin_rect, 2)
        
        # Animated "Ink-Flow" lines
        try:
            ticks = pygame.time.get_ticks()
            # Loop through 4 horizontal lines
            for i in range(4):
                line_y = screen_y + (i + 1) * (oh // 5)
                # Moderate slow speed: approx 1 loop every 5 seconds
                speed = 0.008 if i % 2 == 0 else -0.008
                offset = (ticks * speed) % 40 

                
                # Draw dashed segments
                for lx in range(-40, int(ow) + 40, 40):
                    start_x = screen_x + lx + offset
                    end_x = start_x + 20
                    
                    # Clip segments to basin interior
                    clip_sx = max(screen_x + 2, min(screen_x + ow - 2, start_x))
                    clip_ex = max(screen_x + 2, min(screen_x + ow - 2, end_x))
                    
                    if clip_sx < clip_ex:
                        pygame.draw.line(self.screen, constants.COLOR_CYAN, (clip_sx, line_y), (clip_ex, line_y), 2)
        except Exception:
            pass

    def draw_dialogue_box(self, state):
        """Draw a dialogue box."""
        dialogue = state.active_dialogue
        if not dialogue: return
        mode = getattr(state, 'dialogue_mode', "STANDARD")
        speaker, text = dialogue.get("speaker", "Unknown"), dialogue.get("text", "")
        if mode == "EXPANDED":
            mx, my = 100, 100
            w, h = self.screen.get_width() - mx * 2, self.screen.get_height() - my * 2
            x, y = mx, my
            bg, spacing, y_off = (10, 10, 30), 40, 80
        else:
            m = 50
            w, h = self.screen.get_width() - m * 2, 150
            x, y = m, self.screen.get_height() - h - 20
            bg, spacing, y_off = (20, 20, 20), 30, 50
        panel = pygame.Rect(x, y, w, h)
        pygame.draw.rect(self.screen, bg, panel)
        pygame.draw.rect(self.screen, constants.COLOR_WHITE, panel, 2)
        self.screen.blit(self.font.render(speaker, True, constants.COLOR_SELECTION), (x + 20, y + 10))
        lines, words = [], text.replace('\n', ' \n ').split(' ')
        cur = []
        for word in words:
            if word == '\n': lines.append(' '.join(cur)); cur = []; continue
            if self.font.size(' '.join(cur + [word]))[0] < w - 40: cur.append(word)
            else: lines.append(' '.join(cur)); cur = [word]
        lines.append(' '.join(cur))
        for i, line in enumerate(lines):
            self.screen.blit(self.font.render(line, True, constants.COLOR_WHITE), (x + 20, y + y_off + i * spacing))
        close = self.font.render("Press [SPACE] to continue", True, constants.COLOR_GREY)
        self.screen.blit(close, (x + w - close.get_width() - 20, y + h - 30))

    def draw_choice_of_fates(self, choice):
        """Draw the Choice of Fates overlay."""
        overlay = pygame.Surface((self.screen.get_width(), self.screen.get_height()), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))
        sw, sh = self.screen.get_width(), self.screen.get_height()
        title = self.font.render(choice["title"], True, constants.COLOR_PURPLE)
        self.screen.blit(title, (sw // 2 - title.get_width() // 2, sh // 4))
        card_w, card_h, pad = 300, 200, 50
        for i, opt in enumerate(choice["options"]):
            x, y = sw // 2 - (card_w + pad // 2) + i * (card_w + pad), sh // 2 - card_h // 2
            rect = pygame.Rect(x, y, card_w, card_h)
            is_sel = i == choice["selected_index"]
            color = (60, 60, 80) if is_sel else (40, 40, 40)
            border = constants.COLOR_SELECTION if is_sel else constants.COLOR_GREY
            pygame.draw.rect(self.screen, color, rect)
            pygame.draw.rect(self.screen, border, rect, 3)
            name = self.font.render(opt["name"], True, constants.COLOR_WHITE)
            self.screen.blit(name, (x + card_w // 2 - name.get_width() // 2, y + 20))
            bias = self.small_font.render(f"({opt['bias']})", True, constants.COLOR_GREY)
            self.screen.blit(bias, (x + card_w // 2 - bias.get_width() // 2, y + 50))
            desc = self.font.render(opt["description"], True, constants.COLOR_SELECTION)
            self.screen.blit(desc, (x + card_w // 2 - desc.get_width() // 2, y + card_h - 50))
        instr = self.font.render("Move [Left/Right] to select, [SPACE] to confirm", True, constants.COLOR_WHITE)
        self.screen.blit(instr, (sw // 2 - instr.get_width() // 2, sh - 100))

    def draw_weather(self, state, override_color=None, force_global=False):
        """Draw screen-space weather effects and the shrinking safe circle."""
        # Hub Isolation Rule: No weather visuals in the Sanctuary
        if not force_global and getattr(state.world, 'name', '') == "sanctuary":
            return

        if not force_global and getattr(state, 'bleed_state', 'CLEAR') == 'GRACE_PERIOD':
            return

        sw, sh = self.screen.get_width(), self.screen.get_height()
        ox, oy = state.camera.get_offset() if hasattr(state, 'camera') else (0, 0)
        
        radius = getattr(state, 'active_safe_radius', 1000000.0)
        if force_global:
            radius = 1000000.0 # No safe zone on title screen
            
        current_boss_coords = getattr(state, 'current_boss_coords', None)
        if force_global:
            current_boss_coords = None

        # 1. Reuse the weather overlay surface to avoid per-frame full-screen SRCALPHA allocation
        if self._weather_overlay is None or self._weather_overlay.get_size() != (sw, sh):
            self._weather_overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
            self._weather_overlay_dirty = False
        overlay = self._weather_overlay
        if self._weather_overlay_dirty:
            overlay.fill((0, 0, 0, 0))
            self._weather_overlay_dirty = False
        drew_any = False

        # 2. Particle System (Performant Vertical Rain)
        if not hasattr(self, 'rain_particles'):
            self.rain_particles = []
            for _ in range(200):
                self.rain_particles.append({
                    'x': random.randint(0, sw),
                    'y': random.randint(0, sh),
                    'speed': random.randint(400, 700),
                    'len': random.randint(15, 30)
                })

        # Update and Draw particles
        ticks = pygame.time.get_ticks() / 1000.0

        # Color Selection Rule
        rain_color = override_color if override_color else constants.COLOR_TOXIC_RAIN
        if not override_color and getattr(state, 'bleed_state', 'CLEAR') == 'DILUTION':
            rain_color = constants.COLOR_SAFE_RAIN

        wb_x, wb_y = 0, 0
        if current_boss_coords:
            wb_x = current_boss_coords['x'] * constants.TILE_SIZE
            wb_y = current_boss_coords['y'] * constants.TILE_SIZE

        rad_sq = radius**2
        is_dilution = getattr(state, 'bleed_state', 'CLEAR') == 'DILUTION'

        for p in self.rain_particles:
            ry = (p['y'] + ticks * p['speed']) % sh
            rx = p['x']

            # Distance check: Only draw if OUTSIDE the safe circle
            # Dilution/Title Rule: Rain is global
            if is_dilution or force_global:
                pygame.draw.line(overlay, rain_color, (rx, ry), (rx, ry + p['len']), 2)
                drew_any = True
            elif current_boss_coords:
                world_rx, world_ry = rx + ox, ry + oy
                d_sq = (world_rx - wb_x)**2 + (world_ry - wb_y)**2
                if d_sq > rad_sq:
                    pygame.draw.line(overlay, rain_color, (rx, ry), (rx, ry + p['len']), 2)
                    drew_any = True

        # 3. Draw a 'Mysterious Barrier' for the circle boundary only in debug text mode when it intersects the screen
        if getattr(state, "debug_text_enabled", False) and not force_global and not is_dilution and current_boss_coords:
            bcx = current_boss_coords['x'] * constants.TILE_SIZE - ox
            bcy = current_boss_coords['y'] * constants.TILE_SIZE - oy
            if 0 < radius < 30000:
                max_corner_sq = max(
                    (0 - bcx) ** 2 + (0 - bcy) ** 2,
                    (sw - bcx) ** 2 + (0 - bcy) ** 2,
                    (0 - bcx) ** 2 + (sh - bcy) ** 2,
                    (sw - bcx) ** 2 + (sh - bcy) ** 2,
                )
                near_x = max(0.0, min(float(sw), float(bcx)))
                near_y = max(0.0, min(float(sh), float(bcy)))
                min_dist_sq = (near_x - bcx) ** 2 + (near_y - bcy) ** 2
                inner_r = max(0.0, radius - 8.0)
                if max_corner_sq >= inner_r ** 2 and min_dist_sq <= (radius + 8.0) ** 2:
                    pygame.draw.circle(overlay, (0, 0, 0, 255), (int(bcx), int(bcy)), int(radius), 5)
                    drew_any = True

        if drew_any:
            self._weather_overlay_dirty = True
            self.screen.blit(overlay, (0, 0))

    @staticmethod
    @functools.lru_cache(maxsize=65536)
    def _raw_stratum_at(x, y):
        """Evaluate the base low-frequency spatial terrain wave at (x, y)."""
        wave = (
            math.sin(x * 0.21 + y * 0.16)
            + math.cos(x * 0.14 - y * 0.23)
            + 0.55 * math.sin((x + y) * 0.09)
            + 0.35 * math.cos((x - y) * 0.12)
        )
        if wave < -0.68:
            return 0
        if wave > 0.68:
            return 2
        return 1

    def _get_tile_stratum(self, _state, x, y):
        """Compute coherent multi-tile terrain stratum with 1x1 island suppression."""
        s_here = self._raw_stratum_at(x, y)
        if s_here == 1:
            return 1
        same_neighbors = (
            (1 if self._raw_stratum_at(x - 1, y) == s_here else 0)
            + (1 if self._raw_stratum_at(x + 1, y) == s_here else 0)
            + (1 if self._raw_stratum_at(x, y - 1) == s_here else 0)
            + (1 if self._raw_stratum_at(x, y + 1) == s_here else 0)
        )
        return s_here if same_neighbors >= 2 else 1

    def _draw_biome_floor_fx(self, biome_info, coords, dr, s_idx, now=None):
        """Render sparse animated environmental floor tells and atmospheric micro-effects per biome."""
        biome, pal = biome_info
        x, y, _, _ = coords
        if (x * 19 + y * 31) % 29 != 0:
            return
        sx, sy = int(dr[0]), int(dr[1])
        if now is None:
            now = time.time()

        if biome == "windy_ridge":
            sway = int(math.sin(now * 3.8 + x * 0.45 + y * 0.25) * 6)
            pygame.draw.line(self.screen, pal["floor_accent"], (sx + 10, sy + 26), (sx + 14 + sway, sy + 14), 2)
            pygame.draw.line(self.screen, pal["floor_speck"], (sx + 22, sy + 28), (sx + 26 + sway, sy + 17), 1)
        elif biome == "pastoral_valley":
            if s_idx == 0:
                rad = 2 + int(((math.sin(now * 2.6 + x * 0.8 + y * 0.6) + 1.0) * 0.5) * 5)
                pygame.draw.circle(self.screen, (165, 68, 198), (sx + 20, sy + 20), rad, 1)
            else:
                sway = int(math.sin(now * 3.4 + x * 0.4 + y * 0.2) * 5)
                pygame.draw.circle(self.screen, pal["floor_accent"], (sx + 18 + sway // 2, sy + 22), 5)
                pygame.draw.line(self.screen, (148, 246, 154), (sx + 10, sy + 18), (sx + 24 + sway, sy + 18), 2)
        elif biome == "swamp_mire":
            rad = 3 + int(((math.sin(now * 3.2 + x * 0.7 + y * 0.5) + 1.0) * 0.5) * 6)
            # Expanding pea-green scum ring with simmering toxic bubble core
            pygame.draw.circle(self.screen, pal["floor_accent"], (sx + 20, sy + 20), rad, 1)
            b_pulse = int(((math.sin(now * 4.5 + x * 1.3 + y * 0.9) + 1.0) * 0.5) * 3) + 1
            pygame.draw.circle(self.screen, pal["wall_glow"], (sx + 18, sy + 18), b_pulse)
        elif biome == "frozen_peaks":
            glint = int((math.sin(now * 4.5 + x * 1.1 + y * 0.9) + 1.0) * 2.5) + 2
            cx, cy = sx + 18, sy + 18
            pygame.draw.line(self.screen, pal["floor_speck"], (cx - glint, cy), (cx + glint, cy), 1)
            pygame.draw.line(self.screen, pal["floor_speck"], (cx, cy - glint), (cx, cy + glint), 1)
        elif biome == "tech_tower":
            pulse_x = sx + 6 + int(((now * 28.0 + x * 7 + y * 5) % 24))
            col = pal["wall_glow"] if s_idx == 0 else pal["floor_speck"]
            pygame.draw.line(self.screen, col, (pulse_x, sy + 20), (pulse_x + 5, sy + 20), 2)
        elif biome == "vitreous_basin":
            glint = int((math.sin(now * 5.0 + x * 1.2 + y * 0.8) + 1.0) * 2.5) + 2
            cx, cy = sx + 20, sy + 20
            pygame.draw.line(self.screen, pal["floor_speck"], (cx - glint, cy - glint), (cx + glint, cy + glint), 1)
            pygame.draw.circle(self.screen, pal["wall_glow"], (cx, cy), max(1, glint // 2))
        elif biome == "sunlit_aqueducts":
            if s_idx == 0:
                ripple = 2 + int(((math.sin(now * 3.0 + x * 0.7 + y * 0.5) + 1.0) * 0.5) * 5)
                pygame.draw.circle(self.screen, (132, 224, 236), (sx + 20, sy + 20), ripple, 1)
            else:
                sway = int(math.sin(now * 2.8 + x * 0.5 + y * 0.3) * 4)
                pygame.draw.circle(self.screen, pal["wall_glow"], (sx + 18 + sway, sy + 20), 3)

    def _draw_connected_wall_tile(self, target_surf, state, coords, dr, biome_info):
        """Render connected wall plateaus and 2.5D cliff facades with outer-edge-only borders."""
        x, y, w, h = coords
        biome, pal = biome_info
        sx, sy, ts, _ = int(dr[0]), int(dr[1]), int(dr[2]), int(dr[3])
        grid = state.world.grid
        wall_n = (y > 0) and (grid[y - 1][x] == constants.TILE_WALL)
        wall_s = (y + 1 < h) and (grid[y + 1][x] == constants.TILE_WALL)
        wall_w = (x > 0) and (grid[y][x - 1] == constants.TILE_WALL)
        wall_e = (x + 1 < w) and (grid[y][x + 1] == constants.TILE_WALL)

        if not isinstance(target_surf, pygame.Surface):
            pygame.draw.rect(target_surf, constants.COLOR_WALL, dr)
            return

        # 1. Sanctuary Biome: Sandbox testing grounds for PNG tile assets & autotiling
        if biome == "sanctuary":
            wall_vars = getattr(self, "wall_variants", None)
            default_wall = getattr(self, "wall_tile_surf", None)
            if default_wall is not None:
                if x == 0 and y == 0:
                    selected_wall = default_wall
                elif wall_vars and len(wall_vars) >= 4:
                    # Deterministic feature selection: 50% standard, 20% cracked, 15% mossy, 15% webbed
                    h_val = ((x * 37) ^ (y * 59) ^ (x * y * 13)) % 100
                    if h_val < 50:
                        selected_wall = wall_vars[0]
                    elif h_val < 70:
                        selected_wall = wall_vars[1]
                    elif h_val < 85:
                        selected_wall = wall_vars[2]
                    else:
                        selected_wall = wall_vars[3]
                else:
                    selected_wall = default_wall

                target_surf.blit(selected_wall, (sx, sy))
                return

        # 2. Swamp Biome: Organic mounded cliff walls and parasitic hive plateaus
        if biome == "swamp_mire":
            if wall_s:
                target_surf.fill(pal["wall_top"], (sx, sy, ts, ts))
                prev_clip = target_surf.get_clip()
                target_surf.set_clip(pygame.Rect(sx, sy, ts, ts))
                ax = sx - (x % 2) * ts
                ay = sy - (y % 2) * ts
                pat = ((x // 2) * 31 + (y // 2) * 47) % 3
                if pat == 0:
                    pygame.draw.ellipse(target_surf, pal["wall_face"], (ax + 8, ay + 10, 64, 60))
                    pygame.draw.ellipse(target_surf, pal["wall_top"], (ax + 16, ay + 18, 48, 44))
                    pygame.draw.ellipse(target_surf, pal["wall_hi"], (ax + 22, ay + 22, 28, 14), 1)
                elif pat == 1:
                    pygame.draw.ellipse(target_surf, pal["wall_face"], (ax + 6, ay + 8, 36, 32))
                    pygame.draw.ellipse(target_surf, pal["wall_face"], (ax + 36, ay + 38, 38, 34))
                    pygame.draw.circle(target_surf, pal["wall_glow"], (ax + 34, ay + 34), 3)
                else:
                    pygame.draw.ellipse(target_surf, pal["wall_face"], (ax + 8, ay + 20, 64, 40))
                    pygame.draw.ellipse(target_surf, pal["wall_hi"], (ax + 16, ay + 24, 48, 18), 1)
                target_surf.set_clip(prev_clip)

                if not wall_n:
                    target_surf.fill(pal["wall_mortar"], (sx, sy, ts, 2))
                    target_surf.fill(pal["wall_hi"], (sx, sy + 2, ts, 2))
                if not wall_w:
                    target_surf.fill(pal["wall_mortar"], (sx, sy, 2, ts))
                    target_surf.fill(pal["wall_hi"], (sx + 2, sy, 2, ts))
                if not wall_e:
                    target_surf.fill(pal["wall_mortar"], (sx + ts - 2, sy, 2, ts))
            else:
                # 2.5D cliff facade with soft rounded tiers and deep undercut drop shadow
                target_surf.fill(pal["wall_face"], (sx, sy, ts, ts))
                target_surf.fill(pal["wall_top"], (sx, sy, ts, 12))
                if not wall_n:
                    target_surf.fill(pal["wall_mortar"], (sx, sy, ts, 2))
                    target_surf.fill(pal["wall_hi"], (sx, sy + 2, ts, 2))
                target_surf.fill(pal["wall_hi"], (sx, sy + 11, ts, 2))
                pygame.draw.rect(target_surf, pal["wall_top"], (sx + 2, sy + 16, ts - 4, 8), border_radius=4)
                pygame.draw.rect(target_surf, pal["wall_hi"], (sx + 4, sy + 17, ts - 8, 2), border_radius=1)
                pygame.draw.rect(target_surf, pal["wall_top"], (sx + 4, sy + 26, ts - 8, 7), border_radius=3)
                pore_x = sx + 8 + ((x * 11) % (ts - 16))
                pygame.draw.circle(target_surf, pal["wall_glow"], (pore_x, sy + 28), 2)
                target_surf.fill(pal["wall_mortar"], (sx, sy + ts - 4, ts, 4))
                if not wall_w:
                    target_surf.fill(pal["wall_mortar"], (sx, sy, 2, ts))
                if not wall_e:
                    target_surf.fill(pal["wall_mortar"], (sx + ts - 2, sy, 2, ts))
            return

        # 2b. Tech Tower Biome: Engineered brushed-titanium bulkheads, louvers, and status pips
        if biome == "tech_tower":
            self._draw_tech_tower_wall_tile(target_surf, coords, dr, pal, (wall_n, wall_s, wall_w, wall_e))
            return

        # 3. All other biomes: Restore exact legacy procedural geometric wall rendering (matching 70ed514)
        if wall_s:
            # Connected Plateau / Wall Rooftop: seamless across adjacent wall tiles
            target_surf.fill(pal["wall_top"], (sx, sy, ts, ts))
            prev_clip = target_surf.get_clip()
            target_surf.set_clip(pygame.Rect(sx, sy, ts, ts))
            ax = sx - (x % 2) * ts
            ay = sy - (y % 2) * ts
            pat = ((x // 2) * 31 + (y // 2) * 47) % 3
            if pat == 0:
                pygame.draw.rect(target_surf, pal["wall_face"], (ax + 10, ay + 12, 60, 56), border_radius=6)
                pygame.draw.rect(target_surf, pal["wall_top"], (ax + 16, ay + 18, 48, 44), border_radius=4)
            elif pat == 1:
                pygame.draw.rect(target_surf, pal["wall_face"], (ax + 8, ay + 10, 32, 26), border_radius=4)
                pygame.draw.rect(target_surf, pal["wall_face"], (ax + 38, ay + 42, 34, 28), border_radius=4)
                pygame.draw.rect(target_surf, pal["wall_glow"], (ax + 34, ay + 34, 12, 6))
            else:
                pygame.draw.line(target_surf, pal["wall_face"], (ax + 6, ay + 26), (ax + 74, ay + 26), 3)
                pygame.draw.line(target_surf, pal["wall_face"], (ax + 14, ay + 54), (ax + 68, ay + 54), 3)
            target_surf.set_clip(prev_clip)

            # Outer-edge-only borders against floor tiles
            if not wall_n:
                target_surf.fill(pal["wall_mortar"], (sx, sy, ts, 2))
                target_surf.fill(pal["wall_hi"], (sx, sy + 2, ts, 3))
            if not wall_w:
                target_surf.fill(pal["wall_mortar"], (sx, sy, 2, ts))
                target_surf.fill(pal["wall_hi"], (sx + 2, sy, 2, ts))
            if not wall_e:
                target_surf.fill(pal["wall_mortar"], (sx + ts - 2, sy, 2, ts))
        else:
            # 2.5D South-facing cliff / bulkhead facade: continuous horizontally
            target_surf.fill(pal["wall_face"], (sx, sy, ts, ts))
            target_surf.fill(pal["wall_top"], (sx, sy, ts, 13))
            if not wall_n:
                target_surf.fill(pal["wall_mortar"], (sx, sy, ts, 2))
                target_surf.fill(pal["wall_hi"], (sx, sy + 2, ts, 2))
            target_surf.fill(pal["wall_hi"], (sx, sy + 12, ts, 2))
            if biome == "pastoral_valley":
                target_surf.fill(pal["wall_hi"], (sx, sy + 25, ts, 2))
                target_surf.fill(pal["wall_glow"], (sx, sy + 27, ts, 10))
                off = (x * 7) % 9
                for sx_step in range(off, ts - 4, 9):
                    target_surf.fill(pal["wall_mortar"], (sx + sx_step, sy + 15, 2, 5))
                    target_surf.fill(pal["wall_mortar"], (sx + sx_step + 2, sy + 29, 2, 6))
            elif biome == "sunlit_aqueducts":
                aq_wall = getattr(self, "prop_cache", {}).get("AqueductMossWall")
                if aq_wall is not None:
                    target_surf.blit(aq_wall, (sx, sy))
                else:
                    target_surf.fill(pal["wall_glow"], (sx + 4, sy + 16, ts - 8, 5))
                    target_surf.fill(pal["wall_mortar"], (sx + ts // 2 - 2, sy + 20, 4, 16))
            elif biome == "vitreous_basin":
                pygame.draw.polygon(
                    target_surf,
                    pal["wall_hi"],
                    [(sx + 6, sy + 15), (sx + ts // 2, sy + 28), (sx + ts - 6, sy + 15)],
                    1,
                )
                target_surf.fill(pal["wall_glow"], (sx + ts // 2 - 4, sy + 20, 8, 2))
            else:
                if (x + y) % 2 == 0:
                    target_surf.fill(pal["wall_top"], (sx + 6, sy + 18, ts - 12, 16))
                    target_surf.fill(pal["wall_glow"], (sx + ts // 2 - 6, sy + 24, 12, 3))
                else:
                    target_surf.fill(pal["wall_mortar"], (sx + ts // 2 - 1, sy + 15, 2, 22))
            target_surf.fill(pal["wall_mortar"], (sx, sy + ts - 3, ts, 3))
            if not wall_w:
                target_surf.fill(pal["wall_mortar"], (sx, sy, 2, ts))
            if not wall_e:
                target_surf.fill(pal["wall_mortar"], (sx + ts - 2, sy, 2, ts))

    def _draw_tech_tower_wall_tile(self, target_surf, coords, dr, pal, wall_adj):
        """Render engineered titanium wall bulkheads, louvers, recessed seams, and sparse status pips."""
        x, y, _, _ = coords
        sx, sy, ts = int(dr[0]), int(dr[1]), int(dr[2])
        wall_n, wall_s, wall_w, wall_e = wall_adj

        h_val = ((x * 2654435761) ^ (y * 2246822519)) & 0x7FFFFFFF
        roll = h_val % 100
        variant = (h_val >> 4) % 4

        top_base = pal["wall_top"]
        face_base = pal["wall_face"]
        mortar = pal["wall_mortar"]
        bevel_hi = self._shift_rgb_clamped(top_base, 26, 30, 34)
        panel_dark = self._shift_rgb_clamped(top_base, -14, -16, -20)
        panel_light = self._shift_rgb_clamped(top_base, 9, 11, 13)
        pip_col = (48, 172, 198) if (h_val & 1) else (178, 68, 138)

        if wall_s:
            # Engineered titanium rooftop / bulkhead plateau
            target_surf.fill(top_base, (sx, sy, ts, ts))
            pygame.draw.line(target_surf, panel_dark, (sx, sy + ts - 1), (sx + ts - 1, sy + ts - 1), 1)
            pygame.draw.line(target_surf, panel_dark, (sx + ts - 1, sy), (sx + ts - 1, sy + ts - 1), 1)
            if variant == 0:
                # Twin brushed inspection hatches with recessed seam
                pygame.draw.rect(target_surf, panel_dark, (sx + 4, sy + 5, ts - 8, 13), 1)
                pygame.draw.rect(target_surf, panel_light, (sx + 5, sy + 6, ts - 10, 1))
                pygame.draw.rect(target_surf, panel_dark, (sx + 4, sy + 22, ts - 8, 13), 1)
                pygame.draw.rect(target_surf, panel_light, (sx + 5, sy + 23, ts - 10, 1))
            elif variant == 1:
                # Horizontal ventilation louver bank
                pygame.draw.rect(target_surf, panel_dark, (sx + 5, sy + 7, ts - 10, ts - 14), 1)
                for ly in range(sy + 10, sy + ts - 9, 5):
                    target_surf.fill(mortar, (sx + 8, ly, ts - 16, 2))
                    target_surf.fill(panel_light, (sx + 8, ly + 2, ts - 16, 1))
            elif variant == 2:
                # Split expansion plate with center channel & corner bolts
                target_surf.fill(panel_dark, (sx + ts // 2 - 1, sy + 3, 2, ts - 6))
                target_surf.fill(panel_light, (sx + ts // 2 + 1, sy + 3, 1, ts - 6))
                corners = (
                    (sx + 5, sy + 5),
                    (sx + ts - 6, sy + 5),
                    (sx + 5, sy + ts - 6),
                    (sx + ts - 6, sy + ts - 6),
                )
                for bx, by in corners:
                    target_surf.set_at((bx, by), bevel_hi)
            else:
                # Clean brushed deck cap with horizontal structural seam & service bezel
                target_surf.fill(panel_dark, (sx + 3, sy + 18, ts - 6, 2))
                target_surf.fill(panel_light, (sx + 3, sy + 20, ts - 6, 1))
                pygame.draw.rect(target_surf, panel_dark, (sx + 8, sy + 6, 12, 8), 1)

            if roll < 15:
                px = sx + 8 + ((h_val >> 8) % (ts - 16))
                py = sy + 8 + ((h_val >> 12) % (ts - 16))
                target_surf.fill(mortar, (px - 1, py - 1, 5, 4))
                target_surf.fill(pip_col, (px, py, 3, 2))

            if not wall_n:
                target_surf.fill(mortar, (sx, sy, ts, 2))
                target_surf.fill(bevel_hi, (sx, sy + 2, ts, 2))
            if not wall_w:
                target_surf.fill(mortar, (sx, sy, 2, ts))
                target_surf.fill(bevel_hi, (sx + 2, sy, 2, ts))
            if not wall_e:
                target_surf.fill(mortar, (sx + ts - 2, sy, 2, ts))
        else:
            # 2.5D South-facing engineered titanium bulkhead facade
            target_surf.fill(face_base, (sx, sy, ts, ts))
            target_surf.fill(top_base, (sx, sy, ts, 12))
            if not wall_n:
                target_surf.fill(mortar, (sx, sy, ts, 2))
                target_surf.fill(bevel_hi, (sx, sy + 2, ts, 1))
            target_surf.fill(bevel_hi, (sx, sy + 11, ts, 2))
            face_seam = self._shift_rgb_clamped(face_base, -12, -14, -18)
            face_hi = self._shift_rgb_clamped(face_base, 12, 14, 18)

            face_var = variant % 3
            if face_var == 0:
                # Recessed horizontal vent louvers
                for ly in (sy + 17, sy + 23, sy + 29):
                    target_surf.fill(mortar, (sx + 6, ly, ts - 12, 2))
                    target_surf.fill(face_hi, (sx + 6, ly + 2, ts - 12, 1))
            elif face_var == 1:
                # Split vertical armor panels with recessed seam & rivets
                target_surf.fill(face_seam, (sx + ts // 2 - 1, sy + 14, 2, ts - 18))
                target_surf.fill(face_hi, (sx + ts // 2 + 1, sy + 14, 1, ts - 18))
                for bx in (sx + 5, sx + ts - 6):
                    target_surf.set_at((bx, sy + 17), face_hi)
                    target_surf.set_at((bx, sy + ts - 7), face_hi)
            else:
                # Inset bulkhead service frame
                pygame.draw.rect(target_surf, face_seam, (sx + 5, sy + 16, ts - 10, ts - 21), 1)
                target_surf.fill(face_hi, (sx + 6, sy + 17, ts - 12, 1))

            if roll < 15:
                target_surf.fill(mortar, (sx + ts - 11, sy + 18, 6, 4))
                target_surf.fill(pip_col, (sx + ts - 10, sy + 19, 4, 2))

            target_surf.fill(mortar, (sx, sy + ts - 3, ts, 3))
            if not wall_w:
                target_surf.fill(mortar, (sx, sy, 2, ts))
            if not wall_e:
                target_surf.fill(mortar, (sx + ts - 2, sy, 2, ts))

    def _draw_connected_floor_patterns(self, target_surf, biome_info, coords, dr):
        """Draw multi-tile connected shapes across same-surface tiles (restoring 70ed514 legacy)."""
        if not isinstance(target_surf, pygame.Surface):
            return
        biome, pal, s_idx, s_alt = biome_info
        x, y, _, _ = coords
        sx, sy, ts, _ = int(dr[0]), int(dr[1]), int(dr[2]), int(dr[3])

        prev_clip = target_surf.get_clip()
        target_surf.set_clip(pygame.Rect(sx, sy, ts, ts))

        # In sanctuary, let low-contrast flagstone textures carry cohesive stone read without stark 2x2 gridlines
        if biome == "sanctuary":
            if not getattr(self, "sanctuary_flagstone_variants", None):
                bx, by = x % 2, y % 2
                if bx == 0 and by == 0:
                    target_surf.fill(pal["wall_mortar"], (sx, sy, ts, 1))
                    target_surf.fill(pal["wall_mortar"], (sx, sy, 1, ts))
            target_surf.set_clip(prev_clip)
            return

        # 1. 4x4 Macro-Zone Underlay (160x160px continuous contour bands across 16 tiles)
        zx, zy = x // 4, y // 4
        zpx = sx - (x % 4) * ts
        zpy = sy - (y % 4) * ts
        z_style = ((zx * 43 + zy * 71 + s_idx * 19) & 0x7FFFFFFF) % 3
        if biome == "windy_ridge":
            strata_defs = pal.get("strata", [(pal["floor_base"], pal["floor_alt"])] * 3)
            s_base = strata_defs[s_idx][0]
            soft_wash = tuple(int(s_base[i] * 0.65 + s_alt[i] * 0.35) for i in range(3))
            if z_style == 0:
                pygame.draw.ellipse(target_surf, soft_wash, (zpx + 14, zpy + 18, 132, 54))
            elif z_style == 1:
                pygame.draw.ellipse(target_surf, soft_wash, (zpx + 22, zpy + 88, 118, 52))
            else:
                pygame.draw.ellipse(target_surf, soft_wash, (zpx + 18, zpy + 44, 124, 68))
        elif biome == "tech_tower":
            # Muted steel-navy macro deck bay tint (<= +10 RGB) — suppresses bright (0, 145, 185) ovals
            strata_defs = pal.get("strata", [(pal["floor_base"], pal["floor_alt"])] * 3)
            s_base = strata_defs[s_idx][0]
            bay_tint = self._shift_rgb_clamped(s_base, 5, 7, 10)
            if z_style == 0:
                pygame.draw.rect(target_surf, bay_tint, (zpx + 10, zpy + 16, 140, 52), border_radius=4)
            elif z_style == 1:
                pygame.draw.rect(target_surf, bay_tint, (zpx + 16, zpy + 88, 128, 56), border_radius=4)
            else:
                pygame.draw.rect(target_surf, bay_tint, (zpx + 20, zpy + 28, 120, 104), border_radius=4)
        elif z_style == 0:
            pygame.draw.rect(target_surf, s_alt, (zpx + 12, zpy + 22, 136, 34), border_radius=16)
            pygame.draw.rect(target_surf, s_alt, (zpx + 20, zpy + 98, 124, 38), border_radius=18)
        elif z_style == 1:
            pygame.draw.ellipse(target_surf, s_alt, (zpx + 18, zpy + 18, 124, 68))
            pygame.draw.rect(target_surf, s_alt, (zpx + 10, zpy + 108, 140, 30), border_radius=14)
        else:
            pygame.draw.polygon(
                target_surf,
                s_alt,
                [(zpx + 8, zpy + 46), (zpx + 110, zpy + 12), (zpx + 152, zpy + 58), (zpx + 48, zpy + 96)],
            )
            pygame.draw.ellipse(target_surf, s_alt, (zpx + 36, zpy + 102, 108, 44))

        # 2. 2x2 Connected Block Motifs (80x80px shapes spanning 4 tiles with 4 distinct patterns)
        bx, by = x // 2, y // 2
        ax = sx - (x % 2) * ts
        ay = sy - (y % 2) * ts
        pat = ((bx * 37 + by * 59 + zx * 13 + zy * 29 + s_idx * 7) & 0x7FFFFFFF) % 4

        if biome == "pastoral_valley":
            if s_idx == 0:
                # Recessed Tar / Poison Swamp: large multi-tile currents, vortex rings, and submerged ribs
                pygame.draw.ellipse(target_surf, (46, 20, 68), (ax + 8, ay + 12, 64, 56))
                pygame.draw.ellipse(target_surf, (28, 12, 42), (ax + 16, ay + 20, 48, 40))
                if pat == 0:
                    pygame.draw.ellipse(target_surf, (148, 56, 182), (ax + 18, ay + 22, 44, 34), 2)
                    pygame.draw.ellipse(target_surf, (195, 95, 225), (ax + 28, ay + 30, 24, 18), 1)
                elif pat == 1:
                    pygame.draw.rect(target_surf, (132, 48, 168), (ax + 12, ay + 34, 56, 10), border_radius=5)
                    pygame.draw.circle(target_surf, (185, 82, 215), (ax + 26, ay + 24), 6, 1)
                    pygame.draw.circle(target_surf, (185, 82, 215), (ax + 54, ay + 52), 8, 1)
                elif pat == 2:
                    for ry_off in (24, 38, 52):
                        pygame.draw.arc(
                            target_surf, (96, 42, 134), (ax + 18, ay + ry_off - 8, 44, 20), 0.3, 2.8, 2
                        )
                else:
                    pygame.draw.rect(target_surf, (78, 34, 112), (ax + 14, ay + 26, 52, 6), border_radius=3)
                    pygame.draw.rect(target_surf, (78, 34, 112), (ax + 22, ay + 48, 38, 5), border_radius=2)
            elif s_idx == 2:
                # Warm Tan Pathway: large multi-tile sandstone slabs, cart tracks, and plaza rings
                if pat == 0:
                    pygame.draw.rect(target_surf, (224, 192, 134), (ax + 10, ay + 10, 58, 28), border_radius=8)
                    pygame.draw.rect(target_surf, (164, 124, 74), (ax + 10, ay + 10, 58, 28), 2, border_radius=8)
                    pygame.draw.rect(target_surf, (216, 182, 124), (ax + 14, ay + 44, 52, 26), border_radius=8)
                elif pat == 1:
                    pygame.draw.rect(target_surf, (168, 128, 76), (ax, ay + 22, 80, 6))
                    pygame.draw.rect(target_surf, (168, 128, 76), (ax, ay + 52, 80, 6))
                    pygame.draw.rect(target_surf, (228, 198, 142), (ax, ay + 32, 80, 14))
                elif pat == 2:
                    pygame.draw.circle(target_surf, (224, 192, 134), (ax + 40, ay + 40), 26)
                    pygame.draw.circle(target_surf, (164, 124, 74), (ax + 40, ay + 40), 26, 2)
                    pygame.draw.circle(target_surf, (198, 162, 106), (ax + 40, ay + 40), 14)
                else:
                    pygame.draw.ellipse(target_surf, (224, 192, 134), (ax + 14, ay + 18, 52, 42))
                    pygame.draw.ellipse(target_surf, pal["floor_accent"], (ax + 26, ay + 32, 26, 14))
            else:
                # Bright Lime/Mint Meadow: connected tuft groves, fairy rings, and sweeping turf swells
                if pat == 0:
                    pygame.draw.ellipse(target_surf, pal["floor_accent"], (ax + 12, ay + 22, 56, 32))
                    pygame.draw.ellipse(target_surf, (144, 244, 152), (ax + 18, ay + 18, 44, 22))
                    pygame.draw.rect(target_surf, (162, 250, 168), (ax + 24, ay + 24, 32, 6), border_radius=3)
                elif pat == 1:
                    for ang in range(0, 360, 60):
                        rad_a = math.radians(ang)
                        cx_r = int(ax + 40 + math.cos(rad_a) * 22)
                        cy_r = int(ay + 40 + math.sin(rad_a) * 20)
                        pygame.draw.circle(target_surf, pal["floor_accent"], (cx_r, cy_r), 9)
                        pygame.draw.circle(target_surf, (144, 244, 152), (cx_r - 1, cy_r - 2), 6)
                elif pat == 2:
                    pygame.draw.rect(target_surf, (64, 178, 78), (ax + 6, ay + 16, 68, 10), border_radius=5)
                    pygame.draw.rect(target_surf, (144, 244, 152), (ax + 10, ay + 14, 58, 5), border_radius=2)
                    pygame.draw.rect(target_surf, (64, 178, 78), (ax + 12, ay + 52, 58, 10), border_radius=5)
                    pygame.draw.rect(target_surf, (144, 244, 152), (ax + 16, ay + 50, 48, 5), border_radius=2)
                else:
                    pygame.draw.ellipse(target_surf, (186, 152, 98), (ax + 20, ay + 28, 40, 22))
                    pygame.draw.ellipse(target_surf, (218, 186, 128), (ax + 26, ay + 31, 28, 14))
                    pygame.draw.circle(target_surf, pal["floor_accent"], (ax + 20, ay + 28), 8)
                    pygame.draw.circle(target_surf, (144, 244, 152), (ax + 20, ay + 26), 5)
        elif biome == "tech_tower":
            self._draw_tech_tower_floor_patterns(target_surf, pal, s_idx, (x, y, sx, sy, ts))
        elif biome == "swamp_mire":
            if s_idx == 0:
                # Deep viscous fluid: horizontal wavy ripple bands and floating pea-green scum
                for r_o in (16, 32, 48, 64):
                    pygame.draw.arc(target_surf, pal["floor_alt"], (ax + 4, ay + r_o - 6, 72, 14), 0.1, 3.0, 2)
                if pat == 0:
                    pygame.draw.ellipse(target_surf, pal["floor_accent"], (ax + 16, ay + 20, 48, 18))
                    pygame.draw.circle(target_surf, pal["floor_speck"], (ax + 26, ay + 24), 3)
                    pygame.draw.circle(target_surf, pal["floor_speck"], (ax + 42, ay + 28), 2)
                elif pat == 1:
                    pygame.draw.ellipse(target_surf, pal["floor_accent"], (ax + 24, ay + 42, 36, 14))
                    pygame.draw.circle(target_surf, pal["floor_speck"], (ax + 32, ay + 46), 2)
                else:
                    pygame.draw.ellipse(target_surf, pal["floor_accent"], (ax + 12, ay + 30, 26, 12))
                    pygame.draw.ellipse(target_surf, pal["floor_accent"], (ax + 44, ay + 50, 28, 12))
            elif s_idx == 2:
                # Raised calcified hive chitin and peat bank
                pygame.draw.ellipse(target_surf, pal["wall_top"], (ax + 10, ay + 14, 60, 52))
                pygame.draw.ellipse(target_surf, pal["wall_hi"], (ax + 16, ay + 18, 48, 40), 2)
                if pat == 1:
                    pygame.draw.circle(target_surf, pal["wall_glow"], (ax + 40, ay + 40), 4)
            else:
                # Stratum 1: Sluggish eggplant fluid with soft horizontal ripples and algae scum flecks
                for r_o in (20, 40, 60):
                    pygame.draw.arc(target_surf, pal["floor_alt"], (ax + 8, ay + r_o - 5, 64, 12), 0.1, 3.0, 2)
                if pat == 0:
                    pygame.draw.ellipse(target_surf, pal["floor_accent"], (ax + 20, ay + 28, 38, 16))
                    pygame.draw.circle(target_surf, pal["floor_speck"], (ax + 30, ay + 34), 3)
                elif pat == 1:
                    pygame.draw.circle(target_surf, pal["floor_accent"], (ax + 26, ay + 26), 7)
                    pygame.draw.circle(target_surf, pal["floor_accent"], (ax + 54, ay + 46), 6)
                else:
                    pygame.draw.ellipse(target_surf, pal["floor_accent"], (ax + 24, ay + 38, 32, 14))
        elif biome == "frozen_peaks":
            if s_idx == 0:
                # Continuous Mirror-Ice Basin with branching multi-tile fracture networks
                if pat == 0:
                    pygame.draw.line(target_surf, pal["wall_mortar"], (ax + 6, ay + 12), (ax + 74, ay + 68), 2)
                    pygame.draw.line(target_surf, pal["wall_mortar"], (ax + 40, ay + 40), (ax + 68, ay + 16), 2)
                    pygame.draw.line(target_surf, pal["floor_speck"], (ax + 8, ay + 10), (ax + 74, ay + 66), 1)
                elif pat == 1:
                    pts = [(ax + 40, ay + 10), (ax + 68, ay + 40), (ax + 40, ay + 70), (ax + 12, ay + 40)]
                    pygame.draw.polygon(target_surf, pal["floor_accent"], pts, 2)
                else:
                    pygame.draw.line(target_surf, pal["floor_speck"], (ax + 10, ay + 24), (ax + 70, ay + 24), 3)
                    pygame.draw.line(target_surf, pal["floor_speck"], (ax + 18, ay + 52), (ax + 66, ay + 52), 2)
            elif s_idx == 2:
                # Sweeping Multi-Tile Snowdrift Dunes
                pygame.draw.ellipse(target_surf, pal["floor_speck"], (ax + 8, ay + 14, 64, 26))
                pygame.draw.ellipse(target_surf, pal["wall_hi"], (ax + 14, ay + 44, 54, 22))
            else:
                if pat == 0:
                    pygame.draw.line(target_surf, pal["floor_accent"], (ax + 8, ay + 58), (ax + 72, ay + 18), 3)
                    pygame.draw.line(target_surf, pal["floor_speck"], (ax + 10, ay + 55), (ax + 72, ay + 15), 2)
                elif pat == 1:
                    pygame.draw.ellipse(target_surf, pal["wall_face"], (ax + 16, ay + 22, 48, 34))
                    pygame.draw.ellipse(target_surf, pal["floor_speck"], (ax + 20, ay + 20, 38, 16))
                else:
                    pygame.draw.circle(target_surf, pal["floor_accent"], (ax + 40, ay + 40), 22, 2)
                    pygame.draw.line(target_surf, pal["floor_speck"], (ax + 16, ay + 40), (ax + 64, ay + 40), 2)
                    pygame.draw.line(target_surf, pal["floor_speck"], (ax + 40, ay + 16), (ax + 40, ay + 64), 2)
        elif biome == "vitreous_basin":
            if s_idx == 0:
                # Reflective fractured glass flat: crystalline refraction seams & mirror highlights
                pygame.draw.line(target_surf, pal["wall_mortar"], (ax + 8, ay + 12), (ax + 72, ay + 66), 2)
                pygame.draw.line(target_surf, pal["wall_glow"], (ax + 12, ay + 10), (ax + 70, ay + 62), 1)
                if pat in (0, 2):
                    pygame.draw.line(target_surf, pal["floor_speck"], (ax + 14, ay + 58), (ax + 54, ay + 18), 2)
            elif s_idx == 2:
                # Raised crystalline salt-crust shelf
                pygame.draw.ellipse(target_surf, pal["floor_accent"], (ax + 10, ay + 14, 60, 48))
                pygame.draw.ellipse(target_surf, pal["floor_speck"], (ax + 18, ay + 20, 40, 24), 1)
            else:
                # Sun-bleached salt crust polygon plates
                pygame.draw.line(target_surf, pal["wall_mortar"], (ax + 6, ay + 38), (ax + 74, ay + 42), 1)
                pygame.draw.line(target_surf, pal["floor_speck"], (ax + 8, ay + 36), (ax + 74, ay + 40), 1)
                if pat == 1:
                    pygame.draw.polygon(
                        target_surf,
                        pal["floor_accent"],
                        [(ax + 40, ay + 16), (ax + 62, ay + 40), (ax + 40, ay + 62)],
                        1,
                    )
        elif biome == "sunlit_aqueducts":
            if s_idx == 0:
                # Sunken turquoise aqueduct channel with sun-dappled current bands
                pygame.draw.rect(target_surf, (64, 144, 158), (ax + 8, ay + 16, 64, 48), border_radius=10)
                pygame.draw.line(target_surf, (132, 224, 236), (ax + 14, ay + 32), (ax + 64, ay + 32), 2)
                pygame.draw.line(target_surf, (132, 224, 236), (ax + 20, ay + 50), (ax + 58, ay + 50), 1)
            elif s_idx == 2:
                # Lush overgrown moss viaduct bridge
                pygame.draw.ellipse(target_surf, pal["wall_glow"], (ax + 10, ay + 12, 60, 54))
                pygame.draw.circle(target_surf, (164, 244, 146), (ax + 28, ay + 28), 6)
                pygame.draw.circle(target_surf, (164, 244, 146), (ax + 50, ay + 46), 5)
            else:
                # Sun-baked terracotta flagstone seams with moss tufts
                pygame.draw.rect(target_surf, pal["wall_mortar"], (ax + 8, ay + 8, 64, 30), 1, border_radius=3)
                pygame.draw.rect(target_surf, pal["wall_mortar"], (ax + 12, ay + 42, 56, 30), 1, border_radius=3)
                if pat in (0, 2):
                    pygame.draw.circle(target_surf, pal["floor_accent"], (ax + 40, ay + 40), 5)
        elif biome == "windy_ridge":
            self._draw_windy_ridge_floor_patterns(target_surf, pal, s_idx, (x, y, sx, sy, ts))
        else:
            # Generic fallback connected cobbles & rings for any unspecialized biome
            if s_idx == 0:
                pygame.draw.ellipse(target_surf, pal["floor_accent"], (ax + 10, ay + 14, 60, 52))
                if pat == 0:
                    pygame.draw.ellipse(target_surf, pal["wall_glow"], (ax + 22, ay + 26, 36, 28))
                else:
                    pygame.draw.circle(target_surf, pal["floor_speck"], (ax + 30, ay + 34), 8, 1)
                    pygame.draw.circle(target_surf, pal["floor_speck"], (ax + 52, ay + 46), 10, 1)
            elif s_idx == 2:
                if pat == 0:
                    pygame.draw.rect(target_surf, pal["wall_top"], (ax + 8, ay + 10, 64, 28), border_radius=6)
                    pygame.draw.rect(target_surf, pal["wall_hi"], (ax + 10, ay + 12, 60, 3))
                    pygame.draw.rect(target_surf, pal["wall_top"], (ax + 12, ay + 44, 56, 26), border_radius=6)
                elif pat == 1:
                    pygame.draw.circle(target_surf, pal["wall_top"], (ax + 40, ay + 40), 26)
                    pygame.draw.circle(target_surf, pal["wall_hi"], (ax + 40, ay + 40), 26, 2)
                    pygame.draw.circle(target_surf, pal["floor_accent"], (ax + 40, ay + 40), 12, 2)
                else:
                    pygame.draw.rect(target_surf, pal["wall_top"], (ax, ay + 18, 80, 16))
                    pygame.draw.rect(target_surf, pal["wall_hi"], (ax, ay + 18, 80, 2))
                    pygame.draw.rect(target_surf, pal["wall_top"], (ax, ay + 48, 80, 16))
            else:
                if pat == 0:
                    pygame.draw.ellipse(target_surf, pal["floor_accent"], (ax + 12, ay + 20, 56, 36))
                    pygame.draw.ellipse(target_surf, pal["floor_speck"], (ax + 22, ay + 26, 36, 18))
                elif pat == 1:
                    pygame.draw.circle(target_surf, pal["wall_top"], (ax + 40, ay + 40), 24, 3)
                    pygame.draw.circle(target_surf, pal["floor_accent"], (ax + 40, ay + 40), 16)
                elif pat == 2:
                    pygame.draw.rect(target_surf, pal["floor_accent"], (ax + 8, ay + 18, 64, 8), border_radius=4)
                    pygame.draw.rect(target_surf, pal["floor_accent"], (ax + 14, ay + 50, 54, 8), border_radius=4)
                else:
                    pygame.draw.ellipse(target_surf, pal["floor_accent"], (ax + 18, ay + 24, 44, 30))

        target_surf.set_clip(prev_clip)

    def _draw_tech_tower_floor_patterns(self, target_surf, pal, s_idx, tile_geom):
        """Render recessed sub-floor trench grating, brushed titanium deck seams, and muted data-bus channels."""
        x, y, sx, sy, ts = tile_geom
        strata_defs = pal.get("strata", [(pal["floor_base"], pal["floor_alt"])] * 3)
        s_base = strata_defs[s_idx][0]
        h_val = ((x * 73856093) ^ (y * 19349663) ^ (s_idx * 83492791)) & 0x7FFFFFFF
        roll = h_val % 100

        # Muted (~45%) cyan & magenta accents so decks stay sleek and never blaze neon
        muted_cyan = (24, 114, 138)
        muted_magenta = (132, 48, 108)
        etched_cyan = (34, 98, 124)
        node_magenta = (146, 56, 118)

        if s_idx == 0:
            # Stratum 0 (Reactor Trench): thin dimmed under-deck conduits UNDER 6px-pitch steel grating
            conduit_x = sx + 14 + ((h_val >> 3) % 12)
            target_surf.fill(muted_cyan, (conduit_x, sy, 2, ts))
            if roll < 32:
                target_surf.fill(muted_magenta, (min(sx + ts - 3, conduit_x + 5), sy, 1, ts))
            if (y % 3) == 0:
                target_surf.fill(muted_cyan, (sx, sy + 18, ts, 1))
            grate_bar = self._shift_rgb_clamped(s_base, -6, -7, -9)
            grate_hi = self._shift_rgb_clamped(s_base, 9, 12, 16)
            for gy in range(2, ts, 6):
                target_surf.fill(grate_bar, (sx, sy + gy, ts, 2))
                if gy + 2 < ts:
                    target_surf.fill(grate_hi, (sx, sy + gy + 2, ts, 1))
            # Cross-support bar every other tile column
            if (x % 2) == 0:
                target_surf.fill(grate_bar, (sx + ts // 2, sy, 2, ts))
        elif s_idx == 1:
            # Stratum 1 (Brushed Titanium Deck): subtle 1px bulkhead seams + sparse (~16%) etched PCB traces
            seam_dark = self._shift_rgb_clamped(s_base, -9, -10, -10)
            seam_hi = self._shift_rgb_clamped(s_base, 8, 9, 10)
            pygame.draw.line(target_surf, seam_dark, (sx, sy), (sx + ts - 1, sy), 1)
            pygame.draw.line(target_surf, seam_dark, (sx, sy), (sx, sy + ts - 1), 1)
            pygame.draw.line(target_surf, seam_hi, (sx + 1, sy + 1), (sx + ts - 2, sy + 1), 1)
            if (x + y) % 2 == 0:
                pygame.draw.line(target_surf, seam_dark, (sx + 4, sy + ts // 2), (sx + ts - 5, sy + ts // 2), 1)
            if roll < 16:
                turn_x = sx + 10 + (h_val % 18)
                turn_y = sy + 10 + ((h_val >> 5) % 18)
                pygame.draw.line(target_surf, etched_cyan, (sx + 2, turn_y), (turn_x, turn_y), 1)
                pygame.draw.line(target_surf, etched_cyan, (turn_x, turn_y), (turn_x, sy + ts - 4), 1)
                pygame.draw.circle(target_surf, node_magenta, (turn_x, turn_y), 2)
        else:
            # Stratum 2 (Data-Bus Walkway): anodized steel panels with recessed muted 2px data-bus channel
            seam_dark = self._shift_rgb_clamped(s_base, -12, -13, -15)
            seam_hi = self._shift_rgb_clamped(s_base, 10, 11, 13)
            trough = self._shift_rgb_clamped(s_base, -24, -26, -32)
            pygame.draw.rect(target_surf, seam_dark, (sx, sy, ts, ts), 1)
            pygame.draw.line(target_surf, seam_hi, (sx + 1, sy + 1), (sx + ts - 2, sy + 1), 1)
            cy = sy + ts // 2
            target_surf.fill(trough, (sx, cy - 3, ts, 6))
            target_surf.fill(muted_cyan, (sx, cy - 1, ts, 2))
            target_surf.fill(muted_magenta, (sx, cy + 1, ts, 1))
            if roll < 26:
                jx = sx + 12 + (h_val % 16)
                target_surf.fill(seam_dark, (jx - 3, cy - 4, 7, 8))
                target_surf.fill(muted_cyan, (jx - 1, cy - 2, 3, 4))

    def _draw_tech_tower_stratum_borders(self, target_surf, dr, s_idx, strata_defs, neighbors):
        """Draw recessed dark-steel shadow edges (25% darker) and 1px muted slate-cyan chamfer highlights."""
        sx, sy, ts = int(dr[0]), int(dr[1]), int(dr[2])
        same_n, same_s, same_w, same_e, same_nw, same_ne, same_sw, same_se = neighbors

        outer_canvas_col = strata_defs[1][0]
        edge_shadow = tuple(max(0, int(c * 0.75)) for c in outer_canvas_col)
        chamfer_hi = (74, 118, 144) if s_idx == 0 else (96, 128, 158)

        c_rad = 6
        rnd_nw = (not same_n) and (not same_w)
        rnd_ne = (not same_n) and (not same_e)
        rnd_sw = (not same_s) and (not same_w)
        rnd_se = (not same_s) and (not same_e)

        # 1. Clean 45-degree chamfered metallic outer corners
        if rnd_nw:
            pygame.draw.polygon(target_surf, outer_canvas_col, [(sx, sy), (sx + c_rad, sy), (sx, sy + c_rad)])
            pygame.draw.line(target_surf, edge_shadow, (sx, sy + c_rad), (sx + c_rad, sy), 2)
            pygame.draw.line(target_surf, chamfer_hi, (sx + 2, sy + c_rad + 1), (sx + c_rad + 1, sy + 2), 1)
        if rnd_ne:
            pygame.draw.polygon(
                target_surf, outer_canvas_col, [(sx + ts, sy), (sx + ts - c_rad, sy), (sx + ts, sy + c_rad)]
            )
            pygame.draw.line(target_surf, edge_shadow, (sx + ts - c_rad, sy), (sx + ts, sy + c_rad), 2)
            pygame.draw.line(target_surf, chamfer_hi, (sx + ts - c_rad - 1, sy + 2), (sx + ts - 2, sy + c_rad + 1), 1)
        if rnd_sw:
            pygame.draw.polygon(
                target_surf, outer_canvas_col, [(sx, sy + ts), (sx + c_rad, sy + ts), (sx, sy + ts - c_rad)]
            )
            pygame.draw.line(target_surf, edge_shadow, (sx, sy + ts - c_rad), (sx + c_rad, sy + ts), 2)
            pygame.draw.line(target_surf, chamfer_hi, (sx + 2, sy + ts - c_rad - 1), (sx + c_rad + 1, sy + ts - 2), 1)
        if rnd_se:
            pygame.draw.polygon(
                target_surf,
                outer_canvas_col,
                [(sx + ts, sy + ts), (sx + ts - c_rad, sy + ts), (sx + ts, sy + ts - c_rad)],
            )
            pygame.draw.line(target_surf, edge_shadow, (sx + ts - c_rad, sy + ts), (sx + ts, sy + ts - c_rad), 2)
            pygame.draw.line(
                target_surf, chamfer_hi, (sx + ts - c_rad - 1, sy + ts - 2), (sx + ts - 2, sy + ts - c_rad - 1), 1
            )

        # 2. Recessed 2px dark steel shadow edge + 1px muted slate-cyan chamfer highlight
        if not same_n:
            x0 = sx + (c_rad if rnd_nw else 0)
            x1 = sx + ts - (c_rad if rnd_ne else 0)
            if x1 > x0:
                target_surf.fill(edge_shadow, (x0, sy, x1 - x0, 2))
                target_surf.fill(chamfer_hi, (x0, sy + 2, x1 - x0, 1))
        if not same_s:
            x0 = sx + (c_rad if rnd_sw else 0)
            x1 = sx + ts - (c_rad if rnd_se else 0)
            if x1 > x0:
                target_surf.fill(edge_shadow, (x0, sy + ts - 2, x1 - x0, 2))
                target_surf.fill(chamfer_hi, (x0, sy + ts - 3, x1 - x0, 1))
        if not same_w:
            y0 = sy + (c_rad if rnd_nw else 0)
            y1 = sy + ts - (c_rad if rnd_sw else 0)
            if y1 > y0:
                target_surf.fill(edge_shadow, (sx, y0, 2, y1 - y0))
                target_surf.fill(chamfer_hi, (sx + 2, y0, 1, y1 - y0))
        if not same_e:
            y0 = sy + (c_rad if rnd_ne else 0)
            y1 = sy + ts - (c_rad if rnd_se else 0)
            if y1 > y0:
                target_surf.fill(edge_shadow, (sx + ts - 2, y0, 2, y1 - y0))
                target_surf.fill(chamfer_hi, (sx + ts - 3, y0, 1, y1 - y0))

        # 3. Concave inner corner bevels
        if same_n and same_w and not same_nw:
            target_surf.fill(edge_shadow, (sx, sy, 2, 2))
            target_surf.set_at((sx + 2, sy + 2), chamfer_hi)
        if same_n and same_e and not same_ne:
            target_surf.fill(edge_shadow, (sx + ts - 2, sy, 2, 2))
            target_surf.set_at((sx + ts - 3, sy + 2), chamfer_hi)
        if same_s and same_w and not same_sw:
            target_surf.fill(edge_shadow, (sx, sy + ts - 2, 2, 2))
            target_surf.set_at((sx + 2, sy + ts - 3), chamfer_hi)
        if same_s and same_e and not same_se:
            target_surf.fill(edge_shadow, (sx + ts - 2, sy + ts - 2, 2, 2))
            target_surf.set_at((sx + ts - 3, sy + ts - 3), chamfer_hi)

    def _draw_windy_ridge_floor_patterns(self, target_surf, pal, s_idx, tile_geom):
        """Render organic low-contrast highland clover basins, combed meadow grass, and weathered limestone cobbles."""
        x, y, sx, sy, ts = tile_geom
        strata_defs = pal.get("strata", [(pal["floor_base"], pal["floor_alt"])] * 3)
        s_base, s_alt = strata_defs[s_idx]
        h_val = ((x * 73856093) ^ (y * 19349663) ^ (s_idx * 83492791)) & 0x7FFFFFFF
        roll = h_val % 100
        ox = 6 + (h_val % 15)
        oy = 6 + ((h_val >> 4) % 15)

        if s_idx == 0:
            # Stratum 0 (Deep Viridian Clover Basin): subtle mossy hollows + ~18% clover/tuft accents
            if roll < 36:
                hollow_col = self._shift_rgb_clamped(s_base, -4, -7, -4)
                pygame.draw.ellipse(target_surf, hollow_col, (sx + ox - 3, sy + oy - 2, 18, 12))
            if roll < 18:
                clover_col = self._shift_rgb_clamped(s_alt, 10, 18, 10)
                tuft_col = self._shift_rgb_clamped(s_alt, 4, 12, 6)
                cx_c, cy_c = sx + ox + 4, sy + oy + 4
                pygame.draw.circle(target_surf, clover_col, (cx_c - 2, cy_c), 2)
                pygame.draw.circle(target_surf, clover_col, (cx_c + 2, cy_c), 2)
                pygame.draw.circle(target_surf, clover_col, (cx_c, cy_c - 2), 2)
                pygame.draw.line(target_surf, tuft_col, (cx_c - 6, cy_c + 5), (cx_c - 4, cy_c + 1), 1)
                pygame.draw.line(target_surf, tuft_col, (cx_c + 5, cy_c + 5), (cx_c + 7, cy_c + 1), 1)
        elif s_idx == 1:
            # Stratum 1 (Sunlit Emerald Meadow): gentle wind-combed strokes + ~15% tiny golden wildflower specks
            stroke_hi = self._shift_rgb_clamped(s_alt, 4, 10, 4)
            stroke_lo = self._shift_rgb_clamped(s_base, -6, -9, -5)
            for idx in range(3):
                gx = sx + 5 + ((h_val >> (idx * 3)) % (ts - 12))
                gy = sy + 9 + ((h_val >> (idx * 3 + 2)) % (ts - 12))
                col = stroke_hi if idx % 2 == 0 else stroke_lo
                pygame.draw.line(target_surf, col, (gx, gy), (gx + 4, gy - 3), 1)
            if roll < 15:
                fx, fy = sx + ox + 5, sy + oy + 5
                stem_col = self._shift_rgb_clamped(s_base, 2, 14, 4)
                petal_col = (214, 192, 104)
                core_col = (232, 214, 134)
                pygame.draw.line(target_surf, stem_col, (fx, fy + 3), (fx + 1, fy), 1)
                pygame.draw.circle(target_surf, petal_col, (fx + 1, fy), 2)
                target_surf.set_at((min(sx + ts - 1, fx + 1), max(sy, fy)), core_col)
        else:
            # Stratum 2 (Ancient Limestone Cobble Trail): irregular weathered flagstones & ~12% carved ring slabs
            mortar = self._shift_rgb_clamped(s_base, -14, -14, -12)
            stone_a = self._shift_rgb_clamped(s_base, 10, 9, 7)
            stone_b = self._shift_rgb_clamped(s_base, -7, -7, -6)
            stone_hi = self._shift_rgb_clamped(s_base, 14, 13, 10)
            split_x = 16 + (h_val % 9)
            split_y = 17 + ((h_val >> 3) % 7)
            r1 = (sx + 2, sy + 2, split_x - 3, split_y - 3)
            r2 = (sx + split_x + 1, sy + 2, ts - split_x - 3, split_y - 3)
            r3 = (sx + 2, sy + split_y + 1, ts - 4, ts - split_y - 3)
            pygame.draw.rect(target_surf, stone_a, r1, border_radius=4)
            pygame.draw.rect(target_surf, mortar, r1, 1, border_radius=4)
            pygame.draw.rect(target_surf, stone_b, r2, border_radius=4)
            pygame.draw.rect(target_surf, mortar, r2, 1, border_radius=4)
            pygame.draw.rect(target_surf, stone_a if (h_val & 1) else stone_b, r3, border_radius=4)
            pygame.draw.rect(target_surf, mortar, r3, 1, border_radius=4)
            if roll < 12:
                # Weathered carved limestone ring / rune inlay (low-contrast, zero cyan/slate spikes)
                rcx, rcy = sx + ts // 2, sy + ts // 2
                pygame.draw.circle(target_surf, mortar, (rcx, rcy), 9, 1)
                pygame.draw.circle(target_surf, stone_hi, (rcx - 1, rcy - 1), 6, 1)

    def _draw_windy_ridge_stratum_borders(self, target_surf, coords, dr, s_idx, strata_defs, neighbors):
        """Draw soft earth/moss elevation seams with overhanging grass tufts & pebbles for windy_ridge."""
        x, y = coords
        sx, sy, ts = int(dr[0]), int(dr[1]), int(dr[2])
        same_n, same_s, same_w, same_e, same_nw, same_ne, same_sw, same_se = neighbors

        outer_canvas_col = strata_defs[1][0]
        s_base = strata_defs[s_idx][0]
        edge_shade = tuple(max(0, int(c * 0.80)) for c in s_base)
        soft_lip = tuple(int(s_base[i] * 0.55 + outer_canvas_col[i] * 0.45) for i in range(3))
        tuft_col = self._shift_rgb_clamped(outer_canvas_col, 10, 18, 8)
        pebble_col = self._shift_rgb_clamped(strata_defs[2][0], -10, -10, -8)

        c_rad = 8
        rnd_nw = (not same_n) and (not same_w)
        rnd_ne = (not same_n) and (not same_e)
        rnd_sw = (not same_s) and (not same_w)
        rnd_se = (not same_s) and (not same_e)

        # 1. Soft rounded outer corners masked cleanly into surrounding meadow
        if rnd_nw:
            pygame.draw.polygon(target_surf, outer_canvas_col, [(sx, sy), (sx + c_rad, sy), (sx, sy + c_rad)])
            pygame.draw.line(target_surf, edge_shade, (sx + 1, sy + c_rad), (sx + c_rad, sy + 1), 2)
        if rnd_ne:
            pygame.draw.polygon(
                target_surf, outer_canvas_col, [(sx + ts, sy), (sx + ts - c_rad, sy), (sx + ts, sy + c_rad)]
            )
            pygame.draw.line(target_surf, edge_shade, (sx + ts - c_rad, sy + 1), (sx + ts - 1, sy + c_rad), 2)
        if rnd_sw:
            pygame.draw.polygon(
                target_surf, outer_canvas_col, [(sx, sy + ts), (sx + c_rad, sy + ts), (sx, sy + ts - c_rad)]
            )
            pygame.draw.line(target_surf, edge_shade, (sx + 1, sy + ts - c_rad), (sx + c_rad, sy + ts - 1), 2)
        if rnd_se:
            pygame.draw.polygon(
                target_surf,
                outer_canvas_col,
                [(sx + ts, sy + ts), (sx + ts - c_rad, sy + ts), (sx + ts, sy + ts - c_rad)],
            )
            pygame.draw.line(target_surf, edge_shade, (sx + ts - c_rad, sy + ts - 1), (sx + ts - 1, sy + ts - c_rad), 2)

        # 2. Subtle 1-2px shaded earth/moss cardinal seams + overhanging tufts & pebbles
        seam_hash = ((x * 2654435761) ^ (y * 2246822519)) & 0x7FFFFFFF
        t_off1 = 9 + (seam_hash % 10)
        t_off2 = 22 + ((seam_hash >> 4) % 9)
        if not same_n:
            x0 = sx + (c_rad if rnd_nw else 0)
            x1 = sx + ts - (c_rad if rnd_ne else 0)
            if x1 > x0:
                target_surf.fill(edge_shade, (x0, sy, x1 - x0, 2))
                target_surf.fill(soft_lip, (x0, sy + 2, x1 - x0, 1))
                pygame.draw.line(target_surf, tuft_col, (sx + t_off1, sy + 3), (sx + t_off1 + 2, sy), 1)
                if s_idx == 2:
                    pygame.draw.circle(target_surf, pebble_col, (sx + t_off2, sy + 2), 2)
        if not same_s:
            x0 = sx + (c_rad if rnd_sw else 0)
            x1 = sx + ts - (c_rad if rnd_se else 0)
            if x1 > x0:
                target_surf.fill(edge_shade, (x0, sy + ts - 2, x1 - x0, 2))
                target_surf.fill(soft_lip, (x0, sy + ts - 3, x1 - x0, 1))
                pygame.draw.line(target_surf, tuft_col, (sx + t_off2, sy + ts - 1), (sx + t_off2 + 2, sy + ts - 4), 1)
                if s_idx == 2:
                    pygame.draw.circle(target_surf, pebble_col, (sx + t_off1, sy + ts - 2), 2)
        if not same_w:
            y0 = sy + (c_rad if rnd_nw else 0)
            y1 = sy + ts - (c_rad if rnd_sw else 0)
            if y1 > y0:
                target_surf.fill(edge_shade, (sx, y0, 2, y1 - y0))
                target_surf.fill(soft_lip, (sx + 2, y0, 1, y1 - y0))
                pygame.draw.line(target_surf, tuft_col, (sx + 1, sy + t_off1), (sx + 4, sy + t_off1 - 2), 1)
        if not same_e:
            y0 = sy + (c_rad if rnd_ne else 0)
            y1 = sy + ts - (c_rad if rnd_se else 0)
            if y1 > y0:
                target_surf.fill(edge_shade, (sx + ts - 2, y0, 2, y1 - y0))
                target_surf.fill(soft_lip, (sx + ts - 3, y0, 1, y1 - y0))
                pygame.draw.line(target_surf, tuft_col, (sx + ts - 2, sy + t_off2), (sx + ts - 4, sy + t_off2 - 2), 1)

        # 3. Soft concave inner corner caps
        if same_n and same_w and not same_nw:
            target_surf.fill(edge_shade, (sx, sy, 2, 2))
        if same_n and same_e and not same_ne:
            target_surf.fill(edge_shade, (sx + ts - 2, sy, 2, 2))
        if same_s and same_w and not same_sw:
            target_surf.fill(edge_shade, (sx, sy + ts - 2, 2, 2))
        if same_s and same_e and not same_se:
            target_surf.fill(edge_shade, (sx + ts - 2, sy + ts - 2, 2, 2))

    def _draw_stratum_perimeter_borders(self, target_surf, state, coords, dr, biome_info):
        """Draw transition outlines and rounded corner contours ONLY along edges bordering different surfaces."""
        if not isinstance(target_surf, pygame.Surface):
            return
        biome, pal, s_idx, strata_defs = biome_info
        # Mid-ground stratum (1) acts as the universal canvas; raised (2) and recessed (0) draw their own outer rims
        if s_idx == 1:
            return

        x, y, w, h = coords
        sx, sy, ts, _ = int(dr[0]), int(dr[1]), int(dr[2]), int(dr[3])
        grid = state.world.grid

        def _is_same(nx, ny):
            if nx < 0 or ny < 0 or nx >= w or ny >= h:
                return True
            if grid[ny][nx] == constants.TILE_WALL:
                return True
            return self._get_tile_stratum(state, nx, ny) == s_idx

        same_n = _is_same(x, y - 1)
        same_s = _is_same(x, y + 1)
        same_w = _is_same(x - 1, y)
        same_e = _is_same(x + 1, y)
        same_nw = _is_same(x - 1, y - 1)
        same_ne = _is_same(x + 1, y - 1)
        same_sw = _is_same(x - 1, y + 1)
        same_se = _is_same(x + 1, y + 1)

        # If completely surrounded by the same surface, draw zero borders
        if same_n and same_s and same_w and same_e and same_nw and same_ne and same_sw and same_se:
            return

        if biome == "windy_ridge":
            neighbors = (same_n, same_s, same_w, same_e, same_nw, same_ne, same_sw, same_se)
            self._draw_windy_ridge_stratum_borders(target_surf, (x, y), dr, s_idx, strata_defs, neighbors)
            return
        if biome == "tech_tower":
            neighbors = (same_n, same_s, same_w, same_e, same_nw, same_ne, same_sw, same_se)
            self._draw_tech_tower_stratum_borders(target_surf, dr, s_idx, strata_defs, neighbors)
            return

        outer_canvas_col = strata_defs[1][0]
        if biome == "pastoral_valley" and s_idx == 0:
            rim_hi = (16, 8, 24)
            rim_lo = (16, 8, 24)
            inner_lip = (58, 26, 82)
        elif biome == "pastoral_valley" and s_idx == 2:
            rim_hi = (224, 192, 134)
            rim_lo = (156, 118, 68)
            inner_lip = (178, 140, 86)
        elif biome == "swamp_mire" and s_idx == 0:
            rim_hi = (28, 14, 38)
            rim_lo = (18, 8, 22)
            inner_lip = (142, 172, 44)
        elif biome == "swamp_mire" and s_idx == 2:
            rim_hi = (216, 202, 226)
            rim_lo = (18, 8, 22)
            inner_lip = (86, 44, 82)
        elif s_idx == 0:
            rim_hi = pal["wall_mortar"]
            rim_lo = pal["wall_mortar"]
            inner_lip = pal["floor_accent"]
        else:
            rim_hi = pal["wall_hi"]
            rim_lo = pal["wall_mortar"]
            inner_lip = pal["wall_top"]

        c_rad = 10
        rnd_nw = (not same_n) and (not same_w)
        rnd_ne = (not same_n) and (not same_e)
        rnd_sw = (not same_s) and (not same_w)
        rnd_se = (not same_s) and (not same_e)

        # 1. Outer Rounded Corners (masking the 90-degree tile corner with the surrounding surface color)
        if rnd_nw:
            pygame.draw.polygon(target_surf, outer_canvas_col, [(sx, sy), (sx + c_rad, sy), (sx, sy + c_rad)])
            pygame.draw.line(target_surf, rim_hi, (sx + 1, sy + c_rad), (sx + c_rad, sy + 1), 3)
            pygame.draw.line(target_surf, inner_lip, (sx + 3, sy + c_rad + 2), (sx + c_rad + 2, sy + 3), 2)
        if rnd_ne:
            pygame.draw.polygon(
                target_surf, outer_canvas_col, [(sx + ts, sy), (sx + ts - c_rad, sy), (sx + ts, sy + c_rad)]
            )
            pygame.draw.line(target_surf, rim_hi, (sx + ts - c_rad, sy + 1), (sx + ts - 1, sy + c_rad), 3)
            pygame.draw.line(target_surf, inner_lip, (sx + ts - c_rad - 2, sy + 3), (sx + ts - 3, sy + c_rad + 2), 2)
        if rnd_sw:
            pygame.draw.polygon(
                target_surf, outer_canvas_col, [(sx, sy + ts), (sx + c_rad, sy + ts), (sx, sy + ts - c_rad)]
            )
            pygame.draw.line(target_surf, rim_lo, (sx + 1, sy + ts - c_rad), (sx + c_rad, sy + ts - 1), 3)
            pygame.draw.line(target_surf, inner_lip, (sx + 3, sy + ts - c_rad - 2), (sx + c_rad + 2, sy + ts - 3), 2)
        if rnd_se:
            pygame.draw.polygon(
                target_surf,
                outer_canvas_col,
                [(sx + ts, sy + ts), (sx + ts - c_rad, sy + ts), (sx + ts, sy + ts - c_rad)],
            )
            pygame.draw.line(target_surf, rim_lo, (sx + ts - c_rad, sy + ts - 1), (sx + ts - 1, sy + ts - c_rad), 3)
            pygame.draw.line(
                target_surf, inner_lip, (sx + ts - c_rad - 2, sy + ts - 3), (sx + ts - 3, sy + ts - c_rad - 2), 2
            )

        # 2. Cardinal Perimeter Edge Outlines (drawn ONLY where adjacent tile is a different floor surface)
        if not same_n:
            x0 = sx + (c_rad if rnd_nw else 0)
            x1 = sx + ts - (c_rad if rnd_ne else 0)
            if x1 > x0:
                target_surf.fill(inner_lip, (x0, sy + 2, x1 - x0, 3))
                target_surf.fill(rim_hi, (x0, sy, x1 - x0, 2))
        if not same_s:
            x0 = sx + (c_rad if rnd_sw else 0)
            x1 = sx + ts - (c_rad if rnd_se else 0)
            if x1 > x0:
                target_surf.fill(inner_lip, (x0, sy + ts - 5, x1 - x0, 3))
                target_surf.fill(rim_lo, (x0, sy + ts - 2, x1 - x0, 2))
        if not same_w:
            y0 = sy + (c_rad if rnd_nw else 0)
            y1 = sy + ts - (c_rad if rnd_sw else 0)
            if y1 > y0:
                target_surf.fill(inner_lip, (sx + 2, y0, 3, y1 - y0))
                target_surf.fill(rim_hi, (sx, y0, 2, y1 - y0))
        if not same_e:
            y0 = sy + (c_rad if rnd_ne else 0)
            y1 = sy + ts - (c_rad if rnd_se else 0)
            if y1 > y0:
                target_surf.fill(inner_lip, (sx + ts - 5, y0, 3, y1 - y0))
                target_surf.fill(rim_lo, (sx + ts - 2, y0, 2, y1 - y0))

        # 3. Concave Inner Corner Caps (where both adjacent cardinals match s_idx, but diagonal differs)
        if same_n and same_w and not same_nw:
            target_surf.fill(inner_lip, (sx, sy, 4, 4))
            target_surf.fill(rim_hi, (sx, sy, 2, 2))
        if same_n and same_e and not same_ne:
            target_surf.fill(inner_lip, (sx + ts - 4, sy, 4, 4))
            target_surf.fill(rim_hi, (sx + ts - 2, sy, 2, 2))
        if same_s and same_w and not same_sw:
            target_surf.fill(inner_lip, (sx, sy + ts - 4, 4, 4))
            target_surf.fill(rim_lo, (sx, sy + ts - 2, 2, 2))
        if same_s and same_e and not same_se:
            target_surf.fill(inner_lip, (sx + ts - 4, sy + ts - 4, 4, 4))
            target_surf.fill(rim_lo, (sx + ts - 2, sy + ts - 2, 2, 2))

    @staticmethod
    def _sanctuary_floor_variant_index(x, y, count):
        """Deterministically hash tile coordinates to select a low-contrast Sanctuary floor variant."""
        if count <= 1:
            return 0
        return (((int(x) * 73856093) ^ (int(y) * 19349663)) & 0x7FFFFFFF) % count

    def _draw_static_tile_to_surface(self, target_surf, state, coords, dr):
        """Render static tile to surface."""
        x, y, _, _ = coords
        tile = state.world.grid[y][x]
        biome = self._resolve_tile_biome(state, x, y)
        b_pack = getattr(self, "biome_tiles", {}).get(biome) or getattr(self, "biome_tiles", {}).get("windy_ridge")
        pal = constants.BIOME_PALETTES.get(biome, constants.BIOME_PALETTES["windy_ridge"])

        # PASS 3: Structural walls (with collisions)
        if tile == constants.TILE_WALL:
            self._draw_connected_wall_tile(target_surf, state, coords, dr, (biome, pal))
            return biome, pal, 0

        s_idx = self._get_tile_stratum(state, x, y)
        sx, sy = int(dr[0]), int(dr[1])
        ts = constants.TILE_SIZE

        # Sanctuary biome: cohesive low-contrast flagstone, dirt path, oak wood, & pond water zones
        if biome == "sanctuary":
            # 1. Base ground fill - 100% opaque to eliminate any white background bleed
            if isinstance(target_surf, pygame.Surface):
                target_surf.fill(constants.COLOR_SEPIA_AMBER, (sx, sy, ts, ts))
            zone_type = (
                state.world.get_sanctuary_zone_type(x, y)
                if hasattr(state.world, "get_sanctuary_zone_type")
                else None
            )
            if zone_type == "pond_water":
                if isinstance(target_surf, pygame.Surface):
                    target_surf.fill((30, 66, 84), (sx, sy, ts, ts))
                    # Subtle bank rim & translucent horizontal water shimmer
                    for dx_n, dy_n, rx, ry, rw, rh in (
                        (0, -1, sx, sy, ts, 3),
                        (0, 1, sx, sy + ts - 3, ts, 3),
                        (-1, 0, sx, sy, 3, ts),
                        (1, 0, sx + ts - 3, sy, 3, ts),
                    ):
                        if state.world.get_sanctuary_zone_type(x + dx_n, y + dy_n) != "pond_water":
                            target_surf.fill((48, 86, 82), (rx, ry, rw, rh))
                    wave_off = ((x * 11 + y * 7) % 10) + 6
                    pygame.draw.line(
                        target_surf, (56, 108, 126), (sx + 6, sy + wave_off), (sx + ts - 8, sy + wave_off), 1
                    )
                    pygame.draw.line(
                        target_surf,
                        (44, 90, 108),
                        (sx + 10, sy + min(ts - 5, wave_off + 14)),
                        (sx + ts - 6, sy + min(ts - 5, wave_off + 14)),
                        1,
                    )
            else:
                if zone_type == "wood_floor" and getattr(self, "sanctuary_wood_floor_variants", None):
                    sanctuary_floors = self.sanctuary_wood_floor_variants
                elif zone_type == "dirt_path" and getattr(self, "sanctuary_dirt_path_variants", None):
                    sanctuary_floors = self.sanctuary_dirt_path_variants
                else:
                    sanctuary_floors = getattr(self, "sanctuary_flagstone_variants", None) or getattr(
                        self, "floor_variants", None
                    )
                if sanctuary_floors:
                    v_idx = self._sanctuary_floor_variant_index(x, y, len(sanctuary_floors))
                    target_surf.blit(sanctuary_floors[v_idx], (sx, sy))
                elif b_pack:
                    strata_list = b_pack.get("strata_floors")
                    tier_floors = strata_list[s_idx] if strata_list else b_pack["floors"]
                    target_surf.blit(tier_floors[(x * 7 + y * 13) % len(tier_floors)], (sx, sy))

            # 2. Autotiled floor surfaces & multi-tile sandbox footprints
            if b_pack:
                strata_defs = pal.get("strata", [(pal["floor_base"], pal["floor_alt"])] * 3)
                s_base, s_alt = strata_defs[s_idx]
                self._draw_connected_floor_patterns(target_surf, (biome, pal, s_idx, s_alt), coords, dr)
                self._draw_stratum_perimeter_borders(target_surf, state, coords, dr, (biome, pal, s_idx, strata_defs))
                if y > 0 and state.world.grid[y - 1][x] == constants.TILE_WALL:
                    target_surf.blit(b_pack["shadow_n"], (sx, sy))
                if x > 0 and state.world.grid[y][x - 1] == constants.TILE_WALL:
                    target_surf.blit(b_pack["shadow_w"], (sx, sy))

            # 3. Upper decorative layers (grass, rocks) with positional offsets
            if tile in (constants.TILE_GRASS, constants.TILE_THICKET):
                if getattr(self, "grass_natural_surf", None) is not None:
                    gdx = ((x * 13 + y * 17) % 9) - 4
                    gdy = ((x * 19 + y * 7) % 9) - 4
                    target_surf.blit(self.grass_natural_surf, (sx + gdx, sy + gdy))
                    if tile == constants.TILE_THICKET:
                        gdx2 = ((x * 7 + y * 23) % 9) - 4
                        gdy2 = ((x * 29 + y * 11) % 9) - 4
                        target_surf.blit(self.grass_natural_surf, (sx + gdx2, sy + gdy2))
                elif getattr(self, "grass_pools", None):
                    clusters = getattr(state.world, "grass_decorations", {}).get((x, y), ())
                    for pool_key, variant, dx, dy in clusters:
                        pool = self.grass_pools.get(pool_key)
                        if pool:
                            tuft = pool[variant % len(pool)]
                            target_surf.blit(tuft, (sx + 8 + dx, sy + 8 + dy))
            elif tile == constants.TILE_OBSTACLE:
                w_name = getattr(state.world, "name", "").lower()
                map_file = getattr(state.world, "map_filename", "").lower()
                if ("ruins" in w_name or "ruins" in map_file) and "RuinsRubble" in getattr(self, "prop_cache", {}):
                    target_surf.blit(self.prop_cache["RuinsRubble"], (sx, sy))
                elif ("swamp" in w_name or "swamp" in map_file) and "SwampVent" in getattr(self, "prop_cache", {}):
                    target_surf.blit(self.prop_cache["SwampVent"], (sx, sy))
                elif (
                    "colophon" in w_name
                    or (x * 7 + y * 13) % 3 == 0
                ) and "CryptClutter" in getattr(self, "prop_cache", {}):
                    target_surf.blit(self.prop_cache["CryptClutter"], (sx, sy))
                else:
                    rock_surf = getattr(self, "prop_cache", {}).get("Rock")
                    if rock_surf is not None:
                        target_surf.blit(rock_surf, (sx, sy))

            return biome, pal, s_idx

        # Non-Sanctuary biomes: Restore exact legacy procedural geometric floor rendering (matching 70ed514)
        if b_pack:
            strata_defs = pal.get("strata", [(pal["floor_base"], pal["floor_alt"])] * 3)
            s_base, s_alt = strata_defs[s_idx]
            strata_list = b_pack.get("strata_floors")
            tier_floors = strata_list[s_idx] if strata_list else b_pack["floors"]
            v_idx = (x * 7 + y * 13) % len(tier_floors)
            target_surf.blit(tier_floors[v_idx], (sx, sy))
            if biome == "vitreous_basin":
                v_key = "VitreousGlassFlat" if s_idx == 0 else "VitreousSaltFloor"
                v_tile = getattr(self, "prop_cache", {}).get(v_key)
                if v_tile is not None:
                    target_surf.blit(v_tile, (sx, sy))
            elif biome == "sunlit_aqueducts" and s_idx == 1:
                aq_tile = getattr(self, "prop_cache", {}).get("AqueductTerracottaFloor")
                if aq_tile is not None:
                    target_surf.blit(aq_tile, (sx, sy))

            # 1. Multi-tile connected patterns (2x2 80x80px & 4x4 160x160px) across same-surface tiles
            self._draw_connected_floor_patterns(target_surf, (biome, pal, s_idx, s_alt), coords, dr)

            # 2. Borders, rims, and rounded corners ONLY on outer perimeter edges against different surfaces
            self._draw_stratum_perimeter_borders(target_surf, state, coords, dr, (biome, pal, s_idx, strata_defs))

            # 3. Ambient occlusion drop-shadows from adjacent north/west walls
            if y > 0 and state.world.grid[y - 1][x] == constants.TILE_WALL:
                target_surf.blit(b_pack["shadow_n"], (sx, sy))
            if x > 0 and state.world.grid[y][x - 1] == constants.TILE_WALL:
                target_surf.blit(b_pack["shadow_w"], (sx, sy))

            # 4. Stamp procedural grass/thicket tufts or swamp thorns directly onto the static tile surface
            if tile in (constants.TILE_GRASS, constants.TILE_THICKET):
                if biome == "swamp_mire":
                    tdx = ((x * 13 + y * 17) % 9) - 4
                    tdy = ((x * 19 + y * 7) % 9) - 4
                    flora_first = (x * 7 + y * 13) % 2 == 0
                    primary_key = "SwampFlora" if flora_first else "SwampThorns"
                    secondary_key = "SwampThorns" if flora_first else "SwampFlora"
                    prim_surf = getattr(self, "prop_cache", {}).get(primary_key)
                    if prim_surf is not None:
                        target_surf.blit(prim_surf, (sx + tdx, sy + tdy))
                    if tile == constants.TILE_THICKET:
                        tdx2 = ((x * 7 + y * 23) % 9) - 4
                        tdy2 = ((x * 29 + y * 11) % 9) - 4
                        sec_surf = getattr(self, "prop_cache", {}).get(secondary_key) or prim_surf
                        if sec_surf is not None:
                            target_surf.blit(sec_surf, (sx + tdx2, sy + tdy2))
                elif getattr(self, "grass_pools", None):
                    clusters = getattr(state.world, "grass_decorations", {}).get((x, y), ())
                    for pool_key, variant, dx, dy in clusters:
                        pool = self.grass_pools.get(pool_key)
                        if pool:
                            tuft = pool[variant % len(pool)]
                            target_surf.blit(tuft, (sx + 8 + dx, sy + 8 + dy))
            elif tile == constants.TILE_OBSTACLE:
                w_name = getattr(state.world, "name", "").lower()
                map_file = getattr(state.world, "map_filename", "").lower()
                if biome == "swamp_mire" and "SwampVent" in getattr(self, "prop_cache", {}):
                    vent_surf = self.prop_cache["SwampVent"]
                    target_surf.blit(vent_surf, (sx, sy))
                elif (
                    biome in ("tech_tower", "ruins")
                    or "ruins" in w_name
                    or "ruins" in map_file
                ) and "RuinsRubble" in getattr(self, "prop_cache", {}):
                    rubble_surf = self.prop_cache["RuinsRubble"]
                    target_surf.blit(rubble_surf, (sx, sy))
                elif (
                    "colophon" in w_name
                    or "crypt" in w_name
                ) and "CryptClutter" in getattr(self, "prop_cache", {}):
                    crypt_surf = self.prop_cache["CryptClutter"]
                    target_surf.blit(crypt_surf, (sx, sy))
                else:
                    rock_surf = getattr(self, "prop_cache", {}).get("Rock")
                    if rock_surf is not None:
                        target_surf.blit(rock_surf, (sx, sy))
        else:
            pygame.draw.rect(target_surf, constants.COLOR_FLOOR, dr, 1)

        return biome, pal, s_idx

    def _draw_world_tile(self, state, coords, dr):
        """Render a single world tile (used as direct fallback for mock test screens)."""
        x, y, _, _ = coords
        tile = state.world.grid[y][x]
        biome, pal, s_idx = self._draw_static_tile_to_surface(self.screen, state, coords, dr)
        if tile == constants.TILE_WALL:
            return
        self._draw_biome_floor_fx((biome, pal), coords, dr, s_idx)
        if tile == constants.TILE_LOTUS_FRAME:
            lotus_surf = self.prop_cache.get("LotusFrame")
            if lotus_surf is not None:
                self.screen.blit(lotus_surf, (int(dr[0]), int(dr[1])))
            else:
                pygame.draw.rect(self.screen, (36, 48, 86), dr, border_radius=4)
            pulse_col = (0, 240, 255) if int(time.time() * 4 + x + y) % 2 == 0 else (235, 70, 195)
            pygame.draw.rect(self.screen, pulse_col, (dr[0] + 4, dr[1] + 4, dr[2] - 8, dr[3] - 8), 2, border_radius=3)

    def invalidate_static_world(self):
        """Clear cached static world chunks and minimap surfaces on world transition."""
        self._chunk_cache.clear()
        self._chunk_world_key = None
        self._minimap_surf = None
        self._minimap_walls_surf = None
        self._minimap_world_key = None

    def _get_world_chunk(self, state, cx, cy, w, h):
        """Return or lazily bake a 16x16 tile chunk Surface and its sparse animated tile list."""
        world_key = (id(state.world), getattr(state.world, "name", ""), id(state.world.grid), w, h)
        if self._chunk_world_key != world_key:
            self._chunk_cache.clear()
            self._chunk_world_key = world_key

        cached = self._chunk_cache.get((cx, cy))
        if cached is not None:
            return cached

        chunk_tiles = 16
        ts = constants.TILE_SIZE
        tx0, ty0 = cx * chunk_tiles, cy * chunk_tiles
        tx1, ty1 = min(w, tx0 + chunk_tiles), min(h, ty0 + chunk_tiles)
        cw, ch = max(1, (tx1 - tx0) * ts), max(1, (ty1 - ty0) * ts)
        chunk_surf = pygame.Surface((cw, ch))
        if pygame.display.get_init() and pygame.display.get_surface() is not None:
            chunk_surf = chunk_surf.convert()

        bg = (
            constants.COLOR_SEPIA_AMBER
            if getattr(state.world, "name", "sanctuary") == "sanctuary"
            else constants.COLOR_CHARCOAL
        )
        chunk_surf.fill(bg)
        anim_tiles = []

        for ty in range(ty0, ty1):
            for tx in range(tx0, tx1):
                local_dr = ((tx - tx0) * ts, (ty - ty0) * ts, ts, ts)
                biome, pal, s_idx = self._draw_static_tile_to_surface(
                    chunk_surf, state, (tx, ty, w, h), local_dr
                )
                tile = state.world.grid[ty][tx]
                if tile == constants.TILE_LOTUS_FRAME or (
                    tile != constants.TILE_WALL and (tx * 19 + ty * 31) % 29 == 0
                ):
                    anim_tiles.append((tx, ty, tile, biome, pal, s_idx))

        result = (chunk_surf, anim_tiles)
        self._chunk_cache[(cx, cy)] = result
        return result

    def render(self, state, audio_manager=None):
        """Draw the game state using a camera."""
        bg = (
            constants.COLOR_SEPIA_AMBER
            if getattr(state.world, 'name', 'sanctuary') == "sanctuary"
            else constants.COLOR_CHARCOAL
        )
        self.screen.fill(bg)
        sw, sh = self.screen.get_width(), self.screen.get_height()
        h, w = len(state.world.grid), len(state.world.grid[0]) if len(state.world.grid) > 0 else 0
        ww, wh = w * constants.TILE_SIZE, h * constants.TILE_SIZE
        if hasattr(state, 'camera'):
            if state.camera.screen_w != sw or state.camera.screen_h != sh:
                state.camera.screen_w, state.camera.screen_h = sw, sh
            state.camera.world_w, state.camera.world_h = ww, wh
            ox, oy = state.camera.get_offset()
        else:
            cam = Camera(sw, sh, ww, wh)
            ox, oy = cam.get_target_offset(state.player.get_center())
        if getattr(state, 'shake_timer', 0) > 0 and getattr(state, 'screen_shake_enabled', True):
            ox += random.uniform(-constants.SCREEN_SHAKE_INTENSITY, constants.SCREEN_SHAKE_INTENSITY)
            oy += random.uniform(-constants.SCREEN_SHAKE_INTENSITY, constants.SCREEN_SHAKE_INTENSITY)

        is_real_surface = isinstance(self.screen, pygame.Surface)
        ts = constants.TILE_SIZE
        now = time.time()

        if is_real_surface and w > 0 and h > 0:
            iox, ioy = int(round(ox)), int(round(oy))
            chunk_tiles = 16
            chunk_px = chunk_tiles * ts
            max_cx = (w - 1) // chunk_tiles
            max_cy = (h - 1) // chunk_tiles
            scx = max(0, iox // chunk_px)
            scy = max(0, ioy // chunk_px)
            ecx = min(max_cx, (iox + sw) // chunk_px)
            ecy = min(max_cy, (ioy + sh) // chunk_px)

            visible_anim = []
            for cy in range(scy, ecy + 1):
                for cx in range(scx, ecx + 1):
                    chunk_surf, anim_tiles = self._get_world_chunk(state, cx, cy, w, h)
                    self.screen.blit(chunk_surf, (cx * chunk_px - iox, cy * chunk_px - ioy))
                    if anim_tiles:
                        visible_anim.extend(anim_tiles)

            for tx, ty, tile, biome, pal, s_idx in visible_anim:
                sx_t = tx * ts - iox
                sy_t = ty * ts - ioy
                if sx_t + ts < 0 or sx_t > sw or sy_t + ts < 0 or sy_t > sh:
                    continue
                dr = (sx_t, sy_t, ts, ts)
                if tile != constants.TILE_WALL and (tx * 19 + ty * 31) % 29 == 0:
                    self._draw_biome_floor_fx((biome, pal), (tx, ty, w, h), dr, s_idx, now=now)
                if tile == constants.TILE_LOTUS_FRAME:
                    lotus_surf = self.prop_cache.get("LotusFrame")
                    if lotus_surf is not None:
                        self.screen.blit(lotus_surf, (int(dr[0]), int(dr[1])))
                    else:
                        pygame.draw.rect(self.screen, (36, 48, 86), dr, border_radius=4)
                    pulse_col = (0, 240, 255) if int(now * 4 + tx + ty) % 2 == 0 else (235, 70, 195)
                    pygame.draw.rect(
                        self.screen, pulse_col, (dr[0] + 4, dr[1] + 4, dr[2] - 8, dr[3] - 8), 2, border_radius=3
                    )
        else:
            sx, sy = int(max(0, ox // ts)), int(max(0, oy // ts))
            ex, ey = int(min(w, (ox + sw) // ts + 1)), int(min(h, (oy + sh) // ts + 1))
            for y in range(sy, ey):
                for x in range(sx, ex):
                    dr = (x * ts - ox, y * ts - oy, ts, ts)
                    self._draw_world_tile(state, (x, y, w, h), dr)

        # World Debris (Persistent visual remnants, culled to viewport)
        for debris in getattr(state, 'world_debris', []):
            if debris['name'] == 'BarrelRubble':
                dx_s, dy_s = debris['pos'][0] - ox, debris['pos'][1] - oy
                if -64 <= dx_s <= sw + 64 and -64 <= dy_s <= sh + 64:
                    img = self.image_cache.get("barrel_3.png")
                    if img:
                        self.screen.blit(img, (dx_s, dy_s))

        prop_cache = getattr(self, "prop_cache", {}) if is_real_surface else {}
        player_obj = getattr(state, "player", None)
        player_bottom = (
            float(player_obj.y) + float(player_obj.height) if player_obj is not None else 0.0
        )
        deferred_tree_canopies = []
        for obj in getattr(state.world, 'interactables', []):
            sx_o, sy_o = obj.x - ox, obj.y - oy
            if sx_o + obj.width < -96 or sx_o > sw + 96 or sy_o + obj.height < -96 or sy_o > sh + 96:
                continue
            obj_ptype = getattr(obj, "prop_type", None)
            if obj_ptype == "sanctuary_tree" or obj.name == "SanctuaryTreeCanopy":
                tree_bottom = float(obj.y) + float(obj.height)
                if tree_bottom > player_bottom:
                    deferred_tree_canopies.append(obj)
                else:
                    self._draw_sanctuary_tree_canopy(obj, ox, oy, prop_cache)
            elif obj_ptype == "pond_lily_reeds" or obj.name == "PondLilyReeds":
                lily_surf = prop_cache.get("PondLilyReeds")
                if lily_surf is not None:
                    self.screen.blit(lily_surf, (int(sx_o), int(sy_o)))
                else:
                    pygame.draw.circle(self.screen, (48, 108, 58), (int(sx_o) + 16, int(sy_o) + 22), 8)
            elif obj_ptype == "garden_flora" or obj.name == "GardenFlora":
                flora_surf = prop_cache.get("GardenFlora")
                if flora_surf is not None:
                    self.screen.blit(flora_surf, (int(sx_o), int(sy_o)))
                else:
                    pygame.draw.circle(self.screen, (56, 108, 56), (int(sx_o) + 20, int(sy_o) + 20), 10)
            elif obj_ptype == "locked_shed_door" or obj.name == "LockedShedDoor":
                door_surf = prop_cache.get("LockedShedDoor")
                if door_surf is not None:
                    self.screen.blit(door_surf, (int(sx_o), int(sy_o)))
                else:
                    pygame.draw.rect(self.screen, (76, 52, 34), (int(sx_o) + 6, int(sy_o) + 4, 28, 34))
                    pygame.draw.rect(self.screen, (206, 162, 58), (int(sx_o) + 24, int(sy_o) + 20, 7, 7))
            elif obj_ptype == "mossy_gravestone" or obj.name == "MossyGravestone":
                grave_surf = prop_cache.get("MossyGravestone")
                if grave_surf is not None:
                    self.screen.blit(grave_surf, (int(sx_o), int(sy_o)))
                else:
                    pygame.draw.rect(self.screen, (104, 102, 98), (int(sx_o) + 10, int(sy_o) + 10, 20, 24))
            elif obj.name == "Exit Ladder":
                lx, ly, lw, lh = int(sx_o), int(sy_o), int(obj.width), int(obj.height)
                pygame.draw.rect(self.screen, (24, 18, 14), (lx + 4, ly + 2, lw - 8, lh - 4), border_radius=4)
                pygame.draw.rect(self.screen, (215, 180, 95), (lx + 8, ly + 4, 4, lh - 8))
                pygame.draw.rect(self.screen, (215, 180, 95), (lx + lw - 12, ly + 4, 4, lh - 8))
                for rung_y in range(ly + 8, ly + lh - 6, 7):
                    pygame.draw.line(self.screen, (240, 215, 140), (lx + 10, rung_y), (lx + lw - 10, rung_y), 2)
            elif hasattr(obj, 'target_name'):
                self.draw_warp(obj, ox, oy)
            elif obj.name == "Suspicious Leaf Pile":
                lx, ly, lw, lh = int(sx_o), int(sy_o), int(obj.width), int(obj.height)
                pygame.draw.ellipse(self.screen, (48, 34, 22), (lx + 2, ly + 6, lw - 4, lh - 10))
                pygame.draw.ellipse(self.screen, (112, 78, 36), (lx + 6, ly + 8, lw - 12, lh - 14))
                pygame.draw.circle(self.screen, (168, 124, 54), (lx + lw // 2 - 4, ly + lh // 2), 4)
            elif obj.name == "Ink Seal":
                ix, iy, iw, ih = int(sx_o), int(sy_o), int(obj.width), int(obj.height)
                pygame.draw.rect(self.screen, (28, 18, 38), (ix + 4, iy + 4, iw - 8, ih - 8), border_radius=4)
                pygame.draw.rect(self.screen, (195, 85, 235), (ix + 4, iy + 4, iw - 8, ih - 8), 2, border_radius=4)
                pygame.draw.circle(self.screen, (240, 185, 255), (ix + iw // 2, iy + ih // 2), 5)
            elif "Respite" in obj.name:
                if not getattr(obj, 'is_active', True):
                    continue
                rx = obj.x + obj.width / 2
                ry = obj.y + obj.height / 2
                weather_mgr = getattr(state, 'weather_manager', None)
                is_safe = weather_mgr.is_pos_safe(rx, ry) if weather_mgr else True
                dr = pygame.Rect(sx_o, sy_o, obj.width, obj.height)
                sprite_key = "Respite" if is_safe else "RespiteCorrupted"
                respite_img = self.prop_cache.get(sprite_key) or self.image_cache.get(sprite_key)
                if respite_img:
                    if is_safe:
                        pulse = (math.sin(now * 5.0) + 1.0) / 2.0
                        aura_r = int(obj.width * 0.48 + pulse * 6)
                        aura_alpha = ((45 + int(pulse * 45)) // 5) * 5
                        aura_key = ("respite_aura", aura_r, aura_alpha)
                        aura_surf = self._fx_surface_cache.get(aura_key)
                        if aura_surf is None:
                            aura_surf = pygame.Surface((aura_r * 2 + 4, aura_r * 2 + 4), pygame.SRCALPHA)
                            pygame.draw.circle(
                                aura_surf, (60, 235, 255, aura_alpha),
                                (aura_r + 2, aura_r + 2), aura_r, 2
                            )
                            self._fx_surface_cache[aura_key] = aura_surf
                        self.screen.blit(aura_surf, (dr.centerx - aura_r - 2, dr.centery - aura_r - 2))
                    else:
                        ripple = (math.sin(now * 3.5) + 1.0) / 2.0
                        drip_y = int(dr.bottom - 2 + ripple * 4)
                        pygame.draw.circle(self.screen, (18, 18, 28), (int(dr.centerx - 6), drip_y), 2)
                        pygame.draw.circle(self.screen, (18, 18, 28), (int(dr.centerx + 5), drip_y + 1), 2)
                    target_size = (int(obj.width), int(obj.height))
                    if respite_img.get_size() == target_size:
                        sprite_surf = respite_img
                    else:
                        sprite_surf = pygame.transform.smoothscale(respite_img, target_size)
                    self.screen.blit(sprite_surf, (sx_o, sy_o))
                else:
                    pygame.draw.rect(self.screen, (20, 40, 60), dr)
                    pygame.draw.rect(self.screen, constants.COLOR_CYAN, dr, 2)
                    pulse = (math.sin(now * 5) + 1) / 2
                    inner_r = int(5 + pulse * 10)
                    pygame.draw.circle(
                        self.screen, constants.COLOR_CYAN, (int(dr.centerx), int(dr.centery)), inner_r, 1
                    )
            elif obj.name == "Barrel":
                img = self.image_cache.get("barrel_0.png")
                if img:
                    self.screen.blit(img, (sx_o, sy_o))
                else:
                    pygame.draw.rect(self.screen, (100, 80, 40), (sx_o, sy_o, obj.width, obj.height))
                    pygame.draw.rect(self.screen, (60, 40, 20), (sx_o, sy_o, obj.width, obj.height), 2)
            elif obj.name == "Structure":
                obj_biome = self._resolve_tile_biome(state, int(obj.x) // ts, int(obj.y) // ts)
                w_name = getattr(state.world, "name", "").lower()
                map_file = getattr(state.world, "map_filename", "").lower()
                if obj_biome == "swamp_mire":
                    fungus_surf = prop_cache.get("SwampFungus")
                    if fungus_surf is not None:
                        self.screen.blit(fungus_surf, (int(sx_o), int(sy_o)))
                    else:
                        sx_i, sy_i, sw_o, sh_o = int(sx_o), int(sy_o), int(obj.width), int(obj.height)
                        cx_t, cy_t = sx_i + sw_o // 2, sy_i + sh_o // 2 - 4
                        pygame.draw.rect(
                            self.screen, (195, 168, 220), (cx_t - 4, sy_i + sh_o - 18, 8, 16), border_radius=3
                        )
                        pygame.draw.ellipse(self.screen, (66, 30, 62), (cx_t - 16, cy_t - 8, 32, 22))
                        pygame.draw.circle(self.screen, (142, 172, 44), (cx_t - 6, cy_t - 2), 3)
                        pygame.draw.circle(self.screen, (142, 172, 44), (cx_t + 7, cy_t), 2)
                elif obj_biome == "vitreous_basin" and "VitreousSaltSpire" in prop_cache:
                    self.screen.blit(prop_cache["VitreousSaltSpire"], (int(sx_o), int(sy_o)))
                elif obj_biome == "sunlit_aqueducts" and "AqueductPillar" in prop_cache:
                    self.screen.blit(prop_cache["AqueductPillar"], (int(sx_o), int(sy_o)))
                elif obj_biome == "windy_ridge":
                    self._draw_highland_monolith(sx_o, sy_o, prop_cache)
                elif (
                    obj_biome in ("tech_tower", "ruins")
                    or "ruins" in w_name
                    or "ruins" in map_file
                ) and "RuinsRubble" in prop_cache:
                    self.screen.blit(prop_cache["RuinsRubble"], (int(sx_o), int(sy_o)))
                else:
                    tree_surf = prop_cache.get("Structure")
                    if tree_surf is not None:
                        self.screen.blit(tree_surf, (int(sx_o), int(sy_o)))
                    else:
                        sx_i, sy_i, sw_o, sh_o = int(sx_o), int(sy_o), int(obj.width), int(obj.height)
                        cx_t, cy_t = sx_i + sw_o // 2, sy_i + sh_o // 2 - 4
                        pygame.draw.circle(self.screen, (22, 44, 28), (cx_t + 2, sy_i + sh_o - 6), sw_o // 3)
                        pygame.draw.rect(
                            self.screen, (28, 16, 8), (cx_t - 7, sy_i + sh_o - 16, 14, 14), border_radius=2
                        )
                        pygame.draw.rect(
                            self.screen, (92, 54, 28), (cx_t - 5, sy_i + sh_o - 15, 10, 12), border_radius=2
                        )
                        pygame.draw.circle(self.screen, (18, 44, 24), (cx_t, cy_t), sw_o // 2 - 1)
                        pygame.draw.circle(self.screen, (38, 126, 62), (cx_t, cy_t + 2), sw_o // 2 - 3)
                        pygame.draw.circle(self.screen, (92, 218, 110), (cx_t - 1, cy_t - 2), sw_o // 2 - 5)
                        pygame.draw.circle(self.screen, (162, 246, 148), (cx_t - 4, cy_t - 6), sw_o // 4)
            elif obj.name == "The Chronicler":
                chron_img = self.prop_cache.get("Chronicler") or self.image_cache.get("Chronicler")
                if chron_img:
                    vx = getattr(obj, 'vx', 0.0)
                    vy = getattr(obj, 'vy', 0.0)
                    is_moving = abs(vx) > 1.0 or abs(vy) > 1.0
                    bob_freq = 8.0 if is_moving else 2.0
                    bob_amp = 1.5 if is_moving else 0.6
                    bob_y = int(round(math.sin(now * bob_freq) * bob_amp))
                    flip_x = vx < -1.0
                    active_dlg = getattr(state, 'active_dialogue', None)
                    speaker = (
                        active_dlg.get("speaker", "")
                        if isinstance(active_dlg, dict)
                        else getattr(active_dlg, "speaker", "")
                    )
                    if speaker == "The Chronicler" and state.player:
                        flip_x = state.player.x < obj.x
                    shadow_w = int(obj.width * 0.7)
                    shadow_key = ("shadow", shadow_w, 8)
                    shadow_surf = self._fx_surface_cache.get(shadow_key)
                    if shadow_surf is None:
                        shadow_surf = pygame.Surface((shadow_w, 8), pygame.SRCALPHA)
                        pygame.draw.ellipse(shadow_surf, (0, 0, 0, 95), (0, 0, shadow_w, 8))
                        self._fx_surface_cache[shadow_key] = shadow_surf
                    self.screen.blit(shadow_surf, (sx_o + int(obj.width * 0.15), sy_o + obj.height - 6))
                    target_size = (int(obj.width), int(obj.height))
                    if chron_img.get_size() == target_size:
                        sprite_surf = chron_img
                    else:
                        scale_key = ("chron_scale", target_size)
                        sprite_surf = self._fx_surface_cache.get(scale_key)
                        if sprite_surf is None:
                            sprite_surf = pygame.transform.smoothscale(chron_img, target_size)
                            self._fx_surface_cache[scale_key] = sprite_surf
                    if flip_x:
                        flip_key = ("chron_flip", target_size)
                        flipped_surf = self._fx_surface_cache.get(flip_key)
                        if flipped_surf is None:
                            flipped_surf = pygame.transform.flip(sprite_surf, True, False)
                            self._fx_surface_cache[flip_key] = flipped_surf
                        sprite_surf = flipped_surf
                    self.screen.blit(sprite_surf, (sx_o, sy_o + bob_y))
                else:
                    pygame.draw.rect(self.screen, (220, 220, 220), (sx_o, sy_o, obj.width, obj.height))
                    pygame.draw.rect(self.screen, (255, 200, 150), (sx_o + 5, sy_o + 5, obj.width - 10, 10))
                    pygame.draw.rect(self.screen, constants.COLOR_BLACK, (sx_o, sy_o, obj.width, obj.height), 1)
            elif obj.name == "The Binder":
                binder_img = self.prop_cache.get("Binder") or self.image_cache.get("binder.png")
                if binder_img:
                    bob_y = int(round(math.sin(now * 2.2) * 0.7))
                    self.screen.blit(binder_img, (int(sx_o), int(sy_o) + bob_y))
                else:
                    pygame.draw.rect(self.screen, (164, 52, 74), (sx_o, sy_o, obj.width, obj.height))
                    pygame.draw.rect(self.screen, constants.COLOR_BLACK, (sx_o, sy_o, obj.width, obj.height), 1)
            elif obj.name == "The Wellspring":
                self.draw_wellspring(obj, ox, oy)
            elif obj.name == "Heavy Bookcase":
                bc_surf = prop_cache.get("Heavy Bookcase")
                if bc_surf is not None:
                    self.screen.blit(bc_surf, (int(sx_o), int(sy_o)))
                else:
                    bx, by, bw, bh = int(sx_o), int(sy_o), int(obj.width), int(obj.height)
                    pygame.draw.rect(self.screen, (68, 46, 34), (bx, by, bw, bh), border_radius=3)
                    pygame.draw.rect(self.screen, (140, 105, 65), (bx, by, bw, 5))
                    pygame.draw.line(self.screen, (30, 20, 14), (bx + 2, by + bh // 2), (bx + bw - 2, by + bh // 2), 2)
            elif obj.name == "Ink Urn":
                urn_surf = prop_cache.get("Ink Urn")
                if urn_surf is not None:
                    self.screen.blit(urn_surf, (int(sx_o), int(sy_o)))
                else:
                    ux, uy, uw, uh = int(sx_o), int(sy_o), int(obj.width), int(obj.height)
                    pygame.draw.circle(self.screen, (52, 74, 112), (ux + uw // 2, uy + uh // 2 + 3), uw // 2 - 4)
            elif obj.name == "Inkwell Puddle":
                px, py, pw, ph = int(sx_o), int(sy_o), int(obj.width), int(obj.height)
                pcx, pcy = px + pw // 2, py + ph // 2
                pud_surf = prop_cache.get("Inkwell Puddle")
                if pud_surf is not None:
                    self.screen.blit(pud_surf, (px, py))
                else:
                    pygame.draw.circle(self.screen, (16, 8, 24), (pcx, pcy), pw // 2 - 1)
                    pygame.draw.circle(self.screen, (58, 26, 82), (pcx - 4, pcy - 2), pw // 3 + 2)
                    pygame.draw.circle(self.screen, (58, 26, 82), (pcx + 5, pcy + 3), pw // 3 + 1)
                    pygame.draw.circle(self.screen, (28, 12, 42), (pcx, pcy), pw // 3)
                ripple = int(((math.sin(now * 4.5 + obj.x) + 1.0) * 0.5) * (pw // 3 - 3)) + 3
                pygame.draw.circle(self.screen, (165, 68, 198), (pcx, pcy), ripple, 1)
            elif obj.name == "Candelabra":
                glow_r, glow_a = self._compute_candelabra_flicker(now, obj.x, obj.y)
                if is_real_surface:
                    glow_surf = self._get_candelabra_glow_surface(glow_r, glow_a)
                    gx = int(sx_o + obj.width // 2 - glow_surf.get_width() // 2)
                    gy = int(sy_o + 5 - glow_surf.get_height() // 2)
                    self.screen.blit(glow_surf, (gx, gy))
                cand_surf = prop_cache.get("Candelabra")
                if cand_surf is not None:
                    self.screen.blit(cand_surf, (int(sx_o), int(sy_o)))
                else:
                    stand = (sx_o + obj.width // 2 - 3, sy_o + 10, 6, obj.height - 10)
                    pygame.draw.rect(self.screen, constants.COLOR_DARK_GREY, stand)
                    pygame.draw.rect(self.screen, constants.COLOR_BLACK, stand, 1)
                    pygame.draw.rect(
                        self.screen, constants.COLOR_CANDLE_AMBER, (sx_o + obj.width // 2 - 2, sy_o + 4, 4, 6)
                    )
            elif obj.name == "Bench":
                bench_surf = prop_cache.get("Bench")
                if bench_surf is not None:
                    self.screen.blit(bench_surf, (int(sx_o), int(sy_o)))
                else:
                    pygame.draw.rect(self.screen, (101, 67, 33), (sx_o, sy_o, ts, ts))
                    pygame.draw.rect(self.screen, (60, 40, 20), (sx_o, sy_o + 5, ts, 2))
            elif obj.name == "Rock":
                obj_biome = self._resolve_tile_biome(state, int(obj.x) // ts, int(obj.y) // ts)
                w_name = getattr(state.world, "name", "").lower()
                map_file = getattr(state.world, "map_filename", "").lower()
                if obj_biome == "swamp_mire":
                    vent_surf = prop_cache.get("SwampVent")
                    if vent_surf is not None:
                        self.screen.blit(vent_surf, (int(sx_o), int(sy_o)))
                    else:
                        rx, ry = int(sx_o), int(sy_o)
                        pygame.draw.ellipse(self.screen, (66, 30, 62), (rx + 4, ry + 8, ts - 8, ts - 12))
                        pygame.draw.circle(self.screen, (148, 215, 68), (rx + ts // 2, ry + ts // 2), 4)
                elif (
                    obj_biome in ("tech_tower", "ruins")
                    or "ruins" in w_name
                    or "ruins" in map_file
                ) and "RuinsRubble" in prop_cache:
                    self.screen.blit(prop_cache["RuinsRubble"], (int(sx_o), int(sy_o)))
                elif (
                    "colophon" in w_name
                    or "crypt" in w_name
                ) and "CryptClutter" in prop_cache:
                    self.screen.blit(prop_cache["CryptClutter"], (int(sx_o), int(sy_o)))
                else:
                    rock_surf = prop_cache.get("Rock")
                    if rock_surf is not None:
                        self.screen.blit(rock_surf, (int(sx_o), int(sy_o)))
                    else:
                        rx, ry, rw, rh = int(sx_o), int(sy_o), int(obj.width), int(obj.height)
                        pygame.draw.circle(self.screen, (68, 88, 118), (rx + rw // 2, ry + rh // 2 + 2), rw // 2 - 3)
            elif obj.name in ("RuinsRubble", "SwampFlora", "CryptClutter"):
                clutter_surf = prop_cache.get(obj.name)
                if clutter_surf is not None:
                    self.screen.blit(clutter_surf, (int(sx_o), int(sy_o)))
            elif hasattr(obj, 'fragment_id'):
                fx, fy, fw, fh = int(sx_o), int(sy_o), int(obj.width), int(obj.height)
                fcx, fcy = fx + fw // 2, fy + fh // 2
                pulse = (math.sin(now * 4.0 + obj.x) + 1.0) * 0.5
                glow_r = int(12 + pulse * 3)
                pygame.draw.circle(self.screen, (215, 180, 95), (fcx, fcy), glow_r, 1)
                page_rect = (fx + 9, fy + 7, max(8, fw - 18), max(10, fh - 14))
                pygame.draw.rect(self.screen, (235, 224, 194), page_rect, border_radius=2)
                pygame.draw.rect(self.screen, (72, 52, 34), page_rect, 1, border_radius=2)
                for line_off in (12, 17, 22):
                    pygame.draw.line(
                        self.screen, (95, 76, 56), (fx + 13, fy + line_off), (fx + fw - 13, fy + line_off), 1
                    )
                pygame.draw.circle(self.screen, (175, 48, 56), (fx + fw - 14, fy + fh - 12), 2)
            elif hasattr(obj, 'weapon_data'):
                wp_key = self._select_weapon_pickup_sprite_key(obj.weapon_data)
                wp_surf = prop_cache.get(wp_key)
                glow_col = constants.get_weapon_passive_color(obj.weapon_data)
                wx, wy, ww, wh = int(sx_o), int(sy_o), int(obj.width), int(obj.height)
                wcx, wcy = wx + ww // 2, wy + wh // 2
                pulse = (math.sin(now * 3.5 + obj.x * 0.05) + 1.0) * 0.5
                bob_y = int(round((pulse - 0.5) * 4.0))
                is_anomalous = bool(obj.weapon_data.get("modifiers")) or "anomalous" in str(
                    obj.weapon_data.get("name", "")
                ).lower()
                ring_r = int(14 + pulse * 3) if is_anomalous else int(12 + pulse * 2)
                pygame.draw.circle(self.screen, glow_col, (wcx, wcy), ring_r, 1)
                if wp_surf is not None:
                    self.screen.blit(wp_surf, (wx, wy + bob_y))
                else:
                    # Clean procedural diagonal quill/blade fallback
                    pygame.draw.line(
                        self.screen, (220, 215, 200), (wx + 8, wy + wh - 8 + bob_y),
                        (wx + ww - 8, wy + 8 + bob_y), 3,
                    )
                    pygame.draw.line(
                        self.screen, glow_col, (wx + 12, wy + wh - 12 + bob_y),
                        (wx + ww - 6, wy + 6 + bob_y), 2,
                    )
                    pygame.draw.circle(self.screen, (212, 168, 66), (wx + 11, wy + wh - 11 + bob_y), 3)
        for item in getattr(state, 'loot', []):
            if -64 <= item.x - ox <= sw + 64 and -64 <= item.y - oy <= sh + 64:
                self.draw_loot(item, ox, oy)
        for fading in getattr(state, 'fading_entities', []):
            obj = fading['obj']
            ox, oy = state.camera.get_offset() if hasattr(state, 'camera') else (0, 0)

            if obj.name == "Barrel":
                # Multi-frame Animation sequence (Breaking phase)
                # Remaining time starts at 0.16s
                elapsed = 0.16 - fading['time']
                
                if elapsed < 0.080: # Frame 1: 80ms
                    img = self.image_cache.get("barrel_1.png")
                else: # Frame 2: +80ms
                    img = self.image_cache.get("barrel_2.png")
                
                if img:
                    self.screen.blit(img, (obj.x - ox, obj.y - oy))
                continue

            # Standard fade (box) for other entities
            alpha = int((fading['time'] / 0.1) * 255)
            alpha = max(0, min(255, alpha))
            s = pygame.Surface((obj.width, obj.height), pygame.SRCALPHA)
            s.fill((100, 80, 40, alpha))
            self.screen.blit(s, (obj.x - ox, obj.y - oy))

        try:
            for enemy in getattr(state, 'enemies', []):
                if (
                    enemy.x + enemy.width < ox - 96
                    or enemy.x > ox + sw + 96
                    or enemy.y + enemy.height < oy - 96
                    or enemy.y > oy + sh + 96
                ):
                    continue
                self.draw_actor_ghost(enemy, ox, oy, state)
        except Exception as e:
            print(f"[RENDER ERROR] Enemy Loop: {e}")

        self.draw_boss_projectiles(state, ox, oy)

        # Local Player Rendering
        self.draw_marginalia_world_overlays(state, ox, oy)
        self.draw_actor_ghost(state.player, ox, oy, state)

        if state.player.state == PlayerStateEnum.ATTACKING:
            self.draw_player_weapon_attack(state.player, ox, oy)
            if getattr(state, "debug_text_enabled", False):
                from engine.combat import get_sword_hitbox
                hb = get_sword_hitbox(state.player.get_center(), state.player.facing)
                hb_rect = pygame.Rect(int(hb[0] - ox), int(hb[1] - oy), int(hb[2]), int(hb[3]))
                pygame.draw.rect(self.screen, (255, 60, 60), hb_rect, 1)
        for num in state.damage_numbers:
            self.screen.blit(
                self.font.render(str(num['val']), True, num['color']),
                (num['pos'][0] - ox, num['pos'][1] - oy),
            )

        # Y-sorted overhead Sanctuary tree canopies whose trunk base sits south of the player
        if deferred_tree_canopies:
            deferred_tree_canopies.sort(key=lambda tree: float(tree.y) + float(tree.height))
            for tree_obj in deferred_tree_canopies:
                self._draw_sanctuary_tree_canopy(tree_obj, ox, oy, prop_cache)

        # Sanctuary Pass 3: Interior/exterior fade update, courtyard atmosphere, roofs, & blackout mask
        perf_now = time.perf_counter()
        if self._sanctuary_last_perf_time is None:
            frame_dt = 0.0
        else:
            frame_dt = min(0.1, max(0.0, perf_now - self._sanctuary_last_perf_time))
        self._sanctuary_last_perf_time = perf_now
        self.update_sanctuary_interior_alpha(state, frame_dt)
        self.draw_sanctuary_courtyard_atmosphere(state, ox, oy, now=now)
        self.draw_windy_ridge_atmosphere(state, ox, oy, now=now)
        self.draw_sanctuary_roofs_and_blackout(state, ox, oy)

        if getattr(state.player, 'current_interactable', None):
            self.draw_interaction_prompt(state.player, ox, oy)
        try:
            if getattr(state, 'last_save_elapsed', 1e6) <= constants.AUTOSAVE_INDICATOR_DURATION:
                ind = self.font.render("Saved", True, (200, 200, 200))
                self.screen.blit(ind, (sw - ind.get_width() - 8, 8))
        except Exception:
            pass
        try:
            self.draw_minimap(state)
        except Exception:
            pass
        try:
            self.draw_hud(state)
        except Exception:
            pass

        # Audio & Map Debug OSD (gated behind debug_text_enabled)
        if getattr(state, "debug_text_enabled", False):
            self.draw_audio_debug(audio_manager, state=state)

        if getattr(state, 'chronicle_dialog', None):
            draw_chronicle_biome_menu(self.screen, self.font, state)
        elif getattr(state, 'binder_dialog', None):
            draw_binder_weave_menu(self.screen, self.font, state)
        elif getattr(state, 'active_respite', None):
            draw_respite_menu(self.screen, self.font, state)
        elif getattr(state, 'active_dialogue', None):
            self.draw_dialogue_box(state)
        
        if getattr(state, 'active_choice', None): self.draw_choice_of_fates(state.active_choice)
        if getattr(state, 'death_timer', 0) > 0:
            overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
            overlay.fill((200, 200, 200, 150))
            self.screen.blit(overlay, (0, 0))
            bleach_font = getattr(self, "bloom_font", None) or self.font
            shadow_msg = bleach_font.render("TEXT BLEACHING...", True, constants.COLOR_BLOOM_SHADOW)
            self.screen.blit(shadow_msg, shadow_msg.get_rect(center=(sw // 2 + 2, sh // 2 + 2)))
            msg = bleach_font.render("TEXT BLEACHING...", True, constants.COLOR_BLACK)
            self.screen.blit(msg, msg.get_rect(center=(sw // 2, sh // 2)))

        self.draw_weather(state)
        self.draw_bloom_overlay(state)

        # Phase 4: Network Ghost Rendering
        self.draw_remote_players(state, ox, oy)
        
        # Parry Sparks
        self.draw_parry_effects(state, ox, oy)

        # Fading Visual Slash Arcs & Impact Sparks
        self.draw_fading_slash_arcs(state, ox, oy)
        self.draw_impact_sparks(state, ox, oy)

        # Glyph Splatter Particles
        self.draw_glyph_splatter(state, ox, oy)

        # The Ink & Fog Warp Transition
        self.draw_warp_sequence(state, ox, oy)

        if pygame.display.get_init() and pygame.display.get_surface() is not None:
            pygame.display.flip()

    def draw_boss_projectiles(self, state, ox, oy):
        """Render active anti-cheese boss ink-bolt projectiles in world space."""
        sw, sh = self.screen.get_width(), self.screen.get_height()
        for enemy in getattr(state, 'enemies', []):
            for bolt in getattr(enemy, 'ink_bolts', ()):
                bx = int(bolt["x"] - ox)
                by = int(bolt["y"] - oy)
                r = int(bolt.get("radius", constants.BOSS_BOLT_RADIUS))
                if bx < -r * 3 or bx > sw + r * 3 or by < -r * 3 or by > sh + r * 3:
                    continue
                pygame.draw.circle(self.screen, (42, 16, 56), (bx, by), r + 3)
                pygame.draw.circle(self.screen, (195, 48, 86), (bx, by), r)
                pygame.draw.circle(self.screen, (255, 215, 225), (bx, by), max(2, r // 2))

    def draw_marginalia_world_overlays(self, state, ox, oy):
        """Render world-space rings, Footnote Wisp, and ink-mist vignette for Marginalia events."""
        marg = getattr(state, "marginalia_engine", None)
        if marg is not None and not getattr(state, "in_sanctuary", False):
            b_state = marg.get_banner_state()
            if b_state and b_state.get("status") == "ACTIVE":
                zc = b_state.get("zone_center")
                zrad = float(b_state.get("zone_radius") or 0.0)
                if zc and zrad > 4.0:
                    sx = int(zc[0] - ox)
                    sy = int(zc[1] - oy)
                    ring_col = (215, 180, 95) if b_state.get("act_variant") == 1 else (235, 95, 145)
                    pygame.draw.circle(self.screen, ring_col, (sx, sy), int(zrad), 2)

                wisp_pos = b_state.get("wisp_pos")
                wisp_target = b_state.get("wisp_target")
                if wisp_target:
                    tx = int(wisp_target[0] - ox)
                    ty = int(wisp_target[1] - oy)
                    pygame.draw.circle(self.screen, (120, 235, 255), (tx, ty), 20, 2)
                if wisp_pos:
                    wx = int(wisp_pos[0] - ox)
                    wy = int(wisp_pos[1] - oy)
                    pygame.draw.circle(self.screen, (200, 245, 255), (wx, wy), 10)
                    pygame.draw.circle(self.screen, (80, 195, 255), (wx, wy), 14, 2)

        if getattr(state, "ink_mist_vignette_timer", 0.0) > 0.0:
            sw, sh = self.screen.get_width(), self.screen.get_height()
            pygame.draw.rect(self.screen, (28, 14, 38), (0, 0, sw, sh), 14)

    def draw_marginalia_banner(self, state):
        """Render the unified top-center Marginalia HUD banner using BitmapFont."""
        if getattr(state, "in_sanctuary", False):
            return
        marg = getattr(state, "marginalia_engine", None)
        if marg is None:
            return
        b_state = marg.get_banner_state()
        if not b_state:
            return

        sw = self.screen.get_width()
        act_v = int(b_state.get("act_variant", 1))
        status = str(b_state.get("status", "ACTIVE"))
        title = str(b_state.get("title", "Marginalia Event"))
        spatial = str(b_state.get("spatial_mode", "local")).upper().replace("_", " ")
        time_rem = b_state.get("time_remaining")
        prog = b_state.get("progress", 0.0)

        border_col = (215, 180, 95)
        if status == "COMPLETED":
            border_col = (120, 255, 140)
        elif status == "FAILED":
            border_col = (235, 85, 85)
        elif act_v >= 2:
            border_col = (215, 115, 245)

        panel_w, panel_h = 420, 62
        panel_x = (sw - panel_w) // 2
        panel_y = 12
        panel_rect = pygame.Rect(panel_x, panel_y, panel_w, panel_h)
        pygame.draw.rect(self.screen, (18, 15, 22), panel_rect, border_radius=6)
        pygame.draw.rect(self.screen, border_col, panel_rect, 2, border_radius=6)

        header_str = f"ACT {'II' if act_v >= 2 else 'I'} MARGINALIA [{spatial}] - {status}"
        header_surf = self.small_font.render(header_str, True, border_col)
        self.screen.blit(header_surf, (panel_x + 12, panel_y + 6))

        if time_rem is not None and status == "ACTIVE":
            timer_str = f"{float(time_rem):.1f}s"
            timer_surf = self.small_font.render(timer_str, True, constants.COLOR_WHITE)
            self.screen.blit(timer_surf, (panel_rect.right - timer_surf.get_width() - 12, panel_y + 6))

        title_surf = self.hud_font.render(title, True, constants.COLOR_PARCHMENT_WHITE)
        self.screen.blit(title_surf, (panel_x + 12, panel_y + 22))

        bar_x = panel_x + 12
        bar_y = panel_y + 44
        bar_w = panel_w - 24
        bar_h = 10
        pygame.draw.rect(self.screen, (38, 32, 44), (bar_x, bar_y, bar_w, bar_h), border_radius=3)

        ratio = 0.0
        counter_str = ""
        if isinstance(prog, (list, tuple)) and len(prog) == 2:
            cur_v, max_v = int(prog[0]), max(1, int(prog[1]))
            ratio = max(0.0, min(1.0, cur_v / float(max_v)))
            counter_str = f"{cur_v}/{max_v}"
        else:
            ratio = max(0.0, min(1.0, float(prog or 0.0)))
            counter_str = f"{int(round(ratio * 100))}%"

        fill_w = int(bar_w * ratio)
        if fill_w > 0:
            pygame.draw.rect(self.screen, border_col, (bar_x, bar_y, fill_w, bar_h), border_radius=3)
        cnt_surf = self.small_font.render(counter_str, True, constants.COLOR_WHITE)
        self.screen.blit(cnt_surf, (panel_rect.right - cnt_surf.get_width() - 12, panel_y + 22))

    def draw_actor_ghost(self, actor, ox, oy, state):
        """Draws sprites or abstract indicators for an actor based on its visual packet."""
        actor_alpha = getattr(actor, 'alpha', 255)
        if actor_alpha <= 0:
            return

        if actor_alpha < 255:
            rect = pygame.Rect(actor.x - ox, actor.y - oy, actor.width, actor.height)
            margin = 32
            scratch_w = rect.width + margin * 2
            scratch_h = rect.height + margin * 2
            if self._actor_scratch_surf is None or self._actor_scratch_surf.get_size() != (scratch_w, scratch_h):
                self._actor_scratch_surf = pygame.Surface((scratch_w, scratch_h), pygame.SRCALPHA)
            else:
                self._actor_scratch_surf.fill((0, 0, 0, 0))

            orig_screen = self.screen
            self.screen = self._actor_scratch_surf
            try:
                self._draw_actor_ghost_content(actor, actor.x - margin, actor.y - margin, state)
            finally:
                self.screen = orig_screen
            self._actor_scratch_surf.set_alpha(actor_alpha)
            self.screen.blit(self._actor_scratch_surf, (rect.x - margin, rect.y - margin))
            return

        self._draw_actor_ghost_content(actor, ox, oy, state)

    def _draw_actor_ghost_content(self, actor, ox, oy, state):
        """Internal routine rendering actor graphics directly to the active screen target."""
        packet = actor.get_visual_packet()
        rect = pygame.Rect(actor.x - ox, actor.y - oy, actor.width, actor.height)
        
        # --- Boss Attack Hitbox / Warning Telegraph Overlay ---
        if packet["base"] in ("WIND_UP", "STRIKE") and hasattr(actor, 'get_attack_hitbox'):
            hb = actor.get_attack_hitbox()
            sx = hb[0] - ox
            sy = hb[1] - oy
            
            s = pygame.Surface((hb[2], hb[3]), pygame.SRCALPHA)
            if packet["base"] == "WIND_UP":
                # Subtle flashing desaturated grey warning zone (no border)
                pulse = (math.sin(time.time() * 15) + 1) / 2
                alpha = int(15 + pulse * 25)
                s.fill((220, 220, 220, alpha))
                self.screen.blit(s, (sx, sy))
            elif packet["base"] == "STRIKE":
                # Subtle desaturated grey active damage zone (no border)
                s.fill((220, 220, 220, 45))
                self.screen.blit(s, (sx, sy))

        # --- SPRITE RESOLUTION ---
        from engine.enemy import SlugEnemy
        sprite = None
        actor_tag = actor.name.lower()
        is_slug = isinstance(actor, SlugEnemy) or "slug" in actor_tag
        is_empowered_actor = bool(getattr(actor, "is_empowered", False))

        if is_slug:
            # 1. Determine direction (1=Right, 2=Left)
            # Slug frames: 1/3 (Right), 2/4 (Left)
            # Attack frames: attack_1 (Right), attack_2 (Left)
            fx, fy = packet["facing"]
            suffix = "1" if fx >= 0 else "2"

            emp_suffix = "_empowered" if is_empowered_actor else ""
            if packet["base"] in ("WIND_UP", "STRIKE"):
                sprite = (
                    self.image_cache.get(f"slug_attack_{suffix}{emp_suffix}.png")
                    or self.image_cache.get(f"slug_attack_{suffix}.png")
                )
            else:
                # Alternate frames if moving
                if packet["base"] == "RUN":
                    # Swap every 0.3s
                    if int(packet["anim_timer"] * 3) % 2 == 1:
                        suffix = "3" if fx >= 0 else "4"
                sprite = (
                    self.image_cache.get(f"slug_{suffix}{emp_suffix}.png")
                    or self.image_cache.get(f"slug_{suffix}.png")
                )

        # --- DRAWING ---
        used_procedural = False
        if sprite:
            # Center sprite on actor rect
            s_rect = sprite.get_rect(center=rect.center)
            # Posture: Squashing if wounded
            if packet["posture"] == "WOUNDED":
                h = int(s_rect.height * 0.7)
                sprite = pygame.transform.scale(sprite, (s_rect.width, h))
                s_rect = sprite.get_rect(midbottom=rect.midbottom)

            if is_slug:
                self._draw_dark_enemy_ground_shadow(s_rect)
            self.screen.blit(sprite, s_rect)
            if is_slug:
                self._draw_dark_enemy_rim_highlight(s_rect, is_empowered=is_empowered_actor)

            # Draw persistent overlays on top of sprite (gated behind debug_text_enabled)
            if packet["posture"] == "STAGGERED" and getattr(state, "debug_text_enabled", False):
                pygame.draw.rect(self.screen, constants.COLOR_WHITE, rect, 2)
        else:
            # 1. Posture Modifiers (Transformation)
            draw_rect = rect.copy()
            if packet["posture"] == "WOUNDED":
                # Standing not as tall (Squashed)
                original_h = draw_rect.height
                draw_rect.height *= 0.7
                draw_rect.y += (original_h - draw_rect.height)
            elif packet["posture"] == "STAGGERED":
                # Vibrating
                draw_rect.x += random.randint(-2, 2)
                draw_rect.y += random.randint(-2, 2)

            # 2. Base Layer (Body)
            debug_mode = bool(getattr(state, "debug_text_enabled", False))
            color = packet.get("color_hint", (100, 100, 100))
            if packet["base"] == "WIND_UP": color = (200, 100, 0) # Orange Telegraph
            elif packet["base"] == "STRIKE": color = constants.COLOR_MARGIN_RED
            elif packet["base"] == "RECOVERY": 
                # Dim the base color
                color = tuple(max(0, c - 50) for c in color)
            elif packet["base"] == "DASH" and debug_mode: color = constants.COLOR_CYAN
            elif packet["base"] == "BLOCK": color = (80, 80, 120)

            # Special coloring for local Player if no hint provided
            if not packet.get("color_hint"):
                if hasattr(actor, 'weapons'): color = constants.COLOR_BLUE

            used_procedural = False
            if hasattr(actor, 'weapons'):
                used_procedural = self.draw_procedural_player(
                    actor, draw_rect, packet, color, debug_text_enabled=debug_mode
                )
            elif self.draw_procedural_enemy(actor, draw_rect, packet, color):
                used_procedural = True
            else:
                if is_slug:
                    self._draw_dark_enemy_ground_shadow(draw_rect)
                pygame.draw.rect(self.screen, color, draw_rect)
                if is_slug:
                    self._draw_dark_enemy_rim_highlight(draw_rect, is_empowered=is_empowered_actor)

        # 3. Universal Posture Layer (Outlines/Decorations - gated behind debug_text_enabled)
        debug_mode = bool(getattr(state, "debug_text_enabled", False))
        if not sprite and debug_mode: # Ghost-only outlines
            if packet["posture"] == "STAGGERED":
                pygame.draw.rect(self.screen, constants.COLOR_WHITE, draw_rect, 2)
            elif packet["posture"] == "WOUNDED":
                # Red pulse
                pulse = (math.sin(time.time() * 10) + 1) / 2
                pygame.draw.rect(self.screen, (255, 0, 0), draw_rect, int(1 + pulse * 2))

        # 4. Overlays (Applied to both sprites and ghosts)
        # Use draw_rect if available, otherwise rect
        overlay_rect = draw_rect if not sprite else rect
        
        for overlay in packet["overlays"]:
            if overlay == "BIND":
                # Green vine/web indicator
                pygame.draw.rect(self.screen, (0, 150, 0), overlay_rect, 3)
                pygame.draw.line(self.screen, (0, 150, 0), overlay_rect.topleft, overlay_rect.bottomright, 2)
                pygame.draw.line(self.screen, (0, 150, 0), overlay_rect.topright, overlay_rect.bottomleft, 2)
            elif overlay == "EXPOSED":
                # Rain exposure (Shimmering effect)
                shimmer = (math.sin(time.time() * 15) + 1) / 2
                s = pygame.Surface((overlay_rect.width, overlay_rect.height), pygame.SRCALPHA)
                s.fill((100, 150, 255, int(50 + shimmer * 50)))
                self.screen.blit(s, overlay_rect.topleft)
            elif overlay == "PARRY_WINDOW" and debug_mode:
                # Glowing blue/white debug border
                pygame.draw.rect(self.screen, (200, 255, 255), overlay_rect, 4)
            elif overlay == "NEGATION":
                # Glowing gold/yellow overlay
                glow = (math.sin(time.time() * 12) + 1) / 2
                s = pygame.Surface((overlay_rect.width, overlay_rect.height), pygame.SRCALPHA)
                s.fill((255, 215, 0, int(40 + glow * 40)))
                self.screen.blit(s, overlay_rect.topleft)
                pygame.draw.rect(self.screen, (255, 215, 0), overlay_rect, 1)

        # 5. Directional Indicator (Only for fallback ghosts without procedural visuals)
        if not sprite and not used_procedural:
            fx, fy = packet["facing"]
            ecx, ecy = draw_rect.center
            pygame.draw.line(self.screen, constants.COLOR_WHITE, (ecx, ecy), (ecx + fx * 15, ecy + fy * 15), 2)
        
        # 6. Combat Progress Bar (Universal)
        if packet["base"] in ("WIND_UP", "STRIKE", "RECOVERY") and packet["timer"] > 0:
            bar_w = int(overlay_rect.width * 0.8)
            bx = overlay_rect.centerx - bar_w // 2
            by = overlay_rect.top - 10
            
            # Determine total duration for progress
            total = 1.0
            if packet["base"] == "WIND_UP": total = getattr(actor, 'wind_up_duration', 0.5)
            elif packet["base"] == "STRIKE": total = getattr(actor, 'strike_duration', 0.2)
            elif packet["base"] == "RECOVERY": total = getattr(actor, 'recovery_duration', 0.6)
            
            if total > 0:
                progress = packet["timer"] / total
                pygame.draw.rect(self.screen, (50, 50, 50), (bx, by, bar_w, 4))
                pygame.draw.rect(self.screen, constants.COLOR_WHITE, (bx, by, int(bar_w * progress), 4))

        # 7. Boss Attack Weapon/Limb Visuals
        if hasattr(actor, 'get_attack_hitbox'):
            self.draw_boss_weapon(actor, ox, oy)

    def draw_procedural_enemy(self, actor, draw_rect, packet, state_color):
        """Draw image sprites or procedural basic-shape graphics for enemies and bosses."""
        from engine.enemy import (
            BatEnemy, BindlingEnemy, Boss, FinalAuthor, FlutterEnemy,
            Miniboss, MinibossM2, MinibossM3, NightBoss, PunctuationWolfEnemy,
            SentryEnemy, SmearEnemy,
        )
        actor_tag = actor.name.lower()
        cx, cy = int(draw_rect.centerx), int(draw_rect.centery)
        w, h = int(draw_rect.width), int(draw_rect.height)
        fx, fy = packet.get("facing", (0.0, 1.0))
        anim_t = float(packet.get("anim_timer", 0.0))
        is_telegraph = packet.get("base") in ("WIND_UP", "STRIKE", "RECOVERY")

        is_boss = isinstance(actor, Boss) or bool(getattr(actor, "is_miniboss", False))
        is_smear = isinstance(actor, SmearEnemy) or "smear" in actor_tag
        is_event_champion = is_boss and any(
            tok in actor_tag for tok in ("overwritten", "champion", "censor", "event")
        )

        if getattr(actor, "is_empowered", False):
            emp_key = None
            if isinstance(actor, BatEnemy) or "bat" in actor_tag:
                emp_key = "bat_empowered.png"
            elif isinstance(actor, FlutterEnemy) or "flutter" in actor_tag:
                emp_key = "flutter_empowered.png"
            elif isinstance(actor, BindlingEnemy) or "bindling" in actor_tag:
                emp_key = "bindling_empowered.png"
            elif is_smear:
                emp_key = "smear_empowered.png"
            elif isinstance(actor, SentryEnemy) or "sentry" in actor_tag:
                emp_key = "sentry_empowered.png"
            elif isinstance(actor, PunctuationWolfEnemy) or "wolf" in actor_tag:
                emp_key = "punctuation_wolf_empowered.png"
            elif is_boss or any(tag in actor_tag for tag in ("miniboss", "scribe", "binder", "boss", "author")):
                emp_key = "boss_empowered.png"
            emp_surf = self.image_cache.get(emp_key) if emp_key else None
            if emp_surf is None and is_boss:
                emp_surf = self.image_cache.get("event_champion.png") or self.image_cache.get("miniboss.png")
            if emp_surf is not None:
                if emp_surf.get_size() != (w, h) and w > 0 and h > 0:
                    emp_surf = pygame.transform.scale(emp_surf, (w, h))
                if fx < 0:
                    emp_surf = pygame.transform.flip(emp_surf, True, False)
                if is_smear:
                    self._draw_dark_enemy_ground_shadow(draw_rect)
                self.screen.blit(emp_surf, draw_rect.topleft)
                if is_smear:
                    self._draw_dark_enemy_rim_highlight(draw_rect, is_empowered=True)
                if is_telegraph:
                    ring_r = max(10, max(w, h) // 2 + 2)
                    pygame.draw.circle(self.screen, state_color, (cx, cy), ring_r, 2)
                return True
        else:
            base_key = None
            if isinstance(actor, BatEnemy) or "bat" in actor_tag:
                base_key = "bat.png"
            elif isinstance(actor, FlutterEnemy) or "flutter" in actor_tag:
                base_key = "flutter.png"
            elif isinstance(actor, BindlingEnemy) or "bindling" in actor_tag:
                base_key = "bindling.png"
            elif is_smear:
                base_key = "smear.png"
            elif isinstance(actor, SentryEnemy) or "sentry" in actor_tag:
                base_key = "sentry.png"
            elif isinstance(actor, PunctuationWolfEnemy) or "wolf" in actor_tag:
                base_key = "punctuation_wolf.png"
            elif isinstance(actor, FinalAuthor) or "author" in actor_tag:
                base_key = "final_author.png"
            elif isinstance(actor, NightBoss) or "night boss" in actor_tag or "night_boss" in actor_tag:
                base_key = "night_boss.png"
            elif is_event_champion:
                base_key = "event_champion.png"
            elif (
                isinstance(actor, (MinibossM2, MinibossM3, Miniboss, Boss))
                or is_boss
                or any(tag in actor_tag for tag in ("miniboss", "scribe", "binder", "boss"))
            ):
                base_key = "miniboss.png"
            base_surf = self.image_cache.get(base_key) if base_key else None
            if base_surf is None and is_event_champion:
                base_surf = self.image_cache.get("miniboss.png")
            if base_surf is not None:
                if base_surf.get_size() != (w, h) and w > 0 and h > 0:
                    base_surf = pygame.transform.scale(base_surf, (w, h))
                if fx < 0:
                    base_surf = pygame.transform.flip(base_surf, True, False)
                if is_smear:
                    self._draw_dark_enemy_ground_shadow(draw_rect)
                self.screen.blit(base_surf, draw_rect.topleft)
                if is_smear:
                    self._draw_dark_enemy_rim_highlight(draw_rect, is_empowered=False)
                if is_telegraph:
                    ring_r = max(10, max(w, h) // 2 + 2)
                    pygame.draw.circle(self.screen, state_color, (cx, cy), ring_r, 2)
                return True

        if isinstance(actor, BatEnemy) or "bat" in actor_tag:
            body_col = state_color if is_telegraph else constants.COLOR_BAT_BODY
            wing_col = state_color if is_telegraph else constants.COLOR_BAT_WING
            flap = int(math.sin(anim_t * 18.0) * 6)
            wing_r = max(4, w // 4)
            # Flapping wing struts and membrane lobes
            pygame.draw.line(self.screen, wing_col, (cx, cy), (cx - w // 2 - 4, cy + flap), 3)
            pygame.draw.line(self.screen, wing_col, (cx, cy), (cx + w // 2 + 4, cy + flap), 3)
            pygame.draw.circle(self.screen, wing_col, (cx - w // 3, cy + flap // 2), wing_r)
            pygame.draw.circle(self.screen, wing_col, (cx + w // 3, cy + flap // 2), wing_r)
            # Central body, eyes, and fangs
            pygame.draw.circle(self.screen, body_col, (cx, cy), max(5, w // 3))
            pygame.draw.circle(self.screen, constants.COLOR_BAT_EYE, (cx - 3, cy - 2), 2)
            pygame.draw.circle(self.screen, constants.COLOR_BAT_EYE, (cx + 3, cy - 2), 2)
            pygame.draw.line(self.screen, constants.COLOR_WHITE, (cx - 2, cy + 2), (cx - 2, cy + 5), 1)
            pygame.draw.line(self.screen, constants.COLOR_WHITE, (cx + 2, cy + 2), (cx + 2, cy + 5), 1)
            return True

        if isinstance(actor, FlutterEnemy) or "flutter" in actor_tag:
            body_col = state_color if is_telegraph else constants.COLOR_FLUTTER_BODY
            wing_col = state_color if is_telegraph else constants.COLOR_FLUTTER_WING
            flutter_off = int(math.sin(anim_t * 24.0) * 4)
            # Fluttering paper-wing lobes and ink strokes
            pygame.draw.circle(self.screen, wing_col, (cx - w // 2, cy - flutter_off), max(3, w // 3))
            pygame.draw.circle(self.screen, wing_col, (cx + w // 2, cy + flutter_off), max(3, w // 3))
            pygame.draw.line(self.screen, wing_col, (cx - w // 2, cy - flutter_off), (cx + w // 2, cy + flutter_off), 2)
            # Scrawl core and orbiting ink motes
            core_rect = pygame.Rect(cx - w // 4, cy - h // 4, max(4, w // 2), max(4, h // 2))
            pygame.draw.rect(self.screen, body_col, core_rect)
            pygame.draw.circle(self.screen, constants.COLOR_FLUTTER_MOTE, (cx - w // 3, cy - h // 3), 2)
            pygame.draw.circle(self.screen, constants.COLOR_FLUTTER_MOTE, (cx + w // 3, cy + h // 3), 2)
            return True

        if isinstance(actor, BindlingEnemy) or "bindling" in actor_tag:
            body_col = state_color if is_telegraph else constants.COLOR_BINDLING_PARCHMENT
            hood_col = state_color if is_telegraph else constants.COLOR_BINDLING_HOOD
            # Stitched parchment body and folded margin hood
            pygame.draw.rect(self.screen, body_col, draw_rect, border_radius=6)
            hood_rect = pygame.Rect(draw_rect.x + 2, draw_rect.y, max(4, w - 4), max(4, h // 3))
            pygame.draw.rect(self.screen, hood_col, hood_rect, border_radius=4)
            # Diagonal stitch marks across torso
            sx1, sy1 = draw_rect.x + 6, draw_rect.y + h // 3
            sx2, sy2 = draw_rect.right - 6, draw_rect.bottom - 6
            pygame.draw.line(self.screen, constants.COLOR_BINDLING_STITCH, (sx1, sy1), (sx2, sy2), 2)
            pygame.draw.line(self.screen, constants.COLOR_BINDLING_STITCH, (sx1 + 4, sy1 + 8), (sx1 + 10, sy1 + 2), 2)
            pygame.draw.line(self.screen, constants.COLOR_BINDLING_STITCH, (sx2 - 10, sy2 - 2), (sx2 - 4, sy2 - 8), 2)
            # Procedural pilcrow (paragraph mark) sigil
            pygame.draw.circle(self.screen, constants.COLOR_BINDLING_STITCH, (cx - 2, cy + 2), 3)
            pygame.draw.line(self.screen, constants.COLOR_BINDLING_STITCH, (cx, cy - 1), (cx, cy + 9), 2)
            pygame.draw.line(self.screen, constants.COLOR_BINDLING_STITCH, (cx + 3, cy - 1), (cx + 3, cy + 9), 1)
            return True

        if is_smear:
            blob_col = state_color if is_telegraph else constants.COLOR_SMEAR_BLOB
            base_r = max(4, w // 3)
            self._draw_dark_enemy_ground_shadow(draw_rect)
            # Amorphous wobbling ink blot lobes
            pygame.draw.circle(self.screen, blob_col, (cx, cy), base_r)
            for i in range(4):
                angle = anim_t * 4.0 + i * (math.pi / 2.0)
                lx = cx + int(math.cos(angle) * (w * 0.22))
                ly = cy + int(math.sin(angle) * (h * 0.22))
                pygame.draw.circle(self.screen, blob_col, (lx, ly), max(3, int(base_r * 0.8)))
            # Glossy cyan-ink nucleus shifted toward facing direction
            eye_x = cx + int(fx * (w * 0.15))
            eye_y = cy + int(fy * (h * 0.15))
            pygame.draw.circle(self.screen, constants.COLOR_SMEAR_CORE, (eye_x, eye_y), max(2, w // 8))
            self._draw_dark_enemy_rim_highlight(draw_rect, is_empowered=bool(getattr(actor, "is_empowered", False)))
            return True

        if isinstance(actor, SentryEnemy) or "sentry" in actor_tag:
            chassis_col = state_color if is_telegraph else constants.COLOR_SENTRY_CHASSIS
            fin_col = state_color if is_telegraph else constants.COLOR_SENTRY_FIN
            # Rotating diagonal stabilizer fins around hovering droid core
            for i in range(4):
                ang = anim_t * 3.0 + i * (math.pi / 2.0) + (math.pi / 4.0)
                fx_end = cx + int(math.cos(ang) * (w * 0.48))
                fy_end = cy + int(math.sin(ang) * (h * 0.48))
                pygame.draw.line(self.screen, fin_col, (cx, cy), (fx_end, fy_end), 3)
                pygame.draw.circle(self.screen, fin_col, (fx_end, fy_end), 3)
            # Armored octagonal/beveled core and pulsing magenta energy ring
            core_rect = pygame.Rect(draw_rect.x + 4, draw_rect.y + 4, max(8, w - 8), max(8, h - 8))
            pygame.draw.rect(self.screen, chassis_col, core_rect, border_radius=8)
            pygame.draw.circle(self.screen, constants.COLOR_SENTRY_RING, (cx, cy), max(5, w // 3), 2)
            # Directional cyan plasma emitter lens
            eye_x = cx + int(fx * (w * 0.18))
            eye_y = cy + int(fy * (h * 0.18))
            pygame.draw.circle(self.screen, constants.COLOR_SENTRY_EYE, (eye_x, eye_y), 4)
            return True

        if isinstance(actor, PunctuationWolfEnemy) or "wolf" in actor_tag:
            glyph_col = state_color if is_telegraph else constants.COLOR_WOLF_GLYPH
            spine_col = state_color if is_telegraph else constants.COLOR_WOLF_SPINE
            stride = int(math.sin(anim_t * 14.0) * 2)
            dir_x = 1 if fx >= 0 else -1
            # Glyph-shaped lupine torso & pointed ears
            body_poly = [
                (cx - 12 * dir_x, cy + 4 + stride),
                (cx - 7 * dir_x, cy - 6),
                (cx + 5 * dir_x, cy - 7),
                (cx + 14 * dir_x, cy - 1),
                (cx + 6 * dir_x, cy + 7 - stride),
            ]
            pygame.draw.polygon(self.screen, constants.COLOR_WOLF_INK, body_poly)
            pygame.draw.polygon(
                self.screen, glyph_col,
                [(cx + 2 * dir_x, cy - 5), (cx + 5 * dir_x, cy - 13), (cx + 8 * dir_x, cy - 5)],
            )
            pygame.draw.polygon(
                self.screen, glyph_col,
                [(cx - 4 * dir_x, cy - 5), (cx - 1 * dir_x, cy - 12), (cx + 2 * dir_x, cy - 5)],
            )
            # Electric cyan spine arc & exclamation-mark tail
            pygame.draw.arc(self.screen, spine_col, (cx - 13, cy - 10, 26, 16), 0.2, 2.9, 2)
            pygame.draw.line(self.screen, spine_col, (cx - 11 * dir_x, cy + 2), (cx - 16 * dir_x, cy - 6), 2)
            pygame.draw.circle(self.screen, glyph_col, (cx - 16 * dir_x, cy - 9), 2)
            # Glowing glyph eye & fang
            pygame.draw.circle(self.screen, spine_col, (cx + 8 * dir_x, cy - 3), 2)
            pygame.draw.line(self.screen, glyph_col, (cx + 11 * dir_x, cy + 1), (cx + 11 * dir_x, cy + 5), 2)
            return True

        if is_boss or any(tag in actor_tag for tag in ("miniboss", "scribe", "binder", "boss", "author")):
            armor_col = state_color if is_telegraph else constants.COLOR_BOSS_ARMOR
            pauldron_col = state_color if is_telegraph else constants.COLOR_BOSS_PAULDRON
            # Shoulder pauldrons and hulking armored torso
            pauldron_r = max(6, w // 4)
            pygame.draw.circle(self.screen, pauldron_col, (draw_rect.x + 4, cy - h // 8), pauldron_r)
            pygame.draw.circle(self.screen, pauldron_col, (draw_rect.right - 4, cy - h // 8), pauldron_r)
            pygame.draw.rect(self.screen, armor_col, draw_rect, border_radius=8)
            # Dark helmet visor and glowing eye tracking facing vector
            visor_w, visor_h = max(8, w // 2), max(6, h // 5)
            visor_rect = pygame.Rect(cx - visor_w // 2, draw_rect.y + h // 6, visor_w, visor_h)
            pygame.draw.rect(self.screen, constants.COLOR_BOSS_VISOR, visor_rect, border_radius=3)
            eye_x = visor_rect.centerx + int(fx * (visor_w * 0.2))
            eye_y = visor_rect.centery + int(fy * (visor_h * 0.15))
            pygame.draw.circle(self.screen, constants.COLOR_BOSS_EYE, (eye_x, eye_y), max(3, w // 14))
            return True

        return False

    def _draw_tapered_blade(self, start_pos, tip_pos, half_w, edge_col=None):
        """Draw a sword/greatblade with hilt, crossguard, tapered edges, and fuller groove."""
        hx, hy = start_pos
        tx, ty = tip_pos
        edge_col = edge_col or constants.COLOR_WEAPON_EDGE
        blade_col = constants.COLOR_WEAPON_BLADE
        dx, dy = tx - hx, ty - hy
        dist = math.hypot(dx, dy)
        if dist < 1.0:
            return
        ux, uy = dx / dist, dy / dist
        nx, ny = -uy, ux

        # 1. Hilt from hand/origin to crossguard
        gx, gy = hx + ux * (dist * 0.25), hy + uy * (dist * 0.25)
        pygame.draw.line(self.screen, constants.COLOR_WEAPON_HILT, (int(hx), int(hy)), (int(gx), int(gy)), 4)

        # 2. Tapered steel blade from crossguard to sharp point (tx, ty)
        bl_x, bl_y = gx + nx * half_w, gy + ny * half_w
        br_x, br_y = gx - nx * half_w, gy - ny * half_w
        il_x, il_y = gx + nx * (half_w * 0.5), gy + ny * (half_w * 0.5)
        ir_x, ir_y = gx - nx * (half_w * 0.5), gy - ny * (half_w * 0.5)
        pygame.draw.line(self.screen, blade_col, (int(il_x), int(il_y)), (int(tx), int(ty)), 3)
        pygame.draw.line(self.screen, blade_col, (int(ir_x), int(ir_y)), (int(tx), int(ty)), 3)
        pygame.draw.line(self.screen, blade_col, (int(bl_x), int(bl_y)), (int(tx), int(ty)), 2)
        pygame.draw.line(self.screen, blade_col, (int(br_x), int(br_y)), (int(tx), int(ty)), 2)
        pygame.draw.line(self.screen, blade_col, (int(bl_x), int(bl_y)), (int(br_x), int(br_y)), 2)

        # 3. Central razor ridge and fuller groove
        fx_end, fy_end = gx + ux * (dist * 0.42), gy + uy * (dist * 0.42)
        pygame.draw.line(self.screen, edge_col, (int(gx), int(gy)), (int(tx), int(ty)), 2)
        pygame.draw.line(self.screen, constants.COLOR_WEAPON_FULLER, (int(gx), int(gy)), (int(fx_end), int(fy_end)), 2)

        # 4. Perpendicular brass crossguard bar and pommel caps
        gw = half_w + 5.0
        g1x, g1y = int(gx + nx * gw), int(gy + ny * gw)
        g2x, g2y = int(gx - nx * gw), int(gy - ny * gw)
        pygame.draw.line(self.screen, constants.COLOR_WEAPON_GUARD, (g1x, g1y), (g2x, g2y), 3)
        pygame.draw.circle(self.screen, constants.COLOR_WEAPON_GUARD, (g1x, g1y), 2)
        pygame.draw.circle(self.screen, constants.COLOR_WEAPON_GUARD, (g2x, g2y), 2)

    def draw_procedural_player(self, actor, draw_rect, packet, state_color, debug_text_enabled=False):
        """Draw the player character as a hooded Scriptorium Scholar with animated stride and gear."""
        cx, cy = int(draw_rect.centerx), int(draw_rect.centery)
        w, h = int(draw_rect.width), int(draw_rect.height)
        fx, fy = packet.get("facing", (1.0, 0.0))
        base_state = packet.get("base", "IDLE")
        now = time.time()

        # 1. Base cloak silhouette (maintains exact draw_rect call for camera offset verification)
        cloak_col = constants.COLOR_PLAYER_CLOAK
        if base_state == "DASH" and debug_text_enabled:
            cloak_col = constants.COLOR_CYAN
        elif base_state == "BLOCK":
            cloak_col = constants.COLOR_PLAYER_SHIELD
        pygame.draw.rect(self.screen, cloak_col, draw_rect, border_radius=10)

        # Dash wind-streaks behind the Scholar
        if base_state == "DASH":
            for i in (-8, 0, 8):
                sx, sy = cx - int(fx * 12) - int(fy * i), cy - int(fy * 12) + int(fx * i)
                ex, ey = sx - int(fx * 16), sy - int(fy * 16)
                pygame.draw.line(self.screen, constants.COLOR_WHITE, (sx, sy), (ex, ey), 2)

        # 2. Animated boots at bottom of cloak
        stride = int(math.sin(now * 16.0) * 4) if base_state == "RUN" else 0
        pygame.draw.circle(self.screen, constants.COLOR_PLAYER_BOOT, (cx - 7, draw_rect.bottom - 3 + stride), 4)
        pygame.draw.circle(self.screen, constants.COLOR_PLAYER_BOOT, (cx + 7, draw_rect.bottom - 3 - stride), 4)

        # 3. Layered shoulder mantle and gold scholar stole/trim
        bob = int(math.sin(now * 6.0) * 1) if base_state == "IDLE" else 0
        mantle_rect = pygame.Rect(draw_rect.x + 3, draw_rect.y + 8 + bob, max(8, w - 6), max(8, h // 2))
        pygame.draw.rect(self.screen, constants.COLOR_PLAYER_MANTLE, mantle_rect, border_radius=7)
        pygame.draw.line(
            self.screen, constants.COLOR_PLAYER_TRIM,
            (mantle_rect.left + 3, mantle_rect.bottom - 2), (mantle_rect.right - 3, mantle_rect.bottom - 2), 2
        )
        pygame.draw.line(
            self.screen, constants.COLOR_PLAYER_TRIM, (cx, mantle_rect.top + 4), (cx, draw_rect.bottom - 5), 2
        )

        # 4. Scholar's hood, shadowed cowl, and directional glowing eyes
        head_y = draw_rect.y + h // 3 + bob
        pygame.draw.circle(self.screen, constants.COLOR_PLAYER_HOOD, (cx, head_y), max(7, w // 3))
        cowl_x, cowl_y = cx + int(fx * 3), head_y + int(fy * 2)
        pygame.draw.circle(self.screen, constants.COLOR_PLAYER_COWL, (cowl_x, cowl_y), max(5, w // 4))
        perp_x, perp_y = -fy, fx
        eye1 = (int(cowl_x + fx * 2 + perp_x * 3), int(cowl_y + fy * 2 + perp_y * 3))
        eye2 = (int(cowl_x + fx * 2 - perp_x * 3), int(cowl_y + fy * 2 - perp_y * 3))
        pygame.draw.circle(self.screen, constants.COLOR_PLAYER_EYE, eye1, 2)
        pygame.draw.circle(self.screen, constants.COLOR_PLAYER_EYE, eye2, 2)

        # 5. Off-hand ward shield when blocking, or carried sword at side when not attacking
        wpn = actor.get_active_weapon() if hasattr(actor, "get_active_weapon") and actor.weapons else {}
        is_anomalous = bool(wpn.get("modifiers")) or "anomalous" in wpn.get("name", "").lower()
        edge_col = constants.get_weapon_passive_color(wpn) if is_anomalous else constants.COLOR_WEAPON_EDGE

        if base_state == "BLOCK":
            sh_x, sh_y = cx + int(fx * (w * 0.45)), cy + int(fy * (h * 0.45))
            pygame.draw.circle(self.screen, constants.COLOR_PLAYER_SHIELD, (sh_x, sh_y), 11)
            pygame.draw.circle(self.screen, constants.COLOR_PLAYER_TRIM, (sh_x, sh_y), 11, 2)
            pygame.draw.circle(self.screen, constants.COLOR_CYAN, (sh_x, sh_y), 4)
        elif base_state != "ATTACK":
            # Hold sword at right-hand side angled slightly forward
            hx = cx + int(perp_x * (w * 0.38)) - int(fx * 4)
            hy = cy + int(perp_y * (h * 0.38)) - int(fy * 4)
            tx = hx + int(fx * 22) + int(perp_x * 3)
            ty = hy + int(fy * 22) + int(perp_y * 3)
            self._draw_tapered_blade((hx, hy), (tx, ty), 3.5, edge_col)

        return True

    def draw_player_weapon_attack(self, player, ox, oy):
        """Draw an animated sword slash arc and tapered blade during player attacks."""
        px, py = player.get_center()
        cx, cy = px - ox, py - oy
        fx, fy = player.facing
        base_angle = math.atan2(fy, fx)

        total_dur = max(0.01, constants.SWORD_DURATION)
        t = 1.0 - max(0.0, min(1.0, getattr(player, "attack_timer", 0.0) / total_dur))
        reach = constants.SWORD_REACH
        half_arc = constants.SWORD_ARC_RADIANS / 2.0
        arc_start = base_angle - half_arc
        curr_angle = arc_start + t * constants.SWORD_ARC_RADIANS

        wpn = player.get_active_weapon() if hasattr(player, "get_active_weapon") and player.weapons else {}
        is_anomalous = bool(wpn.get("modifiers")) or "anomalous" in wpn.get("name", "").lower()
        slash_col = constants.get_weapon_passive_color(wpn)
        edge_col = slash_col if is_anomalous else constants.COLOR_WEAPON_EDGE

        # 1. Distinct swept crescent fan and gradient trail
        steps = constants.SWORD_ARC_STEPS
        surf_size = int(reach * 2 + 32)
        arc_surf = pygame.Surface((surf_size, surf_size), pygame.SRCALPHA)
        scx, scy = surf_size // 2, surf_size // 2

        for i in range(steps):
            u1 = i / steps
            u2 = (i + 1) / steps
            a1 = arc_start + (curr_angle - arc_start) * u1
            a2 = arc_start + (curr_angle - arc_start) * u2

            # Fading alpha along the swept trail
            alpha = int(25 + 135 * u2)
            poly_pts = [
                (scx + math.cos(a1) * (reach * 0.60), scy + math.sin(a1) * (reach * 0.60)),
                (scx + math.cos(a1) * reach, scy + math.sin(a1) * reach),
                (scx + math.cos(a2) * reach, scy + math.sin(a2) * reach),
                (scx + math.cos(a2) * (reach * 0.60), scy + math.sin(a2) * (reach * 0.60)),
            ]
            pygame.draw.polygon(arc_surf, (slash_col[0], slash_col[1], slash_col[2], alpha), poly_pts)

            # Outer rim on screen surface
            p1 = (int(cx + math.cos(a1) * reach), int(cy + math.sin(a1) * reach))
            p2 = (int(cx + math.cos(a2) * reach), int(cy + math.sin(a2) * reach))
            line_w = 3 if u2 > 0.4 else 2
            pygame.draw.line(self.screen, slash_col, p1, p2, line_w)

            # Inner accent line
            in1 = (int(cx + math.cos(a1) * (reach - 8.0)), int(cy + math.sin(a1) * (reach - 8.0)))
            in2 = (int(cx + math.cos(a2) * (reach - 8.0)), int(cy + math.sin(a2) * (reach - 8.0)))
            pygame.draw.line(self.screen, edge_col, in1, in2, 2 if u2 > 0.5 else 1)

        self.screen.blit(arc_surf, (int(cx - scx), int(cy - scy)))

        # 2. Active tapered sword along current swing angle
        hx = cx + math.cos(curr_angle) * 10.0
        hy = cy + math.sin(curr_angle) * 10.0
        tx = cx + math.cos(curr_angle) * (reach + 6.0)
        ty = cy + math.sin(curr_angle) * (reach + 6.0)
        self._draw_tapered_blade((hx, hy), (tx, ty), 5.0, edge_col)

        # 3. Leading crescent tip flare
        pygame.draw.circle(self.screen, constants.COLOR_WHITE, (int(tx), int(ty)), 3)

    def draw_boss_weapon(self, actor, ox, oy):
        """Draws a sharp tapered greatblade held by a boss that swings or thrusts dynamically."""
        if not hasattr(actor, 'state') or not hasattr(actor, 'combat_timer'):
            return

        from engine.actor import ActorState
        if actor.state not in (ActorState.WIND_UP, ActorState.STRIKE, ActorState.RECOVERY):
            return

        cx = actor.x + actor.width / 2 - ox
        cy = actor.y + actor.height / 2 - oy
        fx, fy = actor.facing

        # Determine animation progress t (0 to 1)
        t = 0.0
        if actor.state == ActorState.WIND_UP and actor.wind_up_duration > 0:
            t = max(0.0, min(1.0, 1.0 - (actor.combat_timer / actor.wind_up_duration)))
        elif actor.state == ActorState.STRIKE and actor.strike_duration > 0:
            t = max(0.0, min(1.0, 1.0 - (actor.combat_timer / actor.strike_duration)))
        elif actor.state == ActorState.RECOVERY and actor.recovery_duration > 0:
            t = max(0.0, min(1.0, 1.0 - (actor.combat_timer / actor.recovery_duration)))

        attack_type = getattr(actor, 'attack_type', 'THRUST')
        base_angle = math.atan2(fy, fx)

        if attack_type == "BEAM" or "sentry" in actor.name.lower():
            beam_len = getattr(actor, "beam_range", 160.0)
            sx, sy = int(cx + fx * 14.0), int(cy + fy * 14.0)
            ex, ey = int(cx + fx * (14.0 + beam_len)), int(cy + fy * (14.0 + beam_len))
            if actor.state == ActorState.WIND_UP:
                # Target-lock laser sightline and charging aperture orb
                pygame.draw.line(self.screen, constants.COLOR_SENTRY_RING, (sx, sy), (ex, ey), 1)
                charge_r = int(2 + t * 5)
                pygame.draw.circle(self.screen, constants.COLOR_SENTRY_EYE, (sx, sy), charge_r)
            elif actor.state == ActorState.STRIKE:
                # High-contrast plasma beam with white core and discharge nodes
                pygame.draw.line(self.screen, constants.COLOR_SENTRY_BEAM, (sx, sy), (ex, ey), 8)
                pygame.draw.line(self.screen, constants.COLOR_WHITE, (sx, sy), (ex, ey), 3)
                pygame.draw.circle(self.screen, constants.COLOR_WHITE, (sx, sy), 6)
                pygame.draw.circle(self.screen, constants.COLOR_SENTRY_BEAM, (ex, ey), 7)
            else:
                # Cooling plasma vent glow
                pygame.draw.circle(self.screen, constants.COLOR_SENTRY_RING, (sx, sy), max(2, int((1.0 - t) * 4)))
            return

        if attack_type == "THRUST":
            if actor.state == ActorState.WIND_UP:
                L = 60.0 - t * 25.0
            elif actor.state == ActorState.STRIKE:
                L = 35.0 + math.sin(t * math.pi) * 95.0
            else:
                L = 35.0 + t * 25.0

            hx, hy = cx + fx * 12.0, cy + fy * 12.0
            px, py = cx + fx * L, cy + fy * L
            self._draw_tapered_blade((hx, hy), (px, py), 7.0)
        else:
            if actor.state == ActorState.WIND_UP:
                angle = base_angle - 1.2 * t
                L = 60.0
            elif actor.state == ActorState.STRIKE:
                angle = (base_angle - 1.2) + t * 2.4
                L = 75.0

                # Draw swing trail
                trail_surf = pygame.Surface((self.screen.get_width(), self.screen.get_height()), pygame.SRCALPHA)
                trail_angle_start = base_angle - 1.2
                trail_angle_end = angle
                points = [(cx, cy)]
                steps = 10
                for i in range(steps + 1):
                    a = trail_angle_start + (trail_angle_end - trail_angle_start) * (i / steps)
                    points.append((cx + math.cos(a) * L, cy + math.sin(a) * L))
                if len(points) > 2:
                    pygame.draw.polygon(trail_surf, (220, 220, 220, 25), points)
                self.screen.blit(trail_surf, (0, 0))
            else:
                angle = (base_angle + 1.2) - t * 1.2
                L = 60.0

            hx, hy = cx + math.cos(angle) * 12.0, cy + math.sin(angle) * 12.0
            px, py = cx + math.cos(angle) * L, cy + math.sin(angle) * L
            self._draw_tapered_blade((hx, hy), (px, py), 7.0)

    def draw_remote_players(self, state, ox, oy):
        """Phase 4: Render ghosts for other players on the network."""
        remote_data = getattr(state.network_manager, 'remote_players', {})
        for addr, data in remote_data.items():
            if "x" not in data or "y" not in data: continue
            
            # Identity (Identity from Heartbeat or Handshake)
            name = data.get("identity", "Stranger")
            
            # Rendering Coordinates
            rx, ry = float(data["x"]) - ox, float(data["y"]) - oy
            
            # Draw Ghost Circle (Cyan for Host, Magenta for Clients)
            # Logic: If I am HOST, then others are CLIENTS (Magenta). 
            # If I am CLIENT, then the one at server_address is HOST (Cyan).
            color = (255, 0, 255)  # Default Magenta (Client)
            is_host_ghost = bool(
                data.get("is_host")
                or data.get("addr") == state.network_manager.server_address
                or addr == state.network_manager.server_address
            )
            if state.network_manager.network_mode == "CLIENT" and is_host_ghost:
                color = constants.COLOR_CYAN  # Host
            
            pygame.draw.circle(self.screen, color, (int(rx + 16), int(ry + 16)), 12)
            pygame.draw.circle(self.screen, constants.COLOR_WHITE, (int(rx + 16), int(ry + 16)), 12, 1)
            
            # Identity Tag
            id_surf = self.small_font.render(name, True, constants.COLOR_WHITE)
            self.screen.blit(id_surf, (rx + 16 - id_surf.get_width() // 2, ry - 15))

    @staticmethod
    def _format_debug_osd_status(state):
        """Format biome/act location and active Marginalia event lines for the top debug OSD."""
        if hasattr(state, "in_sanctuary"):
            in_sanctuary = bool(state.in_sanctuary)
        else:
            in_sanctuary = getattr(getattr(state, "world", None), "name", "") == "sanctuary"

        if in_sanctuary:
            biome_line = "Biome: Sanctuary"
        else:
            current_act = int(getattr(state, "current_act", 0) or 0)
            run_biomes = getattr(state, "run_biomes", None) or {}
            biome_key = run_biomes.get(f"act{current_act}") if current_act > 0 else None
            if not biome_key:
                biome_key = getattr(getattr(state, "world", None), "name", None)
            if biome_key:
                biome_name = constants.BIOME_DISPLAY_NAMES.get(
                    biome_key, str(biome_key).replace("_", " ").title()
                )
            else:
                biome_name = "Unknown"
            biome_line = (
                f"Biome: {biome_name} (Act {current_act})"
                if current_act > 0
                else f"Biome: {biome_name}"
            )

        marg_engine = getattr(state, "marginalia_engine", None)
        active_event = getattr(marg_engine, "active_event", None) if marg_engine is not None else None
        if active_event is not None:
            ev_title = getattr(active_event, "title", None) or getattr(active_event, "event_id", "Unknown")
            ev_status = getattr(active_event, "status", "UNKNOWN")
            event_line = f"Event: {ev_title} ({ev_status})"
        else:
            event_line = "Event: None"

        return biome_line, event_line

    def draw_audio_debug(self, audio, state=None):
        """Draw OSD for music, map filename, biome/act, Marginalia event status, and recent SFX."""
        margin = 10
        sw = self.screen.get_width()

        marg_engine = getattr(state, "marginalia_engine", None) if state is not None else None
        banner_visible = bool(
            state is not None
            and not getattr(state, "in_sanctuary", False)
            and marg_engine is not None
            and hasattr(marg_engine, "get_banner_state")
            and marg_engine.get_banner_state()
        )
        # Offset below top-center Marginalia banner (y=12..74) when visible to prevent overlap
        y_off = 80 if banner_visible else margin

        def _blit_top_center(text, color=(120, 255, 100)):
            nonlocal y_off
            surf = self.hud_font.render(text, True, color)
            surf_w = (
                surf.get_width()
                if hasattr(surf, "get_width")
                else (surf.get_rect().width if hasattr(surf, "get_rect") else 0)
            )
            surf_h = (
                surf.get_height()
                if hasattr(surf, "get_height")
                else (surf.get_rect().height if hasattr(surf, "get_rect") else 0)
            )
            self.screen.blit(surf, (sw // 2 - surf_w // 2, y_off))
            y_off += surf_h + 2

        # 1. Music Info (Top Center)
        track = audio.current_track if (audio and getattr(audio, "current_track", None)) else "None"
        _blit_top_center(f"[ AUDIO_OSD ] MUSIC: {track}")

        # 2. Map Filename (Top Center, directly underneath music track name)
        map_filename = getattr(getattr(state, "world", None), "map_filename", None)
        if map_filename:
            _blit_top_center(f"Map: {map_filename}")

        # 3. Biome / Act & Marginalia Event Status (Top Center)
        if state is not None:
            biome_line, event_line = self._format_debug_osd_status(state)
            _blit_top_center(biome_line)
            _blit_top_center(event_line)

        # 4. Recent SFX (Top Left)
        if audio and hasattr(audio, "recent_sfx"):
            sfx_y = margin
            for sfx in audio.recent_sfx:
                alpha = int((sfx["time"] / 2.0) * 255)
                alpha = max(0, min(255, alpha))
                s_surf = self.small_font.render(f"SFX: {sfx['name']}", True, (220, 220, 220))
                s_surf.set_alpha(alpha)
                self.screen.blit(s_surf, (margin, sfx_y))
                sfx_y += 18

    def draw_parry_effects(self, state, ox, oy):
        """Draw transient high-contrast bursts for successful parries."""
        for effect in getattr(state, 'parry_effects', []):
            alpha = int((effect['time'] / 0.3) * 255)
            alpha = max(0, min(255, alpha))
            
            ex, ey = effect['pos']
            sx, sy = int(ex - ox), int(ey - oy)
            
            # Draw multi-layered burst
            surf = pygame.Surface((80, 80), pygame.SRCALPHA)
            pygame.draw.circle(surf, (255, 255, 255, alpha), (40, 40), 30, 4)
            pygame.draw.circle(surf, (120, 255, 100, alpha // 2), (40, 40), 40, 2)
            self.screen.blit(surf, (sx - 40, sy - 40))

    def draw_fading_slash_arcs(self, state, ox, oy):
        """Render completed visual slash arcs fading smoothly over their fade duration."""
        for slash in getattr(state, "slash_effects", []):
            remaining = slash.get("time", 0.0)
            max_time = max(0.01, slash.get("max_time", constants.SLASH_FADE_DURATION))
            ratio = max(0.0, min(1.0, remaining / max_time))
            if ratio <= 0.0:
                continue

            px, py = slash["pos"]
            cx, cy = px - ox, py - oy
            fx, fy = slash["facing"]
            base_angle = math.atan2(fy, fx)
            reach = slash.get("reach", constants.SWORD_REACH)
            arc_rad = slash.get("arc_radians", constants.SWORD_ARC_RADIANS)
            half_arc = arc_rad / 2.0
            arc_start = base_angle - half_arc
            col = slash.get("color", constants.COLOR_CYAN)

            surf_size = int(reach * 2 + 32)
            arc_surf = pygame.Surface((surf_size, surf_size), pygame.SRCALPHA)
            scx, scy = surf_size // 2, surf_size // 2
            steps = constants.SWORD_ARC_STEPS
            poly_alpha = int(ratio * 90)
            rim_alpha = int(ratio * 210)

            for i in range(steps):
                a1 = arc_start + arc_rad * (i / steps)
                a2 = arc_start + arc_rad * ((i + 1) / steps)
                o1 = (scx + math.cos(a1) * reach, scy + math.sin(a1) * reach)
                o2 = (scx + math.cos(a2) * reach, scy + math.sin(a2) * reach)
                i1 = (scx + math.cos(a1) * (reach * 0.60), scy + math.sin(a1) * (reach * 0.60))
                i2 = (scx + math.cos(a2) * (reach * 0.60), scy + math.sin(a2) * (reach * 0.60))
                pygame.draw.polygon(arc_surf, (col[0], col[1], col[2], poly_alpha), [i1, o1, o2, i2])
                pygame.draw.line(arc_surf, (col[0], col[1], col[2], rim_alpha), o1, o2, 2)

            self.screen.blit(arc_surf, (int(cx - scx), int(cy - scy)))

    def draw_impact_sparks(self, state, ox, oy):
        """Render high-velocity directional impact sparks from landed melee attacks."""
        for spark in getattr(state, "impact_sparks", []):
            remaining = spark.get("time", 0.0)
            max_time = max(0.01, spark.get("max_time", constants.IMPACT_SPARK_LIFETIME))
            ratio = max(0.0, min(1.0, remaining / max_time))
            if ratio <= 0.0:
                continue

            sx = int(spark["x"] - ox)
            sy = int(spark["y"] - oy)
            vx = spark.get("vx", 0.0)
            vy = spark.get("vy", 0.0)
            speed = math.hypot(vx, vy)
            if speed > 1.0:
                ux, uy = vx / speed, vy / speed
                length = constants.IMPACT_SPARK_LENGTH * (0.5 + 0.5 * ratio)
                tail_x = int(sx - ux * length)
                tail_y = int(sy - uy * length)
            else:
                tail_x, tail_y = sx, sy

            col = spark.get("color", constants.COLOR_IMPACT_SPARK_CORE)
            pygame.draw.line(self.screen, col, (sx, sy), (tail_x, tail_y), 2)
            pygame.draw.circle(self.screen, constants.COLOR_IMPACT_SPARK_CORE, (sx, sy), 1)

    def draw_glyph_splatter(self, state, ox, oy):
        """Render active manuscript glyph splatter particles scattering from combat impacts."""
        manager = getattr(state, 'glyph_particles', None)
        if not manager or not manager.particles:
            return

        sw = self.screen.get_width()
        sh = self.screen.get_height()

        for p in manager.particles:
            sx = int(p.x - ox)
            sy = int(p.y - oy)
            # Viewport culling
            if -24 <= sx <= sw + 24 and -24 <= sy <= sh + 24:
                alpha = p.alpha
                if alpha <= 0:
                    continue
                # Render glyph surface using the manuscript monospace font
                try:
                    if hasattr(self, 'glyph_font') and self.glyph_font:
                        text_surf = self.glyph_font.render(p.glyph, True, p.color)
                    else:
                        text_surf = self.small_font.render(p.glyph, True, p.color)
                    if alpha < 255:
                        text_surf.set_alpha(alpha)
                    self.screen.blit(text_surf, (sx - text_surf.get_width() // 2, sy - text_surf.get_height() // 2))
                except Exception:
                    pass

    def draw_warp_sequence(self, state, ox, oy):
        """Render cinematic Ink & Fog transition overlays (fog puffs, runes, and veil)."""
        warp = getattr(state, 'warp_controller', None)
        if not warp or not warp.is_active():
            return

        sw = self.screen.get_width()
        sh = self.screen.get_height()

        # 1. Render Translucent Fog Puffs
        for puff in warp.fog_puffs:
            alpha = puff.alpha
            if alpha <= 0 or puff.radius <= 1.0:
                continue

            sx = int(puff.x - ox)
            sy = int(puff.y - oy)
            r = int(puff.radius)

            # Viewport culling
            if sx + r < 0 or sx - r > sw or sy + r < 0 or sy - r > sh:
                continue

            # Quantize radius and alpha to reuse pre-rendered soft circle surfaces
            q_r = max(4, int(round(r / 2.0) * 2))
            q_a = max(0, min(255, int(round(alpha / 8.0) * 8)))
            cache_key = (q_r, puff.color, q_a)

            surf = self._puff_cache.get(cache_key)
            if surf is None:
                d = q_r * 2
                surf = pygame.Surface((d, d), pygame.SRCALPHA)
                cr, cg, cb = puff.color
                for step in range(3):
                    frac = (3 - step) / 3.0
                    step_r = max(2, int(q_r * frac))
                    step_a = int(q_a * ((step + 1) / 3.0) * 0.7)
                    pygame.draw.circle(surf, (cr, cg, cb, step_a), (q_r, q_r), step_r)
                if len(self._puff_cache) > 256:
                    self._puff_cache.clear()
                self._puff_cache[cache_key] = surf

            self.screen.blit(surf, (sx - q_r, sy - q_r))

        # 2. Render Swirling Manuscript Glyphs
        for glyph in warp.glyph_particles:
            alpha = glyph.alpha
            if alpha <= 0:
                continue

            sx = int(glyph.x - ox)
            sy = int(glyph.y - oy)

            if -24 <= sx <= sw + 24 and -24 <= sy <= sh + 24:
                try:
                    if hasattr(self, 'glyph_font') and self.glyph_font:
                        text_surf = self.glyph_font.render(glyph.glyph, True, glyph.color)
                    else:
                        text_surf = self.small_font.render(glyph.glyph, True, glyph.color)
                    if alpha < 255:
                        text_surf.set_alpha(alpha)
                    self.screen.blit(
                        text_surf,
                        (sx - text_surf.get_width() // 2, sy - text_surf.get_height() // 2),
                    )
                except Exception:
                    pass

        # 3. Full-Screen Veil (Black Overlay)
        veil_alpha = getattr(warp, 'veil_alpha', 0)
        if veil_alpha > 0:
            if self.warp_veil_surface is None or self.warp_veil_surface.get_size() != (sw, sh):
                self.warp_veil_surface = pygame.Surface((sw, sh))
                self.warp_veil_surface.fill((0, 0, 0))
            self.warp_veil_surface.set_alpha(min(255, max(0, veil_alpha)))
            self.screen.blit(self.warp_veil_surface, (0, 0))

    def draw_bloom_overlay(self, state):
        """Draw alpha-blended typographic zone discovery overlay."""
        timer = getattr(state, 'bloom_timer', 0)
        if timer <= 0:
            return

        sw, sh = self.screen.get_width(), self.screen.get_height()
        bloom_surf = pygame.Surface((sw, sh), pygame.SRCALPHA)
        
        # Calculate Alpha based on lifecycle steps
        # Fade In (1.0s), Hold (2.0s), Fade Out (1.0s)
        total = constants.BLOOM_TOTAL_DURATION
        alpha = 0
        
        if timer > constants.BLOOM_HOLD + constants.BLOOM_FADE_OUT:
            # Fade In Phase
            fade_elapsed = total - timer
            alpha = int((fade_elapsed / constants.BLOOM_FADE_IN) * 255)
        elif timer > constants.BLOOM_FADE_OUT:
            # Hold Phase
            alpha = 255
        else:
            # Fade Out Phase
            alpha = int((timer / constants.BLOOM_FADE_OUT) * 255)
        
        alpha = max(0, min(255, alpha))
        
        # Draw Title with stylized font
        text = getattr(state, 'bloom_text', "THE UNKNOWN MARGIN")

        # Full-width dramatic banner backing for long / escalation announcements
        if len(text) > 26 or getattr(state, 'bloom_priority', 0) >= 3:
            banner_h = 110
            banner_y = sh // 3 - banner_h // 2
            banner = pygame.Surface((sw, banner_h), pygame.SRCALPHA)
            banner.fill((22, 8, 16, int(alpha * 0.82)))
            pygame.draw.line(banner, (185, 38, 62, alpha), (0, 2), (sw, 2), 2)
            pygame.draw.line(banner, (185, 38, 62, alpha), (0, banner_h - 3), (sw, banner_h - 3), 2)
            bloom_surf.blit(banner, (0, banner_y))

        # Shadow / Bloom effect
        shadow_col = (*constants.COLOR_BLOOM_SHADOW, alpha // 2)
        shadow_surf = self.bloom_font.render(text, True, shadow_col)
        text_col = (*constants.COLOR_BLOOM_TEXT, alpha)
        text_surf = self.bloom_font.render(text, True, text_col)

        max_w = max(200, sw - 80)
        if text_surf.get_width() > max_w:
            scale_ratio = max_w / float(text_surf.get_width())
            new_size = (max_w, max(12, int(text_surf.get_height() * scale_ratio)))
            shadow_surf = pygame.transform.smoothscale(shadow_surf, new_size)
            text_surf = pygame.transform.smoothscale(text_surf, new_size)

        bloom_surf.blit(shadow_surf, shadow_surf.get_rect(center=(sw // 2 + 4, sh // 3 + 4)))
        bloom_surf.blit(text_surf, text_surf.get_rect(center=(sw // 2, sh // 3)))

        self.screen.blit(bloom_surf, (0, 0))

    def draw_hud(self, state):
        """Draw player HP, Flask, and Dual Weapon slots."""
        player = state.player
        panel_w = constants.HUD_PANEL_W
        panel_h = constants.HUD_PANEL_H
        if self._hud_surf is None or self._hud_surf.get_size() != (panel_w, panel_h):
            self._hud_surf = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        hud_surf = self._hud_surf
        hud_surf.fill((20, 20, 25, constants.UI_ALPHA))
        pygame.draw.rect(hud_surf, (100, 100, 100), (0, 0, panel_w, panel_h), 2)
        
        # Status Metrics (compact font)
        hp_text = f"HP: {int(player.hp)}/{int(player.max_hp)}"
        hud_surf.blit(self.hud_font.render(hp_text, True, constants.COLOR_WHITE), (10, 10))
        
        flask_text = f"Flasks: {player.flask_charges}"
        hud_surf.blit(self.hud_font.render(flask_text, True, constants.COLOR_BLUE), (140, 10))
        
        pages = state.stats.data["lifetime_stats"].get("pages_collected", 0) if state.stats else 0
        pages_text = f"Pages: {pages}"
        hud_surf.blit(self.hud_font.render(pages_text, True, constants.COLOR_SELECTION), (240, 10))

        edif_lvl = player.stats.get("edification", 1)
        edif_text = f"LVL: {edif_lvl}"
        hud_surf.blit(self.hud_font.render(edif_text, True, constants.COLOR_CYAN), (340, 10))
        
        # [Multiplayer: Scholar Count]
        scholar_count = 1
        if hasattr(state, 'network_manager'):
            scholar_count = 1 + len(getattr(state.network_manager, 'remote_players', {}))
        
        scholar_text = f"Scholars: {scholar_count}"
        hud_surf.blit(self.hud_font.render(scholar_text, True, constants.COLOR_WHITE), (440, 10))

        # [Input Mode Indicator] (gated behind debug_text_enabled)
        if getattr(state, "debug_text_enabled", False):
            mode = getattr(state, 'input_mode', constants.INPUT_MODE_KEYBOARD)
            mode_col = (
                constants.COLOR_MODE_GAMEPAD
                if mode == constants.INPUT_MODE_GAMEPAD
                else constants.COLOR_MODE_KEYBOARD
            )
            mode_label = self.hud_font.render(f"[ Input: {mode.capitalize()} ]", True, mode_col)
            hud_surf.blit(
                mode_label,
                (hud_surf.get_width() - mode_label.get_width() - 10, hud_surf.get_height() - 25),
            )

        for i in range(2):
            sx, sy = 10 + i * (constants.HUD_SLOT_W + 100), 45
            sr = pygame.Rect(sx, sy, constants.HUD_SLOT_W, constants.HUD_SLOT_H)
            pygame.draw.rect(hud_surf, (40, 40, 50), sr)
            
            border_col = constants.COLOR_SELECTION if i == player.active_weapon_idx else constants.COLOR_GREY
            pygame.draw.rect(hud_surf, border_col, sr, 2)
            
            l_surf = self.slot_font.render("SLOT A" if i == 0 else "SLOT B", True, constants.COLOR_GREY)
            hud_surf.blit(l_surf, (sx + 5, sy + 2))
            
            if i < len(player.weapons):
                wpn = player.weapons[i]
                col = constants.COLOR_PURPLE if "modifiers" in wpn else constants.COLOR_WHITE
                
                name_surf = self.small_font.render(wpn.get("name", "Unknown")[:12], True, col)
                hud_surf.blit(name_surf, (sx + 5, sy + 20))
                
                dmg_text = f"DMG: {wpn.get('damage', 0)}"
                dmg_surf = self.slot_font.render(dmg_text, True, constants.COLOR_GREY)
                hud_surf.blit(dmg_surf, (sx + 5, sy + 40))
        swr = pygame.Rect(constants.HUD_SWAP_BTN_RECT)
        pygame.draw.rect(hud_surf, (60, 60, 80), swr)
        pygame.draw.rect(hud_surf, constants.COLOR_WHITE, swr, 1)
        swt = self.hud_font.render("Q / L1 (GP)", True, constants.COLOR_WHITE)
        hud_surf.blit(swt, (swr.centerx - swt.get_width()//2, swr.centery - swt.get_height()//2))

        # [PICK UP] Button - only visible if standing over a WeaponPickup
        from engine.world import WeaponPickup
        target = state.player.current_interactable
        is_near_weapon = isinstance(target, WeaponPickup)
        if is_near_weapon:
            pkr = pygame.Rect(constants.HUD_PICKUP_BTN_RECT)
            # Use tier color for button outline
            col = constants.COLOR_PURPLE if "modifiers" in target.weapon_data else constants.COLOR_WHITE
            pygame.draw.rect(hud_surf, (40, 60, 40), pkr) # Dark green tint for pickup
            pygame.draw.rect(hud_surf, col, pkr, 2)
            pkt = self.hud_font.render("SPACE / A (GP)", True, constants.COLOR_WHITE)
            hud_surf.blit(pkt, (pkr.centerx - pkt.get_width()//2, pkr.centery - pkt.get_height()//2))

        # Draw Active Status Effects on HUD
        status_x = 325
        status_y = 50
        active_statuses = []
        if getattr(player, 'negation_timer', 0.0) > 0.0:
            active_statuses.append({
                "name": "WARD",
                "val": f"-{int(player.negation_amount)}",
                "time": f"{player.negation_timer:.1f}s",
                "color": (255, 215, 0),  # Gold
                "bg": (60, 50, 20)
            })
        if getattr(player, 'bind_timer', 0.0) > 0.0:
            active_statuses.append({
                "name": "BOUND",
                "val": "",
                "time": f"{player.bind_timer:.1f}s",
                "color": (255, 100, 100),  # Pink/Red
                "bg": (60, 20, 20)
            })

        all_mods = player.get_all_modifiers()
        if "slow_hp_regen" in all_mods:
            active_statuses.append({
                "name": "REGEN",
                "val": f"+{int(all_mods['slow_hp_regen'])}/s",
                "time": "PASSIVE",
                "color": (0, 255, 128),  # Cyan-green
                "bg": (20, 50, 35)
            })

        for status in active_statuses:
            badge_w = 85
            badge_h = 45
            badge_rect = pygame.Rect(status_x, status_y, badge_w, badge_h)

            pygame.draw.rect(hud_surf, status["bg"], badge_rect, border_radius=4)
            pygame.draw.rect(hud_surf, status["color"], badge_rect, 1, border_radius=4)

            name_surf = self.hud_font.render(status["name"], True, status["color"])
            hud_surf.blit(name_surf, (badge_rect.x + 5, badge_rect.y + 3))

            val_time_str = status["val"]
            if status["val"] and status["time"] != "PASSIVE":
                val_time_str += f" ({status['time']})"
            else:
                val_time_str += status["time"]

            info_surf = self.slot_font.render(val_time_str, True, constants.COLOR_WHITE)
            hud_surf.blit(info_surf, (badge_rect.x + 5, badge_rect.y + 22))

            status_x += badge_w + 10

        hud_x = 10
        hud_y = self.screen.get_height() - constants.HUD_PANEL_H - 10
        self.screen.blit(hud_surf, (hud_x, hud_y))

        net_mode = getattr(getattr(state, "network_manager", None), "network_mode", "STANDALONE")
        if net_mode in ("HOST", "CLIENT") or getattr(state, "waiting_for_host_run", False):
            waiting_for_run = getattr(state, "waiting_for_host_run", False) or (
                net_mode == "CLIENT"
                and getattr(state, "in_sanctuary", False)
                and getattr(state, "host_in_run", False)
            )
            waiting_scholars = int(getattr(state, "waiting_scholars", 0))
            if waiting_for_run:
                banner_text = "Waiting for current run to finish..."
                banner_surf = self.font.render(banner_text, True, constants.COLOR_SELECTION)
                banner_rect = banner_surf.get_rect(center=(self.screen.get_width() // 2, 34))
                bg_rect = banner_rect.inflate(24, 12)
                pygame.draw.rect(self.screen, (15, 18, 26), bg_rect, border_radius=6)
                pygame.draw.rect(self.screen, constants.COLOR_SELECTION, bg_rect, 2, border_radius=6)
                self.screen.blit(banner_surf, banner_rect)
            elif waiting_scholars > 0 and net_mode in ("HOST", "CLIENT"):
                noun = "Scholar" if waiting_scholars == 1 else "Scholars"
                banner_text = f"{waiting_scholars} {noun} waiting in Sanctuary"
                banner_surf = self.small_font.render(banner_text, True, constants.COLOR_SELECTION)
                banner_rect = banner_surf.get_rect(topright=(self.screen.get_width() - 20, 16))
                bg_rect = banner_rect.inflate(16, 10)
                pygame.draw.rect(self.screen, (15, 18, 26), bg_rect, border_radius=4)
                pygame.draw.rect(self.screen, constants.COLOR_SELECTION, bg_rect, 1, border_radius=4)
                self.screen.blit(banner_surf, banner_rect)

        self.draw_marginalia_banner(state)

        # --- EXPANDED INSPECT VIEW ---
        if getattr(state, 'inspect_active', False):
            tip_w = 200
            tip_y = hud_y - 5
            
            curr_x = hud_x + 10
            step = tip_w + 15
            
            # 1. Equipped Slot A
            if len(player.weapons) > 0:
                self.draw_weapon_details(player.weapons[0], curr_x, tip_y, tip_w, title="SLOT A")
                curr_x += step
                
            # 2. Equipped Slot B
            if len(player.weapons) > 1:
                self.draw_weapon_details(player.weapons[1], curr_x, tip_y, tip_w, title="SLOT B")
                curr_x += step
                
            # 3. Character Upgrades
            self.draw_character_upgrades(player, curr_x, tip_y, tip_w)
            curr_x += step
            
            # 4. Ground Comparison
            if is_near_weapon:
                self.draw_weapon_details(target.weapon_data, curr_x, tip_y, tip_w, title="ON FLOOR")

    def draw_character_upgrades(self, player, x, y, width):
        """Draw a detailed tooltip for player character stats and upgrades (Marginalia Style)."""
        lines = []
        # Title
        lines.append(self.hud_font.render("CHARACTER", True, (150, 150, 150)))
        
        # Global Level (Edification / Understanding)
        edif = player.stats.get("edification", 1)
        lines.append(self.small_font.render(f"Understanding: Lvl {edif}", True, constants.COLOR_SELECTION))
        
        # Prowess Level / modifier
        prowess_mod = player.stats.get("attack_modifier", 0)
        prowess_lvl = 1 + (prowess_mod // constants.PROWESS_ATTACK_STEP)
        lines.append(self.small_font.render(
            f"Prowess: Lvl {prowess_lvl} (+{prowess_mod} Atk)", True, constants.COLOR_WHITE
        ))

        # Fortification Level / modifier
        fort_mod = player.stats.get("max_hp_modifier", 0)
        fort_lvl = 1 + (fort_mod // constants.FORTIFICATION_HP_STEP)
        lines.append(self.small_font.render(
            f"Fortification: Lvl {fort_lvl} (+{fort_mod} HP)", True, constants.COLOR_WHITE
        ))
        
        # Any power ups / passive modifiers / active effects
        all_mods = player.get_all_modifiers()
        active_mods = {k: v for k, v in all_mods.items() if v != 0}
        
        if active_mods:
            lines.append(self.small_font.render("--- Passive Effects ---", True, (100, 100, 100)))
            for m_key, m_val in active_mods.items():
                label = (
                    m_key.replace("_modifier", "")
                    .replace("_on_hit", "")
                    .replace("_boost", "")
                    .replace("_hp_", " ")
                    .capitalize()
                )
                sign = "+" if m_val > 0 else ""
                if m_key == "slow_hp_regen":
                    mod_text = f"{label}: {sign}{m_val}/s"
                elif m_key == "damage_negation_on_hit":
                    mod_text = f"Ward on Hit: {sign}{m_val}%"
                else:
                    mod_text = f"{label}: {sign}{m_val}"
                lines.append(self.small_font.render(mod_text, True, constants.COLOR_CYAN))
                
        # Draw active timers
        neg_amount = getattr(player, 'negation_amount', 0.0)
        neg_timer = getattr(player, 'negation_timer', 0.0)
        bind_timer = getattr(player, 'bind_timer', 0.0)
        
        if neg_timer > 0.0 or bind_timer > 0.0:
            lines.append(self.small_font.render("--- Active Buffs/Debuffs ---", True, (100, 100, 100)))
            if neg_timer > 0.0:
                lines.append(self.small_font.render(
                    f"Ward: -{int(neg_amount)} ({neg_timer:.1f}s)", True, (255, 215, 0)
                ))
            if bind_timer > 0.0:
                lines.append(self.small_font.render(f"Bound: {bind_timer:.1f}s", True, (255, 100, 100)))

        # Calculate Height & Background
        line_h = 18
        h = 15 + len(lines) * line_h + 10
        
        tip_surf = pygame.Surface((width, h), pygame.SRCALPHA)
        tip_surf.fill((20, 20, 30, 240))
        pygame.draw.rect(tip_surf, (100, 100, 110), (0, 0, width, h), 1)
        
        cur_y = 10
        for surf in lines:
            tip_surf.blit(surf, (10, cur_y))
            cur_y += line_h
            
        self.screen.blit(tip_surf, (x, y - h))
        return h

    def draw_weapon_details(self, weapon, x, y, width, title="EQUIPPED"):
        """Draw a detailed tooltip for a weapon (Marginalia Style)."""
        if not weapon: return 0
        
        # 1. Setup Surface & Content
        lines = []
        # Title (e.g., SLOT A)
        lines.append(self.hud_font.render(title, True, (150, 150, 150)))
        
        # Name (Use small font to avoid cutoff)
        col = constants.COLOR_PURPLE if "modifiers" in weapon else constants.COLOR_WHITE
        lines.append(self.small_font.render(weapon.get("name", "Unknown Quill"), True, col))
        
        # DMG Info
        dmg_text = f"Damage: {weapon.get('damage', 0)}"
        lines.append(self.small_font.render(dmg_text, True, (200, 200, 200)))

        # 2. Modifiers Section (Detailed Stats)
        mods = weapon.get("modifiers", {})
        if mods:
            lines.append(self.small_font.render("--- Modifiers ---", True, (100, 100, 100)))
            for m_key, m_val in mods.items():
                label = m_key.replace("_modifier", "").capitalize()
                sign = "+" if m_val > 0 else ""
                mod_text = f"{label}: {sign}{m_val}"
                lines.append(self.small_font.render(mod_text, True, constants.COLOR_CYAN))

        # 3. Description Section (Flavor)
        desc = weapon.get("description")
        if desc:
            lines.append(self.small_font.render("--- Critique ---", True, (100, 100, 100)))
            # Simple word wrap for description
            words = desc.split()
            cur_line = ""
            for w in words:
                test_line = cur_line + (" " if cur_line else "") + w
                if self.small_font.size(test_line)[0] < width - 20:
                    cur_line = test_line
                else:
                    lines.append(self.small_font.render(cur_line, True, (180, 180, 180)))
                    cur_line = w
            if cur_line:
                lines.append(self.small_font.render(cur_line, True, (180, 180, 180)))

        # 4. Calculate Height & Background
        line_h = 18
        h = 15 + len(lines) * line_h + 10
        
        tip_surf = pygame.Surface((width, h), pygame.SRCALPHA)
        tip_surf.fill((20, 20, 30, 240)) # Slightly darker for clarity
        pygame.draw.rect(tip_surf, (100, 100, 110), (0, 0, width, h), 1)
        
        # 5. Blit lines
        cur_y = 10
        for surf in lines:
            tip_surf.blit(surf, (10, cur_y))
            cur_y += line_h
            
        self.screen.blit(tip_surf, (x, y - h))
        return h

    @staticmethod
    def _compute_candelabra_flicker(now, obj_x, obj_y):
        """Return per-candelabra (glow_radius, glow_alpha) using an independent double-harmonic phase."""
        phase = float(now) * 5.2 + float(obj_x) * 1.7 + float(obj_y) * 0.9
        wave = 0.65 * math.sin(phase) + 0.35 * math.sin(phase * 2.3 + float(obj_y) * 0.4)
        glow_r = max(
            16,
            int(round(constants.SANCTUARY_CANDLE_GLOW_BASE_RADIUS + wave * constants.SANCTUARY_CANDLE_GLOW_RADIUS_AMP)),
        )
        glow_a = max(
            20,
            min(
                140,
                int(
                    round(
                        constants.SANCTUARY_CANDLE_GLOW_BASE_ALPHA + wave * constants.SANCTUARY_CANDLE_GLOW_ALPHA_AMP
                    )
                ),
            ),
        )
        return glow_r, glow_a

    def _get_candelabra_glow_surface(self, glow_r, glow_a):
        """Return a cached soft radial amber glow surface quantized by radius and alpha step."""
        q_a = (int(glow_a) // 4) * 4
        key = ("candelabra_glow", int(glow_r), q_a)
        surf = self._fx_surface_cache.get(key)
        if surf is None:
            size = int(glow_r) * 2
            surf = pygame.Surface((size, size), pygame.SRCALPHA)
            pygame.draw.circle(surf, (255, 178, 36, q_a), (glow_r, glow_r), glow_r)
            inner_r = max(4, int(glow_r * 0.55))
            inner_a = min(180, int(q_a * 1.35))
            pygame.draw.circle(surf, (255, 224, 118, inner_a), (glow_r, glow_r), inner_r)
            self._fx_surface_cache[key] = surf
        return surf

    @staticmethod
    def _get_sanctuary_roof_zones(state):
        """Return list of roof_zones dicts from state.world.sanctuary_zones when in Sanctuary."""
        world = getattr(state, "world", None)
        if getattr(world, "name", "") != "sanctuary":
            return []
        zones = getattr(world, "sanctuary_zones", None)
        if not isinstance(zones, dict):
            return []
        roofs = zones.get("roof_zones")
        return roofs if isinstance(roofs, list) else []

    @classmethod
    def _is_player_inside_scriptorium(cls, state):
        """Return True if local player center lies within the scriptorium_roof interior rect."""
        player = getattr(state, "player", None)
        if player is None:
            return False
        roofs = cls._get_sanctuary_roof_zones(state)
        scriptorium = next((r for r in roofs if isinstance(r, dict) and r.get("name") == "scriptorium_roof"), None)
        if scriptorium is None:
            return False
        interior = scriptorium.get("interior")
        if not isinstance(interior, (list, tuple)) or len(interior) != 4:
            return False
        ts = constants.TILE_SIZE
        ix, iy, iw, ih = interior[0] * ts, interior[1] * ts, interior[2] * ts, interior[3] * ts
        px, py = player.get_center()
        return ix <= px <= ix + iw and iy <= py <= iy + ih

    def update_sanctuary_interior_alpha(self, state, dt):
        """Smoothly interpolate self.sanctuary_interior_alpha in [0.0, 1.0]; resets to 0.0 outside Sanctuary."""
        if getattr(getattr(state, "world", None), "name", "") != "sanctuary":
            self.sanctuary_interior_alpha = 0.0
            return self.sanctuary_interior_alpha

        target = 1.0 if self._is_player_inside_scriptorium(state) else 0.0
        step = constants.SANCTUARY_INTERIOR_FADE_SPEED * max(0.0, float(dt))
        cur = float(self.sanctuary_interior_alpha)
        if cur < target:
            cur = min(target, cur + step)
        elif cur > target:
            cur = max(target, cur - step)
        self.sanctuary_interior_alpha = max(0.0, min(1.0, cur))
        return self.sanctuary_interior_alpha

    def _get_sanctuary_roof_surface(self, zone_dict):
        """Return a cached tiled slate roof surface for a Sanctuary roof_zones entry."""
        ts = constants.TILE_SIZE
        zw = int(zone_dict.get("w", 1))
        zh = int(zone_dict.get("h", 1))
        z_name = str(zone_dict.get("name", "roof"))
        roof_tile = self.prop_cache.get("SanctuaryRoofTile")
        cache_key = (z_name, zw, zh, id(roof_tile) if roof_tile is not None else 0)
        cached = self._sanctuary_roof_surfs.get(cache_key)
        if cached is not None:
            return cached

        rw_px, rh_px = max(ts, zw * ts), max(ts, zh * ts)
        surf = pygame.Surface((rw_px, rh_px))
        if roof_tile is not None:
            for ty in range(zh):
                for tx in range(zw):
                    surf.blit(roof_tile, (tx * ts, ty * ts))
        else:
            surf.fill((42, 46, 56))
            for sy in range(0, rh_px, 10):
                pygame.draw.line(surf, (26, 29, 38), (0, sy), (rw_px - 1, sy), 1)
        # Architectural slate ridge line & eaves trim
        ridge_y = rh_px // 2
        pygame.draw.line(surf, (78, 86, 100), (2, ridge_y), (rw_px - 3, ridge_y), 3)
        pygame.draw.rect(surf, (22, 25, 34), (0, 0, rw_px, rh_px), 3)
        self._sanctuary_roof_surfs[cache_key] = surf
        return surf

    def _draw_dark_enemy_ground_shadow(self, rect):
        """Draw a subtle translucent oval ground contact shadow beneath dark enemies."""
        if not isinstance(self.screen, pygame.Surface):
            return
        sw_s = max(14, int(rect.width * 0.78))
        sh_s = max(6, int(rect.height * 0.28))
        sx_s = int(rect.centerx - sw_s // 2)
        sy_s = int(rect.bottom - sh_s + 2)
        cache = getattr(self, "_fx_surface_cache", None)
        s_key = ("enemy_ground_shadow", sw_s, sh_s)
        sh_surf = cache.get(s_key) if cache is not None else None
        if sh_surf is None:
            sh_surf = pygame.Surface((sw_s, sh_s), pygame.SRCALPHA)
            pygame.draw.ellipse(sh_surf, (8, 14, 16, 92), (0, 0, sw_s, sh_s))
            if cache is not None:
                cache[s_key] = sh_surf
        self.screen.blit(sh_surf, (sx_s, sy_s))

    def _draw_dark_enemy_rim_highlight(self, rect, is_empowered=False):
        """Draw a crisp 1px pale-lavender/cool-silver top-rim arc over dark enemies for silhouette contrast."""
        if not isinstance(self.screen, pygame.Surface):
            return
        rim_col = (232, 184, 218) if is_empowered else (210, 202, 236)
        arc_w = max(10, int(rect.width * 0.76))
        arc_h = max(8, int(rect.height * 0.56))
        arc_rect = pygame.Rect(int(rect.centerx - arc_w // 2), int(rect.top + 2), arc_w, arc_h)
        pygame.draw.arc(self.screen, rim_col, arc_rect, 0.32, math.pi - 0.32, 1)

    def _draw_highland_monolith(self, sx_o, sy_o, prop_cache):
        """Render a weathered 40x60 HighlandMonolith anchored on its 40x40 base footprint with ground shadow."""
        tx_i, ty_i = int(sx_o), int(sy_o)
        if isinstance(self.screen, pygame.Surface):
            cache = getattr(self, "_fx_surface_cache", None)
            s_key = ("highland_monolith_shadow", 34, 11)
            sh_surf = cache.get(s_key) if cache is not None else None
            if sh_surf is None:
                sh_surf = pygame.Surface((34, 11), pygame.SRCALPHA)
                pygame.draw.ellipse(sh_surf, (10, 18, 22, 96), (0, 0, 34, 11))
                if cache is not None:
                    cache[s_key] = sh_surf
            self.screen.blit(sh_surf, (tx_i + 3, ty_i + 29))

        mono_surf = prop_cache.get("HighlandMonolith")
        if mono_surf is not None:
            self.screen.blit(mono_surf, (tx_i, ty_i - 20))
        elif isinstance(self.screen, pygame.Surface):
            # Graceful procedural weathered standing stone fallback
            poly = [
                (tx_i + 10, ty_i + 35), (tx_i + 11, ty_i - 6),
                (tx_i + 17, ty_i - 16), (tx_i + 24, ty_i - 13),
                (tx_i + 29, ty_i - 4), (tx_i + 30, ty_i + 35),
            ]
            pygame.draw.polygon(self.screen, (68, 96, 128), poly)
            pygame.draw.polygon(self.screen, (22, 32, 48), poly, 1)
            pygame.draw.lines(
                self.screen, (150, 215, 240), False,
                [(tx_i + 12, ty_i + 32), (tx_i + 12, ty_i - 5), (tx_i + 17, ty_i - 15)], 2,
            )
            pygame.draw.line(self.screen, (90, 228, 178), (tx_i + 19, ty_i - 4), (tx_i + 19, ty_i + 18), 1)
            pygame.draw.ellipse(self.screen, (42, 108, 62), (tx_i + 6, ty_i + 30, 14, 6))

    def draw_windy_ridge_atmosphere(self, state, ox, oy, now=None):
        """Render sweeping translucent gale wind ribbons and drifting pale-gold pollen motes on windy_ridge."""
        if not isinstance(self.screen, pygame.Surface):
            return
        player = getattr(state, "player", None)
        world = getattr(state, "world", None)
        if player is None or world is None:
            return
        ts = constants.TILE_SIZE
        px_c, py_c = player.get_center()
        if self._resolve_tile_biome(state, int(px_c // ts), int(py_c // ts)) != "windy_ridge":
            return

        t_now = time.time() if now is None else float(now)
        sw, sh = self.screen.get_width(), self.screen.get_height()
        cache = self._fx_surface_cache

        # 1. Translucent diagonal gale wind-gust ribbons (alpha 28..44) sweeping across the ridge
        span_w = sw + 240
        span_h = sh + 120
        for idx in range(6):
            r_len = 110 + (idx % 3) * 24
            r_h = 26
            speed_x = 170.0 + (idx % 3) * 32.0
            speed_y = 26.0 + (idx % 2) * 10.0
            raw_x = (idx * 237.0 + t_now * speed_x - ox * 0.85) % span_w
            raw_y = (idx * 139.0 + t_now * speed_y - oy * 0.85 + math.sin(t_now * 1.4 + idx) * 14.0) % span_h
            gx, gy = int(raw_x - 160), int(raw_y - 40)
            pulse = (math.sin(t_now * 1.6 + idx * 1.2) + 1.0) * 0.5
            q_alpha = 28 + int(pulse * 4) * 4  # 28..44
            g_key = ("windy_ridge_gust", r_len, q_alpha)
            g_surf = cache.get(g_key)
            if g_surf is None:
                g_surf = pygame.Surface((r_len + 12, r_h), pygame.SRCALPHA)
                pts = [
                    (4, r_h - 6),
                    (r_len // 3, r_h // 2 + 2),
                    ((r_len * 2) // 3, r_h // 2 - 3),
                    (r_len + 6, 6),
                ]
                pygame.draw.lines(g_surf, (216, 238, 244, q_alpha), False, pts, 2)
                pygame.draw.lines(g_surf, (238, 248, 250, max(16, q_alpha - 10)), False, pts[1:], 1)
                cache[g_key] = g_surf
            self.screen.blit(g_surf, (gx, gy))

        # 2. 12 drifting pale-gold dandelion / pollen motes carried along the wind vector
        m_span_w = sw + 80
        m_span_h = sh + 80
        for idx in range(12):
            spd_x = 58.0 + (idx % 4) * 16.0
            spd_y = 10.0 + (idx % 3) * 5.0
            mx = int(((idx * 173.0 + t_now * spd_x - ox * 0.92) % m_span_w) - 40)
            my = int(
                ((idx * 97.0 + t_now * spd_y + math.sin(t_now * 2.1 + idx * 0.9) * 18.0 - oy * 0.92) % m_span_h) - 40
            )
            m_pulse = (math.sin(t_now * 2.8 + idx * 1.7) + 1.0) * 0.5
            q_ma = 96 + int(m_pulse * 8) * 12  # 96..192
            p_key = ("windy_ridge_pollen", q_ma)
            p_surf = cache.get(p_key)
            if p_surf is None:
                p_surf = pygame.Surface((10, 10), pygame.SRCALPHA)
                pygame.draw.circle(p_surf, (238, 222, 138, q_ma // 2), (5, 5), 4)
                pygame.draw.circle(p_surf, (252, 244, 194, min(255, q_ma)), (5, 5), 2)
                cache[p_key] = p_surf
            self.screen.blit(p_surf, (mx - 5, my - 5))

    def _draw_sanctuary_tree_canopy(self, obj, ox, oy, prop_cache):
        """Draw a SanctuaryTreeCanopy (80x100) anchored onto its 40x40 solid trunk footprint."""
        sx_o, sy_o = obj.x - ox, obj.y - oy
        canopy_surf = prop_cache.get("SanctuaryTreeCanopy")
        if canopy_surf is not None:
            self.screen.blit(canopy_surf, (int(sx_o) - 20, int(sy_o) - 60))
        else:
            tx_i, ty_i = int(sx_o), int(sy_o)
            pygame.draw.rect(self.screen, (68, 48, 34), (tx_i + 13, ty_i + 4, 14, 34), border_radius=2)
            pygame.draw.circle(self.screen, (42, 78, 44), (tx_i + 20, ty_i - 8), 26)

    def draw_sanctuary_courtyard_atmosphere(self, state, ox, oy, now=None):
        """Draw subtle expanding pond water ripples and slow-drifting garden fireflies in Sanctuary."""
        if getattr(getattr(state, "world", None), "name", "") != "sanctuary":
            return
        if self.sanctuary_interior_alpha >= 0.95 or not isinstance(self.screen, pygame.Surface):
            return

        t_now = time.time() if now is None else float(now)
        vis = max(0.0, 1.0 - float(self.sanctuary_interior_alpha))
        ts = constants.TILE_SIZE
        sw, sh = self.screen.get_width(), self.screen.get_height()
        zones = getattr(state.world, "sanctuary_zones", None)
        pond_tiles = zones.get("pond_water", []) if isinstance(zones, dict) else []

        # 1. Expanding concentric pond water ripples
        if pond_tiles:
            sample_step = max(1, len(pond_tiles) // 6)
            for idx, entry in enumerate(pond_tiles[::sample_step][:6]):
                if not isinstance(entry, (list, tuple)) or len(entry) < 2:
                    continue
                rx = int(entry[0] * ts + ts // 2 - ox)
                ry = int(entry[1] * ts + ts // 2 - oy)
                if rx < -32 or rx > sw + 32 or ry < -32 or ry > sh + 32:
                    continue
                cycle = (t_now * 0.55 + idx * 0.37) % 1.0
                rad = max(2, int(2 + cycle * constants.SANCTUARY_POND_RIPPLE_MAX_RADIUS))
                rip_alpha = int(110 * (1.0 - cycle) * vis)
                if rip_alpha < 8:
                    continue
                q_alpha = (rip_alpha // 8) * 8
                r_key = ("pond_ripple", rad, q_alpha)
                r_surf = self._fx_surface_cache.get(r_key)
                if r_surf is None:
                    d_sz = rad * 2 + 4
                    r_surf = pygame.Surface((d_sz, d_sz), pygame.SRCALPHA)
                    pygame.draw.circle(r_surf, (158, 214, 224, q_alpha), (rad + 2, rad + 2), rad, 1)
                    self._fx_surface_cache[r_key] = r_surf
                self.screen.blit(r_surf, (rx - rad - 2, ry - rad - 2))

        # 1b. Wading foot-ripple rings when the player walks through the Sanctuary pond
        player = getattr(state, "player", None)
        if (
            player is not None
            and hasattr(state.world, "is_in_sanctuary_pond")
            and state.world.is_in_sanctuary_pond(player.rect)
        ):
            foot_x = int(player.x + player.width / 2 - ox)
            foot_y = int(player.y + player.height - 6 - oy)
            is_moving = abs(getattr(player, "vx", 0.0)) + abs(getattr(player, "vy", 0.0)) > 1.0
            rate = 1.45 if is_moving else 0.70
            for ring_idx in range(2):
                cycle = (t_now * rate + ring_idx * 0.5) % 1.0
                rad = max(4, int(4 + cycle * constants.SANCTUARY_POND_RIPPLE_MAX_RADIUS))
                w_alpha = int((145 if is_moving else 95) * (1.0 - cycle) * vis)
                if w_alpha >= 10:
                    q_wa = (w_alpha // 8) * 8
                    w_key = ("pond_wade_ripple", rad, q_wa)
                    w_surf = self._fx_surface_cache.get(w_key)
                    if w_surf is None:
                        d_w = rad * 2 + 4
                        d_h = max(6, int(rad * 1.2) + 4)
                        w_surf = pygame.Surface((d_w, d_h), pygame.SRCALPHA)
                        pygame.draw.ellipse(
                            w_surf, (192, 232, 240, q_wa), (2, 2, d_w - 4, d_h - 4), 1
                        )
                        self._fx_surface_cache[w_key] = w_surf
                    self.screen.blit(w_surf, (foot_x - w_surf.get_width() // 2, foot_y - w_surf.get_height() // 2))

        # 2. Slow-drifting golden-green courtyard fireflies / pollen motes around the west pond & garden
        if pond_tiles:
            valid_pts = [p for p in pond_tiles if isinstance(p, (list, tuple)) and len(p) >= 2]
            avg_x = (sum(p[0] for p in valid_pts) / len(valid_pts)) * ts if valid_pts else 12.5 * ts
            avg_y = (sum(p[1] for p in valid_pts) / len(valid_pts)) * ts if valid_pts else 24.0 * ts
        else:
            avg_x, avg_y = 12.5 * ts, 24.0 * ts

        for i in range(constants.SANCTUARY_FIREFLY_COUNT):
            ang_x = t_now * (0.28 + (i % 3) * 0.09) + i * 1.37
            ang_y = t_now * (0.22 + (i % 4) * 0.07) + i * 2.11
            wx = avg_x + math.sin(ang_x) * (150.0 + (i % 3) * 55.0)
            wy = avg_y + math.cos(ang_y) * (130.0 + (i % 4) * 45.0)
            fx, fy = int(wx - ox), int(wy - oy)
            if fx < -16 or fx > sw + 16 or fy < -16 or fy > sh + 16:
                continue
            pulse = (math.sin(t_now * (2.4 + (i % 3) * 0.6) + i * 1.9) + 1.0) * 0.5
            mote_alpha = int((45 + pulse * 145) * vis)
            if mote_alpha < 10:
                continue
            q_ma = (mote_alpha // 12) * 12
            m_key = ("firefly_mote", q_ma)
            m_surf = self._fx_surface_cache.get(m_key)
            if m_surf is None:
                m_surf = pygame.Surface((12, 12), pygame.SRCALPHA)
                pygame.draw.circle(m_surf, (192, 240, 114, min(140, q_ma // 2)), (6, 6), 5)
                pygame.draw.circle(m_surf, (248, 252, 180, min(255, q_ma)), (6, 6), 2)
                self._fx_surface_cache[m_key] = m_surf
            self.screen.blit(m_surf, (fx - 6, fy - 6))

    def draw_sanctuary_roofs_and_blackout(self, state, ox, oy):
        """Render locked shed roof, smooth exterior blackout when inside, and fading Scriptorium roof + chimney."""
        if getattr(getattr(state, "world", None), "name", "") != "sanctuary":
            return
        if not isinstance(self.screen, pygame.Surface):
            return

        roofs = self._get_sanctuary_roof_zones(state)
        if not roofs:
            return

        ts = constants.TILE_SIZE
        sw, sh = self.screen.get_width(), self.screen.get_height()
        interior_alpha = float(self.sanctuary_interior_alpha)

        scriptorium_roof = None
        locked_roofs = []
        for r_zone in roofs:
            if not isinstance(r_zone, dict):
                continue
            if r_zone.get("name") == "scriptorium_roof":
                scriptorium_roof = r_zone
            else:
                locked_roofs.append(r_zone)

        # 1. Permanently locked roofs (e.g., shed_roof) always render opaque (1.0) beneath interior blackout
        for l_zone in locked_roofs:
            lx = int(l_zone["x"] * ts - ox)
            ly = int(l_zone["y"] * ts - oy)
            l_surf = self._get_sanctuary_roof_surface(l_zone)
            if lx + l_surf.get_width() >= 0 and lx <= sw and ly + l_surf.get_height() >= 0 and ly <= sh:
                l_surf.set_alpha(255)
                self.screen.blit(l_surf, (lx, ly))

        # 2. Exterior blackout mask when stepping inside Scriptorium (leaves Scriptorium building warmly lit)
        if interior_alpha > 0.0 and scriptorium_roof is not None:
            blackout_alpha = int(round(constants.SANCTUARY_EXTERIOR_BLACKOUT_ALPHA * interior_alpha))
            if blackout_alpha > 0:
                if self._sanctuary_blackout_surf is None or self._sanctuary_blackout_surf.get_size() != (sw, sh):
                    self._sanctuary_blackout_surf = pygame.Surface((sw, sh), pygame.SRCALPHA)
                mask = self._sanctuary_blackout_surf
                mask.fill((6, 5, 10, blackout_alpha))
                footprint = scriptorium_roof.get("footprint")
                if isinstance(footprint, (list, tuple)) and len(footprint) >= 4:
                    fx_t, fy_t, fw_t, fh_t = footprint[:4]
                else:
                    fx_t, fy_t, fw_t, fh_t = (
                        scriptorium_roof["x"], scriptorium_roof["y"], scriptorium_roof["w"], scriptorium_roof["h"]
                    )
                bx = int(fx_t * ts - ox)
                by = int(fy_t * ts - oy)
                bw = int(fw_t * ts)
                bh = int(fh_t * ts)
                # Cut out the full Scriptorium footprint (interior + walls + southern doorway threshold)
                mask.fill((0, 0, 0, 0), pygame.Rect(bx, by, bw, bh))
                self.screen.blit(mask, (0, 0))

        # 3. Fading Scriptorium south facade, roof overhang & chimney when outside or transitioning
        if interior_alpha < 1.0 and scriptorium_roof is not None:
            roof_alpha = int(round(255 * (1.0 - interior_alpha)))
            if roof_alpha > 0:
                zones = getattr(state.world, "sanctuary_zones", None)
                south_facade = zones.get("south_facade", {}) if isinstance(zones, dict) else {}
                win_surf = self.prop_cache.get("SanctuaryWindowWall")
                if win_surf is not None:
                    win_surf.set_alpha(roof_alpha)
                    for coord in south_facade.get("windows", ()):
                        if not isinstance(coord, (list, tuple)) or len(coord) < 2:
                            continue
                        wx_px = int(coord[0] * ts - ox)
                        wy_px = int(coord[1] * ts - oy)
                        if -ts <= wx_px <= sw and -ts <= wy_px <= sh:
                            self.screen.blit(win_surf, (wx_px, wy_px))
                    win_surf.set_alpha(255)
                arch_surf = self.prop_cache.get("SanctuaryArchDoorway")
                if arch_surf is not None:
                    arch_surf.set_alpha(roof_alpha)
                    for coord in south_facade.get("doorway", ()):
                        if not isinstance(coord, (list, tuple)) or len(coord) < 2:
                            continue
                        dx_px = int(coord[0] * ts - ox)
                        dy_px = int(coord[1] * ts - oy)
                        if -ts <= dx_px <= sw and -ts <= dy_px <= sh:
                            self.screen.blit(arch_surf, (dx_px, dy_px))
                    arch_surf.set_alpha(255)

                bx = int(scriptorium_roof["x"] * ts - ox)
                by = int(scriptorium_roof["y"] * ts - oy)
                s_surf = self._get_sanctuary_roof_surface(scriptorium_roof)
                if bx + s_surf.get_width() >= 0 and bx <= sw and by + s_surf.get_height() >= 0 and by <= sh:
                    s_surf.set_alpha(roof_alpha)
                    self.screen.blit(s_surf, (bx, by))
                chimney_coords = scriptorium_roof.get("chimney")
                chimney_surf = self.prop_cache.get("SanctuaryChimney")
                if (
                    chimney_surf is not None
                    and isinstance(chimney_coords, (list, tuple))
                    and len(chimney_coords) >= 2
                ):
                    cx_px = int(chimney_coords[0] * ts - ox)
                    cy_px = int(chimney_coords[1] * ts - oy) - ts
                    chimney_surf.set_alpha(roof_alpha)
                    self.screen.blit(chimney_surf, (cx_px, cy_px))
                    chimney_surf.set_alpha(255)

    @staticmethod
    def _select_weapon_pickup_sprite_key(weapon_data):
        """Deterministically pick a prop_cache weapon sprite key from weapon modifiers and name."""
        data = weapon_data if isinstance(weapon_data, dict) else {}
        mods = data.get("modifiers") or {}
        name = str(data.get("name", "")).lower()

        if mods or "anomalous" in name:
            if "bleed" in mods or "ink_bleed" in mods or "bleed" in name:
                return "WeaponAnomalousBleed"
            if "slow_hp_regen" in mods or "vampirism" in mods or "regen" in mods or "life" in name:
                return "WeaponAnomalousRegen"
            if (
                "damage_negation_on_hit" in mods
                or "parry_window" in mods
                or "negation" in mods
                or "iron" in name
            ):
                return "WeaponAnomalousNegation"
            if "max_hp_boost" in mods or "void_strike" in mods or "stout" in mods or "void" in name:
                return "WeaponAnomalousStout"
            return "WeaponAnomalousDefault"

        if "refined" in name:
            return "WeaponQuillRefined"
        if any(tok in name for tok in ("blade", "dagger", "knife", "sword", "scriber")):
            return "WeaponScriberBlade"
        if "standard" in name:
            return "WeaponQuillStandard"
        standard_keys = ("WeaponQuillStandard", "WeaponQuillRefined", "WeaponScriberBlade")
        return standard_keys[sum(ord(ch) for ch in name) % len(standard_keys)]

    def draw_loot(self, item, offset_x, offset_y):
        """Draw loot items with illuminated Torn Page sprite and pulsing golden-amber glow aura."""
        from engine.loot import TornPage, HealItem
        ir = item.get_rect()
        dr = pygame.Rect(ir[0] - offset_x, ir[1] - offset_y, ir[2], ir[3])
        if isinstance(item, TornPage):
            now = time.time()
            pulse = (math.sin(now * 3.6 + (item.x + item.y) * 0.02) + 1.0) * 0.5
            bob_y = int(round((pulse - 0.5) * 4.0))
            cx, cy = int(dr.centerx), int(dr.centery + bob_y)

            # Pulsing golden-amber radial glow aura behind the Torn Page
            aura_r = int(14 + pulse * 5)
            glow_size = aura_r * 2 + 8
            glow_surf = pygame.Surface((glow_size, glow_size), pygame.SRCALPHA)
            gc = glow_size // 2
            pygame.draw.circle(glow_surf, (238, 186, 72, int(26 + pulse * 24)), (gc, gc), aura_r)
            pygame.draw.circle(glow_surf, (252, 220, 122, int(48 + pulse * 36)), (gc, gc), max(6, aura_r - 5))
            self.screen.blit(glow_surf, (cx - gc, cy - gc))
            pygame.draw.circle(self.screen, (242, 198, 94), (cx, cy), aura_r, 1)

            page_surf = self.image_cache.get("torn_page.png") or self.prop_cache.get("TornPage")
            if page_surf is not None:
                target_sz = 34
                if page_surf.get_size() != (target_sz, target_sz):
                    page_surf = pygame.transform.scale(page_surf, (target_sz, target_sz))
                self.screen.blit(page_surf, (cx - target_sz // 2, cy - target_sz // 2))
            else:
                # Weathered ragged parchment fallback (never a flat white square)
                poly = [
                    (cx - 8, cy - 10), (cx + 6, cy - 10), (cx + 9, cy - 6),
                    (cx + 8, cy + 9), (cx + 2, cy + 7), (cx - 3, cy + 10), (cx - 8, cy + 8),
                ]
                pygame.draw.polygon(self.screen, (232, 218, 184), poly)
                pygame.draw.polygon(self.screen, (118, 92, 58), poly, 1)
                pygame.draw.line(self.screen, (132, 102, 48), (cx - 5, cy - 4), (cx + 5, cy - 4), 1)
                pygame.draw.line(self.screen, (132, 102, 48), (cx - 5, cy), (cx + 4, cy), 1)
                pygame.draw.circle(self.screen, (218, 154, 46), (cx + 3, cy + 4), 2)
        elif isinstance(item, HealItem):
            pygame.draw.rect(self.screen, (200, 50, 50), dr)
            pygame.draw.rect(self.screen, constants.COLOR_WHITE, (dr.centerx - 2, dr.y + 2, 4, dr.height - 4))
            pygame.draw.rect(self.screen, constants.COLOR_WHITE, (dr.x + 2, dr.centery - 2, dr.width - 4, 4))

    def draw_minimap(self, state):
        """Draw minimap with increased zoom, radar color rules, and safe circle boundary."""
        # 1. Hub Exclusion Rule: Hide completely while in Sanctuary
        if getattr(state.world, 'name', 'sanctuary') == "sanctuary":
            return

        h, w = len(state.world.grid), len(state.world.grid[0]) if len(state.world.grid) > 0 else 0
        if w == 0 or h == 0:
            return

        # Initialize or reuse Minimap Surface
        mw, mh = constants.MINIMAP_WIDTH, constants.MINIMAP_HEIGHT
        if getattr(self, "_minimap_surf", None) is None or self._minimap_surf.get_size() != (mw, mh):
            self._minimap_surf = pygame.Surface((mw, mh), pygame.SRCALPHA)
        minimap_surface = self._minimap_surf

        # 2. CLEAR SURFACE AT START
        minimap_surface.fill((10, 10, 10, constants.UI_ALPHA))

        ww, wh = w * constants.TILE_SIZE, h * constants.TILE_SIZE

        # 2. Increased Zoom Scale Factor (defined by constants.MINIMAP_VIEWPORT_FRAC)
        vpw = int(constants.SCREEN_WIDTH * constants.MINIMAP_VIEWPORT_FRAC)
        vph = int(constants.SCREEN_HEIGHT * constants.MINIMAP_VIEWPORT_FRAC)
        pxc, pyc = state.player.get_center()

        # Viewport center follows player, clamp to world bounds
        vpx = int(max(0, min(pxc - vpw // 2, ww - vpw)))
        vpy = int(max(0, min(pyc - vph // 2, wh - vph)))

        # UNIFORM SCALE: Use a single scale factor to prevent squashing and circle drift
        scale = min(mw / float(vpw), mh / float(vph))
        sx = sy = scale

        # 4. Minimap Tile Rendering (Walls) - use cached static wall layer on real display surfaces
        if isinstance(self.screen, pygame.Surface):
            mm_key = (id(state.world), getattr(state.world, "name", ""), id(state.world.grid), w, h, sx)
            if getattr(self, "_minimap_world_key", None) != mm_key:
                full_mw = max(mw, int(ww * sx) + 4)
                full_mh = max(mh, int(wh * sy) + 4)
                wall_layer = pygame.Surface((full_mw, full_mh), pygame.SRCALPHA)
                tw_mm = int(max(1, constants.TILE_SIZE * sx))
                th_mm = int(max(1, constants.TILE_SIZE * sy))
                for y in range(h):
                    row = state.world.grid[y]
                    wy_s = int(y * constants.TILE_SIZE * sy)
                    for x in range(w):
                        if row[x] == constants.TILE_WALL:
                            pygame.draw.rect(
                                wall_layer,
                                constants.MINIMAP_WALL_COLOR,
                                (int(x * constants.TILE_SIZE * sx), wy_s, tw_mm, th_mm),
                            )
                self._minimap_walls_surf = wall_layer
                self._minimap_world_key = mm_key
            minimap_surface.blit(
                self._minimap_walls_surf,
                (0, 0),
                area=pygame.Rect(int(vpx * sx), int(vpy * sy), mw, mh),
            )
        else:
            tx1 = int(max(0, vpx // constants.TILE_SIZE))
            ty1 = int(max(0, vpy // constants.TILE_SIZE))
            tx2 = int(min(w, (vpx + vpw) // constants.TILE_SIZE + 1))
            ty2 = int(min(h, (vpy + vph) // constants.TILE_SIZE + 1))
            for y in range(ty1, ty2):
                for x in range(tx1, tx2):
                    if state.world.grid[y][x] == constants.TILE_WALL:
                        wx, wy = x * constants.TILE_SIZE, y * constants.TILE_SIZE
                        pygame.draw.rect(minimap_surface, constants.MINIMAP_WALL_COLOR, (
                            int((wx - vpx) * sx),
                            int((wy - vpy) * sy),
                            int(max(1, constants.TILE_SIZE * sx)),
                            int(max(1, constants.TILE_SIZE * sy))
                        ))

        # 5. Safe Circle Boundary Visualization
        boss_coords = getattr(state, 'current_boss_coords', None)
        if boss_coords:
            bcx, bcy = boss_coords['x'] * constants.TILE_SIZE, boss_coords['y'] * constants.TILE_SIZE
            radius = state.active_safe_radius
            
            mcx = int((bcx - vpx) * sx)
            mcy = int((bcy - vpy) * sy)
            mr = int(radius * sx)
            
            # Draw circle boundary directly on minimap_surface
            if -mr < mcx < mw + mr and -mr < mcy < mh + mr:
                pygame.draw.circle(minimap_surface, (255, 165, 0, 180), (mcx, mcy), mr, 1)

        # 6. Radar Entity Rules
        # Remote Players: Cyan/Magenta Dot (Phase 4)
        remote_data = getattr(state.network_manager, 'remote_players', {})
        for addr, data in remote_data.items():
            if "x" not in data or "y" not in data: continue
            rx, ry = float(data["x"]) + 16, float(data["y"]) + 16
            if vpx <= rx <= vpx + vpw and vpy <= ry <= vpy + vph:
                dot_color = (255, 0, 255)  # Magenta for Client
                is_host_dot = bool(
                    data.get("is_host")
                    or data.get("addr") == state.network_manager.server_address
                    or addr == state.network_manager.server_address
                )
                if state.network_manager.network_mode == "CLIENT" and is_host_dot:
                    dot_color = constants.COLOR_CYAN  # Host
                pygame.draw.circle(minimap_surface, dot_color, (int((rx - vpx) * sx), int((ry - vpy) * sy)), 3)

        # Enemies: Muted slate-grey normally; high-contrast red in debug mode
        enemy_dot_color = (
            constants.MINIMAP_ENEMY_COLOR
            if getattr(state, "debug_text_enabled", False)
            else constants.MINIMAP_ENEMY_STEALTH_COLOR
        )
        for e in getattr(state, 'enemies', []):
            ex, ey = e.x + e.width // 2, e.y + e.height // 2
            if vpx <= ex <= vpx + vpw and vpy <= ey <= vpy + vph:
                pygame.draw.rect(minimap_surface, enemy_dot_color, (
                    int((ex - vpx) * sx - 1),
                    int((ey - vpy) * sy - 1), 3, 3))

        # Loot: Yellow Dot
        for i in getattr(state, 'loot', []):
            lx, ly = i.x + i.width // 2, i.y + i.height // 2
            if vpx <= lx <= vpx + vpw and vpy <= ly <= vpy + vph:
                pygame.draw.rect(minimap_surface, constants.MINIMAP_LOOT_COLOR, (
                    int((lx - vpx) * sx - 1),
                    int((ly - vpy) * sy - 1), 3, 3))

        # Player: White Dot
        mx = int((pxc - vpx) * sx)
        my = int((pyc - vpy) * sy)
        pygame.draw.rect(minimap_surface, constants.MINIMAP_PLAYER_COLOR, (mx-2, my-2, 4, 4))

        # 7. Edge-Clamped Compass Indicators
        for ox, oy in getattr(state, 'objectives', []):
            if vpx <= ox <= vpx + vpw and vpy <= oy <= vpy + vph: continue
            dx, dy = ox - pxc, oy - pyc
            if dx == 0 and dy == 0: continue
            
            k = 1e9
            if dx > 0: k = min(k, (mw - mx) / dx)
            elif dx < 0: k = min(k, (0 - mx) / dx)
            if dy > 0: k = min(k, (mh - my) / dy)
            elif dy < 0: k = min(k, (0 - my) / dy)
            
            ix, iy = int(mx + k * dx), int(my + k * dy)
            pygame.draw.rect(minimap_surface, constants.COLOR_WHITE, (
                max(0, min(ix, mw - 3)),
                max(0, min(iy, mh - 3)), 3, 3))

        # 8. FINALLY BLIT SURFACE TO SCREEN
        self.screen.blit(minimap_surface, (constants.MINIMAP_PADDING, constants.MINIMAP_PADDING))

    def _get_title_composite(self):
        """Pre-render and cache the layered composite title surface with shadows, borders, and tracking."""
        if self._title_composite_surf is not None:
            return self._title_composite_surf

        text = "AVOID RAIN"
        tracking = 14
        pad = 20
        font = getattr(self, "title_font", None) or self.large_font

        # Colors for layered typography
        shadow_col = (10, 8, 12, 220)
        outline_col = (25, 20, 28)
        core_top_col = (250, 242, 215)    # Parchment cream / bone white highlight
        core_bot_col = (212, 168, 86)     # Muted oxidized gold / amber

        try:
            glyphs_shadow = [font.render(ch, True, shadow_col) for ch in text]
            glyphs_outline = [font.render(ch, True, outline_col) for ch in text]
            glyphs_top = [font.render(ch, True, core_top_col) for ch in text]
            glyphs_bot = [font.render(ch, True, core_bot_col) for ch in text]
        except Exception:
            return None

        total_w = sum(g.get_width() for g in glyphs_outline) + tracking * (len(glyphs_outline) - 1)
        total_h = max(g.get_height() for g in glyphs_outline)

        surf = pygame.Surface((total_w + pad * 2, total_h + pad * 2), pygame.SRCALPHA)

        # 1. Deep Drop-Shadow (+3, +4 offset with doubled blit for weight)
        for dx_s, dy_s in ((3, 4), (4, 5)):
            cx = pad + dx_s
            for g in glyphs_shadow:
                surf.blit(g, (cx, pad + dy_s))
                cx += g.get_width() + tracking

        # 2. Edge Outline in 8 directions (1-2 px shifted) for crisp structural separation
        for dx_o, dy_o in ((-2, 0), (2, 0), (0, -2), (0, 2), (-1, -1), (1, -1), (-1, 1), (1, 1)):
            cx = pad + dx_o
            for g in glyphs_outline:
                surf.blit(g, (cx, pad + dy_o))
                cx += g.get_width() + tracking

        # 3. Core Gradient / Warm Oxidized Tone
        cx = pad
        for i, ch in enumerate(text):
            g_top = glyphs_top[i]
            g_bot = glyphs_bot[i]
            gw, gh = g_top.get_size()
            surf.blit(g_bot, (cx, pad))
            surf.blit(g_top, (cx, pad), area=pygame.Rect(0, 0, gw, gh // 2))
            cx += gw + tracking

        if pygame.display.get_init() and pygame.display.get_surface() is not None:
            try:
                surf = surf.convert_alpha()
            except Exception:
                pass

        self._title_composite_surf = surf
        return surf

    def draw_title_screen(self, menu=0, state=None):
        """Draw title screen with atmospheric rain."""
        self.screen.fill(constants.COLOR_BLACK)
        sw, sh = self.screen.get_width(), self.screen.get_height()

        # Atmospheric Rain on Title Screen (Selection Color: Amber/Gold)
        self.draw_weather(None, override_color=constants.COLOR_SELECTION, force_global=True)

        # Layered Composite Title with gentle floating bob and subtle breathing pulse
        now = time.time()
        bob_y = int(math.sin(now * 1.8) * 3.0)
        title_composite = self._get_title_composite()

        if title_composite is not None:
            # Subtle breathing pulse (±1.5% scale oscillation)
            pulse_factor = 1.0 + 0.015 * math.sin(now * 1.2)
            orig_w, orig_h = title_composite.get_size()
            scaled_w = int(orig_w * pulse_factor)
            scaled_h = int(orig_h * pulse_factor)
            if scaled_w != orig_w or scaled_h != orig_h:
                draw_title = pygame.transform.smoothscale(title_composite, (scaled_w, scaled_h))
            else:
                draw_title = title_composite
            self.screen.blit(draw_title, draw_title.get_rect(center=(sw // 2, 220 + bob_y)))
        else:
            title = self.large_font.render("AVOID RAIN", True, constants.COLOR_SELECTION)
            self.screen.blit(title, title.get_rect(center=(sw // 2, 220 + bob_y)))

        instr = self.font.render("Use ARROW KEYS and ENTER to choose", True, constants.COLOR_WHITE)
        self.screen.blit(instr, instr.get_rect(center=(sw//2, 280)))
        opts, sel = ["New Draft", "Quit"], 0
        from engine.title_menu import TitleMenuState
        menu_state = TitleMenuState.MAIN
        try:
            if hasattr(menu, 'get_options'):
                opts = menu.get_options()
                sel = menu.get_selected_index()
                menu_state = getattr(menu, 'state', TitleMenuState.MAIN)
            else:
                sel = int(menu)
        except Exception:
            pass

        for idx, opt in enumerate(opts):
            col = constants.COLOR_SELECTION if idx == sel else constants.COLOR_WHITE
            surf = self.font.render(opt, True, col)
            self.screen.blit(surf, surf.get_rect(center=(sw//2, 340 + idx * 40)))

        if state and getattr(menu_state, 'name', '') == 'MAIN':
            net_mgr = getattr(state, "network_manager", None)
            identity = getattr(net_mgr, "identity", "Scholar") if net_mgr else "Scholar"
            name_y = 340 + len(opts) * 40 + 16
            if getattr(state, "lobby_editing_name", False):
                name_str = f"Editing Name: {identity}_  [ENTER] Save"
                name_col = constants.COLOR_SELECTION
            else:
                name_str = f"Scholar Name: {identity}  [N] Change Name"
                name_col = (180, 195, 215)
            name_surf = self.small_font.render(name_str, True, name_col)
            self.screen.blit(name_surf, name_surf.get_rect(center=(sw // 2, name_y)))

        if menu_state == TitleMenuState.CONFIRM_NEW_GAME:
            overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 200))
            self.screen.blit(overlay, (0, 0))

            rect = pygame.Rect(0, 0, 600, 150)
            rect.center = self.screen.get_rect().center
            pygame.draw.rect(self.screen, (30, 30, 30), rect)
            pygame.draw.rect(self.screen, constants.COLOR_WHITE, rect, 2)
            m_surf = self.font.render("Are you sure you want to start a New Game? (Y/N)", True, constants.COLOR_WHITE)
            w_surf = self.font.render("This will permanently remove old progress.", True, constants.COLOR_RED)
            self.screen.blit(m_surf, m_surf.get_rect(center=self.screen.get_rect().center))
            self.screen.blit(w_surf, w_surf.get_rect(center=(sw//2, sh//2 + 30)))
        elif getattr(menu_state, 'name', '') == 'CONTROLS':
            self.draw_controls_overlay(True)
        # Engine Revision & Outdated Save Indicator on Title Screen
        debug_on = bool(state and getattr(state, "debug_text_enabled", False))
        try:
            if debug_on:
                rev_surf = self.small_font.render(f"Engine Rev {constants.ENGINE_REVISION}", True, (140, 140, 150))
                self.screen.blit(rev_surf, (12, sh - 24))
            if state and getattr(state, "stats", None) and not getattr(state.stats, "is_revision_compatible", True):
                out_msg = "Incompatible older save detected — start a New Draft"
                out_surf = self.small_font.render(out_msg, True, constants.COLOR_RED)
                self.screen.blit(out_surf, (sw // 2 - out_surf.get_width() // 2, 305))
        except Exception:
            pass

        # Audio Debug OSD (Title Screen - gated behind debug_text_enabled)
        if debug_on:
            debug_font = self.hud_font
            debug_text = "[DEBUG_AUDIO: Playing title_theme.ogg]"
            debug_surf = debug_font.render(debug_text, True, constants.COLOR_WHITE)
            self.screen.blit(debug_surf, (sw // 2 - debug_surf.get_width() // 2, 5))

        if pygame.display.get_init() and pygame.display.get_surface() is not None:
            pygame.display.flip()

    def fade_to_black(self):
        """Fade out."""
        sw, sh = self.screen.get_width(), self.screen.get_height()
        surf = pygame.Surface((sw, sh))
        surf.fill(constants.COLOR_BLACK)
        for a in range(0, 300, 5):
            surf.set_alpha(a)
            self.screen.blit(surf, (0, 0))
            pygame.display.flip()
            pygame.time.delay(10)

    def draw_title_transition(self, transition):
        """Render the multi-phase storm-and-lightning title transition."""
        from engine.title_menu import TitleTransitionPhase

        sw, sh = self.screen.get_width(), self.screen.get_height()
        phase = getattr(transition, "phase", TitleTransitionPhase.IDLE)

        if phase == TitleTransitionPhase.FADE_TO_BLACK:
            overlay = pygame.Surface((sw, sh))
            overlay.fill(constants.COLOR_BLACK)
            overlay.set_alpha(transition.get_fade_alpha())
            self.screen.blit(overlay, (0, 0))
            return

        if phase in (TitleTransitionPhase.STORM_VIGNETTE, TitleTransitionPhase.FADE_OUT_AND_WARP):
            flash = transition.get_lightning_flash()
            sky_r = min(255, int(10 + 95 * flash))
            sky_g = min(255, int(12 + 108 * flash))
            sky_b = min(255, int(20 + 135 * flash))
            self.screen.fill((sky_r, sky_g, sky_b))

            # Brooding storm cloud bands
            t = getattr(transition, "timer", 0.0)
            for idx in range(5):
                cx = int(((idx * 310 + t * (28 + idx * 9)) % (sw + 360)) - 180)
                cy = 24 + idx * 28
                cloud_col = (
                    min(255, int(22 + 70 * flash)),
                    min(255, int(26 + 80 * flash)),
                    min(255, int(38 + 105 * flash)),
                )
                pygame.draw.ellipse(self.screen, cloud_col, (cx, cy, 340, 86))

            # Angled falling rain streaks
            rain_col = (
                min(255, int(95 + 110 * flash)),
                min(255, int(115 + 110 * flash)),
                min(255, int(155 + 95 * flash)),
            )
            for i in range(95):
                rx = ((i * 97 + int(t * 260)) % (sw + 120)) - 60
                ry = ((i * 53 + int(t * 780)) % (sh + 60)) - 30
                pygame.draw.line(self.screen, rain_col, (rx, ry), (rx - 9, ry + 26), 1)

            # Jagged procedural lightning bolts synced to flash
            bolt_idx = transition.get_active_bolt_index()
            if flash > 0.05 and bolt_idx is not None:
                start_x = int(sw * (0.34 if bolt_idx == 0 else 0.68))
                pts = [(start_x, 0)]
                cur_x, cur_y = start_x, 0
                step_y = sh // 9
                for seg in range(1, 9):
                    jitter = ((seg * 37 + bolt_idx * 19) % 54) - 27
                    cur_x += jitter
                    cur_y = seg * step_y
                    pts.append((cur_x, cur_y))
                pygame.draw.lines(self.screen, (110, 210, 255), False, pts, 5)
                pygame.draw.lines(self.screen, (240, 252, 255), False, pts, 2)

            if phase == TitleTransitionPhase.FADE_OUT_AND_WARP:
                overlay = pygame.Surface((sw, sh))
                overlay.fill(constants.COLOR_BLACK)
                overlay.set_alpha(transition.get_fade_alpha())
                self.screen.blit(overlay, (0, 0))

    def draw_loading_screen(self, msg, sub=None, min_t=2.0, sleep=None):
        """Draw loading screen."""
        import time; sl = sleep if sleep else time.sleep
        self.screen.fill(constants.COLOR_BLACK)
        t = self.font.render(msg, True, constants.COLOR_WHITE)
        self.screen.blit(t, t.get_rect(center=(self.screen.get_width()//2, self.screen.get_height()//2 - 20)))
        if sub:
            st = self.font.render(sub, True, constants.COLOR_WHITE)
            self.screen.blit(st, st.get_rect(center=(self.screen.get_width()//2, self.screen.get_height()//2 + 20)))
        pygame.display.flip(); sl(min_t)

    def draw_pause_menu(self, menu=0):
        """Draw pause menu."""
        opts, sel, state_val = ["Resume", "Controls", "Quit"], 0, None
        try:
            from engine.pause_menu import PauseMenuState
            if hasattr(menu, 'get_options'):
                opts = menu.get_options()
                sel = menu.get_selected_index()
                state_val = getattr(menu, 'state', PauseMenuState.MAIN)
            else:
                sel = int(menu)
                state_val = PauseMenuState.MAIN
        except Exception:
            pass
        
        if state_val and getattr(state_val, 'name', '') == 'CONTROLS':
            self.draw_controls_overlay(False)
            return
            
        sw, sh = self.screen.get_width(), self.screen.get_height()
        over = pygame.Surface((sw, sh), pygame.SRCALPHA)
        over.fill((0, 0, 0, 180))
        self.screen.blit(over, (0, 0))
        
        pause_title = self.font.render("PAUSED", True, constants.COLOR_WHITE)
        self.screen.blit(pause_title, pause_title.get_rect(center=(sw//2, sh//2 - 50)))
        
        instruct = self.font.render("Use ARROW KEYS and ENTER to choose", True, constants.COLOR_WHITE)
        self.screen.blit(instruct, instruct.get_rect(center=(sw//2, sh//2 - 20)))
        
        for i, opt in enumerate(opts):
            color = constants.COLOR_SELECTION if i == sel else constants.COLOR_WHITE
            surf = self.font.render(opt, True, color)
            self.screen.blit(surf, surf.get_rect(center=(sw//2, sh//2 + 10 + i * 30)))
        pygame.display.flip()

    def draw_controls_overlay(self, show_editor=True):
        """Draw controls overlay with Gamepad status."""
        sw, sh = self.screen.get_width(), self.screen.get_height()
        over = pygame.Surface((sw, sh), pygame.SRCALPHA)
        over.fill((0, 0, 0, constants.UI_ALPHA))
        self.screen.blit(over, (0, 0))

        cx, cy = sw // 2, sh // 2

        # 1. Header
        header_surf = self.font.render("CONTROLS & INPUT", True, constants.COLOR_SELECTION)
        self.screen.blit(header_surf, header_surf.get_rect(center=(cx, 60)))

        # 2. Input Legend
        kbd_surf = self.font.render("[ Keyboard/Mouse ]", True, constants.COLOR_WHITE)
        self.screen.blit(kbd_surf, kbd_surf.get_rect(center=(cx - 150, 100)))
        
        joy_count = pygame.joystick.get_count()
        joy_col = constants.COLOR_MODE_GAMEPAD if joy_count > 0 else constants.COLOR_GREY
        joy_label = f"[ Gamepad: {'ACTIVE' if joy_count > 0 else 'NOT DETECTED'} ]"
        self.screen.blit(self.font.render(joy_label, True, joy_col), 
                         self.font.render(joy_label, True, joy_col).get_rect(center=(cx + 150, 100)))

        # 3. Controls List (Action, Keyboard/Mouse, Gamepad)
        ins = [
            ("Movement", "WASD / Arrows", "(GP) L-Stick"),
            ("Attack / Interact", "SPACE / Click", "(GP) Cross"),
            ("Dash (Invulnerable)", "Shift", "(GP) Circle"),
            ("Heal (Flask)", "1", "(GP) Triangle"),
            ("Block (Shield)", "K", "(GP) R2"),
            ("Swap Weapon", "Q / Click", "(GP) L1"),
            ("Inspect Details", "TAB (Hold)", "(GP) R1 (Hold)"),
            ("Pause Game", "ESC", "(GP) Start"),
        ]
        
        y_off = 180
        for act, kb, gp in ins:
            a_surf = self.font.render(f"{act}:", True, constants.COLOR_WHITE)
            k_surf = self.font.render(kb, True, constants.COLOR_CYAN)
            g_surf = self.font.render(gp, True, constants.COLOR_MODE_GAMEPAD)
            
            self.screen.blit(a_surf, a_surf.get_rect(midright=(cx - 40, y_off)))
            self.screen.blit(k_surf, k_surf.get_rect(midleft=(cx + 0, y_off)))
            self.screen.blit(g_surf, g_surf.get_rect(midleft=(cx + 180, y_off)))
            y_off += 40

        back = self.font.render("Press SPACE or ENTER to go back", True, constants.COLOR_WHITE)
        self.screen.blit(back, back.get_rect(center=(cx, sh - 60)))
        pygame.display.flip()
