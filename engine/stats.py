"""
Statistics tracker and persistence for profile_metrics.json.

Low-coupling, self-contained feature: manages lifetime_stats and discovered_bestiary
and provides save/load functionality.
"""
from __future__ import annotations

from pathlib import Path
import json
import os
import time
import tempfile
from typing import Dict, Any

DEFAULT_PATH = Path.home() / ".avoid-rain" / "profile_metrics.json"


class CorruptSaveError(Exception):
    """Raised when a save file is detected as corrupted during load.

    Attributes:
        backup_path: path where the corrupt file was moved to for inspection.
    """
    def __init__(self, message: str, backup_path: Path | None = None):
        super().__init__(message)
        self.backup_path = backup_path


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
        """Mark an enemy as discovered or undiscovered in the bestiary."""
        self.data["discovered_bestiary"][enemy_id] = bool(discovered)

    def to_dict(self) -> Dict[str, Any]:
        """Return the internal data as a plain dictionary."""
        return self.data

    def save(self, path: Path | str | None = None) -> None:
        """Atomically serialize the data to JSON at the given path (or DEFAULT_PATH).

        The parent directory will be created if it does not exist. The method
        writes to a temporary file in the same directory, fsyncs the data and
        then atomically replaces the target file. This minimizes risk of
        corruption on crashes mid-write.
        """
        target = Path(path) if path is not None else DEFAULT_PATH
        # Ensure parent exists
        target.parent.mkdir(parents=True, exist_ok=True)

        # Serialize to bytes first
        payload = json.dumps(self.data, indent=2).encode('utf-8')

        # Write to temporary file in same directory then replace
        fd = None
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, dir=str(target.parent)) as tf:
                fd = tf.fileno()
                tf.write(payload)
                tf.flush()
                os.fsync(fd)
                tmp_path = Path(tf.name)
            # Use os.replace for atomic rename
            os.replace(str(tmp_path), str(target))
        finally:
            # Ensure temp file removed on failure
            if tmp_path is not None and tmp_path.exists():
                try:
                    tmp_path.unlink()
                except Exception:
                    pass

    @classmethod
    def load(cls, path: Path | str | None = None) -> "StatisticsTracker":
        """Load from JSON if it exists; otherwise return a fresh tracker.

        If the file is found to be corrupted (invalid JSON or missing expected
        sections), the corrupt file is moved aside with a timestamped suffix
        and CorruptSaveError is raised with the backup path for inspection.
        """
        target = Path(path) if path is not None else DEFAULT_PATH
        if not target.exists():
            return cls()
        try:
            raw_text = target.read_text(encoding='utf-8')
            raw = json.loads(raw_text)
            # Basic shape check
            if 'lifetime_stats' not in raw or 'discovered_bestiary' not in raw:
                raise ValueError('Missing required sections')
            return cls(data=raw)
        except Exception as exc:
            # Move corrupt file aside so user can inspect it
            t = int(time.time())
            backup = target.with_name(f"{target.name}.corrupt.{t}")
            try:
                os.replace(str(target), str(backup))
            except Exception:
                # fallback to rename
                try:
                    target.rename(backup)
                except Exception:
                    backup = None
            raise CorruptSaveError("Save file is corrupted", backup_path=backup)
