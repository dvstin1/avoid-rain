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

## 4. Climate Engine: Rain Lifecycle & State Machine

The climate engine must operate on a strict 4-stage state machine synchronized with the day/night timer:

1. **State: Clear_Day**
   - Rain particle generator: `OFF`.
   - Environmental damage hazard: `OFF`.
   - Respites: `ACTIVE`.

2. **State: The_Bleed (Night Cycle Peak)**
   - Rain particle generator: `ON` (High density, sharp diagonal vectors, custom cyan/lime palette tint).
   - Constriction: Map boundary collapses inward via a radial clamping vector toward a designated Boss Arena circle.
   - Environmental damage hazard: `ON` (Applies a continuous tick damage modifier to the player if standing outside a Respite boundary before deactivation).
   - Respites: `DEACTIVATED`.

3. **State: The_Dilution (Immediate Post-Boss Victory)**
   - Rain particle generator: `ON` (Maintains current particle count but transitions velocity to a gentle, vertical descent. Change palette tint to low-opacity translucent white/gray).
   - Constriction: Radial boundary restriction instantly dissolves; full map navigation restores.
   - Environmental damage hazard: `OFF` (Rain drops no longer decrement player health).
   - Respites: Enter a 10-second `Rebooting` state (Glyph flashes slowly, rain animation overlays disappear).

4. **State: Clear_Night_Extended (The Breather)**
   - Rain particle generator: `OFF` (Particles fade out smoothly via alpha-channel reduction over 3 seconds).
   - Environmental damage hazard: `OFF`.
   - Respites: `ACTIVE` (Fully operational for leveling and healing before the countdown to Night 2 begins).

### Survival Mechanics & Rules
- **Omnipresence:** The rain ignores all physical boundaries. It penetrates roofs, caves, and all indoor structures.
- **Safe Zone:** A circular region that shrinks over time.
- **Optimized Damage:** Hazard calculations use tile-grid coordinates or distance-based circle math, scaled by `dt`.
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

## 9. Map Design & Topography

### Grid-Cell Mapping
Levels are decoded from a 2D Matrix String Grid:
- `#` : Wall, `.` : Floor, `W` : Warp, `R` : Respite, `T` : Tree, `B` : Barrel.

### The Lotus Page Protocol
Map generation mirrors a **Lotus Seed Pod**:
- **The Solid Frame (Tissue):** Safe navigation pathways (`M`).
- **The Chambers (Cells):** Modular combat/exploration holes (`.`).
- **The Void (`X`):** Impassable outer boundary.

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
