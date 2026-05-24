"""
Handles all Pygame drawing calls.
"""
import pygame
# pylint: disable=no-member
from constants import (
    COLOR_BLACK,
    COLOR_WHITE,
    COLOR_BLUE,
    COLOR_GREEN,
    TILE_SIZE,
    TILE_WALL,
    COLOR_WALL,
    COLOR_FLOOR,
    COLOR_YELLOW,
    COLOR_GREY,
    COLOR_RED,
    COLOR_CYAN,
    COLOR_DARK_GREY,
    COLOR_SEPIA_AMBER,
    COLOR_CHARCOAL,
    COLOR_DEEP_SLATE,
    COLOR_INK_PUDDLE,
    COLOR_CANDLE_AMBER,
    TILE_LOTUS_FRAME,
    SCREEN_SHAKE_INTENSITY,
    UI_ALPHA
)
from engine.player import PlayerStateEnum
from engine.combat import get_sword_hitbox
from engine.camera import Camera
from constants import AUTOSAVE_INDICATOR_DURATION

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

        # Draw Pedestal (Geometric base)
        pedestal_rect = pygame.Rect(screen_x + 5, screen_y + wh - 15, ww - 10, 15)
        pygame.draw.rect(self.screen, COLOR_DARK_GREY, pedestal_rect)
        pygame.draw.rect(self.screen, COLOR_BLACK, pedestal_rect, 1)

        # Draw The Libram (The Chronicle)
        book_rect = pygame.Rect(screen_x + 8, screen_y + 10, ww - 16, 20)
        pygame.draw.rect(self.screen, (139, 69, 19), book_rect) # Brown cover

        # Iron binding detail
        pygame.draw.rect(self.screen, COLOR_GREY, (screen_x + 8, screen_y + 10, 4, 20))

        # Glowing Glyph (Cyan/Neon)
        import math
        import time
        # Pulsing glow effect
        pulse = (math.sin(time.time() * 4) + 1) / 2
        glow_alpha = 100 + int(pulse * 155)
        glyph_color = (0, 255, 255) # Cyan

        # Draw small glowing sigil on the book
        pulse_size = int(pulse * 4)
        sigil_rect = pygame.Rect(0, 0, 4 + pulse_size, 4 + pulse_size)
        sigil_rect.center = (book_rect.centerx, book_rect.centery)
        pygame.draw.rect(self.screen, glyph_color, sigil_rect)

    def draw_interaction_prompt(self, player, offset_x, offset_y):
        """Draw a text prompt above the player's head."""
        target = player.current_interactable

        # Determine the action verb based on the object type or name
        if target.name == "The Chronicler":
            prompt_text = f"Speak to {target.name}"
        elif "Chronicle" in target.name or "Return" in target.name:
            prompt_text = f"Read {target.name}"
        elif hasattr(target, 'weapon_data'):
            # Weapon swap prompt
            current_wpn = player.get_active_weapon().get("name", "Current")
            new_wpn = target.weapon_data.get("name", "New")
            if len(player.weapons) < 2:
                prompt_text = f"Pick up {new_wpn}"
            else:
                prompt_text = f"Swap {current_wpn} for {new_wpn}"
        else:
            prompt_text = f"Interact with {target.name}" if hasattr(target, 'name') else "Interact"

        # AGENTS.md specifies "Press [ATTACK] to Speak"
        prompt_surf = self.font.render(f"Press [E] to {prompt_text}", True, COLOR_WHITE)
        rect = prompt_surf.get_rect()
        # Position above player center
        px, py = player.get_center()
        self.screen.blit(prompt_surf, (px - rect.width // 2 - offset_x, py - player.height - 20 - offset_y))

    def draw_wellspring(self, wellspring, offset_x, offset_y):
        """Draw the Wellspring fountain with animated water lines."""
        ox, oy, ow, oh = wellspring.rect
        screen_x = ox - offset_x
        screen_y = oy - offset_y

        # Draw Basin (Solid blue background)
        basin_rect = pygame.Rect(screen_x, screen_y, ow, oh)
        pygame.draw.rect(self.screen, COLOR_BLUE, basin_rect)
        pygame.draw.rect(self.screen, COLOR_WHITE, basin_rect, 2) # Basin rim

        # Animated Water Lines
        # Specification: 3 to 4 alternating horizontal lines of lighter cyan hue
        try:
            ticks = pygame.time.get_ticks()
            offset = (ticks // 200) % TILE_SIZE

            for i in range(4):
                line_y = screen_y + (i + 1) * (oh // 5)
                # Alternate direction
                line_offset = offset if i % 2 == 0 else -offset

                # Draw segments to simulate flowing water
                segment_len = 15
                gap = 10
                for lx in range(-TILE_SIZE, ow + TILE_SIZE, segment_len + gap):
                    start_x = screen_x + lx + line_offset
                    end_x = start_x + segment_len

                    # Clamp to basin width
                    final_start_x = max(screen_x + 2, min(screen_x + ow - 2, start_x))
                    final_end_x = max(screen_x + 2, min(screen_x + ow - 2, end_x))

                    if final_start_x < final_end_x:
                        pygame.draw.line(self.screen, COLOR_CYAN, (final_start_x, line_y), (final_end_x, line_y), 2)
        except Exception:
            pass

    def draw_dialogue_box(self, state):
        """Draw a dialogue box. Supports STANDARD and EXPANDED modes."""
        dialogue = state.active_dialogue
        if not dialogue:
            return

        mode = getattr(state, 'dialogue_mode', "STANDARD")
        speaker = dialogue.get("speaker", "Unknown")
        text = dialogue.get("text", "")

        if mode == "EXPANDED":
            # Large, centralized screen overlay
            margin_x = 100
            margin_y = 100
            width = self.screen.get_width() - margin_x * 2
            height = self.screen.get_height() - margin_y * 2
            x = margin_x
            y = margin_y
            bg_color = (10, 10, 30) # Darker blueish
            line_spacing = 40
            text_y_offset = 80
        else:
            # Panel dimensions
            margin = 50
            width = self.screen.get_width() - margin * 2
            height = 150
            x = margin
            y = self.screen.get_height() - height - 20
            bg_color = (20, 20, 20)
            line_spacing = 30
            text_y_offset = 50

        # Draw background panel
        panel_rect = pygame.Rect(x, y, width, height)
        pygame.draw.rect(self.screen, bg_color, panel_rect)
        pygame.draw.rect(self.screen, COLOR_WHITE, panel_rect, 2)

        # Draw speaker name
        speaker_surf = self.font.render(speaker, True, COLOR_YELLOW)
        self.screen.blit(speaker_surf, (x + 20, y + 10))

        # Draw text (wrapped, respecting newlines)
        raw_lines = text.split('\n')
        lines = []
        for raw_line in raw_lines:
            words = raw_line.split(' ')
            current_line = []
            for word in words:
                test_line = ' '.join(current_line + [word])
                w, _ = self.font.size(test_line)
                if w < width - 40:
                    current_line.append(word)
                else:
                    lines.append(' '.join(current_line))
                    current_line = [word]
            lines.append(' '.join(current_line))

        for i, line in enumerate(lines):
            line_surf = self.font.render(line, True, COLOR_WHITE)
            self.screen.blit(line_surf, (x + 20, y + text_y_offset + i * line_spacing))

        # Instruction to close
        close_surf = self.font.render("Press [SPACE] to continue", True, COLOR_GREY)
        self.screen.blit(close_surf, (x + width - close_surf.get_width() - 20, y + height - 30))

    def draw_choice_of_fates(self, choice):
        """Draw the Choice of Fates UI overlay."""
        from constants import COLOR_WHITE, COLOR_YELLOW, COLOR_GREY, COLOR_PURPLE

        # Dim background
        overlay = pygame.Surface((self.screen.get_width(), self.screen.get_height()), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))

        sw, sh = self.screen.get_width(), self.screen.get_height()

        # Draw title
        title_surf = self.font.render(choice["title"], True, COLOR_PURPLE)
        self.screen.blit(title_surf, (sw // 2 - title_surf.get_width() // 2, sh // 4))

        # Draw options
        card_w, card_h = 300, 200
        padding = 50

        for i, option in enumerate(choice["options"]):
            x = sw // 2 - (card_w + padding // 2) + i * (card_w + padding)
            y = sh // 2 - card_h // 2

            rect = pygame.Rect(x, y, card_w, card_h)
            color = (40, 40, 40)
            border_color = COLOR_GREY

            if i == choice["selected_index"]:
                color = (60, 60, 80)
                border_color = COLOR_YELLOW

            pygame.draw.rect(self.screen, color, rect)
            pygame.draw.rect(self.screen, border_color, rect, 3)

            # Draw option name
            name_surf = self.font.render(option["name"], True, COLOR_WHITE)
            self.screen.blit(name_surf, (x + card_w // 2 - name_surf.get_width() // 2, y + 20))

            # Draw bias
            bias_surf = self.font.render(f"({option['bias']})", True, COLOR_GREY)
            self.screen.blit(bias_surf, (x + card_w // 2 - bias_surf.get_width() // 2, y + 50))

            # Draw description
            desc_surf = self.font.render(option["description"], True, COLOR_YELLOW)
            self.screen.blit(desc_surf, (x + card_w // 2 - desc_surf.get_width() // 2, y + card_h - 50))

        # Instructions
        instr_surf = self.font.render("Move [Left/Right] to select, [SPACE] to confirm", True, COLOR_WHITE)
        self.screen.blit(instr_surf, (sw // 2 - instr_surf.get_width() // 2, sh - 100))

    def render(self, state):
        """Draw the visible portion of the game state to the screen using a camera.

        The camera attempts to center on the player but is clamped to the world
        bounds so the viewport never shows outside the world.
        """
        # Select background color based on world zone
        bg_color = COLOR_BLACK
        if getattr(state.world, 'name', 'sanctuary') == "sanctuary":
            bg_color = COLOR_SEPIA_AMBER
        else:
            bg_color = COLOR_CHARCOAL

        self.screen.fill(bg_color)

        # Use camera from the game state if available; otherwise create a transient one
        screen_w = self.screen.get_width()
        screen_h = self.screen.get_height()

        # Dynamic World Dimensions
        h = len(state.world.grid)
        w = len(state.world.grid[0]) if h > 0 else 0
        world_w = w * TILE_SIZE
        world_h = h * TILE_SIZE

        if hasattr(state, 'camera'):
            # Ensure camera screen size matches the current screen (window resize)
            # (camera keeps its own screen_w/h so update if needed)
            if state.camera.screen_w != screen_w or state.camera.screen_h != screen_h:
                state.camera.screen_w = screen_w
                state.camera.screen_h = screen_h
            # Also update world bounds in camera for correct clamping
            state.camera.world_w = world_w
            state.camera.world_h = world_h
            offset_x, offset_y = state.camera.get_offset()
        else:
            camera = Camera(screen_w, screen_h, world_w, world_h)
            offset_x, offset_y = camera.get_target_offset(state.player.get_center())

        # Apply Screen Shake
        if getattr(state, 'shake_timer', 0) > 0:
            import random
            offset_x += random.uniform(-SCREEN_SHAKE_INTENSITY, SCREEN_SHAKE_INTENSITY)
            offset_y += random.uniform(-SCREEN_SHAKE_INTENSITY, SCREEN_SHAKE_INTENSITY)

        # Visible tile range (add +1 to ensure partial tiles at edges are drawn)
        start_x = int(max(0, offset_x // TILE_SIZE))
        start_y = int(max(0, offset_y // TILE_SIZE))
        end_x = int(min(w, (offset_x + screen_w) // TILE_SIZE + 1))
        end_y = int(min(h, (offset_y + screen_h) // TILE_SIZE + 1))

        # 1. Draw World Grid (only visible tiles)
        for y in range(start_y, end_y):
            for x in range(start_x, end_x):
                draw_rect = (x * TILE_SIZE - offset_x, y * TILE_SIZE - offset_y, TILE_SIZE, TILE_SIZE)
                tile = state.world.grid[y][x]
                if tile == TILE_WALL:
                    pygame.draw.rect(self.screen, COLOR_WALL, draw_rect)
                elif tile == TILE_LOTUS_FRAME:
                    pygame.draw.rect(self.screen, (40, 40, 80), draw_rect) # Indigo frame
                else:
                    pygame.draw.rect(self.screen, COLOR_FLOOR, draw_rect, 1)

        # 1b. Draw Interactables & GameObjects
        for obj in getattr(state.world, 'interactables', []):
            # Check if it's a warp-type interactable (WarpPortal)
            if hasattr(obj, 'target_name'):
                self.draw_warp(obj, offset_x, offset_y)
            elif obj.name == "Respite":
                # Draw Respite sigil
                ox, oy, ow, oh = obj.rect
                center = (int(ox + ow/2 - offset_x), int(oy + oh/2 - offset_y))
                pygame.draw.circle(self.screen, COLOR_CYAN, center, 10, 2)
            elif obj.name == "Barrel":
                ox, oy, ow, oh = obj.rect
                pygame.draw.rect(self.screen, (100, 80, 40), (ox - offset_x, oy - offset_y, ow, oh))
                pygame.draw.rect(self.screen, (60, 40, 20), (ox - offset_x, oy - offset_y, ow, oh), 2)
            elif obj.name == "Structure":
                ox, oy, ow, oh = obj.rect
                pygame.draw.rect(self.screen, (80, 70, 60), (ox - offset_x, oy - offset_y, ow, oh))
            elif obj.name == "The Chronicler":
                ox, oy, ow, oh = obj.rect
                # Draw Chronicler (Tall, white-ish robe)
                pygame.draw.rect(self.screen, (220, 220, 220), (ox - offset_x, oy - offset_y, ow, oh))
                # Head
                pygame.draw.rect(self.screen, (255, 200, 150), (ox + 5 - offset_x, oy + 5 - offset_y, ow - 10, 10))
                # Outline
                pygame.draw.rect(self.screen, COLOR_BLACK, (ox - offset_x, oy - offset_y, ow, oh), 1)
            elif obj.name == "The Wellspring":
                self.draw_wellspring(obj, offset_x, offset_y)
            elif obj.name == "Heavy Bookcase":
                ox, oy, ow, oh = obj.rect
                # Draw Heavy Bookcase (Dark charcoal rectangle)
                pygame.draw.rect(self.screen, COLOR_DARK_GREY, (ox - offset_x, oy - offset_y, ow, oh))
                pygame.draw.rect(self.screen, COLOR_BLACK, (ox - offset_x, oy - offset_y, ow, oh), 2)
                # Simple shelf lines (using rect for compatibility with current test mocks)
                shelf_y = oy + oh // 2 - offset_y
                pygame.draw.rect(self.screen, COLOR_BLACK, (ox - offset_x, shelf_y, ow, 1))
            elif obj.name == "Ink Urn":
                ox, oy, ow, oh = obj.rect
                # Draw Ink Urn (Deep slate blue square)
                pygame.draw.rect(self.screen, COLOR_DEEP_SLATE, (ox - offset_x, oy - offset_y, ow, oh))
                pygame.draw.rect(self.screen, COLOR_BLACK, (ox - offset_x, oy - offset_y, ow, oh), 1)
                # Rim detail
                rim_rect = (ox + 4 - offset_x, oy + 2 - offset_y, ow - 8, 4)
                pygame.draw.rect(self.screen, COLOR_BLACK, rim_rect)
            elif obj.name == "Inkwell Puddle":
                ox, oy, ow, oh = obj.rect
                # Draw Puddle (Irregular deep blue shape)
                # For prototyping, we'll use a slightly smaller rectangle with rounded corners
                puddle_rect = (ox + 4 - offset_x, oy + 4 - offset_y, ow - 8, oh - 8)
                pygame.draw.rect(self.screen, COLOR_INK_PUDDLE, puddle_rect)
                # Optional: Add small highlight to indicate surface
                pygame.draw.rect(self.screen, (30, 30, 50), (ox + 6 - offset_x, oy + 6 - offset_y, 4, 4))
            elif obj.name == "Candelabra":
                ox, oy, ow, oh = obj.rect
                # Draw Candelabra (Thin iron stand with glow)
                stand_w = 6
                stand_rect = (ox + ow//2 - stand_w//2 - offset_x, oy + 10 - offset_y, stand_w, oh - 10)
                pygame.draw.rect(self.screen, COLOR_DARK_GREY, stand_rect)
                pygame.draw.rect(self.screen, COLOR_BLACK, stand_rect, 1)
                # Draw Light Glow (Flickering amber circle)
                import math
                import time
                flicker = (math.sin(time.time() * 10) * 0.1) + 1.0
                glow_radius = int(30 * flicker)
                # Draw glow as a semi-transparent surface
                glow_surf = pygame.Surface((glow_radius * 2, glow_radius * 2), pygame.SRCALPHA)
                pygame.draw.circle(glow_surf, (255, 190, 40, 60), (glow_radius, glow_radius), glow_radius)
                self.screen.blit(glow_surf, (ox + ow//2 - glow_radius - offset_x, oy + 5 - glow_radius - offset_y))
                # Draw Candle flame (Small bright core)
                flame_rect = (ox + ow//2 - 2 - offset_x, oy + 4 - offset_y, 4, 6)
                pygame.draw.rect(self.screen, COLOR_CANDLE_AMBER, flame_rect)
            elif obj.name == "Bench":
                ox, oy, ow, oh = obj.rect
                # Draw Bench (Dark brown base with backrest line)
                pygame.draw.rect(self.screen, (101, 67, 33), (ox - offset_x, oy - offset_y, ow, oh))
                pygame.draw.rect(self.screen, (60, 40, 20), (ox - offset_x, oy + 5 - offset_y, ow, 2))
            elif obj.name == "Rock":
                ox, oy, ow, oh = obj.rect
                # Draw Rock (Irregular grey block)
                pygame.draw.rect(self.screen, (80, 80, 80), (ox - offset_x, oy - offset_y, ow, oh))
                # Add some highlight detail (using rect for test compatibility)
                pygame.draw.rect(self.screen, (120, 120, 120), (ox + 5 - offset_x, oy + 5 - offset_y, 10, 5))
            elif hasattr(obj, 'weapon_data'):
                # Draw Weapon Drop
                from constants import COLOR_PURPLE, COLOR_WHITE
                ox, oy, ow, oh = obj.rect
                color = COLOR_PURPLE if "modifiers" in obj.weapon_data else COLOR_WHITE
                
                # Draw as a glowing book icon
                pygame.draw.rect(self.screen, color, (ox - offset_x, oy - offset_y, ow, oh))
                pygame.draw.rect(self.screen, COLOR_BLACK, (ox - offset_x, oy - offset_y, ow, oh), 1)
                
                # Add "gaze" glow
                import math
                import time
                glow = (math.sin(time.time() * 5) + 1) / 2
                pygame.draw.rect(self.screen, color, (ox - 2 - offset_x, oy - 2 - offset_y, ow + 4, oh + 4), 1)

        # 1c. Draw Loot (Torn Pages)
        for item in getattr(state, 'loot', []):
            self.draw_loot(item, offset_x, offset_y)

        # 1d. Draw Fading Entities (Destruction Animation)
        for fading in getattr(state, 'fading_entities', []):
            obj = fading['obj']
            # Calculate alpha based on remaining time (0.1s total)
            alpha = int((fading['time'] / 0.1) * 255)
            if alpha > 0:
                ox, oy, ow, oh = obj.rect
                surf = pygame.Surface((ow, oh), pygame.SRCALPHA)
                # Use same color as TILE_PROP/Barrel
                surf.fill((100, 80, 40, alpha))
                self.screen.blit(surf, (ox - offset_x, oy - offset_y))

        # 2. Draw Dummy (with camera offset)
        dummy_rect = pygame.Rect(state.dummy_rect)
        dummy_draw = pygame.Rect(dummy_rect.x - offset_x, dummy_rect.y - offset_y, dummy_rect.width, dummy_rect.height)
        pygame.draw.rect(self.screen, COLOR_GREEN, dummy_draw)
        if state.dummy_outline_timer > 0:
            pygame.draw.rect(self.screen, COLOR_WHITE, dummy_draw, 2)

        # 2b. Draw Enemies
        try:
            from engine.enemy import BatEnemy
            from constants import COLOR_PURPLE
            for enemy in getattr(state, 'enemies', []):
                er = pygame.Rect(enemy.get_rect())
                ed = pygame.Rect(er.x - offset_x, er.y - offset_y, er.width, er.height)

                if isinstance(enemy, BatEnemy):
                    pygame.draw.rect(self.screen, COLOR_PURPLE, ed)
                    # Draw small wings
                    left_wing = ((ed.left - 5, ed.centery), (ed.left, ed.centery - 5))
                    right_wing = ((ed.right + 5, ed.centery), (ed.right, ed.centery - 5))
                    pygame.draw.line(self.screen, COLOR_PURPLE, left_wing[0], left_wing[1], 2)
                    pygame.draw.line(self.screen, COLOR_PURPLE, right_wing[0], right_wing[1], 2)
                else:
                    pygame.draw.rect(self.screen, COLOR_RED, ed)

                # Draw Stagger Outline
                if getattr(enemy, 'stagger_timer', 0) > 0:
                    pygame.draw.rect(self.screen, COLOR_WHITE, ed, 2)
        except Exception:
            pass

        # 3. Draw Player (with camera offset)
        player = state.player
        player_draw = pygame.Rect(player.x - offset_x, player.y - offset_y, player.width, player.height)
        pygame.draw.rect(self.screen, COLOR_BLUE, player_draw)

        # Draw Stagger Outline for player
        if player.state == PlayerStateEnum.STAGGERED:
            pygame.draw.rect(self.screen, COLOR_WHITE, player_draw, 2)

        # 4. Draw Sword (with camera offset)
        if player.state == PlayerStateEnum.ATTACKING:
            hitbox = get_sword_hitbox(player.get_center(), player.facing)
            hitbox_draw = (hitbox[0] - offset_x, hitbox[1] - offset_y, hitbox[2], hitbox[3])
            pygame.draw.rect(self.screen, COLOR_YELLOW, hitbox_draw)

        # 5. Draw Damage Numbers (with camera offset)
        for num in state.damage_numbers:
            text_surf = self.font.render(str(num['val']), True, num['color'])
            x, y = num['pos']
            self.screen.blit(text_surf, (x - offset_x, y - offset_y))

        # 5b. Draw Interaction Prompt
        if getattr(state.player, 'current_interactable', None):
            self.draw_interaction_prompt(state.player, offset_x, offset_y)

        # 6. Draw autosave indicator if a recent autosave occurred
        try:
            if getattr(state, 'last_save_elapsed', 1e6) <= AUTOSAVE_INDICATOR_DURATION:
                indicator_surf = self.font.render("Saved", True, (200, 200, 200))
                rect = indicator_surf.get_rect()
                # Draw in top-right corner with small padding
                self.screen.blit(indicator_surf, (self.screen.get_width() - rect.width - 8, 8))
        except Exception:
            pass

        # 7. Draw minimap in the top-left corner
        try:
            self.draw_minimap(state)
        except Exception:
            pass

        # 8. Draw HUD (HP and Flask)
        try:
            self.draw_hud(state)
        except Exception:
            pass

        # 8b. Draw Dialogue
        if getattr(state, 'active_dialogue', None):
            self.draw_dialogue_box(state)

        # 8c. Draw Choice of Fates
        if getattr(state, 'active_choice', None):
            self.draw_choice_of_fates(state.active_choice)

        # 9. Apply 'Text Bleaching' (Monochrome/Grey Overlay)
        if getattr(state, 'death_timer', 0) > 0:
            overlay = pygame.Surface((self.screen.get_width(), self.screen.get_height()), pygame.SRCALPHA)
            overlay.fill((200, 200, 200, 150)) # semi-transparent light grey
            self.screen.blit(overlay, (0, 0))

            # Message
            msg_surf = self.font.render("TEXT BLEACHING...", True, COLOR_BLACK)
            msg_rect = msg_surf.get_rect(center=(self.screen.get_width()//2, self.screen.get_height()//2))
            self.screen.blit(msg_surf, msg_rect)

        pygame.display.flip()

    def draw_hud(self, state):
        """Draw player HP, Flask, and Dual Weapon slots with a [SWAP] button."""
        from constants import (
            COLOR_WHITE, COLOR_BLUE, COLOR_YELLOW, UI_ALPHA, COLOR_GREY, COLOR_PURPLE,
            HUD_PANEL_W, HUD_PANEL_H, HUD_SLOT_W, HUD_SLOT_H, HUD_SWAP_BTN_RECT
        )
        player = state.player
        hp_text = f"HP: {int(player.hp)}/{int(player.max_hp)}"
        flask_text = f"Flasks: {player.flask_charges}"

        pages = 0
        if state.stats:
            try:
                pages = state.stats.data["lifetime_stats"].get("pages_collected", 0)
            except Exception:
                pass
        pages_text = f"Pages: {pages}"

        # Draw background panel
        hud_surf = pygame.Surface((HUD_PANEL_W, HUD_PANEL_H), pygame.SRCALPHA)
        hud_surf.fill((20, 20, 25, UI_ALPHA))
        pygame.draw.rect(hud_surf, (100, 100, 100), (0, 0, HUD_PANEL_W, HUD_PANEL_H), 2)

        # Basic Stats
        hp_surf = self.font.render(hp_text, True, COLOR_WHITE)
        flask_surf = self.font.render(flask_text, True, COLOR_BLUE)
        pages_surf = self.font.render(pages_text, True, COLOR_YELLOW)
        hud_surf.blit(hp_surf, (10, 10))
        hud_surf.blit(flask_surf, (140, 10))
        hud_surf.blit(pages_surf, (240, 10))

        # Weapon Slots
        for i in range(2):
            slot_x = 10 + i * (HUD_SLOT_W + 100)
            slot_y = 45
            slot_rect = pygame.Rect(slot_x, slot_y, HUD_SLOT_W, HUD_SLOT_H)
            
            # Highlight active slot
            border_color = COLOR_YELLOW if i == player.active_weapon_idx else COLOR_GREY
            pygame.draw.rect(hud_surf, (40, 40, 50), slot_rect)
            pygame.draw.rect(hud_surf, border_color, slot_rect, 2)
            
            # Slot Label
            label = "SLOT A" if i == 0 else "SLOT B"
            label_surf = pygame.font.SysFont("Arial", 12).render(label, True, COLOR_GREY)
            hud_surf.blit(label_surf, (slot_x + 5, slot_y + 2))
            
            # Weapon Content
            if i < len(player.weapons):
                wpn = player.weapons[i]
                wpn_name = wpn.get("name", "Unknown")
                # Tier color: Anomalous = Purple, else White
                name_color = COLOR_PURPLE if "modifiers" in wpn else COLOR_WHITE
                
                # Render name (possibly truncated)
                name_surf = pygame.font.SysFont("Arial", 14).render(wpn_name[:12], True, name_color)
                hud_surf.blit(name_surf, (slot_x + 5, slot_y + 20))
                
                dmg_surf = pygame.font.SysFont("Arial", 12).render(f"DMG: {wpn.get('damage', 0)}", True, COLOR_GREY)
                hud_surf.blit(dmg_surf, (slot_x + 5, slot_y + 40))

        # [SWAP] Button
        swap_rect = pygame.Rect(HUD_SWAP_BTN_RECT)
        pygame.draw.rect(hud_surf, (60, 60, 80), swap_rect)
        pygame.draw.rect(hud_surf, COLOR_WHITE, swap_rect, 1)
        swap_text = pygame.font.SysFont("Arial", 14, bold=True).render("SWAP", True, COLOR_WHITE)
        hud_surf.blit(swap_text, (swap_rect.centerx - swap_text.get_width()//2, swap_rect.centery - swap_text.get_height()//2))

        self.screen.blit(hud_surf, (10, self.screen.get_height() - HUD_PANEL_H - 10))

    def draw_loot(self, item, offset_x, offset_y):
        """Draw loot items with prototype graphics."""
        from engine.loot import TornPage, HealItem
        if isinstance(item, TornPage):
            ir = item.get_rect()
            draw_rect = pygame.Rect(ir[0] - offset_x, ir[1] - offset_y, ir[2], ir[3])
            # Draw as a small white rectangle (parchment) with a yellow outline (glow)
            pygame.draw.rect(self.screen, COLOR_WHITE, draw_rect)
            pygame.draw.rect(self.screen, COLOR_YELLOW, draw_rect, 1)
        elif isinstance(item, HealItem):
            ir = item.get_rect()
            draw_rect = pygame.Rect(ir[0] - offset_x, ir[1] - offset_y, ir[2], ir[3])
            # Draw as a small red rectangle with a white cross
            pygame.draw.rect(self.screen, (200, 50, 50), draw_rect)
            # White cross
            pygame.draw.rect(self.screen, COLOR_WHITE, (draw_rect.centerx - 2, draw_rect.y + 2, 4, draw_rect.height - 4))
            pygame.draw.rect(self.screen, COLOR_WHITE, (draw_rect.x + 2, draw_rect.centery - 2, draw_rect.width - 4, 4))

    def draw_minimap(self, state):
        """Draw a small minimap in the top-left corner showing walls and player.

        The minimap scales the entire world to MINIMAP_WIDTH x MINIMAP_HEIGHT and
        draws a small rectangle for wall tiles and a distinct marker for the player.
        """
        from constants import (
            MINIMAP_WIDTH, MINIMAP_HEIGHT, MINIMAP_PADDING, TILE_SIZE,
            MINIMAP_WALL_COLOR, MINIMAP_PLAYER_COLOR,
            MINIMAP_ENEMY_COLOR, MINIMAP_LOOT_COLOR
        )

        h = len(state.world.grid)
        w = len(state.world.grid[0]) if h > 0 else 0

        # Background rect for minimap
        minimap_bg = pygame.Surface((MINIMAP_WIDTH, MINIMAP_HEIGHT), pygame.SRCALPHA)
        minimap_bg.fill((10, 10, 10, UI_ALPHA))
        self.screen.blit(minimap_bg, (MINIMAP_PADDING, MINIMAP_PADDING))

        world_w = w * TILE_SIZE
        world_h = h * TILE_SIZE
        if world_w == 0 or world_h == 0:
            return

        # Determine viewport in world-space centered on player
        from constants import MINIMAP_VIEWPORT_FRAC
        frac = max(0.1, float(MINIMAP_VIEWPORT_FRAC))
        vp_w = int(world_w * frac)
        vp_h = int(world_h * frac)

        # Clamp viewport to at most the world size
        if vp_w > world_w:
            vp_w = world_w
        if vp_h > world_h:
            vp_h = world_h

        # Center viewport on player
        px_c, py_c = state.player.get_center()
        vp_x0 = int(px_c - vp_w // 2)
        vp_y0 = int(py_c - vp_h // 2)
        # Clamp viewport to world bounds
        vp_x0 = max(0, min(vp_x0, max(0, world_w - vp_w)))
        vp_y0 = max(0, min(vp_y0, max(0, world_h - vp_h)))

        # Avoid division by zero
        if vp_w == 0 or vp_h == 0:
            return

        scale_x = MINIMAP_WIDTH / vp_w
        scale_y = MINIMAP_HEIGHT / vp_h

        # Draw walls that fall within the viewport
        for y in range(h):
            for x in range(w):
                if state.world.grid[y][x] == TILE_WALL:
                    wx_world = x * TILE_SIZE
                    wy_world = y * TILE_SIZE
                    # Check if wall is inside viewport (simple AABB)
                    if wx_world + TILE_SIZE < vp_x0 or wx_world > vp_x0 + vp_w:
                        continue
                    if wy_world + TILE_SIZE < vp_y0 or wy_world > vp_y0 + vp_h:
                        continue
                    # Map to minimap coords relative to viewport origin
                    wx = MINIMAP_PADDING + int((wx_world - vp_x0) * scale_x)
                    wy = MINIMAP_PADDING + int((wy_world - vp_y0) * scale_y)
                    w = max(1, int(TILE_SIZE * scale_x))
                    h = max(1, int(TILE_SIZE * scale_y))
                    pygame.draw.rect(self.screen, MINIMAP_WALL_COLOR, (wx, wy, w, h))

        # Draw enemies on the minimap
        for enemy in getattr(state, 'enemies', []):
            ex, ey = enemy.x + enemy.width // 2, enemy.y + enemy.height // 2
            if vp_x0 <= ex <= vp_x0 + vp_w and vp_y0 <= ey <= vp_y0 + vp_h:
                emx = MINIMAP_PADDING + int((ex - vp_x0) * scale_x)
                emy = MINIMAP_PADDING + int((ey - vp_y0) * scale_y)
                pygame.draw.rect(self.screen, MINIMAP_ENEMY_COLOR, (emx-1, emy-1, 3, 3))

        # Draw loot on the minimap
        for item in getattr(state, 'loot', []):
            lx, ly = item.x + item.width // 2, item.y + item.height // 2
            if vp_x0 <= lx <= vp_x0 + vp_w and vp_y0 <= ly <= vp_y0 + vp_h:
                lmx = MINIMAP_PADDING + int((lx - vp_x0) * scale_x)
                lmy = MINIMAP_PADDING + int((ly - vp_y0) * scale_y)
                pygame.draw.rect(self.screen, MINIMAP_LOOT_COLOR, (lmx-1, lmy-1, 3, 3))

        # Draw player marker centered in the viewport
        mx = MINIMAP_PADDING + int((px_c - vp_x0) * scale_x)
        my = MINIMAP_PADDING + int((py_c - vp_y0) * scale_y)
        pygame.draw.rect(self.screen, MINIMAP_PLAYER_COLOR, (mx-2, my-2, 4, 4))

        # Draw compass indicators for off-screen objectives
        for obj_x, obj_y in getattr(state, 'objectives', []):
            # If objective is inside world-space viewport, we could show it normally,
            # but the spec asks specifically for edge indicators for off-screen.
            if vp_x0 <= obj_x <= vp_x0 + vp_w and vp_y0 <= obj_y <= vp_y0 + vp_h:
                continue

            dx = obj_x - px_c
            dy = obj_y - py_c
            if dx == 0 and dy == 0:
                continue

            # Minimap bounds relative to player marker (mx, my)
            rel_left = MINIMAP_PADDING - mx
            rel_right = MINIMAP_PADDING + MINIMAP_WIDTH - mx
            rel_top = MINIMAP_PADDING - my
            rel_bottom = MINIMAP_PADDING + MINIMAP_HEIGHT - my

            # Find intersection with the minimap rectangle boundary
            k = 1e9
            if dx > 0:
                k = min(k, rel_right / dx)
            elif dx < 0:
                k = min(k, rel_left / dx)

            if dy > 0:
                k = min(k, rel_bottom / dy)
            elif dy < 0:
                k = min(k, rel_top / dy)

            ix = int(mx + k * dx)
            iy = int(my + k * dy)

            # Final clamping to ensure precision errors don't push it outside
            ix = max(MINIMAP_PADDING, min(ix, MINIMAP_PADDING + MINIMAP_WIDTH - 3))
            iy = max(MINIMAP_PADDING, min(iy, MINIMAP_PADDING + MINIMAP_HEIGHT - 3))

            pygame.draw.rect(self.screen, COLOR_WHITE, (ix, iy, 3, 3))

    def draw_title_screen(self, selected_index_or_menu=0):
        """Draw the title screen with a simple menu.

        Accepts either a selected index (int) or a menu object implementing
        get_options() and get_selected_index(). This allows TitleMenu to drive
        the displayed options (e.g., New Game / Continue / Quit).
        """
        self.screen.fill(COLOR_BLACK)

        # 1. Draw the base title background/void mask
        title_surf = self.font.render("AVOID RAIN", True, COLOR_WHITE)
        instr_surf = self.font.render("Use ARROW KEYS and ENTER to choose", True, COLOR_WHITE)

        title_rect = title_surf.get_rect(center=(self.screen.get_width()//2, 220))
        instr_rect = instr_surf.get_rect(center=(self.screen.get_width()//2, 280))

        self.screen.blit(title_surf, title_rect)
        self.screen.blit(instr_surf, instr_rect)

        # Resolve options and selected index from parameter
        options = ["New Game", "Quit"]
        selected_index = 0
        menu_state = None

        from engine.title_menu import TitleMenuState

        try:
            # If passed an object with get_options, use it
            if hasattr(selected_index_or_menu, 'get_options'):
                options = selected_index_or_menu.get_options()
                selected_index = selected_index_or_menu.get_selected_index()
                menu_state = getattr(selected_index_or_menu, 'state', TitleMenuState.MAIN)
            else:
                # treat as integer index
                selected_index = int(selected_index_or_menu)
                menu_state = TitleMenuState.MAIN
        except Exception:
            options = ["New Game", "Quit"]
            selected_index = 0
            menu_state = TitleMenuState.MAIN

        for idx, opt in enumerate(options):
            color = COLOR_YELLOW if idx == selected_index else COLOR_WHITE
            opt_surf = self.font.render(opt, True, color)
            opt_rect = opt_surf.get_rect(center=(self.screen.get_width()//2, 340 + idx * 40))
            self.screen.blit(opt_surf, opt_rect)

        # 2. Draw confirmation overlay if in CONFIRM_NEW_GAME state
        if menu_state == TitleMenuState.CONFIRM_NEW_GAME:
            # Semi-transparent dark overlay for the whole screen
            overlay = pygame.Surface((self.screen.get_width(), self.screen.get_height()), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 200))
            self.screen.blit(overlay, (0, 0))

            # Confirmation box (card box)
            box_w, box_h = 600, 150
            box_rect = pygame.Rect(0, 0, box_w, box_h)
            box_rect.center = self.screen.get_rect().center

            pygame.draw.rect(self.screen, (30, 30, 30), box_rect)
            pygame.draw.rect(self.screen, COLOR_WHITE, box_rect, 2)

            # Confirmation text - anchor to center of viewport
            msg = "Are you sure you want to start a New Game? (Y/N)"
            confirm_surf = self.font.render(msg, True, COLOR_WHITE)
            confirm_rect = confirm_surf.get_rect(center=self.screen.get_rect().center)

            # Warning about losing progress
            warning_msg = "This will permanently remove old progress."
            warning_surf = self.font.render(warning_msg, True, COLOR_RED)
            warning_center = (self.screen.get_rect().centerx, self.screen.get_rect().centery + 30)
            warning_rect = warning_surf.get_rect(center=warning_center)

            self.screen.blit(confirm_surf, confirm_rect)
            self.screen.blit(warning_surf, warning_rect)
        elif getattr(menu_state, 'name', '') == 'CONTROLS':
            self.draw_controls_overlay(show_editor_keys=True)
            return

        pygame.display.flip()

    def fade_to_black(self):
        """Simple fade out effect."""
        fade_surf = pygame.Surface((self.screen.get_width(), self.screen.get_height()))
        fade_surf.fill(COLOR_BLACK)
        for alpha in range(0, 300, 5):
            fade_surf.set_alpha(alpha)
            self.screen.blit(fade_surf, (0, 0))
            pygame.display.flip()
            pygame.time.delay(10)

    def draw_loading_screen(self, message: str, submessage: str | None = None, min_time: float = 2.0, sleep_func=None):
        """Draw a loading screen with a message and optional submessage.

        The function enforces a minimum display time (min_time). sleep_func
        may be injected for tests (defaults to time.sleep).
        """
        import time
        sleep = sleep_func if sleep_func is not None else time.sleep

        self.screen.fill(COLOR_BLACK)
        title_surf = self.font.render(message, True, COLOR_WHITE)
        title_rect = title_surf.get_rect(center=(self.screen.get_width()//2, self.screen.get_height()//2 - 20))
        self.screen.blit(title_surf, title_rect)
        if submessage is not None:
            sub_surf = self.font.render(submessage, True, COLOR_WHITE)
            sub_rect = sub_surf.get_rect(center=(self.screen.get_width()//2, self.screen.get_height()//2 + 20))
            self.screen.blit(sub_surf, sub_rect)
        pygame.display.flip()
        # Ensure the loading screen is visible for at least min_time
        sleep(min_time)

    def draw_pause_menu(self, pause_menu_or_index=0):
        """Draw a simple pause overlay with 'Paused' text.

        Accepts either a selected index (int) or a menu object implementing
        get_options() and get_selected_index().
        """
        options = ["Resume", "Controls", "Quit"]
        selected_index = 0
        menu_state = None

        try:
            from engine.pause_menu import PauseMenuState
            if hasattr(pause_menu_or_index, 'get_options'):
                options = pause_menu_or_index.get_options()
                selected_index = pause_menu_or_index.get_selected_index()
                menu_state = getattr(pause_menu_or_index, 'state', PauseMenuState.MAIN)
            else:
                selected_index = int(pause_menu_or_index)
                menu_state = PauseMenuState.MAIN
        except Exception:
            pass

        if menu_state and getattr(menu_state, 'name', '') == 'CONTROLS':
            self.draw_controls_overlay(show_editor_keys=False)
            return

        overlay = pygame.Surface(
            (self.screen.get_width(), self.screen.get_height()), pygame.SRCALPHA
        )
        overlay.fill((0, 0, 0, 180))  # semi-transparent dark overlay
        self.screen.blit(overlay, (0, 0))
        pause_surf = self.font.render("PAUSED", True, COLOR_WHITE)
        # Show instructions and menu options
        instr_surf = self.font.render("Use ARROW KEYS and ENTER to choose", True, COLOR_WHITE)
        
        # Draw main pause text
        pause_rect = pause_surf.get_rect(
            center=(self.screen.get_width()//2, self.screen.get_height()//2 - 50)
        )
        self.screen.blit(pause_surf, pause_rect)
        # Draw instruction
        instr_rect = instr_surf.get_rect(
            center=(self.screen.get_width()//2, self.screen.get_height()//2 - 20)
        )
        self.screen.blit(instr_surf, instr_rect)
        # Draw options with highlight based on selected_index
        for idx, opt in enumerate(options):
            color = COLOR_YELLOW if idx == selected_index else COLOR_WHITE
            opt_surf = self.font.render(opt, True, color)
            opt_rect = opt_surf.get_rect(
                center=(self.screen.get_width()//2, self.screen.get_height()//2 + 10 + idx * 30)
            )
            self.screen.blit(opt_surf, opt_rect)
        pygame.display.flip()

    def draw_controls_overlay(self, show_editor_keys=True):
        """Draw the Controls overlay used by Title and Pause menus."""
        overlay = pygame.Surface((self.screen.get_width(), self.screen.get_height()), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, UI_ALPHA))
        self.screen.blit(overlay, (0, 0))

        # Render Tabs
        tab_y = 60
        kb_surf = self.font.render("[ Keyboard ]", True, COLOR_WHITE)
        ctrl_surf = self.font.render("[ Controller ] (Not Implemented)", True, COLOR_GREY)
        
        cx = self.screen.get_width() // 2
        self.screen.blit(kb_surf, kb_surf.get_rect(center=(cx - 150, tab_y)))
        self.screen.blit(ctrl_surf, ctrl_surf.get_rect(center=(cx + 150, tab_y)))

        # Draw Title
        title_surf = self.font.render("CONTROLS", True, COLOR_YELLOW)
        self.screen.blit(title_surf, title_surf.get_rect(center=(cx, tab_y + 60)))

        # Draw Inputs
        inputs = [
            ("Movement:", "WASD / Arrows"),
            ("Attack / Interact:", "Space / E"),
            ("Dash:", "Left Shift"),
            ("Flask:", "1"),
            ("Block:", "K"),
            ("Weapon Swap:", "Q"),
            ("Pause Run:", "Escape"),
        ]
        if show_editor_keys:
            inputs.extend([
                ("Editor Box Fill:", "B / Click-and-Drag"),
                ("Canvas Stretch:", "+/- and Ctrl + +/-")
            ])

        start_y = tab_y + 120
        spacing = 40
        for i, (action, keys) in enumerate(inputs):
            action_surf = self.font.render(action, True, COLOR_WHITE)
            keys_surf = self.font.render(keys, True, COLOR_CYAN)
            
            # Align action to the right of center-10, keys to the left of center+10
            action_rect = action_surf.get_rect(midright=(cx - 20, start_y + i * spacing))
            keys_rect = keys_surf.get_rect(midleft=(cx + 20, start_y + i * spacing))
            
            self.screen.blit(action_surf, action_rect)
            self.screen.blit(keys_surf, keys_rect)

        # Draw Back instruction
        back_surf = self.font.render("Press SPACE or ENTER to go back", True, COLOR_WHITE)
        self.screen.blit(back_surf, back_surf.get_rect(center=(cx, start_y + len(inputs) * spacing + 40)))
        
        pygame.display.flip()
