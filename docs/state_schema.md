# State Schema

The `GameState` object is the "Single Source of Truth."

## PlayerState
- `pos`: Vector2 (x, y)
- `vel`: Vector2 (vx, vy)
- `health`: int (current / max)
- `flask`: { 'charges': int, 'level': int, 'potency': int }
- `stats`: { 'atk': int, 'def': int, 'speed': float }
- `inventory`: { 'weapon': str, 'shield': str, 'pages': int }
- `state`: Enum (IDLE, MOVING, DASHING, BLOCKING, ATTACKING, HURT)

## RainState
- `center`: Vector2 (x, y)
- `radius`: float
- `shrink_rate`: float
- `is_active`: bool

## WorldState
- `day`: int (1 or 2)
- `active_sections`: List of section IDs.
- `killed_enemies`: Set of unique enemy IDs (for persistence).
- `story_flags`: Dict { flag_name: bool }
- `respawn_point`: Vector2 (x, y)

## Statistics & Persistence (profile_metrics.json)
- `lifetime_stats`: Dict of cumulative metrics (runs, wins, deaths, pages).
- `discovered_bestiary`: Dict { enemy_id: bool }.
- `run_state`: Serialized snapshot of current player and world state for resumption.
- `last_run_result`: Enum (INIT, VICTORY, DEFEAT) used for dialogue branching.
