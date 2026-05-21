Pause autosave (engine/pause_menu.py & main.py)

Purpose:
Trigger an immediate autosave when the pause menu opens and before transitioning away from gameplay (e.g., quitting to title or exiting the app).

Why it exists:
Provide a reliable, UI-free save point whenever the player pauses or quits to minimize data loss; implemented as a lightweight callback (on_open) on PauseMenu so the pause system stays decoupled.

Notes:
- The pause menu calls the provided on_open callback but swallows exceptions so pause remains robust.
