# Asset Manifest

## Visual Effects (VFX) & UI
- **Damage Numbers:** Font/Sprite set for colored numbers (Red/Yellow).
- **Outlines:** Logic/Assets for 100ms stagger outlines.
- **Transitions:** Solid black surface for "Fade to Black" effects.
- **Screens:**
    - Title Screen background/logo.
    - Loading Screen (placeholder for map generation).

## Sprites & Animations
- **Player:**
    - 4-directional walk cycles.
    - Attack animations: Sword swings, Spear thrusts.
    - Evasion: Rolling/Dashing frames.
    - Blocking: Shield-up stance.
- **NPCs:**
    - Vendors: Specialized shopkeeper sprites.
    - Quest Givers: Unique NPCs for story events.
- **Enemies:** Basic grunt/dummy sprites, Final Boss (large-scale 2D sprite).
- **Environment:**
    - Hub World: Training room assets, "The Book" (run initializer).
    - Respites: Consistent core silhouette/sigil with biome-specific variations.
    - Tile-based floor and wall sets.
    - Portal animation/sprite.

## Items & UI
- **Consumables:** Food icons (bread, fruit, etc.), Potion icons.
- **The Flask:** Main healing vessel sprite (upgradable visuals).
- **Currency:** "Torn Page" sprite (floating paper fragment with glow).
- **Gear:** Shield sprites, Spear sprites, Sword variants.
- **User Interface (UI):**
    - Health/Stamina/Defense bars.
    - Flask Tracker: Counter for charges and upgrade level (e.g., +1).
    - Torn Page counter.
    - Level-up menu (spend pages on Atk/Def/HP).
    - Inventory grid.
    - Interaction prompts for NPCs, items, and Respites.

## Prototyping Graphics Rule
For Phase 1 and 2, do not load external image files.
All newly implemented entities must register their primitive shape, dimensions, and hex color codes here during the prototyping phase to facilitate seamless structural asset injection during later art passes.
Represent all entities using colored `pygame.Surface` primitives:
- Player = 32x32 pixel Blue Square
- Wall Tile = 32x32 pixel Dark Gray Square
- Floor Tile = 32x32 pixel Light Gray Square
- Sword Hitbox = Red translucent rectangle
- Acid Rain = Draw random thin cyan lines (`pygame.draw.line`) descending over the viewport
