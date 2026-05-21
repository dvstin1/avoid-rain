Statistics integration (engine/stats.py & engine/game_state.py)

Purpose:
Provide a low-coupled StatisticsTracker for lifetime metrics (profile_metrics.json) and integrate it into GameState so runs are recorded and can be persisted.

Why it exists:
Keeps persistence logic isolated (engine/stats.py) and allows GameState to increment and save metrics without importing filesystem details across the codebase.

Notes:
- GameState accepts an injected StatisticsTracker or auto-loads one (opt-out available).
- Use GameState.save_stats() to persist the tracker.
