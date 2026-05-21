Future Save Recovery Ideas (Not in This Phase)

Purpose

Collect improvements for save/load robustness that are planned for a later phase. These items are intentionally NOT implemented in the current Phase 1 (Sanctuary Foundation).

Planned improvements

- In-game interactive restore dialog: present a modal with on-screen "Yes (Start New)" and "No (Abort)" buttons, not keyboard-only Y/N. Keep PauseMenu and GameState decoupled; the dialog calls GameState.handle_corrupt_choice.

- Present backup path and "Restore from backup" option: show the location of the corrupt backup (profile_metrics.json.corrupt.TIMESTAMP) and allow the player to attempt restoring from it.

- Attempt automated repair: attempt JSON heuristics or schema-based repair; only offered as an "Attempt Repair" button. Always preserve the original corrupt file by moving it to a .corrupt.* backup.

- Save worker / queue: replace fire-and-forget daemon saves with a single dedicated worker thread and a bounded queue to serialize saves, avoid thread explosion, and provide controlled shutdown.

- Non-blocking save with progress/state: if save payload grows, make writes asynchronous and provide a non-blocking progress indicator; consider writing large sections incrementally.

- Telemetry & logging: log timestamped save failures and backup paths to a rotating log file to aid diagnosis.

- User-visible recovery flow in Title/Loading screens: surface the corrupt-save incident in the loading UI with clear choices and filesystem backup path.

Why deferred

These features increase UI and concurrency complexity and are out-of-scope for Phase 1's low-coupled implementation mandate. They are marked as future work and should be planned for Phase 2 or a dedicated maintenance iteration.

References

- engine/stats.py: CorruptSaveError and backup behavior
- engine/game_state.py: handle_corrupt_choice API
- docs/autosave.md and docs/statistics_integration.md

Status: Planned (Not in this Phase)
