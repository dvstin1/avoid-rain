# Navigation, UI & Input Architecture

This document defines the systems responsible for viewport management, user interface behavior, and input translation.

## 1. Input Architecture (Abstraction Layer)
To maintain a decoupled design, input is translated from raw hardware events into logical "Action" objects.
- **Continuous Input (WASD):** Polled every frame to generate a normalized movement vector, ensuring fluid motion scaled by `dt`.
- **Discrete Actions (Space, Shift, R, 1-3):** Hybrid event/polling handles instant triggers (Attack, Dash) and menu selections.
- **State Lock:** The engine suppresses new actions while the player is in an uninterruptible state (e.g., `ATTACKING`).

### 1.1. Key Mapping
| Key | Context | Action |
| :--- | :--- | :--- |
| **W, A, S, D** | Exploration | Movement (WASD: Pan Camera/Map) |
| **SPACE** | Combat/World | Attack / Interact / Confirm |
| **L_SHIFT** | Combat | Dash (Invulnerability) |
| **R** | Menus | Rest (Respite) |
| **1, 2, 3** | Menus | Select Edification Upgrade |
| **ESCAPE** | Menu | Pause / Quit / Close Dialog |
| **H** | UI | Toggle Help Dialog (Map Editor) |
| **B** | UI | Toggle Pencil/Rectangle Tool (Map Editor) |
| **J** | UI | Select Socket Tool (Map Editor) |

## 2. Viewport Management (Camera)
The `Camera` is a stateful, frame-rate independent controller centered on the player.
- **Smoothing:** Supports exponential damping (`CAMERA_LERP_SPEED`) for smooth following.
- **Clamping:** Viewport is strictly clamped to world boundaries to prevent rendering the "Void."
- **Coupling:** Decouples rendering math from player logic; rendering reads the camera offset to position world assets.

## 3. User Interface Systems

### 3.1. Title Menu
The title screen adaptively presents options based on the physical presence of `save_data.json`.
- **Dynamic Options:** Displays `[Continue]` only if valid save data is detected.
- **Overwrite Protection:** Selecting `[New Game]` while a save exists triggers a mandatory Y/N confirmation modal with a 2-second input lock.

### 3.2. HUD Status Display (Lower-Left)
Text items in the HUD use a compact 14pt font line size to prevent viewport crowding:
- **Metrics:** `HP`, `Flasks`, `Pages`, and `Level`.
- **Equipment:** Dual weapon slots with tier coloring (White: Common, Purple: Anomalous).
- **Buttons:** Clickable `[SWAP]` and `[PICK UP]` widgets for mouse interaction.

### 3.3. System Diagnostic Telemetry (Top-Right Stack)
- **Line 1 (Y: 10px):** Contextual save status indicator (`[Saving...]`).
- **Line 2 (Y: 25px):** Active Audio Track state tracker (`[AUDIO: <track_name>]`).

## 4. Large-Scale Minimap HUD (Top-Left)
The Minimap automatically adapts its rendering states based on the active map sector to guarantee crisp visibility and orientation:

### 1. Conditional Visibility & Scale Zoom
- **The Sanctuary Hub:** The minimap layer is completely deactivated and hidden.
- **The Macro Run Map (440x440):** Active and rendered with a high **Close-Up Zoom Ratio** (e.g., 4x or 6x tile scaling factor).
- **Uniform Scaling Rule:** The system uses a single, consistent scale factor for both X and Y axes to prevent "elliptical" distortion of circular zones and entities.

### 2. UI Color Profiles & Wave Perimeter Mapping
- **The Player:** Rendered as a distinct **White** marker.
- **Hostile Entities:** Rendered as **Red** markers.
- **The Redacting Circle Edge:** Rendered as a concentric **Amber/Orange** line showing the current safe perimeter.

### 3. Surface Processing Order
To prevent frame erasure or blackouts, the minimap follows a strict pipeline:
1. **Clear Pass:** `.fill()` surface with base background tone.
2. **Tile Blitting:** Draw scaled wall structures using integer coordinate casting.
3. **Entity Blitting:** Layer radar dots and safe circle boundary.
4. **Final Blit:** Paint the local surface onto the main display window.

## 5. Typographic Bloom (Dynamic Sector Overlay)
Narrative discovery feedback that draws large, stylized titles across the viewport when entering major 120x120 Room sockets.

### 1. Zone Entry Boundary Filtering
- **State Hysteresis Gate:** Animation only triggers if the player's coordinate zone changes *and* a 10.0 second cooldown has passed since the last transition.
- **Milestone Alerts:** Also used for environmental signals: `"THE INK BEGINS TO RUN"` and `"THE FINAL PARAGRAPH LOCKS"`.

### 2. Alpha-Fade Visual Timeline
The overlay renders with an asynchronous alpha opacity timeline:
1. **Fade In (1.0s):** Text alpha 0 -> 255.
2. **Sustain (2.0s):** Text alpha remains at 255.
3. **Fade Out (1.0s):** Text alpha 255 -> 0.

## 6. Specialized Leveling Interfaces (Respite Menu)

### 1. Dynamic Evaluation & Live Binding
The Respite leveling panel reads values directly from the live `player.stats` layer on every frame.
- **Visual Lockout:** If `player.pages < cost`, the option text color shifts to a muted dark charcoal grey (`#4A4A4A`), and a red `[ Insufficient Pages ]` warning is rendered inline.
- **Immediate Feedback:** The interface regenerates its font surfaces every frame to ensure upgrades and costs update visually the instant a button is pressed.

## 7. Map Editor Interface (Native Pygame Tool)

### 1. Multi-Tool Hotbar (1-0 Keys)
- permanent vertical array of exactly 10 tool slots.
- **Remapping:** Clicking the "SET" button opens a scrollable modal listing all compiled system brushes.
- **Exclusion Logic:** Assigning a tool to a new slot automatically unassigns it from its previous location.

### 2. Controls & Utilities
- **WASD:** Pan camera.
- **Mouse Wheel / +/-:** Zoom in and out.
- **Ctrl+R:** Open interactive resize dialog.
- **Ctrl+S / Ctrl+O:** Save and Load (with scrollable file picker).
- **Ctrl+N:** Reset to blank canvas.
- **Input Bleed-Through Fix:** Implements a mouse-release blocker that ignores map clicks until the button is physically released after closing a modal dialog.
