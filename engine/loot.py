"""
LootManager: a low-coupled probability engine for rolling loot items.

Features:
- Maintain an item->weight table
- Deterministic rolls via injected random.Random
- roll(n, rng=None) returns n items (with replacement)
- add_item/remove_item and introspection helpers
"""
from __future__ import annotations

from typing import Dict, List, Optional
import random


class LootManager:
    """Manage a weighted loot table and perform deterministic rolls.

    The implementation uses simple cumulative weights and random.Random
    for deterministic sampling when a RNG instance is provided.
    """

    def __init__(self, table: Optional[Dict[str, float]] = None) -> None:
        """Initialize LootManager with an optional item->weight table."""
        self._table: Dict[str, float] = dict(table or {})

    def add_item(self, item: str, weight: float) -> None:
        """Add or update an item with the given non-negative weight."""
        if weight < 0:
            raise ValueError("weight must be non-negative")
        self._table[item] = float(weight)

    def remove_item(self, item: str) -> None:
        """Remove an item from the table. Raises KeyError if missing."""
        if item not in self._table:
            raise KeyError(f"item not found: {item}")
        del self._table[item]

    def items(self) -> Dict[str, float]:
        """Return a shallow copy of the item->weight table."""
        return dict(self._table)

    def total_weight(self) -> float:
        """Return the sum of weights in the table."""
        return sum(self._table.values())

    def roll_one(self, rng: Optional[random.Random] = None) -> str:
        """Roll a single item from the table using the provided RNG.

        Raises ValueError if the table is empty or total weight is non-positive.
        """
        if not self._table:
            raise ValueError("loot table is empty")
        total = self.total_weight()
        if total <= 0:
            raise ValueError("total weight must be positive to roll")
        if rng is None:
            rng = random
        pick = rng.random() * total
        cumulative = 0.0
        for item, weight in self._table.items():
            cumulative += weight
            if pick < cumulative:
                return item
        # Fallback (shouldn't happen due to floating point); return last item
        return list(self._table.keys())[-1]

    def roll(self, n: int = 1, rng: Optional[random.Random] = None) -> List[str]:
        """Roll n items (with replacement) and return them as a list.

        n must be non-negative.
        """
        if n < 0:
            raise ValueError("n must be non-negative")
        return [self.roll_one(rng=rng) for _ in range(int(n))]


class TornPage:
    """An collectable item (Unbound Syntax) dropped by enemies."""
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.width = 16
        self.height = 16

    def get_rect(self):
        """Returns the bounding box (x, y, w, h)."""
        return (self.x, self.y, self.width, self.height)

    def execute_pickup(self, state):
        """Increase collected pages metric in statistics."""
        if state.stats:
            try:
                # Add to inventory if we track it on player/state
                # For now, we increment a lifetime/run stat
                state.stats.increment("pages_collected", 1)
            except Exception:
                pass
