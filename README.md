# Avoid Rain

Small 2D engine prototype for the 'Avoid the Rain' project. A "Scriptorium Noir" action-exploration game built with Python and Pygame.

## Phase: Coding — Phase 1 (Core Gameplay Loop)

---

## Getting Started

### Prerequisites
- **Python 3.10+**
- **Pygame-CE** (or standard Pygame)

### Installation
1. Clone the repository.
2. Install dependencies:
   ```bash
   pip install pygame-ce
   ```

---

## Running the Game
To launch the game:
```bash
python main.py
```

### Command-Line Arguments
- `--fullscreen`: Launches the game in fullscreen mode (1280x720 scaled).

---

## Controls
- **WASD / Arrows:** Move Player / Navigate Menus
- **SPACE / (A):** Attack / Interact / Confirm
- **L-SHIFT / (B):** Dash (Invulnerable)
- **K / (RT):** Block (Negates damage, parries on startup)
- **Q / (LB):** Swap Weapons
- **1 / (Y):** Use Healing Flask
- **ESC / (Start):** Pause Menu

---

## Map Editor
The project includes a native Pygame-based map editor for designing modular sub-maps and macro layouts.

To launch the editor:
```bash
python tools/edit_map.py
```

### Editor Controls
- **WASD:** Pan camera
- **Mouse Wheel:** Zoom
- **1-0:** Select Tool Slot
- **Click [SET]:** Remap tool to slot
- **Ctrl+S:** Save Map
- **Ctrl+O:** Open/Load Map
- **Ctrl+R:** Resize Canvas
- **Ctrl+N:** New Blank Map
- **H:** Toggle Help Dialog

---

## Development & Testing

### Running Tests
The project uses `pytest` for unit testing. To run the suite:
```bash
pytest tests/
```
*Note: Tests are configured for headless execution and do not require a display.*

### Linting
All code must pass `pylint` with a score of 8.0 or higher.
```bash
pylint engine/ rendering/ main.py
```

---

## Documentation
Comprehensive documentation is located in the `docs/` directory:
- `architecture.md`: System specs and execution flow.
- `navigation_and_ui.md`: Input and viewport management.
- `modular_system.md`: Level serialization and generation.
- `docs/CHANGELOG.md`: Project history and completed tasks.

---

## License
GNU GPL v2 (see LICENSE)
