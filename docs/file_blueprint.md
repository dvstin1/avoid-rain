# File Directory Blueprint

To maintain the **Decoupled Design** constraint, the project will follow this structure:

```text
avoid_rain/
├── main.py                # Entry point: initializes Pygame and the main loop.
├── constants.py           # Central registry for all configuration and "magic numbers".
├── tests/                 # Pytest suite for engine logic.
│   ├── test_player.py
│   └── test_physics.py
├── engine/                # PURE LOGIC: No pygame imports allowed here.
│   ├── game_state.py      # The master State object.
│   ├── player.py          # Player movement, stats, and state machine.
│   ├── physics.py         # Collision math (AABB) and dt scaling.
│   ├── combat.py          # Hitbox logic and damage calculation.
│   └── world.py           # Rain circle math and modular section logic.
└── rendering/             # PYGAME CODE: Handles all drawing and input mapping.
    ├── renderer.py        # Main drawing coordinator.
    ├── camera.py          # Handles screen offsets and following the player.
    └── assets.py          # Sprite loading and animation management.
```

## Import Rule
- `engine/` files must never import `pygame`.
- `rendering/` files can import `engine/` to read state, but not the other way around.
