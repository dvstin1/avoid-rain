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

## 3. Discrete Input (Actions/Combat)
- **Mechanism:** Event Buffering.
- **Keys:** Spacebar (Attack), Shift (Dash), E (Interact).
- **Behavior:**
    - The `rendering/` layer listens for `pygame.KEYDOWN` events.
    - **Single Trigger:** Each `KEYDOWN` event generates exactly ONE action (e.g., `AttackAction`).
    - **Non-Repeatable:** Holding the Spacebar will NOT trigger subsequent attacks. The player must release and press again to start a new attack sequence.
    - **State Lock:** The `engine/` will ignore new `AttackActions` if the player's current state is already `ATTACKING`.

## 4. Input Translation Map (Initial)
| Key | Input Type | Game Action |
|-----|------------|-------------|
| W, A, S, D | Polled | Move(dir) |
| SPACE | Event | StartAttack |
| L_SHIFT | Event | StartDash |
| K_k | Event | Block(toggle or hold) |
| K_1, K_2 | Event | UseItem |
| ESCAPE | Event | OpenMenu / EndRun |
