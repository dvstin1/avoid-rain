AutosaveManager (engine/autosave.py)

Purpose:
Run periodic, non-fatal automatic saves of player metrics (StatisticsTracker) by calling GameState.save_stats(). Maintains a small timer on GameState (last_save_elapsed) to allow UI feedback.

Why it exists:
Ensure important player metrics are persisted automatically (pause, quit, or regular interval) and to avoid accidental loss without exposing manual save UI.

Safety:
- Save failures are caught and ignored to avoid interrupting gameplay.
- Interval and indicator duration are configurable in constants.py.
