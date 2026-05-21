# Input Handling Specification

To maintain the **Decoupled Design** constraint, input must be translated from raw Pygame events into logical "Action" objects before the `engine/` processes them.

## 1. Input Architecture
- **Rendering/Input Layer:** Captures `pygame.event` and `pygame.key.get_pressed()`.
- **Translator:** Maps physical keys to `GameActions` (e.g., `K_w` -> `MoveAction(0, -1)`).
- **Engine Layer:** Receives the list of actions and updates the `GameState`.

## 2. Continuous Input (Movement)
- **Mechanism:** State Polling.
- **Keys:** WASD.
- **Behavior:**
    - The `rendering/` layer polls the keyboard state every frame using `pygame.key.get_pressed()`.
    - It generates a movement vector based on which keys are held down.
    - This vector is passed to the engine as a `ContinuousMoveAction(x, y)`.
    - **Fluidity:** Because it's polled every frame, movement starts and stops instantly with key presses, scaled by `dt`.

## 3. Discrete & Charged Input (Actions/Combat)
- **Mechanism:** Hybrid Event/Polling.
- **Keys:** Spacebar (Attack), Shift (Dash), E (Interact).
- **Behavior:**
    - **Initial Trigger:** `pygame.KEYDOWN` starts the action sequence.
    - **Charged Attack (Hold):** 
        - If the button is held, the `engine/` increments a `charge_timer`.
        - If released (`pygame.KEYUP`) after the minimum threshold, a **Charged Attack** is executed.
        - If released before the threshold, a **Standard Attack** is executed.
    - **Non-Repeatable:** Holding the button after an attack completes will NOT trigger a new attack; the key must be released and pressed again.
    - **State Lock:** The `engine/` will ignore new input actions if the player's current state is already `ATTACKING` or `CHARGING`.

## 4. Input Translation Map (Initial)
| Key | Input Type | Game Action |
|-----|------------|-------------|
| W, A, S, D | Polled | Move(dir) |
| SPACE | Event | StartAttack |
| L_SHIFT | Event | StartDash |
| K_k | Event | Block(toggle or hold) |
| K_1, K_2 | Event | UseItem |
| ESCAPE | Event | OpenMenu / EndRun |

## Controller & Joystick Abstraction Support

### 1. Unified Input Action Schema
The input manager module must translate raw hardware events (whether keyboard or joystick) into a unified, normalized data structure before passing it to the game state:
- `move_direction`: A `pygame.math.Vector2` representing the raw direction. Values must range from `-1.0` to `1.0`.
- `action_attack`: A single Boolean flag (`True`/`False`) indicating a single, non-repeating attack request.

### 2. Gamepad / Joystick Mapping Rules
When a joystick device is initialized (`pygame.joystick.get_count() > 0`), the controller subsystem must enforce the following technical criteria:
- **Analog Deadzone Threshold:** Apply a software deadzone of `0.15`. Any axis value with an absolute value less than `0.15` must be truncated to exactly `0.0` to eliminate joystick drift.
- **Normalized Vector Length:** Because analog sticks allow circular movement, diagonal input values could theoretically exceed normal bounds. The resultant movement vector must be clamped using `vector.scale_to_length(1.0)` if its magnitude exceeds `1.0`.
- **Button Debouncing:** The attack flag must listen for the specific button-down event (typically Button `0` or `1` depending on Linux controller layout) to prevent continuous holding from spamming the sword attack state.

### 3. Fallback Priority
- If a gamepad is disconnected or unavailable, the input abstraction system must seamlessly fall back to monitoring the keyboard `WASD` / `Spacebar` states without throwing runtime exceptions or halting the game loop.
