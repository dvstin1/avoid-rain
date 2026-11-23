# Avoid Rain

A **"Scriptorium Noir"** 2D action-exploration roguelite built with Python and Pygame. Draft your path across the **Unbound Chronicle** (a 5-Act campaign spanning 7 procedural biomes), outrun the encroaching ink-rain, weave passive scripts with The Binder, and confront each biome's Night Boss on the way to The Final Author.

---

## Requirements

- **Python 3.13**
- **Pygame 2.6.1** (pinned in `requirements.txt`)
- Optional: `numpy` (enables subtle runtime SFX pitch-jitter and faster procedural audio generation) and `pytest` / `pylint` for development.

---

## Windows

> **Note:** Python 3.14+ is currently not supported due to pygame installation issues.

1. Install **Python 3.13** from [python.org](https://www.python.org/downloads/) (enable the `py` launcher during setup).
2. Clone the repository and open a terminal in the project root.
3. Create and activate a Python 3.13 virtual environment, then install dependencies:
   ```powershell
   py -3.13 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```
4. Launch the game:
   ```powershell
   python main.py
   ```

---

## Linux/macOS

1. Ensure **Python 3.13** is installed (`python3.13 --version`).
2. Clone the repository and open a terminal in the project root.
3. Create and activate a Python 3.13 virtual environment, then install dependencies:
   ```bash
   python3.13 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
4. Launch the game:
   ```bash
   python main.py
   ```

---

## Running the Game

```bash
python main.py
```

### Command-Line Arguments
- `--fullscreen`: Launches the game in scaled fullscreen mode (1280x720 internal canvas).

---

## Controls

All primary keyboard bindings can be remapped at any time from the **Title Menu -> Controls** or **Pause Menu -> Controls** screen (persisted automatically to `save_data.json`). Both keyboard/mouse and gamepad inputs are supported with seamless auto-switching.

### Default Bindings
- **WASD / Arrows / Left Stick / D-Pad:** Move / Navigate Menus
- **SPACE / (A):** Attack / Interact / Confirm
- **L-SHIFT / (B):** Dash (Invulnerable / Break Free from Ice Encasement)
- **K / (RT):** Block & Parry
- **Q / (LB):** Swap Active Weapon (or click Slot B on the HUD)
- **1 / (Y):** Drink Healing Flask
- **TAB / (RB):** Inspect Nearby Weapons & Lore
- **R:** Quick-Rest at an open Respite Anchor
- **ESC / (Start):** Pause Menu / Close Overlay

---

## Procedural Content & Map Editor

- **Map Editor:** Design modular biome segments and standalone maps:
  ```bash
  python tools/edit_map.py
  ```
- **Regenerate Procedural Sprites:** `python generate_assets.py`
- **Regenerate Procedural SFX & Music:** `python generate_sfx.py`
- **Regenerate Biome Segment Pools:** `python generate_maps.py --generate-pools`

---

## Development & Testing

### Running Tests
Tests run headlessly via SDL dummy video/audio drivers:
```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest -q
```

### Linting
All Python source files must adhere to a **120-character** maximum line length and pass `pylint` with a score of **8.0 or higher**:
```bash
pylint --max-line-length=120 main.py constants.py engine/ rendering/ ui/
```

---

## Documentation

Detailed architectural and design references live in `docs/`:
- `docs/architecture.md`: Engine systems, state schemas, and combat rules.
- `docs/navigation_and_ui.md`: Camera, HUD, minimap, and input handling.
- `docs/modular_system.md`: Level serialization and Master Loom assembly.
- `docs/visual_style_and_assets.md`: Sprite, tile, and art blueprints.
- `docs/CHANGELOG.md`: Historical archive of completed milestones.

---

## License

GNU GPL v2 (see `LICENSE`).
