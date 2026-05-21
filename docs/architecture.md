# Application Architecture & Lifecycle

This document outlines the high-level execution flow and the main entry point's structural requirements.

## main.py Structural Skeleton
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

## Key Lifecycle Rules
- **Resource Management:** All Pygame surfaces and sound channels must be initialized within the `main()` scope or managed by a dedicated loader that is called within the `try` block.
- **Error Handling:** The `finally` block is mandatory to ensure the terminal state of the Debian environment remains clean.
- **FPS Capping:** The loop must be capped (defaulting to 60 FPS) to prevent excessive CPU usage, while still providing `dt` for frame-rate independence.

## Technical Specification: Rain Lifecycle & State Machine

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

## Climate Engine: Zone Override Rules

To prevent global timer bugs, the game engine must evaluate the current scene's `Zone_Type` before executing the Rain State Machine:

1. **ZONE_SANCTUARY (Hub / Scriptorium)**
   - `Rain_Capable = False`
   - Day/Night Timer: `PAUSED` at 0.
   - Climate State: Forced `Clear_Day` permanently.

2. **ZONE_DUNGEON (Randomized Run Chapters)**
   - `Rain_Capable = True`
   - Day/Night Timer: `ACTIVE`.
   - Climate State: Fully managed by the 4-stage Lifecycle State Machine.

3. **ZONE_FINAL_ARENA (The Author's Study)**
   - `Rain_Capable = False`
   - Day/Night Timer: `PAUSED` at maximum threshold.
   - Climate State: Forced `Clear_Day` (Dry/No Particles) during active combat state.
   - **Victory Trigger:** Upon Author Entity health reaching 0, force-trigger a localized 5-second `The_Dilution` visual particle storm across the entire viewport display before initiating the transition sequence back to `ZONE_SANCTUARY`.

## Climate Engine: Boss Arena & Victory Overrides

The game engine must seamlessly pause and override standard timed rain behaviors based on active Boss Entity life cycles across all `Rain_Capable` zones:

1. **Boss Arena Entry Trigger:**
   - When a Boss Entity initializes (Night 1, Night 2, or Final Boss), force-set `Rain_Particles = OFF` and `Environmental_Damage = OFF`.
   - Freeze the global day/night countdown timer. The arena remains a dry, quiet "Eye of the Storm" for the duration of the battle.

2. **Boss Defeat Handler (Player Wins):**
   - Upon Boss Entity health dropping to exactly 0, instantly trigger a 5-second localized climate event.
   - Set `Rain_Particles = ON` (Gentle vertical vector, low-opacity translucent white/gray "Clear Rain" tint).
   - Set `Environmental_Damage = OFF`. 
   - *Next Step:* If Night 1, resume normal timer exploration. If Night 2, spawn the Appendix Portal. If Final Boss, trigger credit roll and save state before routing back to Sanctuary.

3. **Player Defeat Handler (Player Loses):**
   - Upon Player Entity health dropping to exactly 0 inside a boss arena, instantly trigger an intense 2-second climate event before resetting.
   - Set `Rain_Particles = ON` (Maximum density, hyper-saturated sharp diagonal "Bleed" tint).
   - Set `Environmental_Damage = ON` (Visual indicator of total text erasure).
   - *Next Step:* Execute Game Over state, wipe run temporary buffers, and force-reload scene back to `ZONE_SANCTUARY`.

## Technical Specification: Player Death Animation Loop (The Bleach Phase)

Upon Player Entity health reaching exactly 0, the engine must immediately suspend the standard game loop and execute this 3-step sequence over a minimum of 5 seconds before triggering a scene transition:

1. **Step 1: Entity Desaturation (Instant)**
   - Suspend all active velocity vectors and physics calculations (freeze character, enemy, and boss positions mid-frame).
   - Apply a monochrome surface filter across the viewport, converting all active RGB color values for sprites and background elements into a grayscale spectrum.

2. **Step 2: The Dimming Stasis (Duration: 3 Seconds)**
   - Keep the scene locked in a static, grayscale state.
   - Begin slowly blitting a full-screen black overlay surface with an accumulating alpha channel value to gradually darken the display viewport.

3. **Step 3: Total Fade & Clean-Up (Duration: 2 Seconds)**
   - Accelerate the black overlay alpha to maximum opacity (total black screen).
   - Safely wipe the current level's procedurally generated map arrays and enemy instantiation tables from memory buffers.
   - Route the engine state machine directly to the standard loading screen to initialize `ZONE_SANCTUARY` for a clean run reset.

## System Architecture: Escape Pause Menu & Game Termination Flow

To prevent immediate hard-quits and safely process run statistics, the engine's main event polling loop must intercept the `pygame.K_ESCAPE` keypress to drive a dedicated, modal pause overlay menu state.

### 1. The Interception State Machine
When the engine is running in `ZONE_DUNGEON` or `ZONE_FINAL_ARENA`:
- Pressing **ESCAPE** must NOT terminate the process. It must toggle a boolean flag `game_paused = True`.
- When `game_paused == True`, the engine must temporarily freeze all active update loops (delta-time accumulation, character/enemy kinematics, particle managers, and project timer clocks). It continues to run *only* the UI event polling loop and the background renderer.

### 2. The Menu Layout & Selection Vector
The Pause Menu must present a vertical stack of exactly three clear, interactive text options:

*   **Option 1: Resume Reading**
    - Action: Sets `game_paused = False`. Instantly unfreezes all game vectors and returns the player to active combat/exploration mid-frame.
*   **Option 2: Abandon Chapter (Quit-Out)**
    - Action: This option is ONLY visible or active if the player is currently inside an active run (`ZONE_DUNGEON`). 
    - Critical Trigger: Instantly increments the `"forced_quit_outs"` metric inside `profile_metrics.json`, flushes the temporary run buffers, resets player health, sets `game_paused = False`, and force-reloads the scene back to `ZONE_SANCTUARY`.
*   **Option 3: Close the Libram (Terminate Game)**
    - Action: Safely writes any pending data updates to `profile_metrics.json` to ensure file integrity, calls `pygame.quit()`, and executes a clean `sys.exit()` system termination.

### 3. Rendering Constraints for the Agent
- **Visual Context Preservation:** When the menu is active, the background game world must remain visible beneath the menu options but must be heavily dimmed using a semi-transparent black overlay surface (e.g., 60% alpha opacity).
- **Sanctuary Exception:** If the player presses ESCAPE while already inside the safe hub (`ZONE_SANCTUARY`), the "Abandon Chapter" option must be automatically hidden or disabled, presenting only "Resume" and "Close the Libram".

## Environmental Entity & Interaction Architecture

To prevent class sprawl and maintain optimal decoupling inside the level generation layers, all physical props, breakables, doors, mechanisms, and moving platforms must derive from a unified, component-flagged data structure.

### 1. The Unified GameObject Schema
Rather than creating separate inheritance trees for every world object, all interactive elements are instantiations of a base `GameObject` configured via structural trait properties:

```python
class GameObject(pygame.sprite.Sprite):
    def __init__(self, position, dimensions, sprite_primitive):
        super().__init__()
        self.image = sprite_primitive
        self.rect = pygame.Rect(position, dimensions)
        
        # Core Architectural Trait Flags
        self.is_solid = True         # Blocks player/enemy kinematics
        self.is_breakable = False     # Listens to damage vectors; links to LootManager
        self.is_interactive = False   # Listens to player input triggers
        self.is_kinematic = False     # Modifies passenger velocity vectors (platforms)
```
