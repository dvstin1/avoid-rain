# Application Architecture & Lifecycle

This document outlines the high-level execution flow and the main entry point's structural requirements.

## 1. main.py Structural Skeleton
To ensure a clean exit on Debian Linux and prevent orphaned processes, `main.py` must follow this lifecycle pattern:

```python
import pygame
import sys
from constants import *
from engine.game_state import GameState
from rendering.renderer import Renderer

def main():
    # 1. Initialization
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    clock = pygame.time.Clock()
    
    state = GameState()
    renderer = Renderer(screen)
    
    running = True
    
    try:
        # 2. Main Game Loop
        while running:
            # a. Calculate Delta Time (dt)
            dt = clock.tick(FPS) / 1000.0
            
            # b. Event Handling (Discrete Input)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    # Pass other discrete actions to engine
            
            # c. Polling (Continuous Input)
            # Pass keys to engine for movement
            
            # d. Update Engine Logic
            # state.update(dt, actions)
            
            # e. Rendering
            # renderer.render(state)
            
    finally:
        # 3. Clean Exit Routine
        # This block executes even if the loop is broken by an error
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    main()
```

## 2. Key Lifecycle Rules
- **Resource Management:** All Pygame surfaces and sound channels must be initialized within the `main()` scope or managed by a dedicated loader that is called within the `try` block.
- **Error Handling:** The `finally` block is mandatory to ensure the terminal state of the Debian environment remains clean.
- **FPS Capping:** The loop must be capped (defaulting to 60 FPS) to prevent excessive CPU usage, while still providing `dt` for frame-rate independence.

## 3. Decoupled Directory Structure (File Blueprint)
To maintain the **Decoupled Design** constraint, the project follows this structure:

```text
avoid_rain/
├── main.py                # Entry point: initializes Pygame and the main loop.
├── constants.py           # Central registry for all configuration.
├── engine/                # PURE LOGIC: No pygame imports allowed here.
│   ├── game_state.py      # The master State object.
│   ├── player.py          # Player movement, stats, and state machine.
│   ├── physics.py         # Collision math (AABB) and dt scaling.
│   ├── combat.py          # Hitbox logic and damage calculation.
│   └── world.py           # Rain circle math and modular section logic.
└── rendering/             # PYGAME CODE: Handles all drawing and input mapping.
    ├── renderer.py        # Main drawing coordinator.
    ├── camera.py          # Handles screen offsets.
    └── assets.py          # Sprite loading and animation management.
```

### Import Rules
- `engine/` files must never import `pygame`.
- `rendering/` files can import `engine/` to read state, but not vice versa.

## 4. Climate Engine: The Devouring Storm Lifecycle

The climate engine dictates the pace of gameplay, splitting a standard run into two distinct strategic acts synchronized with a 4-stage state machine.

### Act I: The Exploration Window (0:00 to 10:00)

1. **State: Clear_Day (The Calm Before)**
   - **Duration:** 10 minutes.
   - **Visuals:** Ambient, rhythmic background particle drops.
   - **Hazard:** `OFF`.
   - **Navigation:** Standard movement; player explores the modular chambers.
   - **Respites:** `ACTIVE`.

### Act II: The Closing Collapse (10:00 Onward)

2. **State: The_Bleed (The Corrosive Ink-Storm)**
   - **Transition:** At the 10-minute mark, the weather shifts to a massive, corrosive ink-storm.
   - **Visual density:** High density, sharp diagonal vectors, custom cyan/lime or ink-black palette tint.
   - **The Closing Shrink:** The safe zone (active radius) shrinks continuously toward a randomized central map coordinate over a **3 to 5-minute window**.
   - **The Hazard Boundary:** Any player coordinates outside the active radius take progressive damage: `take_damage(2)` per second.
   - **Respites:** `DEACTIVATED`.
   - **The Climax:** Once the circle reaches its minimum threshold diameter, the Final Boss is instantly instantiated at the center point.

### Resolution & Reset

3. **State: The_Dilution (Immediate Post-Boss Victory)**
   - Rain particle generator: `ON` (Transitions velocity to a gentle, vertical descent. Palette tint shifts to low-opacity translucent white/gray).
   - Constriction: Radial boundary restriction instantly dissolves; full map navigation restores.
   - Environmental damage hazard: `OFF`.
   - Respites: Enter a 10-second `Rebooting` state.

4. **State: Clear_Night_Extended (The Breather)**
   - Rain particle generator: `OFF` (Particles fade out smoothly over 3 seconds).
   - Environmental damage hazard: `OFF`.
   - Respites: `ACTIVE` (Fully operational before the next run cycle/chapter).

### Survival Mechanics & Rules
- **Omnipresence:** The rain ignores all physical boundaries (roofs, caves, etc.).
- **Safe Zone:** A circular region that shrinks continuously during Act II.
- **Optimized Damage:** Hazard calculations use distance-based circle math against player coordinates, scaled by `dt`.
- **Separation of Concerns:** Rain particles are purely visual; storm hazard is a separate logical calculation.

### Zone Override Rules
1. **ZONE_SANCTUARY (Hub / Scriptorium)**
   - `Rain_Capable = False`, Timer: `PAUSED`, State: `Clear_Day`.
2. **ZONE_DUNGEON (Randomized Run Chapters)**
   - `Rain_Capable = True`, Timer: `ACTIVE`, Fully managed by state machine.
3. **ZONE_FINAL_ARENA (The Author's Study)**
   - `Rain_Capable = False`, Timer: `PAUSED`, State: `Clear_Day` (during combat).

### Boss Arena & Victory Overrides
- **Boss Entry:** Freeze timer, `Rain_Particles = OFF`, `Environmental_Damage = OFF`.
- **Boss Defeat (Win):** 5-second `The_Dilution` event, then proceed to next stage/Sanctuary.
- **Boss Defeat (Loss):** 2-second `The_Bleed` event (Max density), then Game Over/Sanctuary.

## 5. Physics & Collision Architecture

### Collision Order of Operations
To ensure consistency and prevent jitter:
1. **Apply Velocity:** `temp_pos = pos + vel * dt`
2. **Wall Collision:** Resolve AABB intersections with static grid.
3. **Boundary Clamp:** Force `temp_pos` into screen bounds (`max(0, min(pos, BOUND))`).
4. **Finalize:** `pos = temp_pos`

### Physics Rules
- **AABB (Axis-Aligned Bounding Box):** Standard rectangle-to-rectangle intersection for walls.
- **Circle Collision:** Distance-based math for circular safe zones.
- **Normalization:** Movement vectors must be normalized to ensure consistent diagonal speed.

### 5.3 Combat Logic & Hitbox Rules
To maintain predictable combat, hitboxes are calculated relative to the player's center and cardinal facing direction:
- **Horizontal Attack:** Hitbox is $60 \times 20$ pixels, offset by 30 pixels from the player center.
- **Vertical Attack:** Hitbox is $20 \times 60$ pixels, offset by 30 pixels from the player center.
- **Resolution:** Damage is applied to all enemies overlapping the sword hitbox during the `ATTACKING` state.

## 6. Player Death Animation Loop (The Bleach Phase)
Upon Player Entity health reaching exactly 0, execute this sequence (min 5s):
1. **Step 1: Entity Desaturation (Instant):** Freeze all velocity, apply monochrome filter.
2. **Step 2: The Dimming Stasis (3s):** Slowly blit black overlay with increasing alpha.
3. **Step 3: Total Fade & Clean-Up (2s):** Max black opacity, wipe session buffers, transition to Sanctuary.

## 7. System Architecture: Escape Pause Menu
To prevent immediate hard-quits, the engine intercepts `pygame.K_ESCAPE` to toggle `game_paused`.
- **Interception:** Freezes delta-time, kinematics, and particle managers.
- **Options:** "Resume Reading" (Unfreeze), "Quit" (Return to Title).
- **Context:** Background remains visible but dimmed (60% alpha). "Abandon Chapter" is hidden in `ZONE_SANCTUARY`.

## 8. Environmental Entity & Interaction Architecture
All interactive elements are instantiations of a base `GameObject` with structural trait flags:
- `is_solid`: Blocks kinematics.
- `is_breakable`: Listens to damage vectors (links to `LootManager`).
- `is_interactive`: Listens to player input triggers.
- `is_kinematic`: Modifies passenger velocity (platforms).

### Interaction Architecture: The Unified Interaction Filter
To prevent input conflicts, the engine routes actions through a **Contextual Interceptor Matrix**:
1. **Trigger Boundary:** Interactables have a bounding box larger than their collision rect.
2. **Input Suppression:** If `player.current_interactable` is set, `ATTACK` key executes interaction; otherwise, it executes combat.

## 9. Map Design & Topography: The Macro-Grid Topology

To facilitate a sustained 10-minute exploration experience before the environmental shift triggers, maps utilize a **Modular Component Matrix** instead of standalone rooms.

### The Modular Component Matrix
Map generation mirrors a **Lotus Seed Pod**:
- **The Global Map Dimensions:** A massive macro-layout (minimum $120 \times 120$ tiles).
- **The Core Framework (Tissue):** The immutable, solid frame of the structure (safe walkways/navigation pathways, marked as `M` or `#`).
- **The Volatile Modular Holes (Cells):** Distinct $20 \times 20$ tile open "cavities" embedded into the frame (marked as `.` for combat/exploration).
- **The Void (`X`):** Impassable outer boundary.

### Phase 1 Testing Constraint
To ensure stability during initial prototyping, the engine initializes the world by generating a macro-map where **all modular holes are populated with exact copies of the established `chapter1` exhibition grid layout**. This allows for testing combat, prop destruction, and hazard navigation multiple times across different sectors of the same massive run.

### Grid-Cell Mapping
Levels are decoded from a 2D Matrix String Grid:
- `#` : Wall, `.` : Floor, `W` : Warp, `R` : Respite, `T` : Tree, `B` : Barrel.

## 10. Dialogue System Architecture: The Blackboard Protocol
Dialogue engine is decoupled from active state via a **Blackboard State & Query Model**.
- **The Global Blackboard:** A flat, persistent dictionary tracking historical milestones (e.g., `has_item_iron_key`, `boss_night1_encountered`).

## 11. System Architecture: The Wellspring Interface (Stats & Bestiary)
Lifetime metrics are managed by a decoupled serialization process.
- **The Persistence Matrix:** `profile_metrics.json` records lifetime stats (`runs_started`, `wins`, `deaths`) and discovered bestiary. Independent of active level memory.

## 12. Input Architecture: Controller & Joystick Abstraction
Translates raw hardware events into a unified, normalized `InputAction` schema.
- **Analog Deadzone:** Software deadzone of `0.15`.
- **Normalized Vector:** Clamps analog stick magnitude to `1.0`.
- **Fallback:** Seamlessly falls back to keyboard if gamepad is disconnected.

## 13. Design Principles

### The Rule of Low-Coupling Isolation
1. **Identify Isolation:** Pick ONE feature that can be fully built without incomplete dependencies.
2. **Design Invariance:** Prioritize independent data schemas.
3. **Test-Driven Mandate:** Write logic alongside tests; do not proceed until tests pass.
4. **Zero Feature Creep:** Implement exactly to spec; no placeholders for unbuilt features.

## Save File Architecture: Linux XDG Compliance Protocol

To prevent save data from vaporizing between runtime sessions and to respect system standards, all user save layers, timeline statistics, and profiles must resolve to standard local filesystem paths.

### 1. Directory Resolution Hierarchy
The save engine must compute the absolute directory path using Python’s built-in `pathlib.Path` framework by checking environment variables in this exact order:

1. **Primary Target State:** Check for the environment string `XDG_STATE_HOME`. If present, use `Path(os.environ["XDG_STATE_HOME"]) / "avoid_rain"`.
2. **Standard Fallback State:** If `XDG_STATE_HOME` is absent or null, resolve explicitly to `Path.home() / ".local" / "state" / "avoid_rain"`.

### 2. Initialization Constraint
Before attempting a write operation on `profile_metrics.json`, the data wrapper must explicitly verify directory presence using:
`save_dir.mkdir(parents=True, exist_ok=True)`
This eliminates filesystem write failures if the app subfolder does not exist yet.

## Save File Architecture: Active Session Suspension (True Continue)

To allow seamless run suspension, the `profile_metrics.json` file must support a decoupled state snapshot that differentiates lifetime stats from volatile runtime properties.

### 1. Unified JSON Save Schema
The JSON document structure must explicitly track whether a run is currently suspended in progress:

```json
{
  "lifetime_stats": {
    "runs_started": 12,
    "wins_chapters_cleared": 2
  },
  "active_session": {
    "in_progress": true,
    "current_zone": "chapter1",
    "player_health": 45,
    "player_max_health": 100,
    "player_position": [144, 288],
    "torn_pages_collected": 3
  }
}

## UI Rendering Architecture: Dialog Scaling & Entity Primitives

To handle both narrative character dialogue and expansive dataset ledger presentation, the rendering engine must support scalable user-interface viewports.

### 1. The Context-Aware UI Matrix
- **Standard Dialog Window:** A lower-third horizontal banner (approx. 25-30% screen height) reserved exclusively for active NPC banter (e.g., The Chronicler).
- **Expanded Manuscript overlay:** A centralized, large modal window (occupying approx. 70-80% of total screen dimensions) featuring a parchment or high-contrast background mask. This mode is explicitly triggered by architectural data-log systems (e.g., The Wellspring Fountain Ledger, The Chronicle Profile Screen) to present dense multiline metrics without string clipping.

## 15. Advanced Entity Architecture: Multi-Tile & Elite Entities

To support diverse map topography and challenging combat encounters, the engine supports entities larger than the standard 1x1 tile grid.

### 1. Multi-Tile Static Props
- **Vertical Occupancy:** Certain symbols in the `LevelLoader` (e.g., `S` for Benches) instantiate `GameObject` instances with a 1x2 footprint (`TILE_SIZE` x `TILE_SIZE * 2`).
- **Collision:** Solid multi-tile props are treated as a single unified AABB for collision resolution.

### 2. Elite Entities: The Miniboss
- **Dimensions:** Minibosses occupy a 2x2 tile area (`TILE_SIZE * 2` x `TILE_SIZE * 2`).
- **Detection & Pursuit:** Minibosses feature an expanded detection radius (default 12 tiles) and use a standardized pursuit vector to track the player.
- **Combat Stats:** Higher health pools and increased contact damage compared to standard enemies.
- **Loot:** Guaranteed Tier 2 drops upon defeat.

### 2. Procedural Animation Constraints (The Wellspring Surface)
- Non-image placeholder structures must utilize frame-relative math or time-based sine vectors to simulate life.
- **The Water Primitive:** A bounding block mapped to the Wellspring position that dynamically alternates rendering layers of primary cyan/blue color bars offset by moving horizontal highlight strokes to mimic continuous liquid currents.

## Prototyping Infrastructure: Core Sandbox Exhibition Rule

To guarantee immediate visual feedback and prevent asset regression during core development, all testing map matrices must comply with the Exhibition Floor Protocol.

### 1. Mandatory Asset Distribution
Every prototype map layer (e.g., `chapter1_start` or active combat testing maps) must intentionally allocate space for at least one active instance of every implemented engine element.
- **Indoor Environments:** Must contain an immediate distribution of Benches (`S`), Rocks (`K`), and Breakable Barrels (`B`).
- **Outdoor Environments:** Must include Static Trees (`T`) alongside standard terrain blockades.
- **Threat Verification:** Must spawn a minimum of one unit per active enemy variant (e.g., standard training target AND the newly added `BatEnemy`) within 5 horizontal tiles of the player spawn coordinates.

## Entity Architecture: Multi-Tile Footprints & Boss Spatial Rules

To accommodate advanced environmental clutter and impactful elite combat encounters, the engine must support composite multi-tile entity parsing.

### 1. Structural Component Dimensions
- **Standard Props (Barrels, Rocks):** Retain a $1 \times 1$ single-tile grid footprint.
- **Benches (`S`):** Span a $1 \times 2$ structural footprint (1 tile wide, 2 tiles tall vertically). The parser must look ahead or allocate bound blocks to prevent overlapping asset artifacts.

### 2. Elite Class Boundaries (Miniboss)
- **The Ink-Stained Miniboss:** Occupies a strict $2 \times 2$ multi-tile tile boundary footprint.
- **Kinematics & Tracking:** Movement code must evaluate collision boundaries relative to a scaled bounding box, ensuring the unit cannot squeeze through narrow $1 \times 1$ hallway corridors.

## 16. Enemy Reset & Lifecycle Persistence
To ensure runs are consistent, enemy states must be managed via a clean re-population strategy:
- **Map Entry:** All enemies are instantiated fresh from map symbols (`Z`, `A`). 
- **Persistence:** Enemies do not track health across map warps. Entering a room always resets enemies to their full HP and starting positions.
- **Cleanup:** Dead enemies must be purged from the active state list immediately to prevent phantom collisions.

## 17. Rendering Standards: Primitive Visibility
During early development phases where primitive shapes (rects, lines) are used instead of sprites:
- **Contrast:** Colors must be selected from the `constants.py` palette to ensure visibility against the `COLOR_FLOOR` backdrop.
- **Layering:** All active entities (Player, Enemies, Props) must be drawn *after* the tile grid to prevent occlusion.
- **Bat Indicators:** Fast-moving enemies like Bats must include wing indicators (lines) to maintain visibility during high-speed movement.

## Level Layout Topography: The Radiant Lotus Wheel Protocol

To prevent architectural monotony and eradicate dead-end traversal traps, the macro-grid generator must transition from a rectangular matrix to a radial, ring-and-spoke structural model.

### 1. The Radial Geometric Layout
The macro-world map ($120 \times 120$ tiles) is generated using explicit geometric distance tracking relative to the true map center `(60, 60)`:
- **The Central Well (Radius 0 to 15):** A vast, circular open plaza (`.`). This serves as the safe entry threshold and the ultimate battleground where the closing weather system finishes its collapse.
- **The Tissue Framework (The Spokes):** Distinct, multi-tile wide avenues that radiate outward at specific angular intervals (e.g., $0^\circ, 60^\circ, 120^\circ, 180^\circ, 240^\circ, 300^\circ$).
- **The Outer Rim Ring (Radius 50 to 55):** A continuous circular pathway running along the perimeter of the map. Every radial spoke links directly into this ring, guaranteeing a closed topological loop with zero dead ends.
- **The Vault Cells:** The $20 \times 20$ modular modular content zones are nested in the negative spaces trapped between the radiating spokes.

## Physics Architecture: Entity Overlap & Repulsion Mechanics

To prevent overlapping graphic clipping and maintain combat readability, active mobile entities (Player and Enemies) must execute dynamic repulsion checks.

### 1. The Soft-Body Repulsion Formula
When a moving threat's bounding box (`enemy.rect`) intersects the player's bounding box (`player.rect`), the physics loop must calculate a separation vector:
- **Direction:** Compute the angle or directional sign vector pointing from the center of the player to the center of the enemy.
- **Displacement:** Apply a minor fractional velocity pushback to the enemy's coordinates along that vector to instantly slide them out of the player's interior space.
- This ensures enemies remain visible, targetable, and positioned at a readable melee engagement distance.

## UI Architecture: Input Mapping & Menu Sub-States

To accommodate growing input configurations (Keyboard and future Gamepad support) without causing text layout crowding, the interface engine must process controls through a dedicated sub-state modal.

### 1. Tabbed Input Presentation
- The Controls Overlay must occupy a large, centralized screen space using the expanded UI overlay specifications.
- **State Partitioning:** The overlay manages an internal state variable: `controls_tab` (default: `"KEYBOARD"`).
- **Future-Proofing Layouts:** 
  - `"KEYBOARD"` mode displays a vertical two-column table aligning mapped actions with their respective key constants.
  - `"GAMEPAD"` mode is reserved to render a visual controller mapping template, entirely isolated from the keyboard layout metrics.
- Pressing `Left` / `Right` arrow keys or a mouse-click event on localized header text buttons toggles the `controls_tab` value.
