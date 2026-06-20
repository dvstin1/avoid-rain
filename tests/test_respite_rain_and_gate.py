"""
Unit tests for gated Respite activation on forest and ruins maps,
and Respite deactivation/auto-closure under rain weather conditions.
"""
# pylint: disable=wrong-import-position,wrong-import-order,no-member

import os
# Ensure headless execution before importing pygame
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pytest
import pygame

from engine.game_state import GameState
from engine.world import Respite, LevelLoader
from engine.maps import create_world
from engine.weather import WeatherManager


@pytest.fixture(scope="module", autouse=True)
def init_pygame():
    """Initializes pygame in headless mode for the test suite."""
    pygame.init()
    yield
    pygame.quit()


def test_respite_gating_on_forest_and_ruins():
    """
    Verifies that on forest and ruins maps, the Respite starts inactive
    if the miniboss is alive, and becomes active once the miniboss is defeated.
    """
    # 1. Test Forest Map
    state = GameState(auto_load=False)
    state.world = create_world("forest")
    state.enemies = state.world.enemies

    # Verify we have at least one Respite and a Miniboss
    respites = [obj for obj in state.world.interactables if isinstance(obj, Respite)]
    minibosses = [e for e in state.enemies if getattr(e, 'is_miniboss', False)]

    assert len(respites) > 0, "No respite found on forest map."
    assert len(minibosses) > 0, "No miniboss found on forest map."

    # Initially, respite should be inactive because the miniboss is alive
    for r in respites:
        assert r.is_active is False, "Respite should be inactive while miniboss is alive."

    # Remove all minibosses to simulate defeating them
    for e in minibosses:
        state.defeated_miniboss_ids.add(e.id)
    state.enemies = [e for e in state.enemies if not getattr(e, 'is_miniboss', False)]

    # Update game state to run the activation logic
    state.update(0.1, {"move": (0, 0)})

    # Now respite should be active
    for r in respites:
        assert r.is_active is True, "Respite should be active after miniboss is defeated."


def test_respite_active_on_other_maps():
    """
    Verifies that on maps other than forest/ruins, the Respite is active
    regardless of whether there are minibosses or not.
    """
    state = GameState(auto_load=False)
    state.world = create_world("sanctuary")
    state.enemies = state.world.enemies

    # Create respite programmatically
    respite = Respite((0, 0), (40, 40))
    state.world.interactables.append(respite)

    assert respite.is_active is True, "Respite on sanctuary should always be active."


def test_respite_rain_interaction_denial():
    """
    Verifies that interacting with a Respite exposed to rain returns a lore accurate
    dialogue message and does not open the Respite level-up UI.
    """
    state = GameState(auto_load=False)
    state.world = create_world("sanctuary")

    # Setup weather manager with rain at Respite location
    state.weather_manager = WeatherManager()
    state.weather_manager.boss_coords_list = [{'x': 0, 'y': 0}]
    state.weather_manager.current_boss_idx = 0
    state.weather_manager.active_safe_radius = 50.0  # Very small safe zone
    state.weather_manager.bleed_state = "SHRINKING"
    state.weather_manager.damage_enabled = True

    # Create respite far away from safe zone (e.g. at 500, 500)
    respite = Respite((500, 500), (40, 40))
    state.world.interactables.append(respite)

    # Verify it is considered rained on
    rx = respite.x + respite.width / 2
    ry = respite.y + respite.height / 2
    assert state.weather_manager.is_pos_safe(rx, ry) is False, "Respite should be outside safe zone."

    # Try interacting with it
    respite.execute_interaction(state)

    # Should show dialogue and not set active_respite
    assert state.active_respite is None, "Respite menu should not open when rained on."
    assert state.active_dialogue is not None, "Lore accurate dialogue should be set."
    # pylint: disable=unsubscriptable-object
    assert "liquid ink" in state.active_dialogue["text"], "Dialogue should contain lore explanation."


def test_respite_rain_auto_closure():
    """
    Verifies that if a Respite starts getting rained on while the player is using it,
    it closes instantly.
    """
    state = GameState(auto_load=False)
    state.world = create_world("sanctuary")

    # Setup weather manager
    state.weather_manager = WeatherManager()
    state.weather_manager.boss_coords_list = [{'x': 0, 'y': 0}]
    state.weather_manager.current_boss_idx = 0
    state.weather_manager.active_safe_radius = 1000.0  # Initially large/safe
    state.weather_manager.bleed_state = "SHRINKING"
    state.weather_manager.damage_enabled = True

    # Create respite inside safe zone
    respite = Respite((100, 100), (40, 40))
    state.world.interactables.append(respite)

    # Interact and open menu
    respite.execute_interaction(state)
    assert state.active_respite == respite, "Respite menu should be open."

    # Shrink safe circle to expose Respite
    state.weather_manager.active_safe_radius = 50.0  # Respite at 100, 100 is now outside

    # Run update
    state.update(0.1, {"move": (0, 0)})

    # Menu should be closed instantly
    assert state.active_respite is None, "Respite menu should close instantly when rained on."
    assert state.active_dialogue is None, "Dialogue should close as well."


def test_respite_gating_modular_proximity():
    """
    Verifies that proximity-based Respite gating works correctly on a custom/stitched map.
    """

    # 1. Define a prototype array where 'R' and 'E' (miniboss) are placed near each other (distance = 2)
    grid_proto = [
        "..........",
        "....R.E...",
        ".........."
    ]

    # 2. Parse the map using a custom/modular name
    _, interactables, _, _, _ = LevelLoader.parse_map(
        grid_proto, map_name="modular_world_test", defeated_ids=set()
    )

    # 3. Find the Respite and verify its gated_by_miniboss_id is set
    respites = [obj for obj in interactables if isinstance(obj, Respite)]
    assert len(respites) == 1
    respite = respites[0]

    # Expected gating miniboss coordinate is (6, 1) since E is at x=6, y=1
    assert respite.gated_by_miniboss_id == "modular_world_test:6,1"
    assert respite.is_active is False, "Respite should start inactive because miniboss is not defeated."

    # 4. If we parse with the miniboss already in defeated_ids
    _, interactables_def, _, _, _ = LevelLoader.parse_map(
        grid_proto, map_name="modular_world_test", defeated_ids={"modular_world_test:6,1"}
    )
    respite_def = [obj for obj in interactables_def if isinstance(obj, Respite)][0]
    assert respite_def.is_active is True, "Respite should start active if the gating miniboss was defeated."
