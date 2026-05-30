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

## 5. System Status Overlay & Diagnostic Telemetry (Top-Right HUD Stack)
The top-right quadrant of the active display window is reserved for transient engine status indicators and persistent debug readouts. Text items in this stack use the compact, small font line size to prevent viewport crowding:
- **Line 1 (Y-Offset: 10px):** Contextual save status indicator (`[Saving...]`).
- **Line 2 (Y-Offset: 25px):** Active Audio Track state tracker readout (`[AUDIO: <track_name>]`).

## 6. Dynamic Multi-Tool Palette Matrix (Map Editor HUD Layout)

To accommodate an expanding registry of environment tiles, enemy variants, and modular design utilities without crowding the editing canvas, the palette utilizes a fixed-row socket framework.

### 1. The 10-Slot Multi-Tool Hotbar
- The editor panel renders a permanent vertical or horizontal array of exactly 10 composite button structures.
- **Left Region (Activation Area):** Displays the current tool's name string (e.g., `[ Floor Tile ]` or `[ Bat Spawner ]`). Clicking this region activates the tool brush globally.
- **Right Region (Configuration Area - labeled "▼"):** Clicking this boundary opens an overlaid scrollable modal listing all compiled system brushes.

### 2. The Unique Mapping Registry (Mutual Exclusion)
- The editor maintains a dictionary vector: `editor.palette_mapping = {0: tool_id, 1: tool_id, ...}`.
- If a user maps an active tool ID to Slot B that is currently registered to Slot A:
  - Slot A's registry is instantly overwritten to `None`.
  - Slot A's visual interface display drops back to an empty template string: `[ Unassigned ]`.

## 7. Map Editor Dimension Control & Scrollable Palettes

### 1. Dimension HUD Button Action
- The Map Size readout `[Size: W x H]` acts as a fully interactive button zone.
- Clicking this string opens a safe, modal text entry box.
- The system handles canvas resizing using dynamic grid padding (appending `" "` for layout growth) or safe edge truncation, fully deprecating legacy row/column insertion hotkeys.

### 2. Multi-Tool Selector Box Behavior
- The tool remapping dialog box supports continuous mouse wheel events (`pygame.MOUSEBUTTONDOWN` with button codes `4` for Up and `5` for Down).
- Clicking a specific row menu item explicitly selects that tool brush, binds it to the current hotbar socket slot, and closes the active dialog overlay cleanly.

## 8. Large-Scale Minimap HUD Systems & Unit Signifiers

The Minimap interface automatically adapts its rendering states based on the scale of the active map sector to guarantee crisp visibility and orientation:

### 1. Conditional Visibility & Scale Zoom Factors
- **The Sanctuary Hub:** The minimap layer is completely deactivated and hidden. No radar components are drawn to the screen canvas.
- **The Macro Run Map (440x440):** The minimap layer is active and rendered at an elevated **Close-Up Zoom Ratio** (e.g., 4x or 6x tile scaling factor), ensuring tight corridor junctions are highly distinct.

### 2. UI Color Profiles & Wave Perimeter Mapping
To maximize legibility at high zoom scales, radar pixels use high-contrast color values:
- **The Player Position:** Rendered as a distinct **Pristine White** pixel/circle marker.
- **Hostile Entities:** Rendered as **Crimson Red** markers.
- **The Redacting Circle Edge:** The map draws a scaled, concentric loop matching the current `active_safe_radius` using a **Vibrant Amber/Orange** brush line, showing you exactly how far the storm is from your current grid box.

## 8. Large-Scale Minimap HUD Systems & Unit Signifiers

### 3. Minimap Surface Frame Processing Order
To prevent frame erasure or empty buffer blackouts, the minimap drawing cycle must adhere to a strict chronological frame execution pipeline:
1. **Instantiation/Clear Pass:** Fill the localized `minimap_surface` with its base background tone (e.g., translucent dark gray/black).
2. **Sub-Surface Blitting Pass:** Draw the scaled static environment tiles, the White player node, the Crimson enemy vectors, and the Amber safe ring onto the `minimap_surface`.
3. **Primary Canvas Blit Pass:** Execute `main_screen.blit(minimap_surface, destination_rect)`. 
- *Constraint:* No surface clearing operations (`.fill()`) or dimension reinstantiations may occur after Step 2 has executed for the current frame.

