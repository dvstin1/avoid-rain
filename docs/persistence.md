# Persistence & Statistics Architecture

This document outlines the systems responsible for tracking lifetime metrics and managing automatic saves.

## 1. Statistics Integration (engine/stats.py)
The `StatisticsTracker` provides a low-coupled interface for recording player progress and lifetime metrics. It isolates filesystem operations from the core game logic.
- **Master Registry:** `profile_metrics.json` records cumulative stats (`runs_started`, `wins`, `deaths`) and the `discovered_bestiary`.
- **Injection Pattern:** `GameState` accepts an injected tracker or auto-loads the default profile on initialization.
- **Serialization:** Call `GameState.save_stats()` to sync the internal dictionary to disk.

## 2. Autosave Mechanics
The engine utilizes several triggers to ensure data integrity without interrupting flow.

### 2.1. Periodic Autosave (engine/autosave.py)
- **Purpose:** Runs non-fatal background saves at regular intervals.
- **UI Feedback:** Maintains a `last_save_elapsed` timer to drive the "Saved" indicator in the HUD.
- **Safety:** All save failures are caught and ignored to prevent gameplay stutter.

### 2.2. Contextual Triggers (engine/pause_menu.py)
- **Pause Autosave:** An immediate save is triggered whenever the `PauseMenu` is opened.
- **Session Suspension:** Before transitioning away from gameplay (Quitting to Title or Exiting), the system captures a full `run_state` snapshot.

## 3. Save Schema (profile_metrics.json)
The persistent JSON document differentiates between permanent lifetime metrics and volatile active session data.

```json
{
  "lifetime_stats": {
    "runs_started": 12,
    "wins_chapters_cleared": 2,
    "deaths": 10,
    "torn_pages_total": 450
  },
  "discovered_bestiary": {
    "SlugEnemy": true,
    "BatEnemy": true
  },
  "active_session": {
    "in_progress": true,
    "world_name": "chapter1",
    "player": {
        "x": 144, "y": 288, "hp": 45
    }
  },
  "last_run_result": "DEFEAT"
}
```

## 4. Future Save Recovery Ideas (Post-Phase 1)
Planned improvements for later development cycles:
- **Interactive Restore Dialog:** On-screen modal for handling corruption instead of keyboard-only prompts.
- **Backup Hierarchy:** Presenting the location of `.corrupt.TIMESTAMP` backups for manual or semi-automated recovery.
- **Save Worker Thread:** Utilizing a dedicated worker with a bounded queue to serialize heavy write operations.
- **Incremental Writes:** Splitting large save payloads into sections to reduce disk I/O spikes.
- **Telemetry Logs:** Timestamped failure logs to aid in remote troubleshooting.
