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
    - **High Stakes:** Dying during a Day 1, Day 2, or Final Boss encounter is an immediate **Game Over** (run ends).
    - **Cycle:** Defeating the Day 1 boss clears the rain for Day 2. Defeating the Day 2 boss opens the final portal.

## Difficulty Scaling
Enemies are tiered by stats and behavior:
- **Stats:** Higher-tier enemies have increased Health, Damage, and Defense.
- **Behavior:** Difficult enemies may have superior movement speed, complex attack patterns, or higher aggression.

## Torn Pages (Currency & Progression)
- **Collection:** Defeated enemies drop "Torn Pages." Harder enemies (Mini-Bosses, Bosses) drop significantly more.
- **Leveling:** Pages are spent at Respite spots to upgrade Health, Defense, and Attack Power.
- **Death & Retrieval:**
    - Upon death, all currently held Torn Pages are dropped at the location of death.
    - The player can retrieve them by returning to that spot.
    - If the player dies again before retrieving the pages, the original pile is lost forever.

## Progression & Persistence
- **Respawning:** If you die during exploration, you respawn at the last visited Respite.
- **Ending a Run:** The Hub World is only accessible after a run ends (Victory, Game Over, or manual "End Run" from the menu).
- **No Resumption:** Once a run is exited or ended, that specific run state is lost; a new run must be started from the Hub.
- **Persistence:** Enemies killed remain dead *within the current run*, but Torn Pages must be retrieved after a normal death.
- **Portal:** Appears only after the Day 2 boss is defeated.
