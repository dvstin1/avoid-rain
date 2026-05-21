import random

import pytest

from engine.loot import LootManager


def test_add_and_roll_single():
    lm = LootManager()
    lm.add_item("common", 1.0)
    lm.add_item("zero", 0.0)
    rng = random.Random(1)
    # zero-weight item should never be chosen
    for _ in range(50):
        assert lm.roll_one(rng=rng) == "common"


def test_weights_bias():
    lm = LootManager()
    lm.add_item("common", 80.0)
    lm.add_item("rare", 20.0)
    rng = random.Random(42)
    rolls = lm.roll(1000, rng=rng)
    common_count = sum(1 for r in rolls if r == "common")
    # Expect common to dominate; allow some statistical variance
    assert common_count > 700


def test_remove_item_and_errors():
    lm = LootManager({"a": 1.0, "b": 1.0})
    lm.remove_item("a")
    assert "a" not in lm.items()
    with pytest.raises(KeyError):
        lm.remove_item("missing")


def test_roll_zero_and_negative_n():
    lm = LootManager({"x": 1.0})
    assert lm.roll(0) == []
    with pytest.raises(ValueError):
        lm.roll(-1)


def test_empty_table_raises():
    lm = LootManager()
    with pytest.raises(ValueError):
        lm.roll_one()
