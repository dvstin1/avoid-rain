"""
Native Pygame-based Map Editor for Avoid Rain.
Supports click-and-drag drawing, canvas resizing, and JSON export.
"""
import sys
import os
import json
import pygame
# pylint: disable=no-member

# Add project root to path so we can import engine/rendering
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# pylint: disable=wrong-import-position
from constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, COLOR_WHITE, COLOR_BLUE, COLOR_YELLOW,
    COLOR_RED, COLOR_CHARCOAL, COLOR_WALL, COLOR_FLOOR, TILE_SIZE,
    COLOR_PURPLE, COLOR_GREY, COLOR_CYAN
)

# List of enemy types for the cyclic button
ENEMY_TYPES = [
    ('A', 'Bat'),
    ('Z', 'Slug'),
    ('f', 'Flutter'),
    ('b', 'Bindling'),
    ('E', 'M1 - Ink-Stained'),
    ('2', 'M2 - Bleeding Scribe'),
    ('3', 'M3 - Forgotten Binder')
]

# Legend for the editor palette - Synchronized with constants.py
PALETTE = [
    ('#', 'WALL'),
    ('.', 'EMPTY'),
    ('B', 'BARREL'),
    ('S', 'BENCH'),
    ('l', 'CANDELABRA'),
    ('v', 'INK_PUDDLE'),
    ('d', 'INK_URN'),
    ('h', 'BOOKCASE'),
    ('T', 'STRUCTURE'),
    ('K', 'ROCK'),
    ('W', 'WARP'),
    ('P', 'PLAYER_START'),
    ('C', 'CHRONICLER'),
    ('F', 'WELLSPRING'),
    ('L', 'LORE'),
    ('R', 'RESPITE'),
    ('MONSTER', 'Monster (Cyclic)')
]

class MapEditor:
    """Main application class for the Map Editor."""
    def __init__(self, width=40, height=30):
        pygame.init()
        # Expanded width for sidebar
        self.sidebar_width = 250
        self.screen = pygame.display.set_mode((SCREEN_WIDTH + self.sidebar_width, SCREEN_HEIGHT))
        pygame.display.set_caption("Avoid Rain Map Editor")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Arial", 18)
        self.large_font = pygame.font.SysFont("Arial", 32)

        self.map_w = width
        self.map_h = height
        self.grid = [['#' for _ in range(width)] for _ in range(height)]
        self.entities = {}
        self.module_sockets = []

        self.brush_idx = 0
        self.current_enemy_idx = 0
        self.camera_x = 0
        self.camera_y = 0
        self.zoom = 1.0

        self.filename = None
        self.input_mode = None  # 'SAVE', 'LOAD', 'PICKER', 'SOCKET_NAME', 'RESIZE_W', 'RESIZE_H'
        self.input_buffer = ""
        
        # File Picker State
        self.map_files = []
        self.file_picker_idx = 0
        self.scroll_offset = 0

        # Tool State
        self.active_tool = "PENCIL"  # "PENCIL", "RECTANGLE", or "SOCKET"
        self.is_dragging = False
        self.drag_start = (0, 0)
        self.drag_current = (0, 0)
        self.pending_socket_bounds = None
        self.selected_socket_idx = -1

    def reset_canvas(self, width=40, height=30):
        """Creates a blank canvas and resets all variables."""
        self.map_w = width
        self.map_h = height
        self.grid = [['#' for _ in range(width)] for _ in range(height)]
        self.entities = {}
        self.module_sockets = []
        self.filename = None
        self.camera_x = 0
        self.camera_y = 0
        self.zoom = 1.0
        self.input_mode = None
        self.input_buffer = ""
        self.active_tool = "PENCIL"
        self.is_dragging = False
        self.selected_socket_idx = -1
        print("Canvas reset to blank.")

    def load_map(self, name):
        """Loads a map from the maps/ directory."""
        if not name.endswith(".json"):
            name += ".json"
        json_path = os.path.join("maps", name)
        if not os.path.exists(json_path):
            print(f"File not found: {json_path}")
            return

        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.map_w = data["dimensions"]["width"]
            self.map_h = data["dimensions"]["height"]
            self.grid = [list(row) for row in data["grid"]]
            self.entities = data.get("entities", {})
            self.module_sockets = data.get("module_sockets", [])
            self.filename = name
            print(f"Loaded {self.filename}")
        except Exception as e:
            print(f"Failed to load map: {e}")

    def save_map(self):
        """Saves the current map to the maps/ directory."""
        if not self.filename.endswith(".json"):
            self.filename += ".json"

        # Construct full legend including all cyclic enemies
        full_legend = dict(PALETTE)
        del full_legend['MONSTER']
        for char, name in ENEMY_TYPES:
            full_legend[char] = name

        data = {
            "map_id": self.filename.replace(".json", ""),
            "dimensions": {"width": self.map_w, "height": self.map_h},
            "legend": full_legend,
            "grid": ["".join(row) for row in self.grid],
            "entities": self.entities,
            "module_sockets": self.module_sockets
        }

        os.makedirs("maps", exist_ok=True)
        path = os.path.join("maps", self.filename)
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            print(f"Saved to {path}")
        except Exception as e:
            print(f"Failed to save map: {e}")

    def fill_rectangle(self):
        """Fills the selected rectangle with the current brush."""
        x1, y1 = self.drag_start
        x2, y2 = self.drag_current
        gx1, gx2 = min(x1, x2), max(x1, x2)
        gy1, gy2 = min(y1, y2), max(y1, y2)

        char = PALETTE[self.brush_idx][0]
        if char == 'MONSTER':
            char = ENEMY_TYPES[self.current_enemy_idx][0]
        for y in range(max(0, gy1), min(self.map_h, gy2 + 1)):
            for x in range(max(0, gx1), min(self.map_w, gx2 + 1)):
                self.grid[y][x] = char

    def draw_grid(self, ts):
        """Draws the map grid."""
        for y in range(self.map_h):
            for x in range(self.map_w):
                rect = pygame.Rect(
                    x * ts - self.camera_x,
                    y * ts - self.camera_y,
                    ts, ts
                )

                char = self.grid[y][x]
                color = COLOR_FLOOR
                if char == '#':
                    color = COLOR_WALL
                elif char == 'W':
                    color = COLOR_PURPLE
                elif char == 'P':
                    color = COLOR_BLUE
                elif char in ('A', 'Z', 'E', '2', '3', 'f', 'b'):
                    color = COLOR_RED

                pygame.draw.rect(self.screen, color, rect)
                pygame.draw.rect(self.screen, (50, 50, 50), rect, 1)

                if ts > 10:
                    sym_surf = self.font.render(char, True, COLOR_WHITE)
                    self.screen.blit(sym_surf, (rect.x + 2, rect.y + 2))

        # Draw Module Sockets
        for i, socket in enumerate(self.module_sockets):
            b = socket["bounds"]
            s_rect = pygame.Rect(
                b["x"] * ts - self.camera_x,
                b["y"] * ts - self.camera_y,
                b["width"] * ts,
                b["height"] * ts
            )
            color = COLOR_YELLOW if i == self.selected_socket_idx else COLOR_CYAN
            pygame.draw.rect(self.screen, color, s_rect, 3)

            # HUD Label: Name + Dimensions
            label = f"{socket['name']} ({b['width']}x{b['height']})"
            name_surf = self.font.render(label, True, color)
            self.screen.blit(name_surf, (s_rect.x + 5, s_rect.y + 5))


    def draw_selection_preview(self, ts):
        """Draws a transparent preview of the rectangle being drawn."""
        if not self.is_dragging or self.active_tool not in ("RECTANGLE", "SOCKET"):
            return

        x1, y1 = self.drag_start
        x2, y2 = self.drag_current
        gx1, gx2 = min(x1, x2), max(x1, x2)
        gy1, gy2 = min(y1, y2), max(y1, y2)

        rect = pygame.Rect(
            gx1 * ts - self.camera_x,
            gy1 * ts - self.camera_y,
            (gx2 - gx1 + 1) * ts,
            (gy2 - gy1 + 1) * ts
        )

        # Draw transparent fill
        preview_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        if self.active_tool == "RECTANGLE":
            color = (0, 120, 255, 80)
            outline_color = (0, 120, 255)
        else:
            color = (0, 255, 255, 80)
            outline_color = (0, 255, 255)
        
        preview_surf.fill(color)
        self.screen.blit(preview_surf, (rect.x, rect.y))
        # Draw opaque outline
        pygame.draw.rect(self.screen, outline_color, rect, 2)

    def draw_sidebar(self, sidebar_x):
        """Draws the UI sidebar."""
        pygame.draw.rect(self.screen, (20, 20, 20), (sidebar_x, 0, self.sidebar_width, SCREEN_HEIGHT))
        pygame.draw.line(self.screen, COLOR_GREY, (sidebar_x, 0), (sidebar_x, SCREEN_HEIGHT), 2)

        y_off = 20
        fname = self.filename if self.filename else "UNTITLED"
        self.screen.blit(self.font.render(f"File: {fname}", True, COLOR_WHITE), (sidebar_x + 10, y_off))
        y_off += 25
        size_text = f"Size: {self.map_w}x{self.map_h}"
        self.screen.blit(self.font.render(size_text, True, COLOR_WHITE), (sidebar_x + 10, y_off))
        y_off += 30
        tool_text = f"Tool: {self.active_tool} [B/J]"
        self.screen.blit(self.font.render(tool_text, True, COLOR_WHITE), (sidebar_x + 10, y_off))
        y_off += 30
        brush_text = f"Brush: {PALETTE[self.brush_idx][1]} ({PALETTE[self.brush_idx][0]})"
        self.screen.blit(self.font.render(brush_text, True, COLOR_YELLOW), (sidebar_x + 10, y_off))
        y_off += 40

        # Socket Info
        if self.selected_socket_idx >= 0:
            sock = self.module_sockets[self.selected_socket_idx]
            b = sock["bounds"]
            self.screen.blit(self.font.render("Selected Socket:", True, COLOR_CYAN), (sidebar_x + 10, y_off))
            y_off += 25
            self.screen.blit(self.font.render(f"Name: {sock['name']}", True, COLOR_WHITE), (sidebar_x + 20, y_off))
            y_off += 25
            self.screen.blit(self.font.render(f"Pos: {b['x']},{b['y']}", True, COLOR_WHITE), (sidebar_x + 20, y_off))
            y_off += 25
            dim_text = f"Dim: {b['width']}x{b['height']}"
            self.screen.blit(self.font.render(dim_text, True, COLOR_WHITE), (sidebar_x + 20, y_off))
            y_off += 25
            self.screen.blit(self.font.render("[DEL] Remove, [E] Rename", True, COLOR_RED), (sidebar_x + 20, y_off))
            y_off += 40

        self.screen.blit(self.font.render("Palette (Click to select):", True, COLOR_GREY), (sidebar_x + 10, y_off))
        y_off += 25
        for i, (char, name) in enumerate(PALETTE):
            is_active = i == self.brush_idx
            color = COLOR_YELLOW if is_active else COLOR_WHITE

            p_rect = pygame.Rect(sidebar_x + 15, y_off, 200, 22)
            if is_active:
                pygame.draw.rect(self.screen, (40, 40, 60), p_rect)
                pygame.draw.rect(self.screen, COLOR_YELLOW, p_rect, 1)

            if char == 'MONSTER':
                e_char, e_name = ENEMY_TYPES[self.current_enemy_idx]
                text = f"[ Monster: {e_char} ]"
                self.screen.blit(self.font.render(text, True, color), (sidebar_x + 20, y_off + 2))
                # Hover descriptor
                if p_rect.collidepoint(pygame.mouse.get_pos()):
                    desc_surf = self.font.render(f"Type: {e_name}", True, COLOR_CYAN)
                    self.screen.blit(desc_surf, (sidebar_x + 20, SCREEN_HEIGHT - 120))
            else:
                p_box = pygame.Rect(sidebar_x + 20, y_off + 2, 18, 18)
                p_color = COLOR_FLOOR
                if char == '#': p_color = COLOR_WALL
                elif char == 'W': p_color = COLOR_PURPLE
                elif char == 'P': p_color = COLOR_BLUE
                pygame.draw.rect(self.screen, p_color, p_box)
                pygame.draw.rect(self.screen, COLOR_WHITE, p_box, 1)
                self.screen.blit(self.font.render(f"{char} - {name}", True, color), (sidebar_x + 45, y_off + 2))

            y_off += 25
            if y_off > SCREEN_HEIGHT - 130:
                break

        self.screen.blit(self.font.render("Controls:", True, COLOR_GREY), (sidebar_x + 10, SCREEN_HEIGHT - 120))
        ctrl_w = "WASD: Pan, Ctrl+N: New"
        self.screen.blit(self.font.render(ctrl_w, True, COLOR_WHITE), (sidebar_x + 10, SCREEN_HEIGHT - 100))
        ctrl_h = "Ctrl+R: Resize Canvas"
        self.screen.blit(self.font.render(ctrl_h, True, COLOR_WHITE), (sidebar_x + 10, SCREEN_HEIGHT - 80))
        ctrl_f = "Ctrl+S: Save, Ctrl+O: Load"
        self.screen.blit(self.font.render(ctrl_f, True, COLOR_WHITE), (sidebar_x + 10, SCREEN_HEIGHT - 60))
        ctrl_q = "Esc: Unselect/Tool"
        self.screen.blit(self.font.render(ctrl_q, True, COLOR_WHITE), (sidebar_x + 10, SCREEN_HEIGHT - 40))

    def draw_file_picker(self):
        """Draws a scrollable list of maps for selection."""
        overlay_w, overlay_h = 400, 500
        x, y = (SCREEN_WIDTH + self.sidebar_width) // 2 - overlay_w // 2, SCREEN_HEIGHT // 2 - overlay_h // 2
        rect = pygame.Rect(x, y, overlay_w, overlay_h)
        
        pygame.draw.rect(self.screen, (30, 30, 40), rect)
        pygame.draw.rect(self.screen, COLOR_WHITE, rect, 2)
        
        title = self.large_font.render("Select Map (Enter to Load)", True, COLOR_YELLOW)
        self.screen.blit(title, (rect.centerx - title.get_width() // 2, rect.y + 10))
        
        # Draw scrollable list
        start_y = rect.y + 70
        visible_count = 12
        for i in range(self.scroll_offset, min(len(self.map_files), self.scroll_offset + visible_count)):
            color = COLOR_YELLOW if i == self.file_picker_idx else COLOR_WHITE
            file_name = self.map_files[i]
            surf = self.font.render(file_name, True, color)
            
            row_rect = pygame.Rect(rect.x + 20, start_y + (i - self.scroll_offset) * 30, overlay_w - 40, 25)
            if i == self.file_picker_idx:
                pygame.draw.rect(self.screen, (60, 60, 80), row_rect)
            
            self.screen.blit(surf, (row_rect.x + 5, row_rect.y + 2))

    def draw_input_banner(self):
        """Draws the input banner overlay."""
        banner_h = 120
        banner_w = SCREEN_WIDTH + self.sidebar_width
        banner_y = SCREEN_HEIGHT // 2 - banner_h // 2
        b_rect = pygame.Rect(0, banner_y, banner_w, banner_h)
        pygame.draw.rect(self.screen, (30, 30, 30), b_rect)
        pygame.draw.rect(self.screen, COLOR_WHITE, b_rect, 3)

        prompts = {
            'SAVE': "ENTER FILENAME TO SAVE:",
            'LOAD': "ENTER FILENAME TO LOAD:",
            'SOCKET_NAME': "ENTER NAME FOR SOCKET:",
            'RESIZE_W': "ENTER NEW WIDTH:",
            'RESIZE_H': "ENTER NEW HEIGHT:"
        }
        prompt = prompts.get(self.input_mode, "ENTER INPUT:")
        p_surf = self.large_font.render(prompt, True, COLOR_YELLOW)
        self.screen.blit(p_surf, (b_rect.centerx - p_surf.get_width() // 2, b_rect.y + 20))

        b_surf = self.large_font.render(self.input_buffer + "_", True, COLOR_WHITE)
        self.screen.blit(b_surf, (b_rect.centerx - b_surf.get_width() // 2, b_rect.y + 60))

    def draw(self):
        """Draws the editor state to the screen."""
        self.screen.fill(COLOR_CHARCOAL)
        ts = int(TILE_SIZE * self.zoom)
        self.draw_grid(ts)
        self.draw_selection_preview(ts)
        self.draw_sidebar(SCREEN_WIDTH)
        if self.input_mode == 'PICKER':
            self.draw_file_picker()
        elif self.input_mode:
            self.draw_input_banner()
        pygame.display.flip()

    def handle_file_picker(self, event):
        """Handles navigation and selection in the file picker."""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                self.file_picker_idx = max(0, self.file_picker_idx - 1)
                if self.file_picker_idx < self.scroll_offset:
                    self.scroll_offset = self.file_picker_idx
            elif event.key == pygame.K_DOWN:
                self.file_picker_idx = min(len(self.map_files) - 1, self.file_picker_idx + 1)
                if self.file_picker_idx >= self.scroll_offset + 12:
                    self.scroll_offset = self.file_picker_idx - 11
            elif event.key == pygame.K_RETURN:
                if self.map_files:
                    self.load_map(self.map_files[self.file_picker_idx])
                self.input_mode = None
            elif event.key == pygame.K_ESCAPE:
                self.input_mode = None

    def handle_input_mode(self, event):
        """Handles events when in input mode."""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                if self.input_mode == 'SAVE':
                    self.filename = self.input_buffer
                    self.save_map()
                elif self.input_mode == 'LOAD':
                    self.load_map(self.input_buffer)
                elif self.input_mode == 'SOCKET_NAME':
                    if self.input_buffer:
                        if self.selected_socket_idx >= 0:
                            self.module_sockets[self.selected_socket_idx]["name"] = self.input_buffer
                        elif self.pending_socket_bounds:
                            self.module_sockets.append({
                                "name": self.input_buffer,
                                "bounds": self.pending_socket_bounds
                            })
                    self.pending_socket_bounds = None
                elif self.input_mode == 'RESIZE_W':
                    try:
                        new_w = int(self.input_buffer)
                        if new_w > 0:
                            # Adjust grid width
                            for row in self.grid:
                                if new_w > self.map_w:
                                    row.extend(['.' for _ in range(new_w - self.map_w)])
                                else:
                                    del row[new_w:]
                            self.map_w = new_w
                    except ValueError:
                        pass
                    self.input_mode = 'RESIZE_H'
                    self.input_buffer = str(self.map_h)
                    return
                elif self.input_mode == 'RESIZE_H':
                    try:
                        new_h = int(self.input_buffer)
                        if new_h > 0:
                            if new_h > self.map_h:
                                for _ in range(new_h - self.map_h):
                                    self.grid.append(['.' for _ in range(self.map_w)])
                            else:
                                del self.grid[new_h:]
                            self.map_h = new_h
                    except ValueError:
                        pass

                self.input_mode = None
                self.input_buffer = ""
            elif event.key == pygame.K_ESCAPE:
                self.input_mode = None
                self.input_buffer = ""
                self.pending_socket_bounds = None
            elif event.key == pygame.K_BACKSPACE:
                self.input_buffer = self.input_buffer[:-1]
            elif event.unicode.isprintable():
                self.input_buffer += event.unicode

    def handle_keyboard(self, event):
        """Handles discrete keyboard events."""
        ctrl_pressed = pygame.key.get_mods() & pygame.KMOD_CTRL

        if ctrl_pressed:
            if event.key == pygame.K_s:
                self.input_mode = 'SAVE'
                self.input_buffer = self.filename if self.filename else ""
                return
            if event.key == pygame.K_o:
                # Scan for maps
                maps_dir = "maps"
                if os.path.exists(maps_dir):
                    self.map_files = [f for f in os.listdir(maps_dir) if f.endswith(".json")]
                    self.map_files.sort()
                self.input_mode = 'PICKER'
                self.file_picker_idx = 0
                self.scroll_offset = 0
                return
            if event.key == pygame.K_n:
                self.reset_canvas()
                return
            if event.key == pygame.K_r:
                self.input_mode = 'RESIZE_W'
                self.input_buffer = str(self.map_w)
                return

        if event.key == pygame.K_ESCAPE:
            if self.selected_socket_idx >= 0:
                self.selected_socket_idx = -1
            else:
                self.active_tool = "PENCIL"
            return

        if self.selected_socket_idx >= 0:
            if event.key == pygame.K_DELETE:
                self.module_sockets.pop(self.selected_socket_idx)
                self.selected_socket_idx = -1
                return
            if event.key == pygame.K_e:
                self.input_mode = 'SOCKET_NAME'
                self.input_buffer = self.module_sockets[self.selected_socket_idx]["name"]
                return

        if event.key == pygame.K_b:
            # Cycle through PENCIL and RECTANGLE
            self.active_tool = "RECTANGLE" if self.active_tool == "PENCIL" else "PENCIL"
            return
        
        if event.key == pygame.K_j:
            self.active_tool = "SOCKET"
            return

        if pygame.K_0 <= event.key <= pygame.K_9:
            idx = event.key - pygame.K_0
            if idx < len(PALETTE):
                self.brush_idx = idx
            return

    def handle_mouse(self):
        """Handles continuous mouse interaction."""
        mouse_buttons = pygame.mouse.get_pressed()
        if mouse_buttons[0]:
            mx, my = pygame.mouse.get_pos()
            if mx < SCREEN_WIDTH:
                ts = int(TILE_SIZE * self.zoom)
                gx = (mx + self.camera_x) // ts
                gy = (my + self.camera_y) // ts
                if 0 <= gx < self.map_w and 0 <= gy < self.map_h:
                    if self.active_tool == "PENCIL":
                        char = PALETTE[self.brush_idx][0]
                        if char == 'MONSTER':
                            char = ENEMY_TYPES[self.current_enemy_idx][0]
                        self.grid[gy][gx] = char
                    elif self.active_tool in ("RECTANGLE", "SOCKET"):
                        self.drag_current = (gx, gy)

    def handle_mouse_event(self, event):
        """Handles discrete mouse button events."""
        mx, my = pygame.mouse.get_pos()
        if event.type == pygame.MOUSEBUTTONDOWN:
            if mx >= SCREEN_WIDTH:
                # Sidebar click
                palette_y_start = 175 # Adjusted for Size display
                # Adjust for potential Socket Info if selected
                if self.selected_socket_idx >= 0:
                    palette_y_start += 140

                click_idx = (my - palette_y_start) // 25
                if 0 <= click_idx < len(PALETTE):
                    if click_idx == self.brush_idx and PALETTE[click_idx][0] == 'MONSTER':
                        # Cycle if already selected
                        self.current_enemy_idx = (self.current_enemy_idx + 1) % len(ENEMY_TYPES)
                    self.brush_idx = click_idx
            elif event.button == 1:
                ts = int(TILE_SIZE * self.zoom)
                gx = (mx + self.camera_x) // ts
                gy = (my + self.camera_y) // ts

                # Try to select a socket
                self.selected_socket_idx = -1
                for i, socket in enumerate(self.module_sockets):
                    b = socket["bounds"]
                    if b["x"] <= gx < b["x"] + b["width"] and b["y"] <= gy < b["y"] + b["height"]:
                        self.selected_socket_idx = i
                        break

                if self.active_tool in ("RECTANGLE", "SOCKET"):
                    self.is_dragging = True
                    self.drag_start = (gx, gy)
                    self.drag_current = self.drag_start
        elif event.type == pygame.MOUSEBUTTONUP:
            if self.active_tool in ("RECTANGLE", "SOCKET") and event.button == 1:
                if self.is_dragging:
                    if self.active_tool == "RECTANGLE":
                        self.fill_rectangle()
                    elif self.active_tool == "SOCKET":
                        x1, y1 = self.drag_start
                        x2, y2 = self.drag_current
                        gx1, gx2 = min(x1, x2), max(x1, x2)
                        gy1, gy2 = min(y1, y2), max(y1, y2)
                        self.pending_socket_bounds = {
                            "x": gx1, "y": gy1,
                            "width": gx2 - gx1 + 1, "height": gy2 - gy1 + 1
                        }
                        self.input_mode = 'SOCKET_NAME'
                        self.input_buffer = f"M{len(self.module_sockets) + 1}"
                    self.is_dragging = False

    def handle_input(self):
        """Handles user input for the editor."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if self.input_mode == 'PICKER':
                self.handle_file_picker(event)
            elif self.input_mode:
                self.handle_input_mode(event)
            else:
                if event.type == pygame.KEYDOWN:
                    self.handle_keyboard(event)
                else:
                    self.handle_mouse_event(event)

        if not self.input_mode:
            keys = pygame.key.get_pressed()
            move_speed = 10
            if keys[pygame.K_a]:
                self.camera_x -= move_speed
            if keys[pygame.K_d]:
                self.camera_x += move_speed
            if keys[pygame.K_w]:
                self.camera_y -= move_speed
            if keys[pygame.K_s] and not pygame.key.get_mods() & pygame.KMOD_CTRL:
                self.camera_y += move_speed
            self.handle_mouse()
        return True
    def run(self):
        """Main loop for the editor."""
        running = True
        while running:
            running = self.handle_input()
            self.draw()
            self.clock.tick(60)
        pygame.quit()

if __name__ == "__main__":
    initial_name = sys.argv[1] if len(sys.argv) > 1 else None
    editor = MapEditor()
    if initial_name:
        editor.load_map(initial_name)
    editor.run()
