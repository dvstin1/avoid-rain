# Navigation, UI & Input Architecture

This document defines the systems responsible for viewport management, user interface behavior, and input translation.

## 1. Input Architecture (Abstraction Layer)
To maintain a decoupled design, input is translated from raw hardware events into logical "Action" objects.
- **Continuous Input (WASD):** Polled every frame to generate a normalized movement vector, ensuring fluid motion scaled by `dt`.
- **Discrete Actions (Space, Shift, R, 1-3):** Hybrid event/polling handles instant triggers (Attack, Dash) and menu selections.
- **State Lock:** The engine suppresses new actions while the player is in an uninterruptible state (e.g., `ATTACKING`).

### 1.1. Key & Button Mapping (Remappable Keyboard Controls)
All 11 keyboard bindings (`DEFAULT_KEYBINDINGS` in `constants.py`) can be remapped interactively via the **Controls** sub-menu (`ControlsConfigMenu` in `ui/menu.py`, accessible from both Title and Pause menus) and are persisted in `save_data.json`. Arrow keys always remain active for movement alongside custom directional bindings.

| Input | Default Keyboard | Gamepad | Action |
| :--- | :--- | :--- | :--- |
| **Move** | WASD / Arrows | L-Stick / D-Pad | Movement / Navigation |
| **Action** | SPACE | Cross / A | Attack / Interact / Pick up |
| **Dash** | L_SHIFT | Circle / B | Invulnerable Dash |
| **Heal** | 1 | Triangle / Y | Use Flask |
| **Swap** | Q | L1 / LB | Toggle Weapon / Contextual Pickup |
| **Inspect** | TAB (Hold) | R1 / RB (Hold) | Reveal Weapon Details |
| **Block** | K | R2 / RT | Raise Shield |
| **Respite Rest** | R | Circle / B (in Respite) | Rest at Respite Anchor |
| **Pause** | ESCAPE | Start / Options | Toggle Menu |

## 2. Viewport Management (Camera)
The `Camera` is a stateful, frame-rate independent controller centered on the player.
- **Smoothing:** Supports exponential damping (`CAMERA_LERP_SPEED`) for smooth following.
- **Clamping:** Viewport is strictly clamped to world boundaries to prevent rendering the "Void."
- **Coupling:** Decouples rendering math from player logic; rendering reads the camera offset to position world assets.

## 3. User Interface Systems

### 3.1. Title Menu
The title screen adaptively presents options based on the physical presence of a compatible `save_data.json` (`engine_revision == ENGINE_REVISION`):
- **Dynamic Options:** Displays `New Draft`, `Continue` (only if a compatible save is detected, selected by default), `Mode: Online` / `Mode: Offline` (or `Mode: Offline (--offline)` when locked via CLI), `Controls`, and `Quit`, plus `[N] Change Name` to edit `player_name` directly on the title screen.
- **Overwrite Protection:** Selecting `New Draft` while a compatible save exists triggers a mandatory Y/N confirmation modal.
- **Tactile Menu Transitions (`compute_menu_transition_state()`):** Title, Confirm, Pause, and Controls panels smoothly unroll vertically like physical parchment with a fading scroll roller edge (`MENU_TRANSITION_DURATION = 0.28s`, sub-views `0.22s`) without blocking immediate keyboard/gamepad navigation.
- **Storm-and-Lightning Transition (`TitleTransition`):** Starting or continuing a game runs a 3-phase sequence (`FADE_TO_BLACK` → `STORM_VIGNETTE` with `storm_intro.ogg`, falling rain, and procedural lightning bolts → `FADE_OUT_AND_WARP` into the Sanctuary). Pressing `Space`, `Enter`, `Escape`, or a gamepad button skips directly to the Sanctuary.

### 3.2. HUD Status Display (Lower-Left & Bottom-Center)
- **Compact Visual HUD (`252x148` Lower-Left):** Visual HP bar, Flask vials, Torn Pages counter, Understanding/Edification level, and dual weapon slots with tier coloring (White: Common, Purple: Anomalous), plus a contextual pickup pill when standing near floor drops.
- **Bottom-Center Boss Name & Health Bar (`Renderer.draw_boss_hud()`):** Displays the active summoned boss's display name (`BOSS_HUD_DISPLAY_NAMES`, `FinalAuthor > NightBoss > Miniboss` priority) in medium `manuscript_serif` font with a dark 8-way outline above a centered bottom HP bar, clearing automatically on defeat.
- **Interaction Rules:**
    - **Pick up:** Stand near an item and press `SPACE / A` to collect it.
    - **Contextual Swap:** Press `Q / L1` while over a weapon to immediately swap it into your current slot.
- **Expanded Inspect View (Hold TAB / R1):** Reveals stylized "Marginalia" parchment tooltips for all equipped quills and any weapon on the floor.
    - **Full Metadata:** Reveals full name, flavor description (Critique), and explicit stat modifiers (e.g., `Bleed`, `Attack`, `Max HP`).
    - **Side-by-Side Comparison:** Tooltips are arranged horizontally for quick evaluation of floor items against current loadouts.

### 3.3. System Diagnostic Telemetry & Pause Options (Top-Center & Pause Menu)
- **Pause Menu Options (`engine/pause_menu.py`):** Exposes `Resume`, conditional `Return to Sanctuary` (shown when `waiting_scholars > 0` in LAN Co-op), `Controls` (remappable keybindings sub-menu), `Debug Text: OFF/ON`, debug-only `Debug Event: ...` & `Reset Margin Scraps`, `Screen Shake: ON/OFF` (`screen_shake_enabled`, default `ON`), `Gamepad Rumble: ON/OFF` (`rumble_enabled`, default `ON`), and `Quit`. All toggles persist in `save_data.json`.
- **Audio & Map OSD (Center):** When `debug_text_enabled` is active, displays the active background music track (e.g., `[ AUDIO_OSD ] MUSIC: night_boss.ogg`) in Toxic Green, followed by the active map filename (`Map: <map_filename>`), Biome/Act status, and active Marginalia event state.
- **SFX Trigger Log (Top-Left):** Real-time list of triggered sound effects (e.g., `SFX: sword_hit.ogg`) that fade out over 2 seconds (gated behind `debug_text_enabled`).
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
To prevent accidental progression errors, the Respite menu (`draw_respite_menu`, `620x290` centered modal) defaults its cursor to `[ CLOSE MENU ]` with press-and-release input ratcheting and implements a staged upgrade system:
1. **Focus:** Navigate vertically between Rest (`[R]`), Upgrades, Finalize, and Close. Resting triggers the `RespiteActivationPulse` localized typographic bloom (immediately and replayed unobstructed upon closing the modal).
2. **Mark:** Pressing `Confirm` (or keys `1-3`) on an upgrade stages it with a `[ +N ]` indicator.
3. **Finalize:** The player must manually navigate to the `[ FINALIZE UPGRADES ]` button to execute the transaction.
- **Visual Lockout:** If `player.pages < cost`, the option text color shifts to a muted dark charcoal grey, and a red `[Insufficient]` warning is rendered inline.
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

### 3. Input Mode Toggling Rules (Automatic Switching)
To provide a seamless experience, the engine monitors all input hardware concurrently:
- **Rule - Switch to Gamepad:** If the engine receives a `JOYBUTTONDOWN` or a significant `JOYAXISMOTION` event, the global `input_mode` is instantly set to `"GAMEPAD"`.
- **Rule - Switch to Keyboard:** If the engine receives a `KEYDOWN` or `MOUSEBUTTONDOWN` event, the global `input_mode` is instantly set to `"KEYBOARD"`.
- **The State Hysteresis:** The HUD indicator and menu navigation logic respond immediately to these state changes, updating visual prompts (e.g., swapping `[SPACE]` for `(X)`) without requiring a manual setting change.

### 4. Input Mode HUD Indicator (Debug-Gated)
- When `debug_text_enabled` is `True`, the UI layer renders a live input-mode tracking string on the active gameplay HUD:
  - Mode Keyboard: Displays `[ Input: Keyboard ]` in standard ivory white.
  - Mode Gamepad: Displays `[ Input: Gamepad ]` in stark gold/amber.
- **The Menu Snapping Rule:** While `input_mode == "GAMEPAD"`, all active menu surfaces (Respite, Chronicle Biome Selection, Binder, Options) utilize directional index trapping. Moving the analog stick shifts focus loops between menu items, completely bypassing mouse cursor coordinate collision requirements.

### 5. Host-Driven 5-of-7 Unbound Chronicle Biome Selection Dialog
Interacting with the Sanctuary Chronicle (`WarpPortal`) opens a 5-step modal (`draw_chronicle_biome_menu` in `ui/menu.py`) before warping:
- **Acts 1–5 Folio Draft (`MAX_ACTS = 5`):** For each Act step `1..5`, the player (or Host in LAN Co-op) selects `Random` or one of the 7 biomes in `CHRONICLE_BIOME_ROSTER` (`windy_ridge`, `pastoral_valley`, `swamp_mire`, `frozen_peaks`, `tech_tower`, `vitreous_basin`, `sunlit_aqueducts`), with already-drafted biomes greyed out to guarantee 5 distinct biomes per run, plus `Back` / `Cancel`. Each step previews the Act's escalation tier from `ACT_SATURATION_MATRIX`.

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
