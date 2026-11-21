"""
Unit and integration tests for Section 7: Binder Scripts (Procedural Upgrade & Conflict Compiler).
Verifies Sanctuary '&' Binder NPC placement & palette parity, Margin Scraps persistence vs.
Closed Volume Paradox, syntax conflict compiler rules, player stat & LAN Co-op sync,
Sanctuary Weaving UI modal navigation, and the Perfect Stitch alternate ending ("STITCH_VICTORY").
"""
# pylint: disable=protected-access,no-member,too-many-locals,too-many-statements

import pygame

import constants
from engine.binder_scripts import (
    toggle_equip_script,
    weave_script,
)
from engine.enemy import FinalAuthor, NightBoss, SlugEnemy
from engine.game_state import GameState
from engine.player import PlayerStateEnum
from engine.stats import StatisticsTracker
from engine.world import Binder, Chronicler
from rendering.bitmap_font import load_font_or_sysfont
from rendering.renderer import Renderer
from tools.edit_map import MASTER_TOOL_REGISTRY
from ui.menu import draw_binder_weave_menu
import generate_maps


def _make_state(tmp_path):
    """Create a headless GameState in Sanctuary backed by a temporary stats path."""
    pygame.init()
    stats_path = str(tmp_path / "stats.json")
    stats = StatisticsTracker()
    state = GameState(auto_load=False, stats=stats, stats_path=stats_path)
    state.online_mode = False
    state.network_manager.stop_network()
    return state


def test_sanctuary_binder_npc_and_palette_parity(tmp_path):
    """Verify '&' spawns The Binder in Sanctuary, is mirrored across editor/generator, and loads in Renderer."""
    assert "&" in constants.TILE_KEY
    assert generate_maps.SYMBOL_BINDER == "&"
    assert generate_maps.MAP_LEGEND["&"] == "The Binder"
    assert any(entry.get("char") == "&" and entry.get("name") == "The Binder" for entry in MASTER_TOOL_REGISTRY)

    state = _make_state(tmp_path)
    binders = [obj for obj in state.world.interactables if isinstance(obj, Binder)]
    assert len(binders) == 1
    binder_npc = binders[0]
    assert binder_npc.name == "The Binder"
    assert binder_npc.is_interactive is True

    # Interacting with The Binder opens binder_dialog
    binder_npc.execute_interaction(state)
    assert state.binder_dialog is not None

    screen = pygame.Surface((1280, 720))
    renderer = Renderer(screen)
    assert "Binder" in renderer.prop_cache
    font = load_font_or_sysfont("ink_sans", 2, "Arial", 24)
    draw_binder_weave_menu(screen, font, state)
    renderer.render(state)


def test_margin_scraps_milestones_and_closed_volume_paradox(tmp_path):
    """Verify Margin Scraps are awarded on milestones and persist across Sanctuary entry while Pages reset to 0."""
    state = _make_state(tmp_path)
    assert state.stats.data["margin_scraps"] == 0

    # 1. Marginalia event completion awards +1 Margin Scrap
    state.in_sanctuary = False
    state.world.name = "generated_world"
    state.current_act = 1
    ev = state.marginalia_engine.start_event(state, "unblotted_margin", act_variant=1)
    assert ev is not None
    assert ev.status == "COMPLETED"
    assert state.stats.data["margin_scraps"] == constants.SCRAPS_REWARD_MARGINALIA_EVENT

    # 2. Night Boss defeat in Act 3 (empowered) awards +3 Margin Scraps
    state.current_act = 3
    state.empowered_act = True
    nb = NightBoss(state.player.x + 20, state.player.y)
    nb.hp = 1.0
    state.enemies = [nb]
    state.player.state = PlayerStateEnum.ATTACKING
    state.player.facing = (1, 0)
    state.update_combat(0.016, False, {"move": (0, 0)}, None)
    expected_scraps = constants.SCRAPS_REWARD_MARGINALIA_EVENT + constants.SCRAPS_REWARD_NIGHT_BOSS_EMPOWERED
    assert state.stats.data["margin_scraps"] == expected_scraps

    # 3. Closed Volume Paradox: on_enter_sanctuary resets pages_collected to 0 but preserves margin_scraps
    state.stats.data["lifetime_stats"]["pages_collected"] = 85
    state.on_enter_sanctuary()
    assert state.stats.data["lifetime_stats"]["pages_collected"] == 0
    assert state.stats.data["margin_scraps"] == expected_scraps


def test_compiler_syntax_conflicts_and_sanctuary_hp_sync(tmp_path):
    """Verify syntax conflict resolution (higher magnitude wins, weaker fails) and HP clamping/refill."""
    state = _make_state(tmp_path)
    state.stats.add_margin_scraps(20)

    # Weave minor (+15 HP) and major (+35 HP) Hemming Scripts
    ok1, _ = weave_script(state.stats, "hemming_minor")
    ok2, _ = weave_script(state.stats, "hemming_major")
    assert ok1 and ok2

    # Equip minor first: player max_hp becomes 115 and HP refills in Sanctuary
    eq1, _, comp1 = toggle_equip_script(state.stats, state.player, "hemming_minor", in_sanctuary=True)
    assert eq1 is True
    assert comp1["modifiers"]["max_hp"] == 15.0
    assert state.player.max_hp == 115.0
    assert state.player.hp == 115.0

    # Equip major second on the same stat ('max_hp'): triggers SYNTAX CONFLICT!
    # Major (+35) wins; minor (+15) is marked CONFLICTED and contributes 0 (total boost = +35, not +50)
    eq2, msg2, comp2 = toggle_equip_script(state.stats, state.player, "hemming_major", in_sanctuary=True)
    assert eq2 is True
    assert "SYNTAX CONFLICT" in msg2
    assert comp2["modifiers"]["max_hp"] == 35.0
    assert len(comp2["conflicts"]) == 1
    assert comp2["conflicts"][0]["id"] == "hemming_minor"
    assert comp2["conflicts"][0]["overridden_by"] == "hemming_major"
    assert state.player.max_hp == 135.0
    assert state.player.hp == 135.0

    # Unequipping major drops max_hp back to 115 and clamps player.hp to 115.0
    toggle_equip_script(state.stats, state.player, "hemming_major", in_sanctuary=False)
    assert state.player.max_hp == 115.0
    assert state.player.hp == 115.0

    # Entering Sanctuary syncs binder scripts before setting player.hp = player.max_hp
    state.player.hp = 40.0
    state.on_enter_sanctuary()
    assert state.player.max_hp == 115.0
    assert state.player.hp == 115.0


def test_player_stat_wiring_and_lan_coop_sync(tmp_path):
    """Verify attack, speed, damage_mitigation, and bleed apply to Player and sync across LAN Co-op."""
    state = _make_state(tmp_path)
    state.stats.add_margin_scraps(30)

    for sid in ("serif_major", "footnote_major", "gloss_major", "gall_major"):
        assert weave_script(state.stats, sid)[0] is True
        assert toggle_equip_script(state.stats, state.player, sid, in_sanctuary=True)[0] is True

    # 1. Speed (+36) increases movement velocity
    base_speed = state.player.speed
    state.player.update(0.1, (1.0, 0.0), [], {"move": (1.0, 0.0)})
    assert abs(state.player.vx - (base_speed + 36.0)) < 1e-3

    # 2. Damage mitigation (+20%) reduces incoming damage
    state.player.state = PlayerStateEnum.IDLE
    state.player.stagger_timer = 0.0
    state.player.hp = 100.0
    state.player.take_damage(50.0, bypass_stagger=True)
    # At 100% HP (>95%), Pristine Concentration reduces by 0.5% (edif=1), plus 20% script mitigation
    assert 59.0 <= state.player.hp <= 61.0

    # 3. Attack (+9) & Bleed (+6.5 DPS) apply on melee hit
    dummy = SlugEnemy(state.player.x + 24, state.player.y)
    dummy.hp = 200.0
    state.enemies = [dummy]
    state.player.state = PlayerStateEnum.ATTACKING
    state.player.facing = (1, 0)
    state.player.hit_entities_this_attack.clear()
    state.update_combat(0.016, False, {"move": (0, 0)}, None)
    assert dummy.hp == 200.0 - (constants.SWORD_DAMAGE + 9)
    assert dummy.bleed_timer == 5.0
    assert dummy.bleed_damage == 6.5

    # 4. LAN Co-op Sync: get_full_player_state & Host-authoritative remote player mitigation
    full_state = state.get_full_player_state()
    assert full_state["script_modifiers"]["damage_mitigation"] == 0.20

    host_state = _make_state(tmp_path)
    peer_key = "client_peer_1"
    host_state.network_manager.remote_players[peer_key] = {
        "x": 200.0,
        "y": 200.0,
        "hp": 100.0,
        "identity": "ScholarTwo",
    }
    host_state.host_cacher_callback("ScholarTwo", "127.0.0.1", full_state, peer_id=peer_key)

    attacker = SlugEnemy(200.0, 200.0)
    attacker.damage = 25.0
    assert attacker.attempt_damage_player(host_state) is True
    # 25.0 damage mitigated by 20% -> 20.0 damage -> 80.0 HP remaining
    assert abs(host_state.network_manager.remote_players[peer_key]["hp"] - 80.0) < 1e-4


def test_perfect_stitch_sequence_and_alternate_ending(tmp_path):
    """Verify completing the 3-step failed-script sequence and defeating The Final Author
    triggers STITCH_VICTORY ('THE INK-BLEED HALTED') and unlocks Chronicler & Binder dialogue."""
    state = _make_state(tmp_path)
    state.stats.add_margin_scraps(40)

    for sid in (
        "hemming_minor",
        "hemming_major",
        "serif_minor",
        "serif_major",
        "gloss_minor",
        "gloss_major",
    ):
        assert weave_script(state.stats, sid)[0] is True

    # Step 1 conflict: max_hp (hemming_minor overridden by hemming_major)
    toggle_equip_script(state.stats, state.player, "hemming_minor")
    toggle_equip_script(state.stats, state.player, "hemming_major")
    assert state.stats.data["binder_scripts"]["failed_sequence"] == ["max_hp"]
    assert state.stats.data["story_flags"]["perfect_stitch_completed"] is False

    # Step 2 conflict: attack (serif_minor overridden by serif_major)
    toggle_equip_script(state.stats, state.player, "serif_minor")
    toggle_equip_script(state.stats, state.player, "serif_major")
    assert state.stats.data["binder_scripts"]["failed_sequence"] == ["max_hp", "attack"]
    assert state.stats.data["story_flags"]["perfect_stitch_completed"] is False

    # Free two slots, then trigger Step 3 conflict: damage_mitigation (gloss_minor overridden by gloss_major)
    toggle_equip_script(state.stats, state.player, "hemming_minor")
    toggle_equip_script(state.stats, state.player, "serif_minor")
    toggle_equip_script(state.stats, state.player, "gloss_minor")
    _, msg_final, _ = toggle_equip_script(state.stats, state.player, "gloss_major")
    assert "PERFECT STITCH COMPLETED" in msg_final
    assert state.stats.data["binder_scripts"]["failed_sequence"] == [
        "max_hp",
        "attack",
        "damage_mitigation",
    ]
    assert state.stats.data["story_flags"]["perfect_stitch_completed"] is True

    # Defeating The Final Author in night_boss_arena triggers STITCH_VICTORY
    state.world.name = "night_boss_arena"
    author = FinalAuthor(300.0, 300.0)
    state.enemies = [author]
    state._handle_victory_conditions(0.016)
    assert state.stats.data["last_run_result"] != "STITCH_VICTORY"

    state.enemies = []
    state._handle_victory_conditions(0.016)
    assert state.stats.data["last_run_result"] == "STITCH_VICTORY"
    assert state.stats.data["story_flags"]["ink_bleed_halted"] is True
    assert state.bloom_text == "THE INK-BLEED HALTED"

    # Both The Chronicler and The Binder select their post-stitch victory dialogue
    chron = Chronicler((100.0, 100.0))
    chron.execute_interaction(state)
    assert isinstance(state.active_dialogue, dict)
    assert "counter-stitch" in state.active_dialogue["text"]

    state.open_binder_dialog()
    assert isinstance(state.binder_dialog, dict)
    assert state.binder_dialog["dialogue_id"] == "binder_stitch_victory"
    assert "bleed is over" in state.binder_dialog["status_msg"]
