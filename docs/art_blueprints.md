# Art Blueprints

## SVG Asset Generation & Token Budget Protocol

1. **Banned Mass-Generation:** The agent must NEVER auto-generate multiple SVG blocks in a single response, even if a phase checklist implies multiple assets are missing.
2. **The Asset Registry Checklist:** All project assets must be indexed in a markdown table tracking their path, state, and approval token.
3. **Strict Single-File Request Lock:** The agent is only permitted to output exactly ONE raw XML SVG code block per user query. It must wait for explicit user confirmation (e.g., "Generate Asset #4") before rendering the next one.

## SVG Vector Template Protocol
- When asked to generate visual templates for player sprites, enemy blocks, tile grids, or weapon animations, the agent must output standard, raw SVG code inside an `xml` code fence block.
- SVGs must use explicit `viewBox` coordinates matching our targeted game pixel boundaries (e.g., `viewBox="0 0 32 32"`).
- Use `shape-rendering="crispEdges"` inside the root `<svg>` tag to preserve clean, un-blurred pixel borders for easy tracing with the Wacom tablet in Krita.
- When generating an SVG template, keep the XML lightweight. Use simple <rect>, <circle>, or basic <path> elements with flat hex colors. Do not include individual pixel-by-pixel blocks, complex gradients, or shading. The SVG is strictly a geometric layout guide for my tablet tracing.

## Master Art Style Guide
To maintain structural cohesion across all SVG and Krita assets, the engine enforces these stylistic rules:
- **Aesthetic:** Dark, high-contrast, moody 1-bit or limited-palette pixel art.
- **Perspective:** Top-down orthographic (flat 2D view, no simulated 3D angles or isometric skewing).
- **Primary Color Palette:**
  - Backgrounds/Walls: Deep slate grays, charcoal, and ink blacks.
  - Interactive/Hazards: Highly vibrant, neon-adjacent colors (e.g., toxic cyan/lime green for acid rain).
  - Characters/Player: High-contrast bright whites or deep blues to pop against dark backgrounds.

## Asset Manifest Specification Rule
When generating or updating the list of needed assets, the agent must NEVER output a simple name string. Every asset entry in the registry must follow this explicit schema:

- **ID & Filename:** (e.g., `#03 - tile_wall_brick.svg`)
- **Dimensions:** (e.g., `32x32 pixels`)
- **Composition & Layout:** A detailed sentence describing the exact geometric arrangement, dominant shapes, and layout rules for the SVG vector paths.
- **Focal Point:** Where the user's eye or tablet brush should focus (e.g., "centered horizontally," "aligned to the bottom 4 pixels").
- **Contrast Rule:** Explicitly state how this asset visually separates itself from adjacent game elements.
