# Navigation, UI & Input Architecture

This document defines the systems responsible for viewport management, user interface behavior, and input translation.

## 1. Input Architecture (Abstraction Layer)
To maintain a decoupled design, input is translated from raw hardware events into logical "Action" objects.
- **Continuous Input (WASD):** Polled every frame to generate a normalized movement vector, ensuring fluid motion scaled by `dt`.
- **Discrete Actions (Space, Shift, Q, K, 1-2):** Hybrid event/polling handles instant triggers (Attack, Dash) and charged states.
- **State Lock:** The engine suppresses new actions while the player is in an uninterruptible state (e.g., `ATTACKING`).

### 1.1. Key Mapping
| Key | Context | Action |
| :--- | :--- | :--- |
| **W, A, S, D** | Exploration | Movement |
| **SPACE** | Combat/World | Attack / Interact |
| **L_SHIFT** | Combat | Dash (Invulnerability) |
| **K** | Combat | Block (Shield-up) |
| **Q** | Combat | Weapon Swap |
| **1, 2** | Survival | Use Item / Flask |
| **ESCAPE** | Menu | Pause / Quit |

## 2. Viewport Management (Camera)
The `Camera` is a stateful, frame-rate independent controller centered on the player.
- **Smoothing:** Supports exponential damping (`CAMERA_LERP_SPEED`) for smooth following.
- **Clamping:** Viewport is strictly clamped to world boundaries to prevent rendering the "Void."
- **Coupling:** Decouples rendering math from player logic; rendering reads the camera offset to position world assets.

## 3. User Interface Systems

### 3.1. Title Menu
The title screen adaptively presents options based on the existence of `profile_metrics.json`.
- **Dynamic Options:** Displays `[Continue]` only if valid save data is detected.
- **Overwrite Protection:** Selecting `[New Game]` while a save exists triggers a mandatory Y/N confirmation modal with a 2-second input lock to prevent accidental loss.

### 3.2. Minimap (Top-Left HUD)
Provides a spatial overview showing a window around the player rather than the full world.
- **Panning:** The minimap viewport centers on the player and pans as they move.
- **Vision:** Only displays wall structures and player position; keeps exploration targets hidden.
- **Future:** Compass indicators for off-screen objectives.

### 3.3. Controls Overlay (Tabbed View)
A centralized modal for remapping and reference.
- **Tabs:** Internal state toggles between `KEYBOARD` and `GAMEPAD` layouts.
- **Isolation:** Keeps different controller mapping metrics entirely separated.
