"""Headless unit tests for the Storm-and-Lightning Title Transition."""
import json
import os
from unittest.mock import MagicMock

import constants
from engine.enemy import SlugEnemy
from engine.game_state import GameState
from engine.stats import StatisticsTracker
from engine.title_menu import TitleTransition, TitleTransitionPhase


def test_title_transition_multi_phase_progression():
    """Verify Phase 1 -> Phase 2 (storm_intro.ogg + lightning) -> Phase 3 -> COMPLETE."""
    tr = TitleTransition()
    mock_audio = MagicMock()

    assert tr.phase == TitleTransitionPhase.IDLE
    assert not tr.is_active()

    tr.start("new_draft")
    assert tr.phase == TitleTransitionPhase.FADE_TO_BLACK
    assert tr.is_active()

    # Mid Phase 1: fade alpha rises, storm_intro.ogg not played yet
    done = tr.update(constants.TITLE_TRANSITION_FADE_IN_DURATION * 0.5, audio_manager=mock_audio)
    assert not done
    assert 100 <= tr.get_fade_alpha() <= 155
    mock_audio.play_sfx.assert_not_called()

    # Enter Phase 2 (Storm Vignette): plays storm_intro.ogg once
    tr.update(constants.TITLE_TRANSITION_FADE_IN_DURATION, audio_manager=mock_audio)
    assert tr.phase == TitleTransitionPhase.STORM_VIGNETTE
    mock_audio.play_sfx.assert_called_once_with(constants.STORM_INTRO_SFX)

    # Lightning flash activates at first bolt timestamp
    bolt_start = constants.TITLE_LIGHTNING_BOLTS[0][0] + 0.02
    tr.update(bolt_start, audio_manager=mock_audio)
    assert tr.get_lightning_flash() > 0.5
    assert tr.get_active_bolt_index() == 0

    # Complete Phase 2 -> enter Phase 3 (Fade to Black & Warp)
    tr.update(constants.TITLE_TRANSITION_STORM_DURATION, audio_manager=mock_audio)
    assert tr.phase == TitleTransitionPhase.FADE_OUT_AND_WARP
    mock_audio.play_sfx.assert_called_once_with(constants.STORM_INTRO_SFX)

    # Complete Phase 3 -> COMPLETE
    done = tr.update(constants.TITLE_TRANSITION_FADE_OUT_DURATION + 0.05, audio_manager=mock_audio)
    assert done is True
    assert tr.phase == TitleTransitionPhase.COMPLETE
    assert not tr.is_active()


def test_title_transition_skip_and_sanctuary_ready():
    """Verify skip() completes immediately and Sanctuary loads cleanly."""
    tr = TitleTransition()
    tr.start("continue")
    tr.update(0.1)
    assert tr.is_active()

    tr.skip()
    assert tr.skipped is True
    assert tr.phase == TitleTransitionPhase.COMPLETE
    assert tr.update(0.016) is True

    gs = GameState(auto_load=False)
    gs.reset_to_new_game()
    assert gs.world.name == "sanctuary"


def test_title_transition_new_draft_and_continue_sanctuary_clean():
    """Regression: new_draft and continue clear stray enemies and align Sanctuary collisions."""
    with open(os.path.join("maps", "sanctuary.json"), encoding="utf-8") as f:
        sanctuary_data = json.load(f)
    expected_w = sanctuary_data["dimensions"]["width"]
    expected_h = sanctuary_data["dimensions"]["height"]

    # 1. Simulate a dirty state with a SlugEnemy before New Draft transition completes
    gs = GameState(auto_load=False, stats=StatisticsTracker())
    gs.enemies = [SlugEnemy(100, 100)]
    tr = TitleTransition()
    tr.start("new_draft")
    tr.skip()
    assert tr.update(0.016) is True
    gs.reset_to_new_game()

    assert gs.world.name == "sanctuary"
    assert gs.enemies == []
    assert len(gs.world.grid) == expected_h
    assert len(gs.world.grid[0]) == expected_w
    assert gs.world.grid[0][0] == constants.TILE_WALL

    # 2. Simulate Continue with a stale generated_world run_state whose temp file is absent
    temp_path = constants.get_generated_world_path()
    if os.path.exists(temp_path):
        os.remove(temp_path)
    gs.stats.data["run_state"] = {
        "world_name": "generated_world",
        "enemies": [{"name": "Slug", "x": 120, "y": 120, "hp": 30}],
        "player": {"x": 200.0, "y": 200.0, "hp": 80.0},
    }
    tr.start("continue")
    tr.skip()
    assert tr.update(0.016) is True
    gs.hydrate_from_disk()

    assert gs.world.name == "sanctuary"
    assert gs.enemies == []
    assert len(gs.world.grid) == expected_h
    assert len(gs.world.grid[0]) == expected_w
    assert gs.world.grid[0][0] == constants.TILE_WALL

    # 3. Verify Renderer.invalidate_static_world() clears chunk and minimap caches
    import pygame
    from rendering.renderer import Renderer
    pygame.init()
    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)
    renderer._chunk_cache[(0, 0)] = ("dummy", [])
    renderer._chunk_world_key = "stale"
    renderer.invalidate_static_world()
    assert renderer._chunk_cache == {}
    assert renderer._chunk_world_key is None
