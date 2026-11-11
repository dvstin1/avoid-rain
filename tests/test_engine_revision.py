"""Unit tests for the Game Engine Revision save compatibility system."""
import json
from constants import ENGINE_REVISION
from engine.stats import StatisticsTracker
from engine.title_menu import TitleMenu
from engine.game_state import GameState


def test_fresh_tracker_stamps_current_engine_revision(tmp_path):
    """Verify new StatisticsTracker instances stamp ENGINE_REVISION and are compatible."""
    save_file = tmp_path / "save_data.json"
    tracker = StatisticsTracker()
    assert tracker.data["engine_revision"] == ENGINE_REVISION
    assert tracker.is_revision_compatible is True

    tracker.save(save_file)
    assert StatisticsTracker.has_compatible_save(save_file) is True

    menu = TitleMenu(has_save=StatisticsTracker.has_compatible_save(save_file))
    assert "Continue" in menu.get_options()


def test_outdated_or_unversioned_save_disables_continue(tmp_path):
    """Verify old save files without matching ENGINE_REVISION disable Continue and strip run_state."""
    old_save = tmp_path / "old_save.json"
    legacy_payload = {
        "player_name": "OldScholar",
        "active_session_in_progress": True,
        "run_state": {
            "world_name": "forest",
            "player": {"x": 300.0, "y": 400.0, "hp": 55.0, "flask_charges": 1}
        },
        "lifetime_stats": {
            "runs_started": 4,
            "wins_chapters_cleared": 1,
            "losses_bleed_wipes": 2,
            "deaths_standard_respawns": 3,
            "forced_quit_outs": 0,
            "pages_collected": 25,
        },
        "discovered_bestiary": {"Slug": True},
    }
    old_save.write_text(json.dumps(legacy_payload), encoding="utf-8")

    # 1. Unversioned save is not compatible for Continue
    assert StatisticsTracker.has_compatible_save(old_save) is False
    menu_unversioned = TitleMenu(has_save=StatisticsTracker.has_compatible_save(old_save))
    assert "Continue" not in menu_unversioned.get_options()
    assert menu_unversioned.get_options()[0] == "New Draft"

    # 2. Loading the outdated save strips run_state and marks tracker incompatible
    loaded = StatisticsTracker.load(old_save)
    assert loaded.is_revision_compatible is False
    assert loaded.data["run_state"] is None
    assert loaded.data["active_session_in_progress"] is False

    # 3. Explicitly older revision number also disables Continue
    legacy_payload["engine_revision"] = ENGINE_REVISION - 1
    old_save.write_text(json.dumps(legacy_payload), encoding="utf-8")
    assert StatisticsTracker.has_compatible_save(old_save) is False
    menu_old_rev = TitleMenu(has_save=StatisticsTracker.has_compatible_save(old_save))
    assert "Continue" not in menu_old_rev.get_options()


def test_game_state_ignores_outdated_run_state_and_upgrades_on_new_game(tmp_path):
    """Verify GameState skips hydrating outdated saves and stamps ENGINE_REVISION on New Draft."""
    save_file = tmp_path / "save_data.json"
    outdated_payload = {
        "engine_revision": ENGINE_REVISION - 1,
        "active_session_in_progress": True,
        "run_state": {
            "world_name": "chapter1",
            "player": {"x": 500.0, "y": 600.0, "hp": 42.0, "flask_charges": 2}
        },
        "lifetime_stats": {
            "runs_started": 1,
            "wins_chapters_cleared": 0,
            "losses_bleed_wipes": 0,
            "deaths_standard_respawns": 0,
            "forced_quit_outs": 0,
            "pages_collected": 10,
        },
        "discovered_bestiary": {},
    }
    save_file.write_text(json.dumps(outdated_payload), encoding="utf-8")

    gs = GameState(stats=None, stats_path=str(save_file), auto_load=True)
    try:
        # Should NOT have hydrated into 'chapter1' because revision is outdated
        assert gs.world.name == "sanctuary"
        assert gs.stats.is_revision_compatible is False

        # Starting a New Draft stamps ENGINE_REVISION and makes the save compatible
        gs.reset_to_new_game()
        gs.save_stats(str(save_file), wait=True)
        assert gs.stats.is_revision_compatible is True
        assert StatisticsTracker.has_compatible_save(save_file) is True
    finally:
        gs.shutdown_save_worker(timeout=1.0)
