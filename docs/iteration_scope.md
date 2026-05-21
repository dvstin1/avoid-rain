# First Iteration Scope: The Sanctuary Foundation

The goal of Phase 1 is to establish the core engine loop and the Hub World (Sanctuary) as a playable sandbox.

## Deliverables
1. **Title Screen:** Simple menu with a "Start Game" option that fades to black.
2. **The Sanctuary:** A static room representing the Hub World.
3. **Player Controller:**
    - WASD movement with normalization.
    - dt-scaled physics.
    - IDLE and MOVING states.
4. **Training Dummy:**
    - A static entity in the Sanctuary.
    - Displays damage numbers when "hit" (simulated for Phase 1).
5. **Constants System:** A `constants.py` file managing window size, colors, and speeds.

## Technical Goals
- **Unit Test:** `tests/test_player.py` verifying position math.
- **Linting:** Initial `main.py` and `engine/` files pass `pylint`.
- **Decoupling:** `rendering/` draws the `engine/` state without logic leakage.
