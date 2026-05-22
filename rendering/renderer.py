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
    GRID_WIDTH,
    GRID_HEIGHT,
    COLOR_YELLOW,
    COLOR_GREY,
    COLOR_RED,
    COLOR_CYAN,
    COLOR_DARK_GREY,
    TILE_LOTUS_FRAME
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
        else:
            prompt_text = f"Interact with {target.name}" if hasattr(target, 'name') else "Interact"
            
        # AGENTS.md specifies "Press [ATTACK] to Speak"
        prompt_surf = self.font.render(f"Press [SPACE] to {prompt_text}", True, COLOR_WHITE)
        rect = prompt_surf.get_rect()
        # Position above player center
        px, py = player.get_center()
        self.screen.blit(prompt_surf, (px - rect.width // 2 - offset_x, py - player.height - 20 - offset_y))

    def draw_dialogue_box(self, dialogue):
        """Draw a dialogue box at the bottom of the screen."""
        if not dialogue:
            return
            
        speaker = dialogue.get("speaker", "Unknown")
        text = dialogue.get("text", "")
        
        # Panel dimensions
        margin = 50
        width = self.screen.get_width() - margin * 2
        height = 150
        x = margin
        y = self.screen.get_height() - height - 20
        
        # Draw background panel
        panel_rect = pygame.Rect(x, y, width, height)
        pygame.draw.rect(self.screen, (20, 20, 20), panel_rect)
        pygame.draw.rect(self.screen, COLOR_WHITE, panel_rect, 2)
        
        # Draw speaker name
        speaker_surf = self.font.render(speaker, True, COLOR_YELLOW)
        self.screen.blit(speaker_surf, (x + 20, y + 10))
        
        # Draw text (wrapped)
        words = text.split(' ')
        lines = []
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
            self.screen.blit(line_surf, (x + 20, y + 50 + i * 30))
            
        # Instruction to close
        close_surf = self.font.render("Press [SPACE] to continue", True, COLOR_GREY)
        self.screen.blit(close_surf, (x + width - close_surf.get_width() - 20, y + height - 30))

    def render(self, state):
        """Draw the visible portion of the game state to the screen using a camera.

        The camera attempts to center on the player but is clamped to the world
        bounds so the viewport never shows outside the world.
        """
        self.screen.fill(COLOR_BLACK)

        # Use camera from the game state if available; otherwise create a transient one
        screen_w = self.screen.get_width()
        screen_h = self.screen.get_height()
        world_w = GRID_WIDTH * TILE_SIZE
        world_h = GRID_HEIGHT * TILE_SIZE

        if hasattr(state, 'camera'):
            # Ensure camera screen size matches the current screen (window resize)
            # (camera keeps its own screen_w/h so update if needed)
            if state.camera.screen_w != screen_w or state.camera.screen_h != screen_h:
                state.camera.screen_w = screen_w
                state.camera.screen_h = screen_h
            offset_x, offset_y = state.camera.get_offset()
        else:
            camera = Camera(screen_w, screen_h, world_w, world_h)
            offset_x, offset_y = camera.get_target_offset(state.player.get_center())

        # Visible tile range (add +1 to ensure partial tiles at edges are drawn)
        start_x = max(0, offset_x // TILE_SIZE)
        start_y = max(0, offset_y // TILE_SIZE)
        end_x = min(GRID_WIDTH, (offset_x + screen_w) // TILE_SIZE + 1)
        end_y = min(GRID_HEIGHT, (offset_y + screen_h) // TILE_SIZE + 1)

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
                pygame.draw.circle(self.screen, COLOR_CYAN, (int(ox + ow/2 - offset_x), int(oy + oh/2 - offset_y)), 10, 2)
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
            for enemy in getattr(state, 'enemies', []):
                er = pygame.Rect(enemy.get_rect())
                ed = pygame.Rect(er.x - offset_x, er.y - offset_y, er.width, er.height)
                pygame.draw.rect(self.screen, COLOR_RED, ed)
        except Exception:
            pass

        # 3. Draw Player (with camera offset)
        player = state.player
        player_draw = pygame.Rect(player.x - offset_x, player.y - offset_y, player.width, player.height)
        pygame.draw.rect(self.screen, COLOR_BLUE, player_draw)

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
            self.draw_dialogue_box(state.active_dialogue)

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
        """Draw player HP and Flask charges in the bottom-left corner."""
        player = state.player
        hp_text = f"HP: {int(player.hp)} / {int(player.max_hp)}"
        flask_text = f"Flasks: {player.flask_charges}"
        
        pages = 0
        if state.stats:
            try:
                pages = state.stats.data["lifetime_stats"].get("pages_collected", 0)
            except Exception:
                pass
        pages_text = f"Pages: {pages}"

        hp_surf = self.font.render(hp_text, True, COLOR_WHITE)
        flask_surf = self.font.render(flask_text, True, COLOR_BLUE)
        pages_surf = self.font.render(pages_text, True, COLOR_YELLOW)

        # Draw background panel
        panel_rect = pygame.Rect(10, self.screen.get_height() - 95, 200, 85)
        pygame.draw.rect(self.screen, (30, 30, 30), panel_rect)
        pygame.draw.rect(self.screen, (100, 100, 100), panel_rect, 2)

        self.screen.blit(hp_surf, (20, self.screen.get_height() - 85))
        self.screen.blit(flask_surf, (20, self.screen.get_height() - 60))
        self.screen.blit(pages_surf, (20, self.screen.get_height() - 35))

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
        from constants import MINIMAP_WIDTH, MINIMAP_HEIGHT, MINIMAP_PADDING, TILE_SIZE, GRID_WIDTH, GRID_HEIGHT, MINIMAP_WALL_COLOR, MINIMAP_PLAYER_COLOR

        # Background rect for minimap
        bg_rect = (MINIMAP_PADDING, MINIMAP_PADDING, MINIMAP_WIDTH, MINIMAP_HEIGHT)
        pygame.draw.rect(self.screen, (10, 10, 10), bg_rect)

        world_w = GRID_WIDTH * TILE_SIZE
        world_h = GRID_HEIGHT * TILE_SIZE
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
        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH):
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

        # Draw player marker centered in the viewport
        mx = MINIMAP_PADDING + int((px_c - vp_x0) * scale_x)
        my = MINIMAP_PADDING + int((py_c - vp_y0) * scale_y)
        pygame.draw.rect(self.screen, MINIMAP_PLAYER_COLOR, (mx-2, my-2, 4, 4))

    def draw_title_screen(self, selected_index_or_menu=0):
        """Draw the title screen with a simple menu.

        Accepts either a selected index (int) or a menu object implementing
        get_options() and get_selected_index(). This allows TitleMenu to drive
        the displayed options (e.g., New Game / Continue / Quit).
        """
        self.screen.fill(COLOR_BLACK)
        title_surf = self.font.render("AVOID RAIN", True, COLOR_WHITE)
        instr_surf = self.font.render("Use ARROW KEYS and ENTER to choose", True, COLOR_WHITE)

        title_rect = title_surf.get_rect(center=(self.screen.get_width()//2, 220))
        instr_rect = instr_surf.get_rect(center=(self.screen.get_width()//2, 280))

        self.screen.blit(title_surf, title_rect)
        self.screen.blit(instr_surf, instr_rect)

        # Resolve options and selected index from parameter
        options = ["New Game", "Quit"]
        selected_index = 0
        try:
            # If passed an object with get_options, use it
            if hasattr(selected_index_or_menu, 'get_options'):
                options = selected_index_or_menu.get_options()
                selected_index = selected_index_or_menu.get_selected_index()
            else:
                # treat as integer index
                selected_index = int(selected_index_or_menu)
        except Exception:
            options = ["New Game", "Quit"]
            selected_index = 0

        for idx, opt in enumerate(options):
            color = COLOR_YELLOW if idx == selected_index else COLOR_WHITE
            opt_surf = self.font.render(opt, True, color)
            opt_rect = opt_surf.get_rect(center=(self.screen.get_width()//2, 340 + idx * 40))
            self.screen.blit(opt_surf, opt_rect)
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

    def draw_pause_menu(self, selected_index: int = 0):
        """Draw a simple pause overlay with 'Paused' text.

        selected_index controls which menu option is highlighted.
        """
        overlay = pygame.Surface(
            (self.screen.get_width(), self.screen.get_height()), pygame.SRCALPHA
        )
        overlay.fill((0, 0, 0, 180))  # semi-transparent dark overlay
        self.screen.blit(overlay, (0, 0))
        pause_surf = self.font.render("PAUSED", True, COLOR_WHITE)
        # Show instructions and menu options
        instr_surf = self.font.render("Use ARROW KEYS and ENTER to choose", True, COLOR_WHITE)
        options = ["Resume", "Quit"]
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
