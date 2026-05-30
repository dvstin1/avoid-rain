"""
Handles all Pygame drawing calls.
"""
import pygame
import constants
from engine.player import PlayerStateEnum
from engine.combat import get_sword_hitbox
from engine.camera import Camera

class Renderer:
    """Coordinates rendering of the game state."""
    def __init__(self, screen):
        self.screen = screen
        self.font = pygame.font.SysFont("Arial", 24)

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
        import math, time
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
        """Draw the Wellspring fountain."""
        ox, oy, ow, oh = wellspring.rect
        screen_x, screen_y = ox - offset_x, oy - offset_y
        basin_rect = pygame.Rect(screen_x, screen_y, ow, oh)
        pygame.draw.rect(self.screen, constants.COLOR_BLUE, basin_rect)
        pygame.draw.rect(self.screen, constants.COLOR_WHITE, basin_rect, 2)
        try:
            ticks = pygame.time.get_ticks()
            offset = (ticks // 200) % constants.TILE_SIZE
            for i in range(4):
                line_y = screen_y + (i + 1) * (oh // 5)
                line_offset = offset if i % 2 == 0 else -offset
                for lx in range(-constants.TILE_SIZE, ow + constants.TILE_SIZE, 25):
                    sx, ex = screen_x + lx + line_offset, screen_x + lx + line_offset + 15
                    fsx, fex = max(screen_x + 2, min(screen_x + ow - 2, sx)), max(screen_x + 2, min(screen_x + ow - 2, ex))
                    if fsx < fex: pygame.draw.line(self.screen, constants.COLOR_CYAN, (fsx, line_y), (fex, line_y), 2)
        except Exception: pass

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
        self.screen.blit(self.font.render(speaker, True, constants.COLOR_YELLOW), (x + 20, y + 10))
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
            color, border = (60, 60, 80) if i == choice["selected_index"] else (40, 40, 40), constants.COLOR_YELLOW if i == choice["selected_index"] else constants.COLOR_GREY
            pygame.draw.rect(self.screen, color, rect)
            pygame.draw.rect(self.screen, border, rect, 3)
            name = self.font.render(opt["name"], True, constants.COLOR_WHITE)
            self.screen.blit(name, (x + card_w // 2 - name.get_width() // 2, y + 20))
            bias = self.font.render(f"({opt['bias']})", True, constants.COLOR_GREY)
            self.screen.blit(bias, (x + card_w // 2 - bias.get_width() // 2, y + 50))
            desc = self.font.render(opt["description"], True, constants.COLOR_YELLOW)
            self.screen.blit(desc, (x + card_w // 2 - desc.get_width() // 2, y + card_h - 50))
        instr = self.font.render("Move [Left/Right] to select, [SPACE] to confirm", True, constants.COLOR_WHITE)
        self.screen.blit(instr, (sw // 2 - instr.get_width() // 2, sh - 100))

    def draw_weather(self, state):
        """Draw screen-space weather effects and the shrinking safe circle."""
        if getattr(state, 'bleed_state', 'CLEAR') == 'GRACE_PERIOD':
            return

        boss_coords = getattr(state.world, 'boss_coords', None)
        if not boss_coords:
            return

        sw, sh = self.screen.get_width(), self.screen.get_height()
        ox, oy = state.camera.get_offset()
        bcx, bcy = boss_coords['x'] * constants.TILE_SIZE - ox, boss_coords['y'] * constants.TILE_SIZE - oy
        radius = state.active_safe_radius

        # 1. Draw the Safe Circle Boundary
        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        
        # 2. Particle System (Performant Vertical Rain)
        if not hasattr(self, 'rain_particles'):
            import random
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
        
        rain_color = constants.COLOR_TOXIC_RAIN
        wb_x, wb_y = boss_coords['x'] * constants.TILE_SIZE, boss_coords['y'] * constants.TILE_SIZE
        rad_sq = radius**2

        for p in self.rain_particles:
            ry = (p['y'] + ticks * p['speed']) % sh
            rx = p['x']
            
            # Distance check: Only draw if OUTSIDE the safe circle
            world_rx, world_ry = rx + ox, ry + oy
            d_sq = (world_rx - wb_x)**2 + (world_ry - wb_y)**2
            
            if d_sq > rad_sq:
                pygame.draw.line(overlay, rain_color, (rx, ry), (rx, ry + p['len']), 2)

        # 3. Draw a glowing edge for the circle
        if 0 < radius < 30000:
            pygame.draw.circle(overlay, (255, 100, 0, 150), (int(bcx), int(bcy)), int(radius), 3)

        self.screen.blit(overlay, (0, 0))

    def render(self, state):
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
            import random
            ox += random.uniform(-constants.SCREEN_SHAKE_INTENSITY, constants.SCREEN_SHAKE_INTENSITY)
            oy += random.uniform(-constants.SCREEN_SHAKE_INTENSITY, constants.SCREEN_SHAKE_INTENSITY)
        sx, sy = int(max(0, ox // constants.TILE_SIZE)), int(max(0, oy // constants.TILE_SIZE))
        ex, ey = int(min(w, (ox + sw) // constants.TILE_SIZE + 1)), int(min(h, (oy + sh) // constants.TILE_SIZE + 1))
        for y in range(sy, ey):
            for x in range(sx, ex):
                dr = (x * constants.TILE_SIZE - ox, y * constants.TILE_SIZE - oy, constants.TILE_SIZE, constants.TILE_SIZE)
                tile = state.world.grid[y][x]
                if tile == constants.TILE_WALL: pygame.draw.rect(self.screen, constants.COLOR_WALL, dr)
                elif tile == constants.TILE_LOTUS_FRAME: pygame.draw.rect(self.screen, (40, 40, 80), dr)
                else: pygame.draw.rect(self.screen, constants.COLOR_FLOOR, dr, 1)
        for obj in getattr(state.world, 'interactables', []):
            if hasattr(obj, 'target_name'): self.draw_warp(obj, ox, oy)
            elif obj.name == "Respite":
                c = (int(obj.x + obj.width/2 - ox), int(obj.y + obj.height/2 - oy))
                pygame.draw.circle(self.screen, constants.COLOR_CYAN, c, 10, 2)
            elif obj.name == "Barrel":
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
                import math, time
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
                import math, time
                glow = (math.sin(time.time() * 5) + 1) / 2
                pygame.draw.rect(self.screen, col, (obj.x - 2 - ox, obj.y - 2 - oy, obj.width + 4, obj.height + 4), 1)
        for item in getattr(state, 'loot', []): self.draw_loot(item, ox, oy)
        for fading in getattr(state, 'fading_entities', []):
            obj, alpha = fading['obj'], int((fading['time'] / 0.1) * 255)
            if alpha > 0:
                s = pygame.Surface((obj.width, obj.height), pygame.SRCALPHA)
                s.fill((100, 80, 40, alpha))
                self.screen.blit(s, (obj.x - ox, obj.y - oy))
        dummy_draw = pygame.Rect(state.dummy_rect[0] - ox, state.dummy_rect[1] - oy, state.dummy_rect[2], state.dummy_rect[3])
        pygame.draw.rect(self.screen, constants.COLOR_GREEN, dummy_draw)
        if state.dummy_outline_timer > 0: pygame.draw.rect(self.screen, constants.COLOR_WHITE, dummy_draw, 2)
        try:
            from engine.enemy import BatEnemy
            for enemy in getattr(state, 'enemies', []):
                ed = pygame.Rect(enemy.x - ox, enemy.y - oy, enemy.width, enemy.height)
                if isinstance(enemy, BatEnemy):
                    pygame.draw.rect(self.screen, constants.COLOR_PURPLE, ed)
                    pygame.draw.line(self.screen, constants.COLOR_PURPLE, (ed.left - 5, ed.centery), (ed.left, ed.centery - 5), 2)
                    pygame.draw.line(self.screen, constants.COLOR_PURPLE, (ed.right + 5, ed.centery), (ed.right, ed.centery - 5), 2)
                else: pygame.draw.rect(self.screen, constants.COLOR_RED, ed)
                if getattr(enemy, 'stagger_timer', 0) > 0: pygame.draw.rect(self.screen, constants.COLOR_WHITE, ed, 2)
        except Exception: pass
        p_draw = pygame.Rect(state.player.x - ox, state.player.y - oy, state.player.width, state.player.height)
        pygame.draw.rect(self.screen, constants.COLOR_BLUE, p_draw)
        if state.player.state == PlayerStateEnum.STAGGERED: pygame.draw.rect(self.screen, constants.COLOR_WHITE, p_draw, 2)
        if state.player.state == PlayerStateEnum.ATTACKING:
            hb = get_sword_hitbox(state.player.get_center(), state.player.facing)
            pygame.draw.rect(self.screen, constants.COLOR_YELLOW, (hb[0] - ox, hb[1] - oy, hb[2], hb[3]))
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
        debug_font = pygame.font.SysFont("Arial", 14, bold=True)
        debug_text = f"[DEBUG_AUDIO: Playing {state.player.active_track_name}]"
        debug_surf = debug_font.render(debug_text, True, constants.COLOR_WHITE)
        self.screen.blit(debug_surf, (sw // 2 - debug_surf.get_width() // 2, 5))

        if getattr(state, 'active_dialogue', None): self.draw_dialogue_box(state)
        if getattr(state, 'active_choice', None): self.draw_choice_of_fates(state.active_choice)
        if getattr(state, 'death_timer', 0) > 0:
            overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
            overlay.fill((200, 200, 200, 150))
            self.screen.blit(overlay, (0, 0))
            msg = self.font.render("TEXT BLEACHING...", True, constants.COLOR_BLACK)
            self.screen.blit(msg, msg.get_rect(center=(sw//2, sh//2)))

        self.draw_weather(state)
        pygame.display.flip()

    def draw_hud(self, state):
        """Draw player HP, Flask, and Dual Weapon slots."""
        player = state.player
        hud_font = pygame.font.SysFont("Arial", 14, bold=True)
        panel_w = constants.HUD_PANEL_W
        panel_h = constants.HUD_PANEL_H
        hud_surf = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        hud_surf.fill((20, 20, 25, constants.UI_ALPHA))
        pygame.draw.rect(hud_surf, (100, 100, 100), (0, 0, panel_w, panel_h), 2)
        
        # Status Metrics (compact font)
        hp_text = f"HP: {int(player.hp)}/{int(player.max_hp)}"
        hud_surf.blit(hud_font.render(hp_text, True, constants.COLOR_WHITE), (10, 10))
        
        flask_text = f"Flasks: {player.flask_charges}"
        hud_surf.blit(hud_font.render(flask_text, True, constants.COLOR_BLUE), (140, 10))
        
        pages = state.stats.data["lifetime_stats"].get("pages_collected", 0) if state.stats else 0
        pages_text = f"Pages: {pages}"
        hud_surf.blit(hud_font.render(pages_text, True, constants.COLOR_YELLOW), (240, 10))

        edif_lvl = player.stats.get("edification", 1)
        edif_text = f"LVL: {edif_lvl}"
        hud_surf.blit(hud_font.render(edif_text, True, constants.COLOR_CYAN), (340, 10))

        for i in range(2):
            sx, sy = 10 + i * (constants.HUD_SLOT_W + 100), 45
            sr = pygame.Rect(sx, sy, constants.HUD_SLOT_W, constants.HUD_SLOT_H)
            pygame.draw.rect(hud_surf, (40, 40, 50), sr)
            
            border_col = constants.COLOR_YELLOW if i == player.active_weapon_idx else constants.COLOR_GREY
            pygame.draw.rect(hud_surf, border_col, sr, 2)
            
            slot_font = pygame.font.SysFont("Arial", 12)
            l_surf = slot_font.render("SLOT A" if i == 0 else "SLOT B", True, constants.COLOR_GREY)
            hud_surf.blit(l_surf, (sx + 5, sy + 2))
            
            if i < len(player.weapons):
                wpn = player.weapons[i]
                col = constants.COLOR_PURPLE if "modifiers" in wpn else constants.COLOR_WHITE
                
                name_font = pygame.font.SysFont("Arial", 14)
                name_surf = name_font.render(wpn.get("name", "Unknown")[:12], True, col)
                hud_surf.blit(name_surf, (sx + 5, sy + 20))
                
                dmg_text = f"DMG: {wpn.get('damage', 0)}"
                dmg_surf = slot_font.render(dmg_text, True, constants.COLOR_GREY)
                hud_surf.blit(dmg_surf, (sx + 5, sy + 40))
        swr = pygame.Rect(constants.HUD_SWAP_BTN_RECT)
        pygame.draw.rect(hud_surf, (60, 60, 80), swr)
        pygame.draw.rect(hud_surf, constants.COLOR_WHITE, swr, 1)
        swt = pygame.font.SysFont("Arial", 14, bold=True).render("SWAP", True, constants.COLOR_WHITE)
        hud_surf.blit(swt, (swr.centerx - swt.get_width()//2, swr.centery - swt.get_height()//2))

        # [PICK UP] Button - only visible if standing over a WeaponPickup
        from engine.world import WeaponPickup
        target = state.player.current_interactable
        if isinstance(target, WeaponPickup):
            pkr = pygame.Rect(constants.HUD_PICKUP_BTN_RECT)
            # Use tier color for button outline
            col = constants.COLOR_PURPLE if "modifiers" in target.weapon_data else constants.COLOR_WHITE
            pygame.draw.rect(hud_surf, (40, 60, 40), pkr) # Dark green tint for pickup
            pygame.draw.rect(hud_surf, col, pkr, 2)
            pkt = pygame.font.SysFont("Arial", 14, bold=True).render("PICK UP", True, constants.COLOR_WHITE)
            hud_surf.blit(pkt, (pkr.centerx - pkt.get_width()//2, pkr.centery - pkt.get_height()//2))

        self.screen.blit(hud_surf, (10, self.screen.get_height() - constants.HUD_PANEL_H - 10))

    def draw_loot(self, item, offset_x, offset_y):
        """Draw loot items."""
        from engine.loot import TornPage, HealItem
        ir = item.get_rect()
        dr = pygame.Rect(ir[0] - offset_x, ir[1] - offset_y, ir[2], ir[3])
        if isinstance(item, TornPage):
            pygame.draw.rect(self.screen, constants.COLOR_WHITE, dr)
            pygame.draw.rect(self.screen, constants.COLOR_YELLOW, dr, 1)
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
        mbg = pygame.Surface((constants.MINIMAP_WIDTH, constants.MINIMAP_HEIGHT), pygame.SRCALPHA)
        mbg.fill((10, 10, 10, constants.UI_ALPHA))
        self.screen.blit(mbg, (constants.MINIMAP_PADDING, constants.MINIMAP_PADDING))
        
        ww, wh = w * constants.TILE_SIZE, h * constants.TILE_SIZE
        if ww == 0 or wh == 0: return

        # 2. Increased Zoom Scale Factor (defined by constants.MINIMAP_VIEWPORT_FRAC)
        vpw, vph = int(SCREEN_WIDTH * constants.MINIMAP_VIEWPORT_FRAC), int(SCREEN_HEIGHT * constants.MINIMAP_VIEWPORT_FRAC)
        pxc, pyc = state.player.get_center()
        # Viewport center follows player
        vpx, vpy = pxc - vpw // 2, pyc - vph // 2
        sx, sy = constants.MINIMAP_WIDTH / vpw, constants.MINIMAP_HEIGHT / vph

        # 3. Minimap Tile Rendering (Walls only for clarity)
        # Calculate range of tiles visible in minimap viewport
        tx1, ty1 = max(0, vpx // constants.TILE_SIZE), max(0, vpy // constants.TILE_SIZE)
        tx2, ty2 = min(w, (vpx + vpw) // constants.TILE_SIZE + 1), min(h, (vpy + vph) // constants.TILE_SIZE + 1)
        
        for y in range(int(ty1), int(ty2)):
            for x in range(int(tx1), int(tx2)):
                if state.world.grid[y][x] == constants.TILE_WALL:
                    wx, wy = x * constants.TILE_SIZE, y * constants.TILE_SIZE
                    pygame.draw.rect(self.screen, constants.MINIMAP_WALL_COLOR, (
                        constants.MINIMAP_PADDING + int((wx - vpx) * sx),
                        constants.MINIMAP_PADDING + int((wy - vpy) * sy),
                        max(1, int(constants.TILE_SIZE * sx)),
                        max(1, int(constants.TILE_SIZE * sy))
                    ))

        # 4. Safe Circle Boundary Visualization
        boss_coords = getattr(state.world, 'boss_coords', None)
        if boss_coords:
            bcx, bcy = boss_coords['x'] * constants.TILE_SIZE, boss_coords['y'] * constants.TILE_SIZE
            radius = state.active_safe_radius
            
            # Project world center to minimap coordinates
            mcx = constants.MINIMAP_PADDING + int((bcx - vpx) * sx)
            mcy = constants.MINIMAP_PADDING + int((bcy - vpy) * sy)
            mr = int(radius * sx)
            
            # Only draw if part of the circle might be visible
            if -mr < mcx < constants.MINIMAP_WIDTH + mr and -mr < mcy < constants.MINIMAP_HEIGHT + mr:
                # Clip the circle to minimap bounds manually or using sub-surface
                # Simple approach: draw circle on minimap surface and blit
                circle_surf = pygame.Surface((constants.MINIMAP_WIDTH, constants.MINIMAP_HEIGHT), pygame.SRCALPHA)
                pygame.draw.circle(circle_surf, (255, 165, 0, 180), (mcx - constants.MINIMAP_PADDING, mcy - constants.MINIMAP_PADDING), mr, 1)
                self.screen.blit(circle_surf, (constants.MINIMAP_PADDING, constants.MINIMAP_PADDING))

        # 5. Radar Entity Rules
        # Enemies: Red Dot
        for e in getattr(state, 'enemies', []):
            ex, ey = e.x + e.width // 2, e.y + e.height // 2
            if vpx <= ex <= vpx + vpw and vpy <= ey <= vpy + vph:
                pygame.draw.rect(self.screen, constants.MINIMAP_ENEMY_COLOR, (
                    constants.MINIMAP_PADDING + int((ex - vpx) * sx) - 1,
                    constants.MINIMAP_PADDING + int((ey - vpy) * sy) - 1, 3, 3))

        # Loot: Yellow Dot
        for i in getattr(state, 'loot', []):
            lx, ly = i.x + i.width // 2, i.y + i.height // 2
            if vpx <= lx <= vpx + vpw and vpy <= ly <= vpy + vph:
                pygame.draw.rect(self.screen, constants.MINIMAP_LOOT_COLOR, (
                    constants.MINIMAP_PADDING + int((lx - vpx) * sx) - 1,
                    constants.MINIMAP_PADDING + int((ly - vpy) * sy) - 1, 3, 3))

        # Player: White Dot
        mx, my = constants.MINIMAP_PADDING + int((pxc - vpx) * sx), constants.MINIMAP_PADDING + int((pyc - vpy) * sy)
        pygame.draw.rect(self.screen, constants.MINIMAP_PLAYER_COLOR, (mx-2, my-2, 4, 4))

        # 6. Edge-Clamped Compass Indicators
        for ox, oy in getattr(state, 'objectives', []):
            if vpx <= ox <= vpx + vpw and vpy <= oy <= vpy + vph: continue
            dx, dy = ox - pxc, oy - pyc
            if dx == 0 and dy == 0: continue
            rl, rr, rt, rb = 0, constants.MINIMAP_WIDTH, 0, constants.MINIMAP_HEIGHT
            k = 1e9
            if dx > 0: k = min(k, (rr - (mx - constants.MINIMAP_PADDING)) / dx)
            elif dx < 0: k = min(k, (rl - (mx - constants.MINIMAP_PADDING)) / dx)
            if dy > 0: k = min(k, (rb - (my - constants.MINIMAP_PADDING)) / dy)
            elif dy < 0: k = min(k, (rt - (my - constants.MINIMAP_PADDING)) / dy)
            ix, iy = int((mx - constants.MINIMAP_PADDING) + k * dx), int((my - constants.MINIMAP_PADDING) + k * dy)
            pygame.draw.rect(self.screen, constants.COLOR_WHITE, (
                constants.MINIMAP_PADDING + max(0, min(ix, constants.MINIMAP_WIDTH - 3)),
                constants.MINIMAP_PADDING + max(0, min(iy, constants.MINIMAP_HEIGHT - 3)), 3, 3))

    def draw_title_screen(self, menu=0):
        """Draw title screen."""
        self.screen.fill(constants.COLOR_BLACK)
        sw, sh = self.screen.get_width(), self.screen.get_height()
        title = self.font.render("AVOID RAIN", True, constants.COLOR_WHITE)
        instr = self.font.render("Use ARROW KEYS and ENTER to choose", True, constants.COLOR_WHITE)
        self.screen.blit(title, title.get_rect(center=(sw//2, 220)))
        self.screen.blit(instr, instr.get_rect(center=(sw//2, 280)))
        opts, sel = ["New Game", "Quit"], 0
        from engine.title_menu import TitleMenuState
        state = TitleMenuState.MAIN
        try:
            if hasattr(menu, 'get_options'):
                opts = menu.get_options()
                sel = menu.get_selected_index()
                state = getattr(menu, 'state', TitleMenuState.MAIN)
            else:
                sel = int(menu)
        except Exception:
            pass

        for idx, opt in enumerate(opts):
            col = constants.COLOR_YELLOW if idx == sel else constants.COLOR_WHITE
            surf = self.font.render(opt, True, col)
            self.screen.blit(surf, surf.get_rect(center=(sw//2, 340 + idx * 40)))

        if state == TitleMenuState.CONFIRM_NEW_GAME:
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
        elif getattr(state, 'name', '') == 'CONTROLS':
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
            color = constants.COLOR_YELLOW if i == sel else constants.COLOR_WHITE
            surf = self.font.render(opt, True, color)
            self.screen.blit(surf, surf.get_rect(center=(sw//2, sh//2 + 10 + i * 30)))
        pygame.display.flip()

    def draw_controls_overlay(self, show_editor=True):
        """Draw controls overlay."""
        sw, sh = self.screen.get_width(), self.screen.get_height()
        over = pygame.Surface((sw, sh), pygame.SRCALPHA)
        over.fill((0, 0, 0, constants.UI_ALPHA))
        self.screen.blit(over, (0, 0))

        cx, cy = sw // 2, sh // 2

        self.screen.blit(self.font.render("[ Keyboard ]", True, constants.COLOR_WHITE), self.font.render("[ Keyboard ]", True, constants.COLOR_WHITE).get_rect(center=(cx - 150, 60)))
        self.screen.blit(self.font.render("[ Controller ] (Not Implemented)", True, constants.COLOR_GREY), self.font.render("[ Controller ] (Not Implemented)", True, constants.COLOR_GREY).get_rect(center=(cx + 150, 60)))
        self.screen.blit(self.font.render("CONTROLS", True, constants.COLOR_YELLOW), self.font.render("CONTROLS", True, constants.COLOR_YELLOW).get_rect(center=(cx, 120)))
        ins = [("Movement:", "WASD / Arrows"), ("Attack / Interact:", "Space"), ("Dash:", "Left Shift"), ("Flask:", "1"), ("Block:", "K"), ("Weapon Swap:", "Q"), ("Pause Run:", "Escape")]
        if show_editor: ins.extend([("Editor Box Fill:", "B / Click-and-Drag"), ("Canvas Stretch:", "+/- and Ctrl + +/-")])
        for i, (a, k) in enumerate(ins):
            asurf, ksurf = self.font.render(a, True, constants.COLOR_WHITE), self.font.render(k, True, constants.COLOR_CYAN)
            self.screen.blit(asurf, asurf.get_rect(midright=(cx - 20, 180 + i * 40)))
            self.screen.blit(ksurf, ksurf.get_rect(midleft=(cx + 20, 180 + i * 40)))
        back = self.font.render("Press SPACE or ENTER to go back", True, constants.COLOR_WHITE)
        self.screen.blit(back, back.get_rect(center=(cx, 180 + len(ins) * 40 + 40)))
        pygame.display.flip()
