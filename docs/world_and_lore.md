# World & Lore: The Boundless Archive

This document establishes the narrative framework, geographical classifications, and environmental mechanics of the *Libram of Rain*.

## 1. Narrative Framework
The game world exists within the iron-bound covers of a mysterious, shifting tome known as **The Libram**.
- **The Reader:** The player is projected into the ink-and-parchment reality written inside the book.
- **The Author:** The entity holding the quill at the end of the manuscript. The hazardous rain is liquid ink leaking from their pen, intended to erase "errant characters" (the player).
- **The Menagerie:** Creatures composed of stolen text and malicious prose. Killing them is like removing a typo; they drop "Torn Pages" (Unbound Syntax).
- **The Chronicle:** A personification of the book's original purpose, grieving for the scar tissue where characters are violently ripped from the pages.

## 2. Geographical Classifications
The world is a massive manuscript page divided into the stable **Tissue** (frame) and the unstable **Cells** (modular holes).

### 2.1. The Distorted Regions
- **The Bleached Forest:** Timber grown from calcified parchment; the canopy behaves like a massive blotting sheet.
- **The Sunken Pond:** A mirror of liquid carbon fed by runoff from abandoned drafts. Items dissolve into raw syntax here.
- **The Forgotten Ruins:** Structural pillars made of compressed ledger volumes. The halls loop non-linearly, like an author rewriting the same tragic paragraph.
- **The Deserted Outpost:** Fortifications guarding the margins, overlooking an absolute void of unrendered white space.
- **The Constellation Void:** Patterns of absence on the reverse side of the page, visible only when held up to the Wellspring's light.
- **The Market of Margins:** A sliver of commerce in the folds between chapters where footnote-spirits trade in discarded annotations.

## 3. Environmental Mechanics

### 3.1. Respites ("The First Edition")
Ancient anchor fragments of the original, uncorrupted manuscript.
- **Function:** Serves as a baseline alignment tool. Heals the player, refills Flask charges, processes stat upgrades (leveling), and sets checkpoint data.
- **The Rain Inversion:** High-volume ink saturation ("The Bleed") smothers the energetic frequency, deactivating the Respite until the climate is cleared.
- **Visuals:** Features an elevated pedestal with a glowing glyph (Open Lectern silhouette).

### 3.2. The Wellspring (The Fountain)
A pressure valve connected to the "Unwritten Page"—the untainted source of the universe.
- **Atmospheric Contrast:** Emits clear water, the antithesis to toxic ink rain.
- **The Reflection:** The basin acts as a memory matrix, projecting historical logs (statistics) and encountered shapes (Bestiary).

### 3.3. The Devouring Storm Cycle
- **Act I (Clear Day):** 10 minutes of exploration. Ambient background particles. Respites are ACTIVE.
- **Act II (The Bleed):** Corrosive ink-storm. Safe zone shrinks toward center over 3-5 minutes. Respites are DEACTIVATED.
- ** Act III (The Dilution):** Post-boss victory. Toxic ink dilutes into mundane water, flushing the landscape.

## 4. Systems & Equipment Lore

### 4.1. The Twin Cradle (Weapon System)
Readers sustain exactly two weapons (The Draft and The Revision).
- **The Full-Cradle Rule:** When both slots are full, defeating a Miniboss forces the manuscript to generate an **Anomalous Weapon** (e.g., INK_BLEED, VOID_STRIKE).

### 4.2. Item Loot & Rewards
All drops route through a central `LootManager` probability matrix:
- **Tier 4:** Barrels/Chests (Minor instants).
- **Tier 3:** Minor Enemies (Currency packets).
- **Tier 2:** Mini-Bosses (Currency bundles or stat upgrades).
- **Tier 1:** Night Censors/Final Boss (The Choice of Fates: high-value hybrid stat cards).

### 4.3. Player Eradication (Death)
Reaching 0 HP triggers "Text Bleaching." The character and surrounding assets turn monochrome as they are drained of data, eventually fading into the oblivion of a rejected draft.
- **Abandoning a Run:** Defined as "Slamming the Libram Shut," leaving a systemic scar on the timeline.

## 5. Scriptural Progression: Edification & Respite Mechanics

### The Concept of Edification
Edification represents a traveler's deep textual comprehension of the distorted manuscript layers. It scales directly via the conversion of recovered loose pages. As a reader's Edification rises, they gain passive defensive parsing capabilities:
- **Pristine Concentration (Above 95% HP):** When entering a fight with total clarity, the player receives slightly increased defense, mitigating initial ambush impacts.
- **Desperate Synthesis (Under 30% HP):** When focus is critically depleted, survival instincts sharpen, scaling up defense parameters to prevent a total session collapse.

### The Fresh View Cycle (World Respawns)
Interacting with an unlocked Respite forces a structural reset across the active module sector. Much like closing a profound book and reopening it later to find lines you completely overlooked, resting grants a "fresh view." The architecture settles, standard ink entities (common enemies) re-manifest along the margins, but the heavily redacted passages (defeated Miniboss strains) remain permanently expunged.

### The Strict Economy of Review
Edification cannot be accumulated casually or incrementally while standing in a zone of safety. A reader must completely clear their mind and open the manuscript anew to process deeper meaning. Therefore, a Level Up sequence can only be performed immediately following a fresh complete world reset (Resting) within the current interaction. Once a point of edification is gained, the connection to the First Edition becomes unstable, requiring the player to commit to another Rest cycle to unblock further progression. To progress, you must accept the burden of an altered world—re-invoking the very common threats you previously cleared.

### Redaction In perpetuity (Miniboss Permanence)
Minibosses represent corrupted, highly unique critical passages within the world's text. Because they drop powerful anomalous equipment variants and premium page bundles, their defeat represents a permanent, irreversible redaction of that threat from the active run. They cannot be re-summoned or farmed, preventing any artificial duplication of the world's highest-tier rewards.

### The Closed Volume Paradox (Sanctuary Reset Law)
Edification is not an inherent trait carved into the traveler's soul; it is a temporary state of deep, active cognitive resonance with a *specific manuscript*. 

When a traveler falls in battle or uses the Chronicle gateway to return to the Sanctuary hub, that specific volume is closed. The text is either safely restored to the archival shelves or fragmented and lost to the shifting ink. Because a reader cannot maintain an active comprehension of a closed book, their Edification level instantly collapses back to **Level 1**. 

Every journey through the gateway requires picking up an entirely fresh, unread ledger from the archive. And no matter how learned a scholar is, every new book must always be read starting from **Page One**.
