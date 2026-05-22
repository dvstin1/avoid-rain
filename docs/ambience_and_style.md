# Ambience and Style Specification

## Overview
This document defines the visual and atmospheric standards for *Avoid Rain*, specifically focusing on the "Scriptorium Noir" aesthetic.

## The Scriptorium Noir Aesthetic
- **The Mood:** Oppressive, academic, eerie, and melancholic, balanced by the safe, warm, candle-lit sanctuary of the Hub.
- **Color Palette:**
  - **Sanctuary Hub:** Warm sepia, soft amber, and aged parchment tones.
  - **Combat Zones:** Stark charcoal, deep ink blues, and cold greys.
  - **Highlights:** Glowing cyan (The Chronicle), soft amber (Candlelight/Respite).

## Atmospheric Props
These props are used to populate the world and reinforce the narrative theme of an ancient, corrupted library.

### 1. Heavy Bookcase (`h`)
- **Visuals:** A solid primitive rectangle.
- **Color:** Dark charcoal grey.
- **Size:** 2x1 tiles (Horizontal).
- **Physics:** Solid (Impassable).
- **Description:** Immense shelves filled with leaden, unreadable tomes.

### 2. Ink-Drip Urn (`d`)
- **Visuals:** A solid primitive square.
- **Color:** Deep slate blue.
- **Size:** 1x1 tile.
- **Physics:** Solid (Impassable).
- **Description:** Ceramic vessels overflowing with viscous, stagnant ink.

### 3. Spilled Inkwell Puddle (`v`)
- **Visuals:** Irregular circular primitive.
- **Color:** Deep ink blue/black.
- **Size:** 1x1 tile.
- **Physics:** Hazard (50% speed reduction when inside).
- **Description:** A slick, treacherous patch of spilled manuscript ink.

### 4. Iron Candelabra (`l`)
- **Visuals:** Thin vertical stand with a flickering amber glow.
- **Color:** Dark charcoal grey stand, amber flame.
- **Size:** 1x1 tile.
- **Physics:** Solid (Impassable).
- **Description:** A heavy iron stand holding a single, defiant candle.

## Lighting and Effects
- **Background Clear Color:**
  - **ZONE_SANCTUARY:** Warm, low-contrast dark sepia/amber.
  - **Combat Zones:** Cold, stark dark charcoal.
- **Flicker Primitives:** Safe zones (Respite points, Sanctuary) must use radiating circles of soft amber, simulating candlelight.
