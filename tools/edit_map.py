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
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Avoid Rain Map Editor")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Arial", 18)

        self.map_w = width
        self.map_h = height
        self.grid = [['#' for _ in range(width)] for _ in range(height)]
        self.entities = {}

        self.brush_idx = 0
        self.camera_x = 0
        self.camera_y = 0
        self.zoom = 1.0

        self.filename = "new_map.json"

    def load_map(self, name):
        """Loads a map from the maps/ directory."""
        json_path = os.path.join("maps", f"{name}.json")
        if not os.path.exists(json_path):
            print(f"File not found: {json_path}")
            return

        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self.map_w = data["dimensions"]["width"]
        self.map_h = data["dimensions"]["height"]
        self.grid = [list(row) for row in data["grid"]]
        self.entities = data.get("entities", {})
        self.filename = f"{name}.json"
        print(f"Loaded {self.filename}")

    def save_map(self):
        """Saves the current map to the maps/ directory."""
        data = {
            "map_id": self.filename.replace(".json", ""),
            "dimensions": {"width": self.map_w, "height": self.map_h},
            "legend": dict(PALETTE),
            "grid": ["".join(row) for row in self.grid],
            "entities": self.entities
        }

        os.makedirs("maps", exist_ok=True)
        path = os.path.join("maps", self.filename)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        print(f"Saved to {path}")

    def draw(self):
        """Draws the editor state to the screen."""
        self.screen.fill(COLOR_CHARCOAL)

        # Draw Grid
        ts = int(TILE_SIZE * self.zoom)
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

                # Draw symbol
                if ts > 10:
                    sym_surf = self.font.render(char, True, COLOR_WHITE)
                    self.screen.blit(sym_surf, (rect.x + 2, rect.y + 2))

        # UI Overlay
        ui_rect = pygame.Rect(0, 0, 250, SCREEN_HEIGHT)
        pygame.draw.rect(self.screen, (20, 20, 20), ui_rect)

        y_off = 20
        self.screen.blit(self.font.render(f"File: {self.filename}", True, COLOR_WHITE), (10, y_off))
        y_off += 30
        brush_text = f"Brush: {PALETTE[self.brush_idx][1]} ({PALETTE[self.brush_idx][0]})"
        self.screen.blit(self.font.render(brush_text, True, COLOR_YELLOW), (10, y_off))
        y_off += 40

        self.screen.blit(self.font.render("Palette (Keys 0-9, Q,W,E...):", True, COLOR_GREY), (10, y_off))
        y_off += 25
        for i, (char, name) in enumerate(PALETTE):
            color = COLOR_YELLOW if i == self.brush_idx else COLOR_WHITE
            text = f"{i%10}: {char} - {name}"
            self.screen.blit(self.font.render(text, True, color), (20, y_off))
            y_off += 20
            if y_off > SCREEN_HEIGHT - 100:
                break

        self.screen.blit(self.font.render("Controls:", True, COLOR_GREY), (10, SCREEN_HEIGHT - 80))
        self.screen.blit(self.font.render("WASD: Pan, +/-: Resize", True, COLOR_WHITE), (10, SCREEN_HEIGHT - 60))
        self.screen.blit(self.font.render("Ctrl+S: Save, L: Load", True, COLOR_WHITE), (10, SCREEN_HEIGHT - 40))

        pygame.display.flip()

    def handle_input(self):
        """Handles user input for the editor."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_s and pygame.key.get_mods() & pygame.KMOD_CTRL:
                    self.save_map()

                # Palette Selection
                if pygame.K_0 <= event.key <= pygame.K_9:
                    idx = event.key - pygame.K_0
                    if idx < len(PALETTE):
                        self.brush_idx = idx

                # Canvas Resizing
                if event.key == pygame.K_EQUALS: # Plus
                    for row in self.grid:
                        row.append('#')
                    self.map_w += 1
                if event.key == pygame.K_MINUS and self.map_w > 1:
                    for row in self.grid:
                        row.pop()
                    self.map_w -= 1

                if event.key == pygame.K_l:
                    name = input("Enter map name to load (e.g. sanctuary): ")
                    self.load_map(name)

        # Continuous Input
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

        # Mouse Interaction
        mouse_buttons = pygame.mouse.get_pressed()
        if mouse_buttons[0]: # Left Click
            mx, my = pygame.mouse.get_pos()
            ts = int(TILE_SIZE * self.zoom)
            gx = (mx + self.camera_x) // ts
            gy = (my + self.camera_y) // ts
            if 0 <= gx < self.map_w and 0 <= gy < self.map_h:
                self.grid[gy][gx] = PALETTE[self.brush_idx][0]
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
