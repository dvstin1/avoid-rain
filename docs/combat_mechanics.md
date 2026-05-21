# Combat & Gameplay Mechanics

## Movement
- **WASD Control:** Standard 8-directional movement.
- **Delta Time (dt):** All movement and physics must be scaled by `dt` to ensure frame rate independence.

## Combat
- **Swinging Sword:** A state-driven attack system with startup, active, and recovery frames.
- **Directional Hitboxes:** Hitboxes project in the direction of the player's last movement or aim.
- **Enemy Dummy:** Static or simple AI entities used to verify hit detection and damage application.

## The Rain (Survival Mechanic)
- **Safe Zone:** A circular region that shrinks over time on Day 1, forcing players inward.
- **Rain Damage:** Players outside the safe zone take periodic damage.
- **Cycle:** The rain ceases on Day 2, allowing for final exploration/preparation before the boss portal appears.

## Progression
- **Portal:** Appears at the end of Day 2, transporting the player to a separate arena for the final boss encounter.
