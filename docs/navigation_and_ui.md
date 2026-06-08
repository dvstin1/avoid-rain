# Navigation, UI & Input Architecture

This document defines the systems responsible for viewport management, user interface behavior, and input translation.

## 1. Input Architecture (Abstraction Layer)
To maintain a decoupled design, input is translated from raw hardware events into logical "Action" objects.
- **Continuous Input (WASD):** Polled every frame to generate a normalized movement vector, ensuring fluid motion scaled by `dt`.
- **Discrete Actions (Space, Shift, R, 1-3):** Hybrid event/polling handles instant triggers (Attack, Dash) and menu selections.
- **State Lock:** The engine suppresses new actions while the player is in an uninterruptible state (e.g., `ATTACKING`).

### 1.1. Key & Button Mapping
| Input | Keyboard | Gamepad | Action |
| :--- | :--- | :--- | :--- |
| **Move** | WASD / Arrows | L-Stick / D-Pad | Movement / Navigation |
| **Action** | SPACE | Cross / A | Attack / Interact / Confirm |
| **Dash** | L_SHIFT | Circle / B | Invulnerable Dash |
| **Heal** | 1 | Triangle / Y | Use Flask |
| **Swap** | Q | L1 / LB | Toggle Weapon Slots |
| **Block** | K | R2 / RT | Raise Shield |
| **Pause** | ESCAPE | Start / Options | Toggle Menu |

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
- **Hotkeys:** Integrated labels showing `[Q / L1]` for Swapping and `[SPACE / A]` for Pickups.

### 3.3. System Diagnostic Telemetry (Top-Center & Left)
- **Audio OSD (Center):** Displays the active background track (e.g., `[ AUDIO_OSD ] MUSIC: night_boss.ogg`) in Toxic Green.
- **SFX Trigger Log (Top-Left):** Real-time list of triggered sound effects (e.g., `SFX: attack_hit.ogg`) that fade out over 2 seconds.
- **Save Status (Top-Right):** Contextual indicator (`[Saved]`) following autosave operations.

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

### 1. The Mark & Finalize Workflow
To prevent accidental progression errors, the Respite menu implements a staged upgrade system:
1. **Focus:** Navigate vertically between Rest, Upgrades, Finalize, and Close.
2. **Mark:** Pressing `Confirm` (or keys `1-3`) on an upgrade stages it with a `[ MARKED ]` indicator.
3. **Finalize:** The player must manually navigate to the `[ FINALIZE UPGRADE ]` button to execute the transaction.
- **Visual Lockout:** If `player.pages < cost`, the option text color shifts to a muted dark charcoal grey, and a red `[ Insufficient Pages ]` warning is rendered inline.
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

## 8. Unified Gamepad Mapping & Input Mode State Machine

The input engine supports concurrent Keyboard/Mouse and Joystick execution via an explicit state toggle system to guarantee 100% controller-only navigation.

### 1. Hardened Drift Resilience
To ensure reliable menu navigation on hardware with significant analog drift:
- **Vertical Targeting:** The navigation ratchet only monitors the specific vertical axis (Stick Y) and D-pad state during menu loops.
- **The 0.6 Threshold:** The engine ignores any stick movement below 60% of the maximum throw when checking for the "Neutral" reset signal. This prevents drift from "locking" the selection.
- **Temporal Debounce:** A mandatory **0.2 second cooldown** is enforced between all menu moves to prevent rapid-fire selection spam.

### 2. Gamepad Device Profiles
The engine registers explicit button vectors based on the hardware initialization name string:
- **Profile A: Sony PlayStation 5 DualSense**
  - Left Stick / D-Pad: Movement Axes 0 & 1
  - Button 0 (Cross): `ACTION_CONFIRM` / `SWORD_SWING`
  - Button 1 (Circle): `ACTION_CANCEL` / `DASH`
- **Profile B: SteelSeries Free Bluetooth**
  - Left Stick / D-Pad: Map to corresponding Axis vectors
  - Face Buttons (Right Quadrant): Map to matching unified action strings based on device index lookup arrays.

### 2. Input Mode Toggling Rules (Automatic Switching)
To provide a seamless experience, the engine monitors all input hardware concurrently:
- **Rule - Switch to Gamepad:** If the engine receives a `JOYBUTTONDOWN` or a significant `JOYAXISMOTION` event, the global `input_mode` is instantly set to `"GAMEPAD"`.
- **Rule - Switch to Keyboard:** If the engine receives a `KEYDOWN` or `MOUSEBUTTONDOWN` event, the global `input_mode` is instantly set to `"KEYBOARD"`.
- **The State Hysteresis:** The HUD indicator and menu navigation logic respond immediately to these state changes, updating visual prompts (e.g., swapping `[SPACE]` for `(X)`) without requiring a manual setting change.

### 3. Input Mode HUD Indicator
- The UI layer renders a permanent tracking string on the active gameplay HUD matrix.
- **Display Configurations:**
  - Mode Keyboard: Displays `[ Input: Keyboard ]` in standard ivory white.
  - Mode Gamepad: Displays `[ Input: Gamepad ]` in stark gold/amber.
- **The Menu Snapping Rule:** While `input_mode == "GAMEPAD"`, all active menu surfaces (Respite, Options) utilize directional index trapping. Moving the analog stick shifts focus loops between menu items, completely bypassing mouse cursor coordinate collision requirements.

## 9. Map Editor Access & Core Controls
The project includes a native Pygame-based map editor for designing modular sub-maps and macro layouts.

- **Launch Command:** `python tools/edit_map.py`
- **Primary Interface:** A 2D grid-based canvas with a tool sidebar.

### 1. Navigation & Viewport
- **WASD / Arrows:** Pan the camera around the map.
- **Mouse Wheel / [+/-] Keys:** Zoom in and out.
- **[H] Key:** Toggle the Help Dialog (Command Reference).

### 2. Tools & Brushes
- **1-0 Keys:** Select one of the 10 active tool slots.
- **[SET] Button:** Click the "SET" label on a slot to open the Tool Registry modal and assign a new tile, enemy, or utility to that slot.
- **Left-Click:** Place the active tool on the grid.
- **Right-Click:** Eraser (sets tile to TILE_EMPTY).

### 3. Canvas & File Management
- **Ctrl+S:** Save the current map to `maps/`.
- **Ctrl+O:** Open the visual map picker to load an existing JSON file.
- **Ctrl+R:** Open the Resize Dialog to alter the grid dimensions.
- **Ctrl+N:** Reset to a blank 20x20 canvas.
