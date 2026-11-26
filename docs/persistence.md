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
  "engine_revision": 2,
  "player_name": "Scholar",
  "online_mode": true,
  "debug_text_enabled": false,
  "screen_shake_enabled": true,
  "rumble_enabled": true,
  "keybindings": {
    "move_up": 119,
    "move_down": 115,
    "move_left": 97,
    "move_right": 100,
    "attack": 32,
    "block": 107,
    "dash": 1073742049,
    "flask": 49,
    "swap": 113,
    "inspect": 9,
    "respite_rest": 114
  },
  "last_run_result": "INIT",
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
  "margin_scraps": 8,
  "binder_scripts": {
    "unlocked": ["hemming_minor", "hemming_major"],
    "equipped": ["hemming_minor", "hemming_major"],
    "failed_sequence": ["max_hp"],
    "conflicts_triggered": 1
  },
  "story_flags": {
    "perfect_stitch_completed": false,
    "ink_bleed_halted": false
  },
  "active_session_in_progress": true,
  "run_state": {
    "world_name": "generated_world",
    "current_act": 1,
    "empowered_act": false,
    "run_biomes": {
      "act1": "windy_ridge",
      "act2": "pastoral_valley",
      "act3": "swamp_mire",
      "act4": "frozen_peaks",
      "act5": "tech_tower"
    },
    "act_worlds": {
      "1": {},
      "2": {},
      "3": {},
      "4": {},
      "5": {}
    },
    "player": {
        "x": 144, "y": 288, "hp": 45
    },
    "weather": {
        "bleed_state": "SHRINKING",
        "active_safe_radius": 12000,
        "paused": false,
        "rain_dps": 2.0
    }
  }
}
```

### 3.1. Binder Scripts & Persistent Meta-Progression Fields
- **`margin_scraps` (`int`):** Persistent Sanctuary currency earned from Night Bosses (`+1` in Acts 1–2, `+2` in Acts 3–5), Marginalia event completions (`+0`), and *The Final Author* (`+3`). Unlike active-run Torn Pages (`lifetime_stats.pages_collected`), which reset to `0` on `GameState.on_enter_sanctuary()` per the Closed Volume Paradox, `margin_scraps` persist across runs for weaving Binder Scripts.
- **`binder_scripts` (`dict`):** Tracks `unlocked` script IDs, `equipped` script IDs (up to `BINDER_MAX_EQUIPPED_SCRIPTS = 4`), `failed_sequence` (ordered stat archetypes of syntax-conflicted scripts toward `BINDER_PERFECT_STITCH_SEQUENCE`), and `conflicts_triggered`.
- **`story_flags` (`dict`):** Persistent narrative milestones including `perfect_stitch_completed` (`bool`) and `ink_bleed_halted` (`bool`). When `perfect_stitch_completed` is `True` and *The Final Author* is defeated, `last_run_result` is set to `"STITCH_VICTORY"` (`"THE INK-BLEED HALTED"`).

## 4. Save Reliability Features
Key implementations for data safety:
- **Save Worker Thread (IMPLEMENTED):** Utilizing a dedicated worker thread with a bounded queue to serialize heavy write operations without blocking the main game loop.
- **Atomic Operations:** Uses temporary files and `os.replace` to prevent data corruption during unexpected power loss.
- **Directory Isolation:** Stores data in `~/.config/avoid_rain/` to ensure user permissions and system cleanup protocols are respected.
