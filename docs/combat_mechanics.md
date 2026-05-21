# Combat & Gameplay Mechanics

## Player Actions
- **WASD Control:** Standard 8-directional movement.
- **Evasion:** Dash or roll move for quick repositioning and temporary invulnerability.
- **Blocking:** If a shield is equipped, the player can block incoming attacks.
    - **Penalty:** Movement speed is significantly reduced while blocking.
- **Delta Time (dt):** All movement and physics must be scaled by `dt`.

## Weapon Types
- **Swords:** Balanced speed and range. Circular/Arc hitboxes.
- **Spears:** Slower attack speed but significantly longer and narrower hitboxes. Ideal for keeping enemies at a distance.

## Items & Consumables
- **Consumables:** Items like food that can regenerate health or provide temporary stat buffs (e.g., increased defense).
- **Upgrades:** Materials or services from vendors to improve weapon stats (damage, speed, reach).
- **Inventory:** System to manage equipped weapons, shields, and consumables.

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
