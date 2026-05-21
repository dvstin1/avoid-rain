# Combat & Gameplay Mechanics

## Movement
- **WASD Control:** Standard 8-directional movement.
- **Delta Time (dt):** All movement and physics must be scaled by `dt` to ensure frame rate independence.

## Combat
- **Swinging Sword:** A state-driven attack system with startup, active, and recovery frames.
- **Directional Hitboxes:** Hitboxes project in the direction of the player's last movement or aim.
- **Enemy Dummy:** Static or simple AI entities used to verify hit detection and damage application.

## The Rain (Survival Mechanic)
- **Safe Zone:** A circular region that shrinks over time on Day 1 and Day 2, forcing players inward.
- **Rain Damage:** Players outside the safe zone take periodic damage.
- **End-of-Day Boss:** Once the circle reaches its minimum size, a mandatory Boss fight begins.
    - **Survival:** You must defeat the boss or survive the encounter to progress. Dying here ends the run.
    - **Cycle:** Defeating the Day 1 boss clears the rain for Day 2. Defeating the Day 2 boss opens the final portal.

## Difficulty Scaling
Enemies are tiered by stats and behavior:
- **Stats:** Higher-tier enemies have increased Health, Damage, and Defense.
- **Behavior:** Difficult enemies may have superior movement speed, complex attack patterns, or higher aggression.

## Progression & Persistence
- **Respawning:** If you die during normal exploration, you respawn, but the run continues.
- **Persistence:** Enemies killed during exploration remain dead after you respawn.
- **Portal:** Appears only after the Day 2 boss is defeated, transporting the player to the final arena.
