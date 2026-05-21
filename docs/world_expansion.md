World expansion & island perimeter (engine/world.py & constants.py)

Purpose:
Make the playable world larger than the visible screen by adding extra tiles (WORLD_EXTRA_TILES_X/Y) and create a centered island perimeter (inner wall) to separate an inner sanctuary from outside.

Why it exists:
Allow simple multi-screen maps without changing rendering or player movement systems. The player is clamped to world bounds; the renderer and camera handle view scrolling.

Notes:
- Constants control the extra tile counts; avoid hardcoding values elsewhere.
- Island includes a doorway left open for access; adjust in World._init_sanctuary_walls if needed.
