# Equipment and Lore: The Twin Cradle

In the *Libram of Rain*, a Reader's power is balanced by their ability to maintain "The Cradle"—a conceptual mental space for holding the weight of written artifacts.

## 1. The Two-Slot Weapon System
Every Reader can sustain exactly two weapons within their Cradle. This duality represents the balance between the **Draft** (immediate action) and the **Revision** (strategic alternative).

### Mechanics:
- **Active Slot:** Only the active weapon contributes its damage and effects to the player's attack action.
- **Weapon Swap:** Switching between the two slots takes zero time but cannot be performed during an active attack animation.
- **Acquisition:** 
    - Walking over a weapon and interacting with it will add it to an empty slot.
    - If both slots are full, picking up a new weapon will discard the currently active one onto the ground.

## 2. The Full-Cradle Rule (Anomalous Manifestation)
The world responds to a prepared Reader. When both weapon slots are occupied (The Full Cradle), the energetic frequency of the Reader stabilizes. 

### Miniboss Interaction:
Minibosses are manifestations of intense, corrupted focus. Under normal conditions, they drop standard remnants. However, when they are defeated by a Reader who has achieved the Full Cradle, the resulting feedback loop forces the manuscript to generate an **Anomalous Weapon**.

- **Standard Drop:** A basic weapon without modifiers.
- **Anomalous Drop:** A weapon imbued with a random dictionary of effects (e.g., `{"effect": "INK_BLEED", "damage_bonus": 5}`). These anomalies represent "glitches" in the corrupted text that favor the Reader.

## 3. Lore of the Anomalies
- **INK_BLEED:** The weapon leaves a trail of corrosive ink on the target, dealing damage over time.
- **VOID_STRIKE:** Attacks have a chance to briefly delete the enemy's collision, allowing the player to pass through them.
- **CHRONICLE_ECHO:** Every third hit creates a shadow-swing that mimics the previous attack.

## 3. The Sanctuary Purge & Resource Reset Lifecycle
The Sanctuary Hub operates as an immutable reality anchor. Stepping through a warp gate back into the Hub instantly triggers a complete inventory and health flush:
- **Weapon Stripping:** The player's weapon list is completely cleared and reset to a single, baseline `Common` tier starter weapon. Slot B is completely emptied.
- **Vitals Restoration:** Player health is fully replenished to maximum capacity.
- **Heal Reservoir:** The player's active healing flask counter is refilled to its standard baseline starting capacity.

## 4. Elite Enemy Strains (The Devoured Authors)
To fully stress-test the weapon drop matrix and the Full-Cradle Rule, the engine maintains three distinct Miniboss variants:
1. `Ink-Stained Miniboss` (M1): Heavy pursuit vector, drops blunt-force sweeping weapons.
2. `Bleeding Scribe` (M2): Fast erratic vector, drops sharp piercing or bleeding rapier variants.
3. `The Forgotten Binder` (M3): Teleporting or area-denial vector, drops wide-range anomalous cleavers.
