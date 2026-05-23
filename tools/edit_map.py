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
    COLOR_PURPLE, COLOR_GREY
)

# Legend for the editor palette
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
    ('A', 'BAT_SPAWN'),
    ('Z', 'SLUG_SPAWN'),
    ('E', 'MINIBOSS_SPAWN')
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

        self.brush_idx = 0
        self.camera_x = 0
        self.camera_y = 0
        self.zoom = 1.0

        self.filename = "new_map.json"
        self.input_mode = None  # 'SAVE' or 'LOAD'
        self.input_buffer = ""

        # Tool State
        self.active_tool = "PENCIL"  # "PENCIL" or "RECTANGLE"
        self.is_dragging = False
        self.drag_start = (0, 0)
        self.drag_current = (0, 0)

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
            self.filename = name
            print(f"Loaded {self.filename}")
        except Exception as e:
            print(f"Failed to load map: {e}")

    def save_map(self):
        """Saves the current map to the maps/ directory."""
        if not self.filename.endswith(".json"):
            self.filename += ".json"

        data = {
            "map_id": self.filename.replace(".json", ""),
            "dimensions": {"width": self.map_w, "height": self.map_h},
            "legend": dict(PALETTE),
            "grid": ["".join(row) for row in self.grid],
            "entities": self.entities
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
                elif char in ('A', 'Z', 'E'):
                    color = COLOR_RED

                pygame.draw.rect(self.screen, color, rect)
                pygame.draw.rect(self.screen, (50, 50, 50), rect, 1)

                if ts > 10:
                    sym_surf = self.font.render(char, True, COLOR_WHITE)
                    self.screen.blit(sym_surf, (rect.x + 2, rect.y + 2))

    def draw_selection_preview(self, ts):
        """Draws a transparent preview of the rectangle being drawn."""
        if not self.is_dragging or self.active_tool != "RECTANGLE":
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
        preview_surf.fill((0, 120, 255, 80))
        self.screen.blit(preview_surf, (rect.x, rect.y))
        # Draw opaque outline
        pygame.draw.rect(self.screen, (0, 120, 255), rect, 2)

    def draw_sidebar(self, sidebar_x):
        """Draws the UI sidebar."""
        pygame.draw.rect(self.screen, (20, 20, 20), (sidebar_x, 0, self.sidebar_width, SCREEN_HEIGHT))
        pygame.draw.line(self.screen, COLOR_GREY, (sidebar_x, 0), (sidebar_x, SCREEN_HEIGHT), 2)

        y_off = 20
        self.screen.blit(self.font.render(f"File: {self.filename}", True, COLOR_WHITE), (sidebar_x + 10, y_off))
        y_off += 30
        tool_text = f"Tool: {self.active_tool} [B]"
        self.screen.blit(self.font.render(tool_text, True, COLOR_WHITE), (sidebar_x + 10, y_off))
        y_off += 30
        brush_text = f"Brush: {PALETTE[self.brush_idx][1]} ({PALETTE[self.brush_idx][0]})"
        self.screen.blit(self.font.render(brush_text, True, COLOR_YELLOW), (sidebar_x + 10, y_off))
        y_off += 40

        self.screen.blit(self.font.render("Palette (Click to select):", True, COLOR_GREY), (sidebar_x + 10, y_off))
        y_off += 25
        for i, (char, name) in enumerate(PALETTE):
            color = COLOR_YELLOW if i == self.brush_idx else COLOR_WHITE

            p_rect = pygame.Rect(sidebar_x + 15, y_off, 20, 20)
            p_color = COLOR_FLOOR
            if char == '#':
                p_color = COLOR_WALL
            elif char == 'W':
                p_color = COLOR_PURPLE
            elif char == 'P':
                p_color = COLOR_BLUE
            elif char in ('A', 'Z', 'E'):
                p_color = COLOR_RED
            pygame.draw.rect(self.screen, p_color, p_rect)
            pygame.draw.rect(self.screen, COLOR_WHITE, p_rect, 1)

            self.screen.blit(self.font.render(f"{char} - {name}", True, color), (sidebar_x + 45, y_off))
            y_off += 25
            if y_off > SCREEN_HEIGHT - 120:
                break

        self.screen.blit(self.font.render("Controls:", True, COLOR_GREY), (sidebar_x + 10, SCREEN_HEIGHT - 100))
        ctrl_w = "WASD: Pan, +/-: Resize W"
        self.screen.blit(self.font.render(ctrl_w, True, COLOR_WHITE), (sidebar_x + 10, SCREEN_HEIGHT - 80))
        ctrl_h = "Ctrl +/-: Resize H"
        self.screen.blit(self.font.render(ctrl_h, True, COLOR_WHITE), (sidebar_x + 10, SCREEN_HEIGHT - 60))
        ctrl_f = "Ctrl+S: Save, Ctrl+O: Load"
        self.screen.blit(self.font.render(ctrl_f, True, COLOR_WHITE), (sidebar_x + 10, SCREEN_HEIGHT - 40))

    def draw_input_banner(self):
        """Draws the input banner overlay."""
        banner_h = 120
        banner_w = SCREEN_WIDTH + self.sidebar_width
        banner_y = SCREEN_HEIGHT // 2 - banner_h // 2
        b_rect = pygame.Rect(0, banner_y, banner_w, banner_h)
        pygame.draw.rect(self.screen, (30, 30, 30), b_rect)
        pygame.draw.rect(self.screen, COLOR_WHITE, b_rect, 3)

        prompt = f"ENTER FILENAME TO {self.input_mode}:"
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
        if self.input_mode:
            self.draw_input_banner()
        pygame.display.flip()

    def handle_input_mode(self, event):
        """Handles events when in input mode."""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                if self.input_mode == 'SAVE':
                    self.filename = self.input_buffer
                    self.save_map()
                elif self.input_mode == 'LOAD':
                    self.load_map(self.input_buffer)
                self.input_mode = None
                self.input_buffer = ""
            elif event.key == pygame.K_ESCAPE:
                self.input_mode = None
                self.input_buffer = ""
            elif event.key == pygame.K_BACKSPACE:
                self.input_buffer = self.input_buffer[:-1]
            elif event.unicode.isprintable():
                self.input_buffer += event.unicode

    def handle_resizing(self, event, ctrl_pressed):
        """Handles map resizing events."""
        if event.key == pygame.K_EQUALS:
            if ctrl_pressed:
                self.grid.append(['#' for _ in range(self.map_w)])
                self.map_h += 1
            else:
                for row in self.grid:
                    row.append('#')
                self.map_w += 1
        elif event.key == pygame.K_MINUS:
            if ctrl_pressed:
                if self.map_h > 1:
                    self.grid.pop()
                    self.map_h -= 1
            elif self.map_w > 1:
                for row in self.grid:
                    row.pop()
                self.map_w -= 1

    def handle_keyboard(self, event):
        """Handles discrete keyboard events."""
        ctrl_pressed = pygame.key.get_mods() & pygame.KMOD_CTRL

        if ctrl_pressed:
            if event.key == pygame.K_s:
                self.input_mode = 'SAVE'
                self.input_buffer = self.filename
                return
            if event.key == pygame.K_o:
                self.input_mode = 'LOAD'
                self.input_buffer = ""
                return

        if event.key == pygame.K_b:
            self.active_tool = "RECTANGLE" if self.active_tool == "PENCIL" else "PENCIL"
            return

        if pygame.K_0 <= event.key <= pygame.K_9:
            idx = event.key - pygame.K_0
            if idx < len(PALETTE):
                self.brush_idx = idx
            return

        self.handle_resizing(event, ctrl_pressed)

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
                        self.grid[gy][gx] = PALETTE[self.brush_idx][0]
                    elif self.active_tool == "RECTANGLE":
                        self.drag_current = (gx, gy)

    def handle_mouse_event(self, event):
        """Handles discrete mouse button events."""
        mx, my = pygame.mouse.get_pos()
        if event.type == pygame.MOUSEBUTTONDOWN:
            if mx >= SCREEN_WIDTH:
                # Sidebar click
                click_idx = (my - 115) // 25
                if 0 <= click_idx < len(PALETTE):
                    self.brush_idx = click_idx
            elif self.active_tool == "RECTANGLE" and event.button == 1:
                ts = int(TILE_SIZE * self.zoom)
                self.is_dragging = True
                self.drag_start = ((mx + self.camera_x) // ts, (my + self.camera_y) // ts)
                self.drag_current = self.drag_start
        elif event.type == pygame.MOUSEBUTTONUP:
            if self.active_tool == "RECTANGLE" and event.button == 1:
                if self.is_dragging:
                    self.fill_rectangle()
                    self.is_dragging = False

    def handle_input(self):
        """Handles user input for the editor."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if self.input_mode:
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
