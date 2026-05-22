# Roadmap
## Development Roadmap Priority Rules
- **Phase 1 (Current): Core Gameplay Loop.** Focus exclusively on the hostile game world mechanics (vector physics, procedural tile generation mapping, grid-based enemy AI tracking, and damage collision).
- **Phase 2 (Future): Hub & Narrative Polish.** Visual expansion of the safe zone, advanced NPC dialogue trees, and environment tiling sheets will remain locked until the core combat loop is verified and stable.

## Technical Specification: The Unified Interaction Filter

To prevent input conflicts (e.g., executing a combat swing while attempting a world interaction), the engine must route action inputs through a strict **Contextual Interceptor Matrix**.

### 1. Interaction Trigger Boundary
Warp Zones, NPCs, Chests, and Levers must possess an interaction bounding box larger than their physical collision rect. 
- When the Player bounding box overlaps this interaction zone, set `player.current_interactable = target_entity`.
- Draw a clean, localized text primitive overlay above the player's head (e.g., `"Press [ATTACK] to Read/Activate"`).
- When the player leaves the boundary, clear the tracking property back to `None` and remove the text overlay.

### 2. Input Suppression State Machine
When the player triggers the key bound to `ATTACK` (e.g., `pygame.K_SPACE` or a mouse click), the input handling script must execute this deterministic evaluation branch:

```python
# System Input Filter Constraint
if player.current_interactable is not None:
    # Bypasses combat entirely: triggers the object's code without spawning a hitbox
    player.current_interactable.execute_interaction(scene_context)
else:
    # Normal gameplay fallback
    player.execute_combat_swing()
