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

# Master Registry of all available tools and brushes
MASTER_TOOL_REGISTRY = [
    {"id": "tile_wall", "char": "#", "name": "Wall Tile", "type": "tile"},
    {"id": "tile_floor", "char": ".", "name": "Floor Tile", "type": "tile"},
    {"id": "tile_barrel", "char": "B", "name": "Barrel", "type": "tile"},
    {"id": "tile_bench", "char": "S", "name": "Bench", "type": "tile"},
    {"id": "tile_candelabra", "char": "l", "name": "Candelabra", "type": "tile"},
    {"id": "tile_ink_puddle", "char": "v", "name": "Ink Puddle", "type": "tile"},
    {"id": "tile_ink_urn", "char": "d", "name": "Ink Urn", "type": "tile"},
    {"id": "tile_bookcase", "char": "h", "name": "Bookcase", "type": "tile"},
    {"id": "tile_structure", "char": "T", "name": "Structure", "type": "tile"},
    {"id": "tile_rock", "char": "K", "name": "Rock", "type": "tile"},
    {"id": "tile_warp", "char": "W", "name": "Warp", "type": "tile"},
    {"id": "tile_player_start", "char": "P", "name": "Player Start", "type": "tile"},
    {"id": "tile_chronicler", "char": "C", "name": "Chronicler", "type": "tile"},
    {"id": "tile_wellspring", "char": "F", "name": "Wellspring", "type": "tile"},
    {"id": "tile_lore", "char": "L", "name": "Lore", "type": "tile"},
    {"id": "tile_respite", "char": "R", "name": "Respite", "type": "tile"},

    {"id": "enemy_bat", "char": "A", "name": "Bat", "type": "enemy"},
    {"id": "enemy_slug", "char": "Z", "name": "Slug", "type": "enemy"},
    {"id": "enemy_flutter", "char": "f", "name": "Flutter", "type": "enemy"},
    {"id": "enemy_bindling", "char": "b", "name": "Bindling", "type": "enemy"},
    {"id": "enemy_smear", "char": "s", "name": "Smear", "type": "enemy"},
    {"id": "enemy_miniboss_m1", "char": "E", "name": "Miniboss M1", "type": "enemy"},
    {"id": "enemy_miniboss_m2", "char": "2", "name": "Miniboss M2", "type": "enemy"},
    {"id": "enemy_miniboss_m3", "char": "3", "name": "Miniboss M3", "type": "enemy"},

    {"id": "tool_pencil", "name": "Pencil Tool", "type": "utility"},
    {"id": "tool_rect", "name": "Rectangle Tool", "type": "utility"},
    {"id": "tool_socket", "name": "Socket Tool", "type": "utility"},
]

class MapEditor:
    """Main application class for the Map Editor."""
    def __init__(self, width=40, height=30):
        pygame.init()
        # Expanded width for sidebar
        self.sidebar_width = 300
        self.screen = pygame.display.set_mode((SCREEN_WIDTH + self.sidebar_width, SCREEN_HEIGHT))
        pygame.display.set_caption("Avoid Rain Map Editor")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Arial", 18)
        self.small_font = pygame.font.SysFont("Arial", 14)
        self.large_font = pygame.font.SysFont("Arial", 32)

        self.map_w = width
        self.map_h = height
        self.grid = [['#' for _ in range(width)] for _ in range(height)]
        self.entities = {}
        self.module_sockets = []

        # Tool & Hotbar State
        self.hotbar = [None] * 10
        self.hotbar[0] = "tile_wall"
        self.hotbar[1] = "tile_floor"
        self.hotbar[2] = "enemy_bat"
        self.hotbar[3] = "enemy_slug"
        self.hotbar[4] = "tool_pencil"
        self.hotbar[5] = "tool_rect"
        self.hotbar[6] = "tool_socket"

        self.selected_slot = 0
        self.current_brush_char = "#"
        self.active_tool = "PENCIL"  # "PENCIL", "RECTANGLE", or "SOCKET"

        self.camera_x = 0
        self.camera_y = 0
        self.zoom = 1.0

        self.filename = None
        self.input_mode = None  # 'SAVE', 'LOAD', 'PICKER', 'SOCKET_NAME', 'RESIZE_W', 'RESIZE_H', 'TOOL_PICKER'
        self.input_buffer = ""

        # File/Tool Picker State
        self.map_files = []
        self.file_picker_idx = 0
        self.tool_picker_idx = 0
        self.remapping_slot = -1
        self.scroll_offset = 0

        self.is_dragging = False
        self.drag_start = (0, 0)
        self.drag_current = (0, 0)
        self.pending_socket_bounds = None
        self.selected_socket_idx = -1

    def select_hotbar_slot(self, idx):
        """Selects a tool slot and updates editor state."""
        self.selected_slot = idx
        tool_id = self.hotbar[idx]
        if not tool_id:
            return

        tool = next((t for t in MASTER_TOOL_REGISTRY if t["id"] == tool_id), None)
        if not tool:
            return

        if tool["type"] in ("tile", "enemy"):
            self.current_brush_char = tool["char"]
            if self.active_tool == "SOCKET":
                self.active_tool = "PENCIL"
        elif tool["type"] == "utility":
            if tool["id"] == "tool_pencil":
                self.active_tool = "PENCIL"
            elif tool["id"] == "tool_rect":
                self.active_tool = "RECTANGLE"
            elif tool["id"] == "tool_socket":
                self.active_tool = "SOCKET"

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

        # Construct full legend from registry
        full_legend = {t["char"]: t["name"] for t in MASTER_TOOL_REGISTRY if "char" in t}

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

        char = self.current_brush_char
        for y in range(max(0, gy1), min(self.map_h, gy2 + 1)):
            for x in range(max(0, gx1), min(self.map_w, gx2 + 1)):
                self.grid[y][x] = char

    def draw_grid(self, ts):
        """Draws the map grid."""
        enemy_chars = [t["char"] for t in MASTER_TOOL_REGISTRY if t["type"] == "enemy"]

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
                elif char in enemy_chars:
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

        # Interactive Size Button
        size_rect = pygame.Rect(sidebar_x + 10, y_off, self.sidebar_width - 20, 30)
        pygame.draw.rect(self.screen, (40, 40, 40), size_rect)
        pygame.draw.rect(self.screen, COLOR_GREY, size_rect, 1)
        size_text = f"Size: {self.map_w}x{self.map_h} (Click to Resize)"
        self.screen.blit(self.small_font.render(size_text, True, COLOR_WHITE), (size_rect.x + 5, size_rect.y + 7))
        y_off += 35

        tool_text = f"Tool: {self.active_tool}"
        self.screen.blit(self.font.render(tool_text, True, COLOR_WHITE), (sidebar_x + 10, y_off))
        y_off += 30
        brush_text = f"Brush Char: {self.current_brush_char}"
        self.screen.blit(self.font.render(brush_text, True, COLOR_YELLOW), (sidebar_x + 10, y_off))
        y_off += 40

        # Tool Hotbar
        self.screen.blit(self.font.render("Tool Hotbar (1-0):", True, COLOR_GREY), (sidebar_x + 10, y_off))
        y_off += 25

        for i in range(10):
            is_selected = i == self.selected_slot
            tool_id = self.hotbar[i]
            tool = next((t for t in MASTER_TOOL_REGISTRY if t["id"] == tool_id), None)

            # Slot Rect
            slot_rect = pygame.Rect(sidebar_x + 10, y_off, self.sidebar_width - 20, 35)
            # Left 80% for selection, Right 20% for remapping
            left_part = pygame.Rect(slot_rect.x, slot_rect.y, slot_rect.width - 40, slot_rect.height)
            right_part = pygame.Rect(slot_rect.x + slot_rect.width - 35, slot_rect.y, 35, slot_rect.height)

            # Draw Slot Background
            bg_color = (40, 40, 60) if is_selected else (30, 30, 30)
            pygame.draw.rect(self.screen, bg_color, slot_rect)
            pygame.draw.rect(self.screen, COLOR_GREY, slot_rect, 1)
            if is_selected:
                pygame.draw.rect(self.screen, COLOR_YELLOW, slot_rect, 2)

            # Draw Left Part (Tool Info)
            display_idx = (i + 1) % 10
            label_text = f"{display_idx}: "
            if tool:
                label_text += f"{tool['name']}"
                if "char" in tool:
                    label_text += f" ({tool['char']})"
            else:
                label_text += "[EMPTY]"

            label_surf = self.small_font.render(label_text, True, COLOR_WHITE)
            self.screen.blit(label_surf, (left_part.x + 5, left_part.y + 10))

            # Draw Right Part (Remap Button)
            pygame.draw.rect(self.screen, (50, 50, 50), right_part)
            pygame.draw.rect(self.screen, COLOR_GREY, right_part, 1)
            remap_surf = self.small_font.render("SET", True, COLOR_CYAN)
            self.screen.blit(remap_surf, (right_part.x + 5, right_part.y + 10))

            y_off += 40

        # Socket Info
        if self.selected_socket_idx >= 0:
            sock = self.module_sockets[self.selected_socket_idx]
            self.screen.blit(self.font.render("Selected Socket:", True, COLOR_CYAN), (sidebar_x + 10, y_off))
            y_off += 25
            self.screen.blit(self.font.render(f"Name: {sock['name']}", True, COLOR_WHITE), (sidebar_x + 20, y_off))
            y_off += 25
            self.screen.blit(self.font.render("[DEL] Remove, [E] Rename", True, COLOR_RED), (sidebar_x + 20, y_off))
            y_off += 40

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

    def draw_tool_picker(self):
        """Draws a scrollable list of all tools in the registry."""
        overlay_w, overlay_h = 450, 550
        x, y = (SCREEN_WIDTH + self.sidebar_width) // 2 - overlay_w // 2, SCREEN_HEIGHT // 2 - overlay_h // 2
        rect = pygame.Rect(x, y, overlay_w, overlay_h)

        pygame.draw.rect(self.screen, (30, 30, 40), rect)
        pygame.draw.rect(self.screen, COLOR_WHITE, rect, 2)

        title = self.large_font.render(f"Assign Tool to Slot {self.remapping_slot + 1}", True, COLOR_YELLOW)
        self.screen.blit(title, (rect.centerx - title.get_width() // 2, rect.y + 10))

        # Draw scrollable list
        start_y = rect.y + 70
        visible_count = 14
        for i in range(self.scroll_offset, min(len(MASTER_TOOL_REGISTRY), self.scroll_offset + visible_count)):
            color = COLOR_YELLOW if i == self.tool_picker_idx else COLOR_WHITE
            tool = MASTER_TOOL_REGISTRY[i]

            type_tag = f"[{tool['type'].upper()}]"
            label = f"{type_tag} {tool['name']}"
            if "char" in tool:
                label += f" ('{tool['char']}')"

            surf = self.font.render(label, True, color)

            row_rect = pygame.Rect(rect.x + 20, start_y + (i - self.scroll_offset) * 30, overlay_w - 40, 25)
            if i == self.tool_picker_idx:
                pygame.draw.rect(self.screen, (60, 60, 80), row_rect)

            self.screen.blit(surf, (row_rect.x + 5, row_rect.y + 2))

    def draw_input_dialog(self):
        """Draws a clean text input dialog banner."""
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
        elif self.input_mode == 'TOOL_PICKER':
            self.draw_tool_picker()
        elif self.input_mode:
            self.draw_input_dialog()
        pygame.display.flip()

    def handle_tool_picker(self, event):
        """Handles navigation and selection in the tool picker."""
        overlay_w, overlay_h = 450, 550
        x, y = (SCREEN_WIDTH + self.sidebar_width) // 2 - overlay_w // 2, SCREEN_HEIGHT // 2 - overlay_h // 2
        rect = pygame.Rect(x, y, overlay_w, overlay_h)

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                self.tool_picker_idx = max(0, self.tool_picker_idx - 1)
                if self.tool_picker_idx < self.scroll_offset:
                    self.scroll_offset = self.tool_picker_idx
            elif event.key == pygame.K_DOWN:
                self.tool_picker_idx = min(len(MASTER_TOOL_REGISTRY) - 1, self.tool_picker_idx + 1)
                if self.tool_picker_idx >= self.scroll_offset + 14:
                    self.scroll_offset = self.tool_picker_idx - 13
            elif event.key == pygame.K_RETURN:
                self.assign_tool_to_hotbar(self.tool_picker_idx)
            elif event.key == pygame.K_ESCAPE:
                self.input_mode = None
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 4:  # Wheel Up
                self.scroll_offset = max(0, self.scroll_offset - 1)
            elif event.button == 5:  # Wheel Down
                max_scroll = max(0, len(MASTER_TOOL_REGISTRY) - 14)
                self.scroll_offset = min(max_scroll, self.scroll_offset + 1)
            elif event.button == 1:  # Left Click
                mx, my = pygame.mouse.get_pos()
                start_y = rect.y + 70
                if rect.x + 20 <= mx <= rect.x + overlay_w - 20:
                    clicked_row = (my - start_y) // 30
                    clicked_idx = clicked_row + self.scroll_offset
                    if self.scroll_offset <= clicked_idx < min(len(MASTER_TOOL_REGISTRY), self.scroll_offset + 14):
                        self.assign_tool_to_hotbar(clicked_idx)

    def assign_tool_to_hotbar(self, tool_idx):
        """Helper to assign a tool and clean up remapping state."""
        selected_tool = MASTER_TOOL_REGISTRY[tool_idx]
        tool_id = selected_tool["id"]

        # Remap Exclusion: If this tool is assigned elsewhere, clear that slot
        for i in range(10):
            if self.hotbar[i] == tool_id:
                self.hotbar[i] = None

        self.hotbar[self.remapping_slot] = tool_id
        self.input_mode = None
        self.select_hotbar_slot(self.remapping_slot)

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

        if pygame.K_1 <= event.key <= pygame.K_9:
            self.select_hotbar_slot(event.key - pygame.K_1)
            return
        if event.key == pygame.K_0:
            self.select_hotbar_slot(9)
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
                        self.grid[gy][gx] = self.current_brush_char
                    elif self.active_tool in ("RECTANGLE", "SOCKET"):
                        self.drag_current = (gx, gy)

    def handle_mouse_event(self, event):
        """Handles discrete mouse button events."""
        mx, my = pygame.mouse.get_pos()
        if event.type == pygame.MOUSEBUTTONDOWN:
            if mx >= SCREEN_WIDTH:
                # Check for Size Button
                size_rect = pygame.Rect(SCREEN_WIDTH + 10, 45, self.sidebar_width - 20, 30)
                if size_rect.collidepoint(mx, my):
                    self.input_mode = 'RESIZE_W'
                    self.input_buffer = str(self.map_w)
                    return

                # Hotbar Clicks
                y_start = 175 # Shifted slightly due to size button changes
                slot_idx = (my - y_start) // 40
                if 0 <= slot_idx < 10:
                    slot_rect = pygame.Rect(SCREEN_WIDTH + 10, y_start + slot_idx * 40, self.sidebar_width - 20, 35)
                    right_part = pygame.Rect(slot_rect.x + slot_rect.width - 35, slot_rect.y, 35, slot_rect.height)

                    if right_part.collidepoint(mx, my):
                        # Enter Remapping
                        self.input_mode = 'TOOL_PICKER'
                        self.remapping_slot = slot_idx
                        self.tool_picker_idx = 0
                        self.scroll_offset = 0
                    else:
                        # Select Slot
                        self.select_hotbar_slot(slot_idx)
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
            elif self.input_mode == 'TOOL_PICKER':
                self.handle_tool_picker(event)
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
