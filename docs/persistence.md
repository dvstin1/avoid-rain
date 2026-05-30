# Persistence & Statistics Architecture

This document outlines the systems responsible for tracking lifetime metrics and managing automatic saves.

## 1. Statistics Integration (engine/stats.py)
The `StatisticsTracker` provides a low-coupled interface for recording player progress and lifetime metrics. It isolates filesystem operations from the core game logic.
- **Master Registry:** `save_data.json` records cumulative stats (`runs_started`, `wins`, `deaths`) and the `discovered_bestiary`.
- **Injection Pattern:** `GameState` accepts an injected tracker or auto-loads the default profile on initialization.
- **Serialization:** Call `GameState.save_stats()` to sync the internal dictionary to disk.

## 2. Autosave Mechanics
The engine utilizes several triggers to ensure data integrity without interrupting flow.

### 2.1. Periodic Autosave (engine/autosave.py)
- **Purpose:** Runs non-fatal background saves at regular intervals.
- **UI Feedback:** Maintains a `last_save_elapsed` timer to drive the "Saved" indicator in the HUD.
- **Safety:** All save failures are caught and ignored to prevent gameplay stutter.

### 2.2. Contextual Triggers (engine/game_state.py)
- **Pause Autosave:** An immediate save is triggered whenever the `PauseMenu` is opened.
- **Session Suspension:** Before transitioning away from gameplay (Quitting to Title or Exiting), the system captures a full `run_state` snapshot.

## 3. Save Schema (save_data.json)
The persistent JSON document differentiates between permanent lifetime metrics and volatile active session data.

```json
{
  "lifetime_stats": {
    "runs_started": 12,
    "wins_chapters_cleared": 2,
    "deaths": 10,
    "pages_collected": 0
  },
  "discovered_bestiary": {
    "SlugEnemy": true,
    "BatEnemy": true
  },
  "active_session_in_progress": true,
  "run_state": {
    "world_name": "macro_generated",
    "player": {
        "x": 144, "y": 288, "hp": 45
    },
    "weather": {
        "bleed_state": "SHRINKING",
        "active_safe_radius": 12000
    }
  },
  "last_run_result": "DEFEAT"
}
```

## 4. Save Reliability Features
Key implementations for data safety:
- **Save Worker Thread (IMPLEMENTED):** Utilizing a dedicated worker thread with a bounded queue to serialize heavy write operations without blocking the main game loop.
- **Atomic Operations:** Uses temporary files and `os.replace` to prevent data corruption during unexpected power loss.
- **Directory Isolation:** Stores data in `~/.config/avoid_rain/` to ensure user permissions and system cleanup protocols are respected.
