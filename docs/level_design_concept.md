# Level design concepts

---

### Geometry, Flow, and Interconnection

Strong top-down level layouts rarely rely on simple rectilinear grids or dead-end mazes. Instead, they use distinct macro-shapes combined with looping paths to sustain momentum:

* **Macro-Shapes:**
* **The Figure-8 and Nested Loops:** Rather than branching dead-ends, levels branch into secondary loops that reconnect to a central artery. In a swamp or flooded biome, this looks like diverging wooden walkways or raised stone dams that wrap around deep water hazards before returning to the main trail.
* **Hourglass / Choke Nodes:** Wide exploration arenas funnel into narrow transition corridors. A wide open windy ridge collapses into a compressed bridge over an abyss, forcing a shift from evasive maneuvering to precision spacing.
* **Perimeter and Core:** A high perimeter path overlooking an inaccessible central courtyard or generator core. The player circles the exterior first to observe objectives and enemy densities before unlocking access to the lower floor.


* **Creating the Illusion of Verticality:**
* **Occlusion and Parallax Layering:** True verticality in a 2D or orthographic perspective relies on layering. Foreground canopies, crumbling overpass bridges, hanging vines, or suspended cybernetic conduits pass *over* the player and enemies.
* **Drop-Downs and One-Way Ledges:** Stepped cliffs or broken metal gantries where players can jump or fall down from level $Z+1$ to $Z$, but cannot walk back up without navigating around the loop. This converts explored space into shortcut routes.
* **Visible Lower/Upper Strata:** Rendering the ground plane of a lower tier (e.g., murky swamp water, glowing reactor trenches) beneath grated walkways or cliff edges. Combining this with vertical shadow casting—where high towers cast long, angled ambient occlusion shadows across lower platforms—immediately establishes elevation without 3D camera rotation.



---

### Enemy Density, Orientations, and Sightlines

Single-screen arcade challenges often flood the playfield with 15–30 uniform threats moving in synchronized waves. In scrolling, interconnected top-down action, density shifts toward intentional combat encounters:

* **Encounter Footprint:**
* **Transit/Traversing:** 2 to 4 low-threat or harassment enemies per screen-equivalent area to maintain tension without halting motion.
* **Combat Arenas/Chambers:** 5 to 10 active threats, sharply divided by role rather than sheer volume.


* **Directional Pressure:**
* **The 180-Degree Rule:** Avoid surrounding the player from 360 degrees upon entry unless it is an explicit, telegraph-heavy ambush arena. The most readable combat pushes from an arc of 120 to 180 degrees ahead, allowing the player to manage spacing and retreat lines.
* **Pincer Dynamics:** Top-tier layouts occasionally introduce a secondary flanker (1–2 units) appearing from a side path or 90-degree angle *after* the front wave engages, forcing lateral repositions without causing blind off-screen damage.


* **Enemy Role Synergy:**
* **Anchors/Disrupters:** Stationed centrally (e.g., a technomantic turret, a heavy armored golem, or a spore-spewing swamp fixture) to command territory.
* **Swarmers/Chasers:** Fast, low-health units that flush the player out of cover or push them toward environmental hazards.
* **Artillery/Snipers:** Positioned across impassable terrain—such as across a windy chasm or across deep water—forcing the player to dodge ranged fire while dealing with ground units.



---

### Entrances, Exits, and Micro-Pacing

Placement of portals, checkpoints, and transition points dictates how players build a mental map of your world:

* **Entrances with Visual Anchors (Weaning):**
* When stepping into a new screen or sub-area, the exit or the key landmark (a glowing spire, an elevator shaft, a massive gate) should be partially glimpsed immediately, even if the direct path to it is blocked. This gives directional purpose before tactical navigation begins.


* **The "Safe Threshold" Rule:**
* Never place aggressive aggro zones directly on an entrance boundary or room transition. Give the player a minimum of 1.5 to 2 player-widths of "neutral ground" where they can assess the room layout, read enemy types, and plan their initial vector of attack before triggering encounters.


* **Loop Closures and Shortcuts:**
* Entrances to deeper zones should often circle back to unlock a shortcut to an earlier resting point or hub (e.g., kicking down a ladder from a tower terrace to the base swamp, or disabling an energy barrier that opens a straight line back to the entrance).



---

### Biome-Specific Spatial Architecture

Integrating the sci-fi/fantasy hybrid theme into functional gameplay geometry:

* **Windy Ridge / Sky Tower Areas:**
* *Characteristics:* High negative space, sheer drops, linear gantries, and gusting wind lanes.
* *Gameplay Impact:* Narrow paths emphasize edge-knockback risks. Wind channels act as conveyor belts or speed modifiers, altering dash distances and projectile arcs. Safe pockets are formed behind ancient monoliths or reinforced bulkheads.


* **Swamp and Murky Water Areas:**
* *Characteristics:* Organic, non-linear islands surrounded by variable-depth liquid.
* *Gameplay Impact:* Water functions as dual-tier terrain: shallow areas slow player movement or disable certain dashes, while deep water acts as an impassable barrier for land units but allows submerged fantasy predators or hover-drones to bypass standard lanes.


* **Monolithic Tower / Tech-Citadel Areas:**
* *Characteristics:* Hard angular geometry, interlocking circular chambers, elevator cores, and energy conduits.
* *Gameplay Impact:* Vertical stacking illusion is strongest here. Spiral ramp designs, descending security barriers, moving platforms over bottomless power cores, and clean sightlines that contrast sharply with organic biomes.



---

### Balancing Surprise vs. Predictability

Great action design relies on **fair predictability in mechanics** paired with **novelty in enemy and terrain combinations**.

* **Environmental Foreshadowing (The "Tell"):**
* Surprise attacks should never be arbitrary. If a swamp beast is waiting to burst out of the water, mark the spot with subtle bubbling surface disturbances or broken floating debris. If an orbital laser or magical artillery strike is dialed into a bridge, mark the stone with scorch marks and charging runic ground decals.


* **Mechanical Predictability:**
* Enemy wind-ups, attack cones, projectile speeds, and terrain rules must remain strictly consistent. A player should always know what an enemy *can* do; the surprise should come from *where* and *in what combination* they do it.


* **Rhythm of Tension and Relief:**
* **High Tension (Compression):** Confined corridors, converging enemy lines, hazards active, high soundscape intensity.
* **Climax (Arena):** Multi-threat engagement with room to move and execute mastery.
* **Decompression (Reward/Orient):** Silent, open spaces with visual breadth, narrative props, supply caches, and clear vistas overlooking the path ahead. Never place two high-intensity arena fights directly adjacent without a decompression buffer.
