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
        self._load_barrel_assets()
        self._load_tile_assets()
        self._load_slug_assets()

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
                self.image_cache[name] = pygame.transform.scale(img, (constants.TILE_SIZE, constants.TILE_SIZE))
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

        # 1. Draw the Safe Circle Boundary
        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        
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
            wb_x, wb_y = current_boss_coords['x'] * constants.TILE_SIZE, current_boss_coords['y'] * constants.TILE_SIZE
        
        rad_sq = radius**2

        for p in self.rain_particles:
            ry = (p['y'] + ticks * p['speed']) % sh
            rx = p['x']
            
            # Distance check: Only draw if OUTSIDE the safe circle
            # Dilution/Title Rule: Rain is global
            is_dilution = getattr(state, 'bleed_state', 'CLEAR') == 'DILUTION'
            
            if is_dilution or force_global:
                pygame.draw.line(overlay, rain_color, (rx, ry), (rx, ry + p['len']), 2)
            elif current_boss_coords:
                world_rx, world_ry = rx + ox, ry + oy
                d_sq = (world_rx - wb_x)**2 + (world_ry - wb_y)**2
                if d_sq > rad_sq:
                    pygame.draw.line(overlay, rain_color, (rx, ry), (rx, ry + p['len']), 2)

        # 3. Draw a 'Mysterious Barrier' for the circle boundary
        if not force_global and getattr(state, 'bleed_state', 'CLEAR') != 'DILUTION' and current_boss_coords:
            bcx, bcy = current_boss_coords['x'] * constants.TILE_SIZE - ox, current_boss_coords['y'] * constants.TILE_SIZE - oy
            if 0 < radius < 30000:
                # Black, 5px wide, 100% opaque (255 alpha)
                pygame.draw.circle(overlay, (0, 0, 0, 255), (int(bcx), int(bcy)), int(radius), 5)

        self.screen.blit(overlay, (0, 0))

    def render(self, state, audio_manager=None):
        """Draw the game state using a camera."""
        bg = constants.COLOR_SEPIA_AMBER if getattr(state.world, 'name', 'sanctuary') == "sanctuary" else constants.COLOR_CHARCOAL
        self.screen.fill(bg)
        sw, sh = self.screen.get_width(), self.screen.get_height()
        h, w = len(state.world.grid), len(state.world.grid[0]) if len(state.world.grid) > 0 else 0
        ww, wh = w * constants.TILE_SIZE, h * constants.TILE_SIZE
        if hasattr(state, 'camera'):
            if state.camera.screen_w != sw or state.camera.screen_h != sh: state.camera.screen_w, state.camera.screen_h = sw, sh
            state.camera.world_w, state.camera.world_h = ww, wh
            ox, oy = state.camera.get_offset()
        else:
            cam = Camera(sw, sh, ww, wh)
            ox, oy = cam.get_target_offset(state.player.get_center())
        if getattr(state, 'shake_timer', 0) > 0:
            ox += random.uniform(-constants.SCREEN_SHAKE_INTENSITY, constants.SCREEN_SHAKE_INTENSITY)
            oy += random.uniform(-constants.SCREEN_SHAKE_INTENSITY, constants.SCREEN_SHAKE_INTENSITY)
        sx, sy = int(max(0, ox // constants.TILE_SIZE)), int(max(0, oy // constants.TILE_SIZE))
        ex, ey = int(min(w, (ox + sw) // constants.TILE_SIZE + 1)), int(min(h, (oy + sh) // constants.TILE_SIZE + 1))
        for y in range(sy, ey):
            for x in range(sx, ex):
                dr = (x * constants.TILE_SIZE - ox, y * constants.TILE_SIZE - oy, constants.TILE_SIZE, constants.TILE_SIZE)
                tile = state.world.grid[y][x]
                if tile == constants.TILE_WALL:
                    img = self.image_cache.get("brown_wall.png")
                    if img:
                        self.screen.blit(img, (dr[0], dr[1]))
                    else:
                        pygame.draw.rect(self.screen, constants.COLOR_WALL, dr)
                elif tile == constants.TILE_EMPTY:
                    img = self.image_cache.get("tile_floor.png")
                    if img:
                        self.screen.blit(img, (dr[0], dr[1]))
                    else:
                        pygame.draw.rect(self.screen, constants.COLOR_FLOOR, dr, 1)
                elif tile == constants.TILE_LOTUS_FRAME: pygame.draw.rect(self.screen, (40, 40, 80), dr)
                else: pygame.draw.rect(self.screen, constants.COLOR_FLOOR, dr, 1)
        
        # World Debris (Persistent visual remnants)
        for debris in getattr(state, 'world_debris', []):
            if debris['name'] == 'BarrelRubble':
                img = self.image_cache.get("barrel_3.png")
                if img:
                    self.screen.blit(img, (debris['pos'][0] - ox, debris['pos'][1] - oy))

        for obj in getattr(state.world, 'interactables', []):
            if hasattr(obj, 'target_name'): self.draw_warp(obj, ox, oy)
            elif "Respite" in obj.name:
                if not getattr(obj, 'is_active', True):
                    continue
                # Draw Respite Anchor as a large pulsing sigil
                dr = pygame.Rect(obj.x - ox, obj.y - oy, obj.width, obj.height)
                pygame.draw.rect(self.screen, (20, 40, 60), dr) # Dark base
                pygame.draw.rect(self.screen, constants.COLOR_CYAN, dr, 2)
                pulse = (math.sin(time.time() * 5) + 1) / 2
                inner_r = int(5 + pulse * 10)
                pygame.draw.circle(self.screen, constants.COLOR_CYAN, (int(dr.centerx), int(dr.centery)), inner_r, 1)
            elif obj.name == "Barrel":
                img = self.image_cache.get("barrel_0.png")
                if img:
                    self.screen.blit(img, (obj.x - ox, obj.y - oy))
                else:
                    pygame.draw.rect(self.screen, (100, 80, 40), (obj.x - ox, obj.y - oy, obj.width, obj.height))
                    pygame.draw.rect(self.screen, (60, 40, 20), (obj.x - ox, obj.y - oy, obj.width, obj.height), 2)
            elif obj.name == "Structure": pygame.draw.rect(self.screen, (80, 70, 60), (obj.x - ox, obj.y - oy, obj.width, obj.height))
            elif obj.name == "The Chronicler":
                pygame.draw.rect(self.screen, (220, 220, 220), (obj.x - ox, obj.y - oy, obj.width, obj.height))
                pygame.draw.rect(self.screen, (255, 200, 150), (obj.x + 5 - ox, obj.y + 5 - oy, obj.width - 10, 10))
                pygame.draw.rect(self.screen, constants.COLOR_BLACK, (obj.x - ox, obj.y - oy, obj.width, obj.height), 1)
            elif obj.name == "The Wellspring": self.draw_wellspring(obj, ox, oy)
            elif obj.name == "Heavy Bookcase":
                pygame.draw.rect(self.screen, constants.COLOR_DARK_GREY, (obj.x - ox, obj.y - oy, obj.width, obj.height))
                pygame.draw.rect(self.screen, constants.COLOR_BLACK, (obj.x - ox, obj.y - oy, obj.width, obj.height), 2)
                pygame.draw.rect(self.screen, constants.COLOR_BLACK, (obj.x - ox, obj.y + obj.height // 2 - oy, obj.width, 1))
            elif obj.name == "Ink Urn":
                pygame.draw.rect(self.screen, constants.COLOR_DEEP_SLATE, (obj.x - ox, obj.y - oy, obj.width, obj.height))
                pygame.draw.rect(self.screen, constants.COLOR_BLACK, (obj.x - ox, obj.y - oy, obj.width, obj.height), 1)
                pygame.draw.rect(self.screen, constants.COLOR_BLACK, (obj.x + 4 - ox, obj.y + 2 - oy, obj.width - 8, 4))
            elif obj.name == "Inkwell Puddle":
                pygame.draw.rect(self.screen, constants.COLOR_INK_PUDDLE, (obj.x + 4 - ox, obj.y + 4 - oy, obj.width - 8, obj.height - 8))
                pygame.draw.rect(self.screen, (30, 30, 50), (obj.x + 6 - ox, obj.y + 6 - oy, 4, 4))
            elif obj.name == "Candelabra":
                stand = (obj.x + obj.width//2 - 3 - ox, obj.y + 10 - oy, 6, obj.height - 10)
                pygame.draw.rect(self.screen, constants.COLOR_DARK_GREY, stand)
                pygame.draw.rect(self.screen, constants.COLOR_BLACK, stand, 1)
                rad = int(30 * (math.sin(time.time() * 10) * 0.1 + 1.0))
                g = pygame.Surface((rad * 2, rad * 2), pygame.SRCALPHA)
                pygame.draw.circle(g, (255, 190, 40, 60), (rad, rad), rad)
                self.screen.blit(g, (obj.x + obj.width//2 - rad - ox, obj.y + 5 - rad - oy))
                pygame.draw.rect(self.screen, constants.COLOR_CANDLE_AMBER, (obj.x + obj.width//2 - 2 - ox, obj.y + 4 - oy, 4, 6))
            elif obj.name == "Bench":
                pygame.draw.rect(self.screen, (101, 67, 33), (obj.x - ox, obj.y - oy, obj.width, obj.height))
                pygame.draw.rect(self.screen, (60, 40, 20), (obj.x - ox, obj.y + 5 - oy, obj.width, 2))
            elif obj.name == "Rock":
                pygame.draw.rect(self.screen, (80, 80, 80), (obj.x - ox, obj.y - oy, obj.width, obj.height))
                pygame.draw.rect(self.screen, (120, 120, 120), (obj.x + 5 - ox, obj.y + 5 - oy, 10, 5))
            elif hasattr(obj, 'weapon_data'):
                col = constants.COLOR_PURPLE if "modifiers" in obj.weapon_data else constants.COLOR_WHITE
                pygame.draw.rect(self.screen, col, (obj.x - ox, obj.y - oy, obj.width, obj.height))
                pygame.draw.rect(self.screen, constants.COLOR_BLACK, (obj.x - ox, obj.y - oy, obj.width, obj.height), 1)
                glow = (math.sin(time.time() * 5) + 1) / 2
                pygame.draw.rect(self.screen, col, (obj.x - 2 - ox, obj.y - 2 - oy, obj.width + 4, obj.height + 4), 1)
        for item in getattr(state, 'loot', []): self.draw_loot(item, ox, oy)
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
                self.draw_actor_ghost(enemy, ox, oy, state)
        except Exception as e:
            print(f"[RENDER ERROR] Enemy Loop: {e}")

        # Local Player Rendering
        self.draw_actor_ghost(state.player, ox, oy, state)
        
        # Sword Hitbox Visual (Optional debug-style but kept for feedback)
        if state.player.state == PlayerStateEnum.ATTACKING:
            from engine.combat import get_sword_hitbox
            hb = get_sword_hitbox(state.player.get_center(), state.player.facing)
            pygame.draw.rect(self.screen, constants.COLOR_SELECTION, (hb[0] - ox, hb[1] - oy, hb[2], hb[3]), 1)
        for num in state.damage_numbers:
            self.screen.blit(self.font.render(str(num['val']), True, num['color']), (num['pos'][0] - ox, num['pos'][1] - oy))
        if getattr(state.player, 'current_interactable', None): self.draw_interaction_prompt(state.player, ox, oy)
        try:
            if getattr(state, 'last_save_elapsed', 1e6) <= constants.AUTOSAVE_INDICATOR_DURATION:
                ind = self.font.render("Saved", True, (200, 200, 200))
                self.screen.blit(ind, (sw - ind.get_width() - 8, 8))
        except Exception: pass
        try: self.draw_minimap(state)
        except Exception: pass
        try: self.draw_hud(state)
        except Exception: pass

        # Audio Debug OSD
        if audio_manager:
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
                # Flashing semi-transparent orange warning zone
                s.fill((255, 120, 0, 70))
                self.screen.blit(s, (sx, sy))
                
                # Flashing outline
                pulse = (math.sin(time.time() * 15) + 1) / 2
                outline_color = (255, 140, 0, int(150 + pulse * 105))
                s_outline = pygame.Surface((hb[2], hb[3]), pygame.SRCALPHA)
                pygame.draw.rect(s_outline, outline_color, (0, 0, hb[2], hb[3]), 2)
                self.screen.blit(s_outline, (sx, sy))
            elif packet["base"] == "STRIKE":
                # Semi-transparent red active damage zone
                s.fill((255, 0, 0, 110))
                self.screen.blit(s, (sx, sy))
                
                s_outline = pygame.Surface((hb[2], hb[3]), pygame.SRCALPHA)
                pygame.draw.rect(s_outline, (255, 0, 0), (0, 0, hb[2], hb[3]), 2)
                self.screen.blit(s_outline, (sx, sy))

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

        # 5. Directional Indicator (Only for ghosts)
        if not sprite:
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

    def draw_boss_weapon(self, actor, ox, oy):
        """Draws a literal weapon held by a limb that swings or thrusts dynamically based on attack state."""
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
        
        # Visual styling: Bosses carry a giant ink-dripping quill/blade
        wood_color = (139, 90, 43)   # Dark brown shaft
        ink_color = (20, 20, 30)      # Deep black/blue ink
        steel_color = (192, 192, 192) # Silver quill nib
        
        base_angle = math.atan2(fy, fx)
        
        if attack_type == "THRUST":
            # Determine weapon length L based on state
            if actor.state == ActorState.WIND_UP:
                L = 60.0 - t * 25.0
            elif actor.state == ActorState.STRIKE:
                L = 35.0 + math.sin(t * math.pi) * 95.0
            else: # RECOVERY
                L = 35.0 + t * 25.0
                
            px = cx + fx * L
            py = cy + fy * L
            
            # Draw wood shaft from boss center to tip
            pygame.draw.line(self.screen, wood_color, (cx, cy), (px, py), 6)
            # Draw silver steel nib at the end
            nib_start_x = cx + fx * (L - 15)
            nib_start_y = cy + fy * (L - 15)
            pygame.draw.line(self.screen, steel_color, (nib_start_x, nib_start_y), (px, py), 8)
            # Draw ink drop at the very tip
            pygame.draw.circle(self.screen, ink_color, (int(px), int(py)), 6)
            
        else: # SWING
            # Determine swing angle based on state
            if actor.state == ActorState.WIND_UP:
                angle = base_angle - 1.2 * t
                L = 60.0
            elif actor.state == ActorState.STRIKE:
                angle = (base_angle - 1.2) + t * 2.4
                L = 70.0
                
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
                    pygame.draw.polygon(trail_surf, (0, 180, 255, 60), points)
                self.screen.blit(trail_surf, (0, 0))
            else: # RECOVERY
                angle = (base_angle + 1.2) - t * 1.2
                L = 60.0
                
            px = cx + math.cos(angle) * L
            py = cy + math.sin(angle) * L
            
            # Draw wood shaft
            pygame.draw.line(self.screen, wood_color, (cx, cy), (px, py), 6)
            # Draw silver quill nib/blade
            blade_start_x = cx + math.cos(angle) * (L - 20)
            blade_start_y = cy + math.sin(angle) * (L - 20)
            pygame.draw.line(self.screen, steel_color, (blade_start_x, blade_start_y), (px, py), 8)
            # Draw ink drop
            pygame.draw.circle(self.screen, ink_color, (int(px), int(py)), 6)

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
        hud_surf = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
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

        # [Input Mode Indicator]
        mode = getattr(state, 'input_mode', constants.INPUT_MODE_KEYBOARD)
        mode_col = constants.COLOR_MODE_GAMEPAD if mode == constants.INPUT_MODE_GAMEPAD else constants.COLOR_MODE_KEYBOARD
        mode_label = self.hud_font.render(f"[ Input: {mode.capitalize()} ]", True, mode_col)
        hud_surf.blit(mode_label, (hud_surf.get_width() - mode_label.get_width() - 10, hud_surf.get_height() - 25))

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

        hud_x = 10
        hud_y = self.screen.get_height() - constants.HUD_PANEL_H - 10
        self.screen.blit(hud_surf, (hud_x, hud_y))

        # --- EXPANDED INSPECT VIEW ---
        if getattr(state, 'inspect_active', False):
            tip_w = 200
            tip_y = hud_y - 5
            
            # 1. Equipped Slot A
            if len(player.weapons) > 0:
                self.draw_weapon_details(player.weapons[0], hud_x + 10, tip_y, tip_w, title="SLOT A")
                
            # 2. Equipped Slot B
            if len(player.weapons) > 1:
                self.draw_weapon_details(player.weapons[1], hud_x + tip_w + 20, tip_y, tip_w, title="SLOT B")
                
            # 3. Ground Comparison
            if is_near_weapon:
                self.draw_weapon_details(target.weapon_data, hud_x + (tip_w + 20) * 2, tip_y, tip_w, title="ON FLOOR")

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

        # Initialize Minimap Surface (Create once or reuse if size is fixed)
        mw, mh = constants.MINIMAP_WIDTH, constants.MINIMAP_HEIGHT
        minimap_surface = pygame.Surface((mw, mh), pygame.SRCALPHA)
        
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
        # Calculate scale based on the width/height to ensure uniform mapping
        scale = min(mw / float(vpw), mh / float(vph))
        sx = sy = scale

        # 4. Minimap Tile Rendering (Walls)
        tx1, ty1 = int(max(0, vpx // constants.TILE_SIZE)), int(max(0, vpy // constants.TILE_SIZE))
        tx2, ty2 = int(min(w, (vpx + vpw) // constants.TILE_SIZE + 1)), int(min(h, (vpy + vph) // constants.TILE_SIZE + 1))
        
        for y in range(ty1, ty2):
            for x in range(tx1, tx2):
                if state.world.grid[y][x] == constants.TILE_WALL:
                    wx, wy = x * constants.TILE_SIZE, y * constants.TILE_SIZE
                    # Draw onto minimap_surface
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
        # Audio Debug OSD (Title Screen)
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
