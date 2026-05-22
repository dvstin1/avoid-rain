# World Lore & Structure

## The Hub World
The "Sanctuary" is a safe space outside of the rain cycle, accessible only between runs.
- **Environment:** A blend of indoor structures and outdoor island areas, surrounded by a lethal ocean.
- **Lethal Water:** Falling into the ocean results in instant death. However, as it is outside a run, the player respawns within the Sanctuary with **no loss of Torn Pages**.
- **The Chronicler (NPC):** A friendly NPC who provides greetings and basic lore/guidance. They are immortal and cannot be harmed.
- **Training Room:** Contains indestructible dummies for testing weapons, combos, and movement.
- **The Chronicle:** A mysterious book that the player reads to begin a new run.

## Story Flags & NPC Events
Interaction with friendly NPCs can trigger events that persist or affect the current run.
- **Random Events:** Every run has a chance to spawn specific NPC scenarios in modular sections.
- **Quest Rewards:** Completing a task for an NPC (e.g., retrieving an item, clearing a sub-zone) can:
    - Permanently increase player power.
    - Provide "intel" or items that weaken a specific Boss.
    - Unlock new vendor inventory in the Hub.

## The Shifting World
The game world is a massive island map composed of modular sections.
- **Environment:** Sections can be outdoor (beaches, fields) or indoor (caves, ruins).
- **Dynamic Sections:** Randomly swap between variants each run.
- **Vendors:** NPCs found in the world selling upgrades or consumables.
- **Mini-Bosses:** Each modular section contains an optional mini-boss with useful rewards.

## Respites
Scattered across the map are "Respite" spots—ancient, consistent structures that offer safety.
- **Functions:**
    - **Healing:** Instantly restores the player to full health and refills the Flask charges.
    - **Progression:** The primary location to spend Torn Pages on stat upgrades (Health, Defense, Attack).
    - **Checkpoint:** Sets the player's respawn point.
- **The Rain Constraint:** Respites are **disabled** once they are consumed by the rain. No healing or leveling can occur within the storm.
- **Visuals:** While the aesthetic of a Respite may change to match its biome (e.g., stone in caves, wooden in forests), they always share a consistent, recognizable silhouette or glowing sigil.

## Enemy Hierarchy
1. **Easy:** Low HP, low damage, slow movement.
2. **Normal:** Standard stats; the baseline for exploration.
3. **Mini-Boss:** High HP/Defense, specialized mechanics, optional.
4. **Boss:** Maximum stats, lethal patterns, mandatory for progression.

## The Devouring Storm Cycle
The climate of the world actively dictates the pace of gameplay, splitting a standard run into two distinct strategic acts:

- **Act I: The Exploration Window (0:00 to 10:00):** The player spawns onto the solid framework and explores the modular chambers. The weather is visually represented as ambient, rhythmic background particle drops.
- **Act II: The Closing Collapse (10:00 Onward):** At the 10-minute mark, the weather shifts into a massive, corrosive ink-storm. The safe zone begins closing inward toward a randomized central map coordinate over a **3 to 5-minute window**. 
- **The Hazard Boundary:** Any player outside the active radius takes progressive, rapid damage over time (`take_damage(2)` per second).
- **The Climax:** Once the circle reaches its minimum threshold, the Final Boss is instantiated at the center point, triggering the ultimate survival event.

## The Narrative
The player is a wanderer in a world that is literally dissolving. The "Rain" isn't just water; it's a supernatural force of erasure—a manifestation of corrupted ink originating from "The Author." Because it is a fundamental breakdown of reality, it ignores all physical boundaries—roofs, caves, and thick walls offer no protection once the rain arrives. To stop the cycle, the source must be defeated in their own domain.

## Project World Lore & Narrative Schemas
- **The Setting:** The Scriptorium (Hub) acts as the anchor point. A safe sandbox zone.
- **The Gateway:** Activating the central Libram object initializes the randomized map matrix engine.
- **The Core Threat:** The environmental "Acid Rain" is a manifestation of corrupted ink originating from the final chapter boss ("The Author").
- **Economy Schema:** Enemies drop "Torn Pages" (Unbound Syntax). These are unreadable data strings traded to the "Binder" NPC to increment player core attributes.
- **Co-op Metaphor:** Local LAN connectivity (future) functions as a "Shared Reading" event, synchronizing two client positions within the host's active chapter draft.

## Environmental Mechanic: Respites ("The First Edition")
- **Narrative Origin:** Unalterable anchor fragments of the game world's original, uncorrupted master manuscript.
- **Function Schema:** Serves as a baseline alignment tool. Synchronizes player continuity data (respawn anchor), processes syntax currency (leveling via Torn Pages), and flushes character anomalies (healing).
- **The Rain Inversion:** High-volume ink saturation ("The Bleed") temporarily smothers the anchor's energetic frequency, completely deactivating all safety protocols until the local climate is cleared.
- **Visual Silhouette Rule:** Must always feature an elevated, geometric pedestal base tapering upward to support a central, high-contrast glowing glyph (e.g., a stylized "Alpha" or "Bookmark" shape). 
- **Deactivated Visual State:** Glyph light shuts off; asset uses a cascading downward dark particle sprite to simulate liquid ink pooling over the structure.

## The Post-Censor Climate Transition ("The Dilution")
- **The Event:** Defeating a Night Censor instantly severs the Author's corrupting frequency.
- **Narrative Logic:** The remaining airborne ink loses its toxic acidity, instantly diluting into mundane, non-hazardous water. This pure rain acts as a systemic flush, washing away the pooled "Bleed" stains from the landscape before evaporating entirely into a Clear Sky state.
- **Environmental Cue:** Represents a brief era of narrative stability where the "First Edition" physics temporarily reclaim the page.

## Environmental Stability Zones: Sanctuary & Final Arena

- **The Sanctuary (The Scriptorium):** Narratively defined as the "Binding and Outer Covers." Because it exists completely structural-adjacent to the text, it is inherently immune to the Ink Bleed timeline. The climate engine is permanently locked to a dry state.
- **The Final Arena (The Appendix/Inkwell):** The spatial source where the Author edits reality. It exists physically above the manuscript layers, meaning the localized climate is completely dry and static during combat operations.
- **The Author's Collapse (The Clear Wash):** Slaying the final boss triggers an immediate, full-screen downpour of hyper-pure Clear Rain. This represents the total dilution and cleansing of the master manuscript, purging all hostile syntax blocks simultaneously before saving the game state and returning the player profile to the Sanctuary.

## Boss Arena Climate Dynamics ("The Eye of the Storm")

- **The Combat Phase (The Draw):** While engaging a Night Censor or The Author, ambient environmental rain completely ceases. The boss entity acts as a gravitational sink, pulling all airborne ink into its active core to manifest its combat form.
- **The Victory Resolution (The Clear Wash):** Slaying any boss causes its compressed text mass to destabilize. The malicious frequency is shattered, causing the gathered ink to instantly dilute and explode outward as a celebratory, harmless torrent of Clear Rain across the viewport.
- **The Defeat Resolution (The Bleed Submersion):** Player death instantly collapses the local stabilization field. The unsuspended ink mass falls simultaneously, immediately triggering an absolute "Bleed" flash-flood that strikes out the player's text profile and triggers a full state reset.

## Player Eradication & The Bleaching State
- **Narrative Logic:** Reaching 0 health initiates a localized "Text Bleaching" event. Because color signifies living intent within the Libram, the sudden shift to absolute monochrome indicates that the character profile and surrounding text assets are being completely drained of their vital data.
- **The Stasis:** The 5-second monochrome freeze represents the narrative hardening into a discarded, unreadable draft—the animation loop halts as the ink permanently dries.
- **The Oblivion (Fade to Black):** The final fade symbolizes the physical closure of the current chapter. The manuscript page is rejected, blacked out, and reset by the system architecture.

## Character Lore: The Chronicler
- **Identity:** The living personification of "The Chronicle" master manuscript. An immortal entity bound to the foundational text of the Scriptorium.
- **Narrative Purpose:** Acts as the safe anchor for the player. They are completely immune to environmental damage and cannot be deleted from the system profile.
- **Emotional Resonance:** Their psychological state mirrors the internal health of the book's pages. A successful run purges their text, resulting in highly positive, warm interactions. A failed run stains their consciousness with corrupt ink residues, causing them to retreat into a distant, trauma-induced silence.

## Environmental Hub Asset: The Wellspring (The Fountain)
- **Narrative Origin:** A localized pressure valve routing pure energy directly from the "Unwritten Page"—the pristine state of reality before the Author's corruption.
- **The Atmospheric Contrast:** Emits completely clear, constant-flowing water, serving as a direct physical and visual antithesis to the toxic, heavy "Bleed" rain experienced during active runs.
- **The Phenomenon of Reflection:** The basin operates as a temporal memory matrix. Peering into the liquid mirror translates the water's memories into legible data, projecting a historical log of the Reader's timeline metrics (statistics) and the architectural shapes of encountered hostile syntax blocks (the Bestiary).

## Narrative Meta-Mechanic: The Torn Closure (Abandoning a Run)
- **The Act:** Forcing a quit-out via the pause menu is narratively defined as the Reader "Slamming the Libram Shut" mid-sentence.
- **The Consequence:** Because the Reader violently severs their connection to the page before a natural resolution (Victory or Censor Defeat), the active draft collapses chaotically. The character entity is violently pulled back into the Scriptorium. This systemic shock leaves a scar on the timeline, which is permanently logged by the Wellspring fountain as a "Forced Quit-Out."

## The Lore: The Lotus Manuscript (Macro-Grid Topology)

- **The Topology:** Within the pages of the Libram, reality follows typography. The master map structure—the **Modular Component Matrix**—is known as the Lotus Page.

- **The Framework vs. The Draft:** The solid frame (the "Tissue") represents the immutable, preserved margins of the world. The **Modular Holes** (the "Cells") are literal blank windows in the text where localized, unstable stories are drafted. When you warp into a run, your consciousness lands safely on the firm, unyielding frame of the manuscript. You then choose which open chamber to step down into, braving the randomized, shifting combat zones below.
