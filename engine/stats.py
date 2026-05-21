"""
Statistics tracker and persistence for profile_metrics.json.

Low-coupling, self-contained feature: manages lifetime_stats and discovered_bestiary
and provides save/load functionality.
"""
from __future__ import annotations

from pathlib import Path
import json
from typing import Dict, Any

DEFAULT_FILENAME = "profile_metrics.json"


class StatisticsTracker:
    """Manage lifetime statistics and discovered bestiary entries.

    Data shape:
    {
        "lifetime_stats": { ... },
        "discovered_bestiary": { enemy_id: bool }
    }
    """

    def __init__(self, data: Dict[str, Any] | None = None) -> None:
        if data is None:
            self.data: Dict[str, Any] = {
                "lifetime_stats": {
                    "runs_started": 0,
                    "wins_chapters_cleared": 0,
                    "losses_bleed_wipes": 0,
                    "deaths_standard_respawns": 0,
                    "forced_quit_outs": 0,
                },
                "discovered_bestiary": {},
            }
        else:
            self.data = data

    def increment(self, key: str, amount: int = 1) -> None:
        """Increment a lifetime stat. Raises KeyError if the stat key is unknown."""
        if key not in self.data["lifetime_stats"]:
            raise KeyError(f"Unknown lifetime stat: {key}")
        self.data["lifetime_stats"][key] += int(amount)

    def set_bestiary(self, enemy_id: str, discovered: bool = True) -> None:
        """Mark an enemy as discovered or undiscovered."""
        self.data["discovered_bestiary"][enemy_id] = bool(discovered)

    def to_dict(self) -> Dict[str, Any]:
        return self.data

    def save(self, path: Path | str | None = None) -> None:
        """Serialize the data to JSON at the given path (or DEFAULT_FILENAME in cwd)."""
        target = Path(path) if path is not None else Path(DEFAULT_FILENAME)
        # Ensure parent exists
        if not target.parent.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(self.data, indent=2))

    @classmethod
    def load(cls, path: Path | str | None = None) -> "StatisticsTracker":
        """Load from JSON if exists, otherwise return a fresh tracker."""
        target = Path(path) if path is not None else Path(DEFAULT_FILENAME)
        if not target.exists():
            return cls()
        raw = json.loads(target.read_text())
        return cls(data=raw)
