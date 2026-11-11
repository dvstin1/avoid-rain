# pylint: disable=too-many-locals,too-many-branches,too-many-statements,no-member
# pylint: disable=import-outside-toplevel,redefined-outer-name,reimported,invalid-name
# pylint: disable=unused-argument,unused-import,wrong-import-order,too-many-public-methods
# pylint: disable=attribute-defined-outside-init,broad-exception-caught,multiple-statements
# pylint: disable=unused-variable

import math
import random
import time

import pygame

import constants
from engine.player import PlayerStateEnum
from engine.camera import Camera
from ui.menu import draw_respite_menu
from ui.lobby_menu import draw_lobby_menu

class Renderer:
    """Coordinates rendering of the game state."""
    def __init__(self, screen):
        self.screen = screen
        self.font = pygame.font.SysFont("Arial", 24)
        self.small_font = pygame.font.SysFont("Arial", 14)
        self.large_font = pygame.font.SysFont("Arial", 32)
        self.hud_font = pygame.font.SysFont("Arial", 14, bold=True)
        self.slot_font = pygame.font.SysFont("Arial", 12)
        self.bloom_font = pygame.font.SysFont("Times New Roman", 72, bold=True, italic=True)
        
        # Image Cache
        self.image_cache = {}
        self.prop_cache = {}
        self._chunk_cache = {}
        self._chunk_world_key = None
        self._weather_overlay = None
        self._weather_overlay_dirty = False
        self._hud_surf = None
        self._minimap_surf = None
        self._minimap_walls_surf = None
        self._minimap_world_key = None
        self._load_barrel_assets()
        self._load_tile_assets()
        self._load_slug_assets()
        self.grass_pools = {}
        self._load_grass_assets()
        self._generate_prop_cache()

    def _load_barrel_assets(self):
        """Pre-load barrel animation frames."""
        import os
        base_path = os.path.join("assets", "graphics")
        display_init = pygame.display.get_init()
        
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
        display_init = pygame.display.get_init()
        
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
                    self.image_cache[name] = pygame.transform.scale(img, (48, 48))
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

    def _load_tile_assets(self):
        """Pre-load tile assets like walls and floors."""
        import os
        base_path = os.path.join("assets", "graphics")
        display_init = pygame.display.get_init()
        
        # 1. Brown Wall
        name = "brown_wall.png"
        path = os.path.join(base_path, name)
        if os.path.exists(path):
            try:
                img = pygame.image.load(path)
                if display_init:
                    img = img.convert_alpha()
                scaled_img = pygame.transform.scale(img, (constants.TILE_SIZE, constants.TILE_SIZE))
                try:
                    scaled_img = self._desaturate_surface(scaled_img)
                except Exception as de_err:
                    print(f"[RENDER] Grayscale conversion fallback: {de_err}")
                self.image_cache[name] = scaled_img
            except Exception as e:
                print(f"[RENDER] Error loading {name}: {e}")

        # 2. Floor Tile
        name = "tile_floor.png"
        path = os.path.join(base_path, name)
        if os.path.exists(path):
            try:
                img = pygame.image.load(path)
                if display_init:
                    img = img.convert_alpha()
                self.image_cache[name] = pygame.transform.scale(img, (constants.TILE_SIZE, constants.TILE_SIZE))
            except Exception as e:
                print(f"[RENDER] Error loading {name}: {e}")

        self.biome_tiles = {}
        self._generate_biome_tile_cache()

    def _generate_biome_tile_cache(self):
        """Procedurally generate seamless base floor and wall surfaces per biome."""
        ts = constants.TILE_SIZE
        display_init = pygame.display.get_init() and pygame.display.get_surface() is not None
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
            for _s_idx, (s_base, _s_alt) in enumerate(strata_defs):
                tier_variants = []
                for _v in range(4):
                    # Borderless base surface so adjacent tiles of the same stratum blend seamlessly
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

        # Populate default cache keys with windy_ridge procedural surfaces
        self.image_cache["brown_wall.png"] = self.biome_tiles["windy_ridge"]["wall_front"]
        self.image_cache["tile_floor.png"] = self.biome_tiles["windy_ridge"]["floors"][0]

    def _resolve_tile_biome(self, state, tx, ty):
        """Determine the biome key for tile coordinates (tx, ty)."""
        w_name = getattr(state.world, "name", "sanctuary").lower()
        if w_name == "sanctuary":
            return "sanctuary"
        for key in ("windy_ridge", "pastoral_valley", "swamp_mire", "frozen_peaks", "tech_tower"):
            if key in w_name:
                return key
        if any(k in w_name for k in ("ruins", "final_boss", "boss")):
            return "tech_tower"

        resolved = None
        for sock in getattr(state.world, "module_sockets", []):
            b = sock.get("bounds", {})
            bx, by, bw, bh = b.get("x", 0), b.get("y", 0), b.get("width", 0), b.get("height", 0)
            if bx <= tx < bx + bw and by <= ty < by + bh:
                plug = sock.get("active_plug", "").lower()
                if "pastoral" in plug or "valley" in plug or "meadow" in plug:
                    resolved = "pastoral_valley"
                elif "swamp" in plug or "mire" in plug:
                    resolved = "swamp_mire"
                elif "frozen" in plug or "peak" in plug:
                    resolved = "frozen_peaks"
                elif any(k in plug for k in ("tech", "tower", "gantry", "ruins", "boss")):
                    resolved = "tech_tower"
                else:
                    resolved = "windy_ridge"
                break

        if resolved:
            return resolved
        sector = ((tx // 40) + (ty // 40)) % 5
        return ("windy_ridge", "pastoral_valley", "swamp_mire", "frozen_peaks", "tech_tower")[sector]

    def _load_grass_assets(self):
        """Generate lightweight procedural grass tuft surfaces in RAM (no PNG pixmap loading)."""
        self.grass_pools = {"small": [], "medium": [], "tall": []}
        display_init = pygame.display.get_init()
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
        ts = constants.TILE_SIZE
        display_init = pygame.display.get_init()

        # 1. Structure (Stylized Deciduous Tree)
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

        # 2. Inkwell Puddle (Recessed Tar / Poison Swamp Pool)
        puddle = pygame.Surface((ts, ts), pygame.SRCALPHA)
        pcx, pcy = ts // 2, ts // 2
        pygame.draw.circle(puddle, (16, 8, 24), (pcx, pcy), ts // 2 - 1)
        pygame.draw.circle(puddle, (58, 26, 82), (pcx - 4, pcy - 2), ts // 3 + 2)
        pygame.draw.circle(puddle, (58, 26, 82), (pcx + 5, pcy + 3), ts // 3 + 1)
        pygame.draw.circle(puddle, (28, 12, 42), (pcx, pcy), ts // 3)
        self.prop_cache["Inkwell Puddle"] = puddle.convert_alpha() if display_init else puddle

        # 3. Rock (Faceted Slate/Ice Boulder)
        rock = pygame.Surface((ts, ts), pygame.SRCALPHA)
        pygame.draw.circle(rock, (68, 88, 118), (ts // 2, ts // 2 + 2), ts // 2 - 3)
        pygame.draw.circle(rock, (135, 185, 225), (ts // 2 - 4, ts // 2 - 3), ts // 4)
        pygame.draw.line(rock, (220, 245, 255), (10, 12), (ts // 2, 8), 2)
        self.prop_cache["Rock"] = rock.convert_alpha() if display_init else rock

        # 4. Heavy Bookcase (80x40)
        bw, bh = ts * 2, ts
        bk = pygame.Surface((bw, bh), pygame.SRCALPHA)
        pygame.draw.rect(bk, (68, 46, 34), (0, 0, bw, bh), border_radius=3)
        pygame.draw.rect(bk, (140, 105, 65), (0, 0, bw, 5))
        pygame.draw.line(bk, (30, 20, 14), (2, bh // 2), (bw - 2, bh // 2), 2)
        for sx_off in range(6, bw - 6, 8):
            col = (0, 210, 240) if (sx_off // 8) % 2 == 0 else (225, 75, 175)
            pygame.draw.rect(bk, col, (sx_off, 8, 5, bh // 2 - 10))
        self.prop_cache["Heavy Bookcase"] = bk.convert_alpha() if display_init else bk

        # 5. Ink Urn (40x40)
        urn = pygame.Surface((ts, ts), pygame.SRCALPHA)
        pygame.draw.circle(urn, (52, 74, 112), (ts // 2, ts // 2 + 3), ts // 2 - 4)
        pygame.draw.circle(urn, (110, 175, 230), (ts // 2 - 4, ts // 2), 4)
        pygame.draw.rect(urn, (190, 165, 105), (8, 4, ts - 16, 6), border_radius=2)
        pygame.draw.circle(urn, (0, 240, 255), (ts // 2, 7), 3)
        self.prop_cache["Ink Urn"] = urn.convert_alpha() if display_init else urn

        # 6. Candelabra Glow Halo (60x60)
        glow_r = 30
        glow = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
        pygame.draw.circle(glow, (255, 190, 40, 60), (glow_r, glow_r), glow_r)
        self.prop_cache["CandelabraGlow"] = glow.convert_alpha() if display_init else glow

    def draw_warp(self, warp, offset_x, offset_y):
        """Draw the Warp Point as 'The Chronicle' book on a pedestal."""
        wx, wy, ww, wh = warp.rect
        screen_x = wx - offset_x
        screen_y = wy - offset_y
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
        self.screen.blit(prompt_surf, (px - prompt_surf.get_width() // 2 - offset_x, py - player.height - 20 - offset_y))

    def draw_wellspring(self, wellspring, offset_x, offset_y):
        """Draw the Wellspring fountain with animated water lines."""
        ox, oy, ow, oh = wellspring.rect
        screen_x, screen_y = ox - offset_x, oy - offset_y
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
            color, border = (60, 60, 80) if i == choice["selected_index"] else (40, 40, 40), constants.COLOR_SELECTION if i == choice["selected_index"] else constants.COLOR_GREY
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

        # 3. Draw a 'Mysterious Barrier' for the circle boundary only if it intersects the screen
        if not force_global and not is_dilution and current_boss_coords:
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
            col = pal["floor_speck"] if s_idx == 0 else pal["floor_accent"]
            pygame.draw.circle(self.screen, col, (sx + 20, sy + 20), rad, 1)
        elif biome == "frozen_peaks":
            glint = int((math.sin(now * 4.5 + x * 1.1 + y * 0.9) + 1.0) * 2.5) + 2
            cx, cy = sx + 18, sy + 18
            pygame.draw.line(self.screen, pal["floor_speck"], (cx - glint, cy), (cx + glint, cy), 1)
            pygame.draw.line(self.screen, pal["floor_speck"], (cx, cy - glint), (cx, cy + glint), 1)
        elif biome == "tech_tower":
            pulse_x = sx + 6 + int(((now * 28.0 + x * 7 + y * 5) % 24))
            col = pal["wall_glow"] if s_idx == 0 else pal["floor_speck"]
            pygame.draw.line(self.screen, col, (pulse_x, sy + 20), (pulse_x + 5, sy + 20), 2)

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

    def _draw_connected_floor_patterns(self, target_surf, biome_info, coords, dr):
        """Draw multi-tile (2x2 80x80px and 4x4 160x160px) connected shapes across same-surface tiles."""
        if not isinstance(target_surf, pygame.Surface):
            return
        biome, pal, s_idx, s_alt = biome_info
        x, y, _, _ = coords
        sx, sy, ts, _ = int(dr[0]), int(dr[1]), int(dr[2]), int(dr[3])

        prev_clip = target_surf.get_clip()
        target_surf.set_clip(pygame.Rect(sx, sy, ts, ts))

        # 1. 4x4 Macro-Zone Underlay (160x160px continuous contour bands across 16 tiles)
        zx, zy = x // 4, y // 4
        zpx = sx - (x % 4) * ts
        zpy = sy - (y % 4) * ts
        z_style = ((zx * 43 + zy * 71 + s_idx * 19) & 0x7FFFFFFF) % 3
        if z_style == 0:
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
            if s_idx == 0:
                # Continuous Sub-Floor Reactor Trench Grating across the entire 80x80 block
                for gy in range(8, 80, 10):
                    target_surf.fill(pal["wall_mortar"], (ax, ay + gy, 80, 5))
                if pat in (0, 2):
                    target_surf.fill(pal["wall_glow"], (ax + 28, ay, 14, 80))
                    target_surf.fill(pal["floor_speck"], (ax + 32, ay, 6, 80))
                else:
                    target_surf.fill(pal["floor_accent"], (ax, ay + 32, 80, 12))
                    pygame.draw.circle(target_surf, pal["wall_glow"], (ax + 40, ay + 38), 16, 3)
            elif s_idx == 2:
                # Continuous High-Voltage Data-Bus Walkway
                target_surf.fill(pal["floor_accent"], (ax, ay + 36, 80, 8))
                target_surf.fill(pal["floor_speck"], (ax, ay + 39, 80, 2))
                if pat == 0:
                    target_surf.fill(pal["floor_accent"], (ax + 36, ay, 8, 80))
                    pygame.draw.rect(target_surf, pal["wall_face"], (ax + 24, ay + 24, 32, 32), border_radius=4)
                    pygame.draw.rect(target_surf, pal["wall_glow"], (ax + 30, ay + 30, 20, 20), 2, border_radius=3)
                elif pat == 1:
                    for bx_p in (16, 40, 64):
                        pygame.draw.circle(target_surf, pal["wall_glow"], (ax + bx_p, ay + 40), 5)
            else:
                # Giant 2x2 Bulkhead Hull Plates & Circuit Routing
                if pat == 0:
                    pygame.draw.rect(target_surf, pal["wall_face"], (ax + 4, ay + 4, 72, 72), 2, border_radius=8)
                    pygame.draw.rect(target_surf, pal["floor_accent"], (ax + 26, ay + 26, 28, 28), 1, border_radius=4)
                elif pat == 1:
                    pygame.draw.line(target_surf, pal["floor_accent"], (ax, ay + 24), (ax + 52, ay + 24), 2)
                    pygame.draw.line(target_surf, pal["floor_accent"], (ax + 52, ay + 24), (ax + 52, ay + 80), 2)
                    pygame.draw.line(target_surf, pal["wall_glow"], (ax + 24, ay), (ax + 24, ay + 56), 2)
                    pygame.draw.line(target_surf, pal["wall_glow"], (ax + 24, ay + 56), (ax + 80, ay + 56), 2)
                    pygame.draw.circle(target_surf, pal["floor_speck"], (ax + 52, ay + 24), 4)
                    pygame.draw.circle(target_surf, pal["floor_speck"], (ax + 24, ay + 56), 4)
                elif pat == 2:
                    pygame.draw.circle(target_surf, pal["wall_face"], (ax + 40, ay + 40), 28, 3)
                    pygame.draw.circle(target_surf, pal["wall_glow"], (ax + 40, ay + 40), 18, 1)
                else:
                    pygame.draw.rect(target_surf, pal["wall_face"], (ax + 6, ay + 6, 68, 30), 2, border_radius=4)
                    pygame.draw.rect(target_surf, pal["wall_face"], (ax + 6, ay + 44, 68, 30), 2, border_radius=4)
        elif biome == "swamp_mire":
            if s_idx == 0:
                if pat == 0:
                    pygame.draw.ellipse(target_surf, pal["wall_mortar"], (ax + 8, ay + 12, 64, 56))
                    pygame.draw.ellipse(target_surf, pal["floor_accent"], (ax + 16, ay + 20, 48, 40), 2)
                    pygame.draw.ellipse(target_surf, pal["floor_speck"], (ax + 28, ay + 30, 24, 20), 1)
                elif pat == 1:
                    for r_o in (18, 34, 50):
                        pygame.draw.arc(
                            target_surf, pal["floor_accent"], (ax + 14, ay + r_o, 52, 22), 0.2, 2.9, 2
                        )
                else:
                    pygame.draw.ellipse(target_surf, pal["wall_mortar"], (ax + 12, ay + 18, 56, 44))
                    pygame.draw.circle(target_surf, pal["floor_speck"], (ax + 30, ay + 36), 6, 1)
                    pygame.draw.circle(target_surf, pal["floor_accent"], (ax + 50, ay + 44), 9, 1)
            elif s_idx == 2:
                # Continuous Multi-Tile Timber Boardwalk Planks spanning full 80px width
                for py in range(6, 76, 14):
                    target_surf.fill(pal["wall_top"], (ax, ay + py, 80, 10))
                    target_surf.fill(pal["wall_hi"], (ax, ay + py, 80, 2))
                    joint_x = (py * 3 + bx * 17) % 60 + 10
                    target_surf.fill(pal["wall_mortar"], (ax + joint_x, ay + py, 2, 10))
                if pat == 1:
                    pygame.draw.rect(target_surf, pal["wall_face"], (ax + 16, ay + 16, 48, 48), 3)
            else:
                if pat == 0:
                    pygame.draw.line(target_surf, pal["floor_accent"], (ax + 8, ay + 14), (ax + 72, ay + 66), 3)
                    pygame.draw.line(target_surf, pal["floor_accent"], (ax + 14, ay + 64), (ax + 68, ay + 18), 2)
                    pygame.draw.circle(target_surf, pal["floor_speck"], (ax + 40, ay + 40), 10)
                elif pat == 1:
                    for hx, hy in ((26, 26), (54, 26), (40, 50)):
                        pygame.draw.circle(target_surf, pal["floor_accent"], (ax + hx, ay + hy), 13, 2)
                else:
                    pygame.draw.ellipse(target_surf, pal["floor_accent"], (ax + 14, ay + 22, 52, 36))
                    pygame.draw.ellipse(target_surf, pal["floor_speck"], (ax + 26, ay + 30, 24, 16))
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
        else:
            # windy_ridge & sanctuary: connected highland cobbles, ancient stone rings, and scriptorium inlays
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

        outer_canvas_col = strata_defs[1][0]
        if biome == "pastoral_valley" and s_idx == 0:
            rim_hi = (16, 8, 24)
            rim_lo = (16, 8, 24)
            inner_lip = (58, 26, 82)
        elif biome == "pastoral_valley" and s_idx == 2:
            rim_hi = (224, 192, 134)
            rim_lo = (156, 118, 68)
            inner_lip = (178, 140, 86)
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

    def _draw_static_tile_to_surface(self, target_surf, state, coords, dr):
        """Render the static base, connected multi-tile shapes, perimeter borders, shadows, and grass tufts."""
        x, y, _, _ = coords
        tile = state.world.grid[y][x]
        biome = self._resolve_tile_biome(state, x, y)
        b_pack = getattr(self, "biome_tiles", {}).get(biome) or getattr(self, "biome_tiles", {}).get("windy_ridge")
        pal = constants.BIOME_PALETTES.get(biome, constants.BIOME_PALETTES["windy_ridge"])

        if tile == constants.TILE_WALL:
            self._draw_connected_wall_tile(target_surf, state, coords, dr, (biome, pal))
            return biome, pal, 0

        s_idx = self._get_tile_stratum(state, x, y)
        if b_pack:
            strata_defs = pal.get("strata", [(pal["floor_base"], pal["floor_alt"])] * 3)
            s_base, s_alt = strata_defs[s_idx]
            strata_list = b_pack.get("strata_floors")
            tier_floors = strata_list[s_idx] if strata_list else b_pack["floors"]
            v_idx = (x * 7 + y * 13) % len(tier_floors)
            target_surf.blit(tier_floors[v_idx], (dr[0], dr[1]))

            # 1. Draw multi-tile connected patterns (2x2 80x80px & 4x4 160x160px) across same-surface tiles
            self._draw_connected_floor_patterns(target_surf, (biome, pal, s_idx, s_alt), coords, dr)

            # 2. Draw borders, rims, and rounded corners ONLY on outer perimeter edges against different surfaces
            self._draw_stratum_perimeter_borders(target_surf, state, coords, dr, (biome, pal, s_idx, strata_defs))

            # 3. Cast ambient occlusion drop-shadows from adjacent north/west walls
            sx, sy = int(dr[0]), int(dr[1])
            if y > 0 and state.world.grid[y - 1][x] == constants.TILE_WALL:
                target_surf.blit(b_pack["shadow_n"], (sx, sy))
            if x > 0 and state.world.grid[y][x - 1] == constants.TILE_WALL:
                target_surf.blit(b_pack["shadow_w"], (sx, sy))

            # 4. Stamp procedural grass/thicket tufts directly onto the static tile surface
            if tile in (constants.TILE_GRASS, constants.TILE_THICKET) and getattr(self, "grass_pools", None):
                clusters = getattr(state.world, "grass_decorations", {}).get((x, y), ())
                for pool_key, variant, dx, dy in clusters:
                    pool = self.grass_pools.get(pool_key)
                    if pool:
                        tuft = pool[variant % len(pool)]
                        target_surf.blit(tuft, (sx + 8 + dx, sy + 8 + dy))
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
            pygame.draw.rect(self.screen, (36, 48, 86), dr, border_radius=4)
            pulse_col = (0, 240, 255) if int(time.time() * 4 + x + y) % 2 == 0 else (235, 70, 195)
            pygame.draw.rect(self.screen, pulse_col, (dr[0] + 4, dr[1] + 4, dr[2] - 8, dr[3] - 8), 2, border_radius=3)

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
        if getattr(state, 'shake_timer', 0) > 0:
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
        for obj in getattr(state.world, 'interactables', []):
            sx_o, sy_o = obj.x - ox, obj.y - oy
            if sx_o + obj.width < -64 or sx_o > sw + 64 or sy_o + obj.height < -64 or sy_o > sh + 64:
                continue
            if hasattr(obj, 'target_name'):
                self.draw_warp(obj, ox, oy)
            elif "Respite" in obj.name:
                if not getattr(obj, 'is_active', True):
                    continue
                dr = pygame.Rect(sx_o, sy_o, obj.width, obj.height)
                pygame.draw.rect(self.screen, (20, 40, 60), dr)
                pygame.draw.rect(self.screen, constants.COLOR_CYAN, dr, 2)
                pulse = (math.sin(now * 5) + 1) / 2
                inner_r = int(5 + pulse * 10)
                pygame.draw.circle(self.screen, constants.COLOR_CYAN, (int(dr.centerx), int(dr.centery)), inner_r, 1)
            elif obj.name == "Barrel":
                img = self.image_cache.get("barrel_0.png")
                if img:
                    self.screen.blit(img, (sx_o, sy_o))
                else:
                    pygame.draw.rect(self.screen, (100, 80, 40), (sx_o, sy_o, obj.width, obj.height))
                    pygame.draw.rect(self.screen, (60, 40, 20), (sx_o, sy_o, obj.width, obj.height), 2)
            elif obj.name == "Structure":
                tree_surf = prop_cache.get("Structure")
                if tree_surf is not None:
                    self.screen.blit(tree_surf, (int(sx_o), int(sy_o)))
                else:
                    sx_i, sy_i, sw_o, sh_o = int(sx_o), int(sy_o), int(obj.width), int(obj.height)
                    cx_t, cy_t = sx_i + sw_o // 2, sy_i + sh_o // 2 - 4
                    pygame.draw.circle(self.screen, (22, 44, 28), (cx_t + 2, sy_i + sh_o - 6), sw_o // 3)
                    pygame.draw.rect(self.screen, (28, 16, 8), (cx_t - 7, sy_i + sh_o - 16, 14, 14), border_radius=2)
                    pygame.draw.rect(self.screen, (92, 54, 28), (cx_t - 5, sy_i + sh_o - 15, 10, 12), border_radius=2)
                    pygame.draw.circle(self.screen, (18, 44, 24), (cx_t, cy_t), sw_o // 2 - 1)
                    pygame.draw.circle(self.screen, (38, 126, 62), (cx_t, cy_t + 2), sw_o // 2 - 3)
                    pygame.draw.circle(self.screen, (92, 218, 110), (cx_t - 1, cy_t - 2), sw_o // 2 - 5)
                    pygame.draw.circle(self.screen, (162, 246, 148), (cx_t - 4, cy_t - 6), sw_o // 4)
            elif obj.name == "The Chronicler":
                pygame.draw.rect(self.screen, (220, 220, 220), (sx_o, sy_o, obj.width, obj.height))
                pygame.draw.rect(self.screen, (255, 200, 150), (sx_o + 5, sy_o + 5, obj.width - 10, 10))
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
                stand = (sx_o + obj.width // 2 - 3, sy_o + 10, 6, obj.height - 10)
                pygame.draw.rect(self.screen, constants.COLOR_DARK_GREY, stand)
                pygame.draw.rect(self.screen, constants.COLOR_BLACK, stand, 1)
                glow_surf = prop_cache.get("CandelabraGlow")
                if glow_surf is not None:
                    self.screen.blit(glow_surf, (int(sx_o + obj.width // 2 - 32), int(sy_o + 5 - 32)))
                pygame.draw.rect(
                    self.screen, constants.COLOR_CANDLE_AMBER, (sx_o + obj.width // 2 - 2, sy_o + 4, 4, 6)
                )
            elif obj.name == "Bench":
                pygame.draw.rect(self.screen, (101, 67, 33), (sx_o, sy_o, obj.width, obj.height))
                pygame.draw.rect(self.screen, (60, 40, 20), (sx_o, sy_o + 5, obj.width, 2))
            elif obj.name == "Rock":
                rock_surf = prop_cache.get("Rock")
                if rock_surf is not None:
                    self.screen.blit(rock_surf, (int(sx_o), int(sy_o)))
                else:
                    rx, ry, rw, rh = int(sx_o), int(sy_o), int(obj.width), int(obj.height)
                    pygame.draw.circle(self.screen, (68, 88, 118), (rx + rw // 2, ry + rh // 2 + 2), rw // 2 - 3)
            elif hasattr(obj, 'weapon_data'):
                col = constants.COLOR_PURPLE if "modifiers" in obj.weapon_data else constants.COLOR_WHITE
                pygame.draw.rect(self.screen, col, (sx_o, sy_o, obj.width, obj.height))
                pygame.draw.rect(self.screen, constants.COLOR_BLACK, (sx_o, sy_o, obj.width, obj.height), 1)
                pygame.draw.rect(self.screen, col, (sx_o - 2, sy_o - 2, obj.width + 4, obj.height + 4), 1)
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

        # Local Player Rendering
        self.draw_actor_ghost(state.player, ox, oy, state)

        if state.player.state == PlayerStateEnum.ATTACKING:
            self.draw_player_weapon_attack(state.player, ox, oy)
        for num in state.damage_numbers:
            self.screen.blit(
                self.font.render(str(num['val']), True, num['color']),
                (num['pos'][0] - ox, num['pos'][1] - oy),
            )
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

        # Audio Debug OSD (gated behind debug_text_enabled)
        if audio_manager and getattr(state, "debug_text_enabled", False):
            self.draw_audio_debug(audio_manager)

        if getattr(state, 'active_respite', None):
            draw_respite_menu(self.screen, self.font, state)
        elif getattr(state, 'active_dialogue', None):
            self.draw_dialogue_box(state)
        
        if getattr(state, 'active_choice', None): self.draw_choice_of_fates(state.active_choice)
        if getattr(state, 'death_timer', 0) > 0:
            overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
            overlay.fill((200, 200, 200, 150))
            self.screen.blit(overlay, (0, 0))
            msg = self.font.render("TEXT BLEACHING...", True, constants.COLOR_BLACK)
            self.screen.blit(msg, msg.get_rect(center=(sw//2, sh//2)))

        self.draw_weather(state)
        self.draw_bloom_overlay(state)

        # Phase 4: Network Ghost Rendering
        self.draw_remote_players(state, ox, oy)
        
        # Parry Sparks
        self.draw_parry_effects(state, ox, oy)

        pygame.display.flip()

    def draw_actor_ghost(self, actor, ox, oy, state):
        """Draws sprites or abstract indicators for an actor based on its visual packet."""
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
        sprite = None
        actor_tag = actor.name.lower()
        
        if "slug" in actor_tag:
            # 1. Determine direction (1=Right, 2=Left)
            # Slug frames: 1/3 (Right), 2/4 (Left)
            # Attack frames: attack_1 (Right), attack_2 (Left)
            fx, fy = packet["facing"]
            suffix = "1" if fx >= 0 else "2"
            
            if packet["base"] in ("WIND_UP", "STRIKE"):
                sprite = self.image_cache.get(f"slug_attack_{suffix}.png")
            else:
                # Alternate frames if moving
                if packet["base"] == "RUN":
                    # Swap every 0.3s
                    if int(packet["anim_timer"] * 3) % 2 == 1:
                        suffix = "3" if fx >= 0 else "4"
                sprite = self.image_cache.get(f"slug_{suffix}.png")

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
            
            self.screen.blit(sprite, s_rect)
            
            # Draw persistent overlays on top of sprite
            if packet["posture"] == "STAGGERED":
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
            color = packet.get("color_hint", (100, 100, 100))
            if packet["base"] == "WIND_UP": color = (200, 100, 0) # Orange Telegraph
            elif packet["base"] == "STRIKE": color = constants.COLOR_MARGIN_RED
            elif packet["base"] == "RECOVERY": 
                # Dim the base color
                color = tuple(max(0, c - 50) for c in color)
            elif packet["base"] == "DASH": color = constants.COLOR_CYAN
            elif packet["base"] == "BLOCK": color = (80, 80, 120)

            # Special coloring for local Player if no hint provided
            if not packet.get("color_hint"):
                if hasattr(actor, 'weapons'): color = constants.COLOR_BLUE

            used_procedural = False
            if hasattr(actor, 'weapons'):
                used_procedural = self.draw_procedural_player(actor, draw_rect, packet, color)
            elif self.draw_procedural_enemy(actor, draw_rect, packet, color):
                used_procedural = True
            else:
                pygame.draw.rect(self.screen, color, draw_rect)

        # 3. Universal Posture Layer (Outlines/Decorations)
        if not sprite: # Ghost-only outlines
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
            elif overlay == "PARRY_WINDOW":
                # Glowing blue/white border
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
        """Draw procedural basic-shape graphics for enemies without image sprites."""
        actor_tag = actor.name.lower()
        cx, cy = int(draw_rect.centerx), int(draw_rect.centery)
        w, h = int(draw_rect.width), int(draw_rect.height)
        fx, fy = packet.get("facing", (0.0, 1.0))
        anim_t = float(packet.get("anim_timer", 0.0))
        is_telegraph = packet.get("base") in ("WIND_UP", "STRIKE", "RECOVERY")

        if "bat" in actor_tag:
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

        if "flutter" in actor_tag:
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

        if "bindling" in actor_tag:
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

        if "smear" in actor_tag:
            blob_col = state_color if is_telegraph else constants.COLOR_SMEAR_BLOB
            base_r = max(4, w // 3)
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
            return True

        if "sentry" in actor_tag:
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

        if any(tag in actor_tag for tag in ("miniboss", "scribe", "binder", "boss", "author")):
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

    def draw_procedural_player(self, actor, draw_rect, packet, state_color):
        """Draw the player character as a hooded Scriptorium Scholar with animated stride and gear."""
        cx, cy = int(draw_rect.centerx), int(draw_rect.centery)
        w, h = int(draw_rect.width), int(draw_rect.height)
        fx, fy = packet.get("facing", (1.0, 0.0))
        base_state = packet.get("base", "IDLE")
        now = time.time()

        # 1. Base cloak silhouette (maintains exact draw_rect call for camera offset verification)
        cloak_col = constants.COLOR_PLAYER_CLOAK
        if base_state == "DASH":
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
        is_anomalous = "modifiers" in wpn
        edge_col = constants.COLOR_PURPLE if is_anomalous else constants.COLOR_WEAPON_EDGE

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
        arc_start = base_angle - 1.05
        curr_angle = arc_start + t * 2.10
        reach = constants.SWORD_OFFSET + constants.SWORD_WIDTH * 0.45

        wpn = player.get_active_weapon() if hasattr(player, "get_active_weapon") and player.weapons else {}
        is_anomalous = "modifiers" in wpn
        slash_col = constants.COLOR_PURPLE if is_anomalous else constants.COLOR_CYAN
        edge_col = constants.COLOR_PURPLE if is_anomalous else constants.COLOR_WEAPON_EDGE

        # 1. Layered crescent slash trail behind the active blade angle
        steps = 8
        for i in range(steps):
            a1 = arc_start + (curr_angle - arc_start) * (i / steps)
            a2 = arc_start + (curr_angle - arc_start) * ((i + 1) / steps)
            p1 = (int(cx + math.cos(a1) * reach), int(cy + math.sin(a1) * reach))
            p2 = (int(cx + math.cos(a2) * reach), int(cy + math.sin(a2) * reach))
            pygame.draw.line(self.screen, slash_col, p1, p2, 3)
            in1 = (int(cx + math.cos(a1) * (reach - 8)), int(cy + math.sin(a1) * (reach - 8)))
            in2 = (int(cx + math.cos(a2) * (reach - 8)), int(cy + math.sin(a2) * (reach - 8)))
            pygame.draw.line(self.screen, constants.COLOR_WEAPON_EDGE, in1, in2, 2)

        # 2. Active tapered sword along current swing angle
        hx = cx + math.cos(curr_angle) * 10.0
        hy = cy + math.sin(curr_angle) * 10.0
        tx = cx + math.cos(curr_angle) * (reach + 6.0)
        ty = cy + math.sin(curr_angle) * (reach + 6.0)
        self._draw_tapered_blade((hx, hy), (tx, ty), 5.0, edge_col)

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
            color = (255, 0, 255) # Default Magenta (Client)
            if state.network_manager.network_mode == "CLIENT" and addr == state.network_manager.server_address:
                color = constants.COLOR_CYAN # Host
            
            pygame.draw.circle(self.screen, color, (int(rx + 16), int(ry + 16)), 12)
            pygame.draw.circle(self.screen, constants.COLOR_WHITE, (int(rx + 16), int(ry + 16)), 12, 1)
            
            # Identity Tag
            id_surf = self.small_font.render(name, True, constants.COLOR_WHITE)
            self.screen.blit(id_surf, (rx + 16 - id_surf.get_width() // 2, ry - 15))

    def draw_audio_debug(self, audio):
        """Draw OSD for currently playing music and recent SFX triggers."""
        margin = 10
        y_off = margin
        sw = self.screen.get_width()
        
        # 1. Music Info (Top Center)
        track = audio.current_track if audio.current_track else "None"
        m_surf = self.hud_font.render(f"[ AUDIO_OSD ] MUSIC: {track}", True, (120, 255, 100))
        self.screen.blit(m_surf, (sw // 2 - m_surf.get_width() // 2, y_off))
        
        # 2. Recent SFX (Top Left)
        y_off = margin
        for sfx in audio.recent_sfx:
            alpha = int((sfx['time'] / 2.0) * 255)
            alpha = max(0, min(255, alpha))
            s_surf = self.small_font.render(f"SFX: {sfx['name']}", True, (220, 220, 220))
            s_surf.set_alpha(alpha)
            self.screen.blit(s_surf, (margin, y_off))
            y_off += 18

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
        
        # Shadow / Bloom effect
        shadow_col = (*constants.COLOR_BLOOM_SHADOW, alpha // 2)
        shadow_surf = self.bloom_font.render(text, True, shadow_col)
        bloom_surf.blit(shadow_surf, shadow_surf.get_rect(center=(sw // 2 + 5, sh // 3 + 5)))
        
        # Primary Text
        text_col = (*constants.COLOR_BLOOM_TEXT, alpha)
        text_surf = self.bloom_font.render(text, True, text_col)
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
        prowess_lvl = 1 + (prowess_mod // 5)
        lines.append(self.small_font.render(
            f"Prowess: Lvl {prowess_lvl} (+{prowess_mod} Atk)", True, constants.COLOR_WHITE
        ))
        
        # Fortification Level / modifier
        fort_mod = player.stats.get("max_hp_modifier", 0)
        fort_lvl = 1 + (fort_mod // 10)
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

    def draw_loot(self, item, offset_x, offset_y):
        """Draw loot items."""
        from engine.loot import TornPage, HealItem
        ir = item.get_rect()
        dr = pygame.Rect(ir[0] - offset_x, ir[1] - offset_y, ir[2], ir[3])
        if isinstance(item, TornPage):
            pygame.draw.rect(self.screen, constants.COLOR_WHITE, dr)
            pygame.draw.rect(self.screen, constants.COLOR_SELECTION, dr, 1)
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
                dot_color = (255, 0, 255) # Magenta for Client
                if state.network_manager.network_mode == "CLIENT" and addr == state.network_manager.server_address:
                    dot_color = constants.COLOR_CYAN # Host
                pygame.draw.circle(minimap_surface, dot_color, (int((rx - vpx) * sx), int((ry - vpy) * sy)), 3)

        # Enemies: Red Dot
        for e in getattr(state, 'enemies', []):
            ex, ey = e.x + e.width // 2, e.y + e.height // 2
            if vpx <= ex <= vpx + vpw and vpy <= ey <= vpy + vph:
                pygame.draw.rect(minimap_surface, constants.MINIMAP_ENEMY_COLOR, (
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

    def draw_title_screen(self, menu=0, state=None):
        """Draw title screen with atmospheric rain."""
        self.screen.fill(constants.COLOR_BLACK)
        sw, sh = self.screen.get_width(), self.screen.get_height()

        # Atmospheric Rain on Title Screen (Selection Color: Amber/Gold)
        self.draw_weather(None, override_color=constants.COLOR_SELECTION, force_global=True)

        title = self.large_font.render("AVOID RAIN", True, constants.COLOR_SELECTION)
        instr = self.font.render("Use ARROW KEYS and ENTER to choose", True, constants.COLOR_WHITE)
        self.screen.blit(title, title.get_rect(center=(sw//2, 220)))
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
        elif menu_state == TitleMenuState.LOBBY and state:
            draw_lobby_menu(self.screen, self.font, state)
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
            debug_font = pygame.font.SysFont("Arial", 14, bold=True)
            debug_text = "[DEBUG_AUDIO: Playing title_theme.ogg]"
            debug_surf = debug_font.render(debug_text, True, constants.COLOR_WHITE)
            self.screen.blit(debug_surf, (sw // 2 - debug_surf.get_width() // 2, 5))

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
        self.screen.blit(self.font.render("CONTROLS & INPUT", True, constants.COLOR_SELECTION), 
                         self.font.render("CONTROLS & INPUT", True, constants.COLOR_SELECTION).get_rect(center=(cx, 60)))
        
        # 2. Input Legend
        self.screen.blit(self.font.render("[ Keyboard/Mouse ]", True, constants.COLOR_WHITE), 
                         self.font.render("[ Keyboard/Mouse ]", True, constants.COLOR_WHITE).get_rect(center=(cx - 150, 100)))
        
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
