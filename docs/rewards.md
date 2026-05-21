## Item Loot & Reward Tier Protocols

To prevent item drop logic from clustering inside enemy death frames or breakable object interaction scripts, the engine must use a decoupled **Weighted Probability Matrix** and a structured **Stat Bundle Generator**.

### 1. The 4-Tier Loot Table Structure
All drop-capable entities must route their death/destruction events through a central `LootManager`. Drops are determined by evaluating a floating-point probability check against these explicit tiers:

| Tier | Source Entity | Drop Chance | Reward Structural Rules |
| :--- | :--- | :--- | :--- |
| **Tier 4 (Lowest)** | Barrels / Basic Chests | 100% (Chest) / 15% (Barrel) | Minor Instants: Tiny currency value (`torn_pages: 1-3`) or single-point health restoration. |
| **Tier 3** | Standard Minor Enemies | 5% Chance | Standard Loot: Flat currency packet (`torn_pages: 5-10`). No direct stat buffs. |
| **Tier 2 (Mid)** | Room Mini-Bosses | 100% Guaranteed | Major Consolidation: Massive currency bundle OR a single flat stat upgrade selection. |
| **Tier 1 (Highest)** | Night Censors / Final Boss | 100% Guaranteed | **The Choice of Fates:** Forces a UI pause state presenting two mutually exclusive, high-value hybrid stat cards. |

### 2. Tier 1 Dual-Choice Card Architecture (Stat Bundles)
When a Tier 1 reward is triggered, the engine must generate exactly two choices using a **Biased Polar Distribution Formula**. The options must always contrast high-offense against high-defense:

*   **Card Option A (The Quill - Offensive Bias):**
    - Major Modifier: $+X$ Attack Damage (Scaled to current level).
    - Minor Modifier: $+Y$ Max Health ($Y$ must be calculated as roughly 20-30% of $X$'s power weight).
*   **Card Option B (The Binding - Defensive Bias):**
    - Major Modifier: $+X$ Max Health (Scaled to current level).
    - Minor Modifier: $+Y$ Attack Damage ($Y$ must be calculated as roughly 20-30% of $X$'s power weight).

### 3. Engineering Constraints for the Agent
- **Data-Driven Drops:** Do NOT hardcode item instantiations inside `enemy.py` or `prop.py`. For now, these classes should call the LootManager API (e.g., `LootManager.roll()` or `roll_one()`) to obtain drop results. A tiered API like `LootManager.roll_drop(source_tier, position)` is planned in the roadmap and will be implemented later to support explicit source tiers and position-aware spawning.
- **UI State Locking:** Presenting a Tier 1 Choice Card must invoke a dedicated Pygame UI overlay layout block that completely pauses the underlying game loop timers, physics calculations, and particle engines. The game resumes only when an input choice coordinates are registered.
- **Stat Immutable Ledger:** All chosen modifications must be applied directly to a flat dictionary on the Player profile (e.g., `player.stats["attack_modifier"]`), ensuring the combat script reads from a clean, single source of truth when running damage calculations.
