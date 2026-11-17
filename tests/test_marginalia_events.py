"""
Unit and integration tests for the Marginalia Event Engine (Section 10).
"""
# pylint: disable=protected-access,no-member,import-outside-toplevel,too-many-locals,too-many-statements
import random
import pygame
import pytest

from constants import (
    FLASK_MAX_CHARGES,
    MARGINALIA_CENSOR_HUNT_DURATION,
    MARGINALIA_CENSORED_TARGET_CHARGE,
)
from engine.game_state import GameState
from engine.marginalia_events import (
    MARGINALIA_EVENT_CATALOG,
    MarginaliaEventEngine,
    adjust_torn_pages,
)
from engine.stats import StatisticsTracker
from engine.world import ExitLadder, PitfallTrigger, Respite, WeaponPickup, World


def _make_active_run_state(act: int = 1) -> GameState:
    """Create a headless GameState in an active macro-world run."""
    state = GameState(stats=StatisticsTracker(), auto_load=False)
    state.network_manager.stop_network()
    world = World("generated_world")
    world.boss_coords_list = [{"x": 50, "y": 50}]
    state.world = world
    state.in_sanctuary = False
    state.current_act = act
    state.empowered_act = act >= 2
    state.player.x, state.player.y = 400.0, 400.0
    state.weather_manager.reset(boss_coords_list=world.boss_coords_list)
    return state


def test_per_act_roll_and_step_idx_gating():
    """Verify 20% per-Act roll (max 1 per Act) and current_step_idx < 2 / bleed_state gating."""
    state = _make_active_run_state(act=1)

    # 1. Blocked when current_step_idx >= 2
    state.weather_manager.current_step_idx = 2
    state.marginalia_engine = MarginaliaEventEngine(rng=random.Random(1), trigger_chance=1.0)
    assert state.marginalia_engine.try_roll_for_act(state) is None
    assert 1 not in state.marginalia_engine.rolled_acts

    # 2. Blocked during BOSS_PHASE or DILUTION
    state.weather_manager.current_step_idx = 1
    for blocked_state in ("BOSS_PHASE", "DILUTION"):
        state.weather_manager.bleed_state = blocked_state
        assert state.marginalia_engine.try_roll_for_act(state) is None

    # 3. Succeeds when current_step_idx < 2 and bleed_state is valid, max 1 per Act
    state.weather_manager.bleed_state = "GRACE_PERIOD"
    ev1 = state.marginalia_engine.try_roll_for_act(state)
    assert ev1 is not None
    assert ev1.event_id in MARGINALIA_EVENT_CATALOG
    assert 1 in state.marginalia_engine.rolled_acts
    assert 1 in state.marginalia_engine.triggered_acts

    # Subsequent roll in Act 1 returns None (max 1 event per Act)
    assert state.marginalia_engine.try_roll_for_act(state) is None

    # Transition to Act 2 allows a fresh roll for Act 2
    state.current_act = 2
    state.marginalia_engine.active_event = None
    ev2 = state.marginalia_engine.try_roll_for_act(state)
    assert ev2 is not None
    assert ev2.act_variant == 2
    assert state.marginalia_engine.try_roll_for_act(state) is None

    # Verify ~20% statistical roll rate across 500 seeded trials
    rng = random.Random(42)
    triggered = 0
    for _ in range(500):
        s = _make_active_run_state(act=1)
        s.marginalia_engine = MarginaliaEventEngine(rng=rng, trigger_chance=0.20)
        if s.marginalia_engine.try_roll_for_act(s) is not None:
            triggered += 1
    assert 70 <= triggered <= 135


def test_weather_manager_paused_lifecycle():
    """Verify WeatherManager.paused freezes timers and suppresses exposure damage."""
    state = _make_active_run_state(act=1)
    wm = state.weather_manager
    wm.bleed_state = "SHRINKING"
    wm.timer = 20.0
    wm.active_safe_radius = 50.0  # Player at (400, 400) is far outside safe zone (2000, 2000)

    ev = state.marginalia_engine.start_event(state, "unbound_folio", act_variant=1)
    assert ev is not None
    assert wm.paused is True

    initial_hp = state.player.hp
    initial_radius = wm.active_safe_radius
    wm.update(5.0, state.player, state.world)
    assert wm.timer == 20.0
    assert wm.active_safe_radius == initial_radius
    assert state.player.is_exposed is False
    assert state.player.hp == initial_hp

    # Completing or failing event restores paused = False
    state.marginalia_engine._fail_event(state, ev)
    assert wm.paused is False

    # Sanctuary return also clears paused and resets Marginalia state
    wm.paused = True
    state.on_enter_sanctuary()
    assert state.weather_manager.paused is False
    assert state.marginalia_engine.active_event is None


def test_return_anchor_pitfall_and_exit_ladder():
    """Verify The Sunken Margin pitfall warps party into Ink Well Cellar and Exit Ladder returns."""
    state = _make_active_run_state(act=1)
    overworld = state.world
    state.player.x, state.player.y = 520.0, 640.0

    ev = state.marginalia_engine.seed_map_anchor(state, "sunken_margin", act_variant=1)
    assert ev is not None
    assert ev.status == "PENDING"
    leaf_pile = next(o for o in state.world.interactables if o.name == "Suspicious Leaf Pile")

    # Step onto the disguised leaf pile
    state.player.x, state.player.y = leaf_pile.x, leaf_pile.y
    state.marginalia_engine.update(0.016, state)

    assert ev.status == "ACTIVE"
    assert state.world.name == "ink_well_cellar"
    assert len(state.return_anchor_stack) == 1
    assert state.weather_manager.paused is True
    assert len(state.enemies) == 4

    # Defeat all cellar ambush enemies
    state.enemies.clear()
    state.marginalia_engine.update(0.016, state)
    assert ev.status == "COMPLETED"
    assert state.stats.data["lifetime_stats"]["pages_collected"] == 4

    ladder = next((o for o in state.world.interactables if isinstance(o, ExitLadder)), None)
    assert ladder is not None

    # Use Exit Ladder to pop ReturnAnchor and return to exact overworld coordinates
    ladder.execute_interaction(state)
    assert state.world is overworld
    assert (state.player.x, state.player.y) == (leaf_pile.x, leaf_pile.y)
    assert len(state.return_anchor_stack) == 0
    assert state.weather_manager.paused is False


def test_respite_rest_anti_farming_persistence():
    """Verify triggered/completed map_anchor events stay consumed across Respite.execute_rest()."""
    state = _make_active_run_state(act=1)
    ev = state.marginalia_engine.seed_map_anchor(state, "sunken_margin", act_variant=1)
    assert ev is not None
    leaf_pile = next(o for o in state.world.interactables if o.name == "Suspicious Leaf Pile")

    # Trigger and complete the pitfall anchor
    state.marginalia_engine.trigger_pitfall_anchor(state, leaf_pile)
    state.enemies.clear()
    state.marginalia_engine.update(0.016, state)
    state.pop_return_anchor()

    # Add a counterfeit leaf pile and rest at Respite: consumed anchor must be stripped and cannot re-trigger
    state.world.interactables.append(PitfallTrigger((400, 400), anchor_id=ev.anchor_id))
    respite = Respite((400, 400), (40, 40))
    respite.execute_rest(state)

    assert not any(o.name == "Suspicious Leaf Pile" for o in state.world.interactables)
    assert state.marginalia_engine.trigger_pitfall_anchor(state) is False


@pytest.mark.parametrize("act", [1, 2])
def test_all_9_events_completion_failure_and_economy_rules(act):
    """Verify all 9 Marginalia events in Act 1 & Act 2 obey Torn Pages, Full-Cradle, and Edification rules."""
    # 1. The Unbound Folio (Completion & Failure)
    state = _make_active_run_state(act=act)
    state.player.flask_charges = 0
    ev = state.marginalia_engine.start_event(state, "unbound_folio", act_variant=act)
    for _ in range(ev.total_waves):
        state.enemies.clear()
        state.marginalia_engine.update(0.016, state)
    assert ev.status == "COMPLETED"
    assert state.stats.data["lifetime_stats"]["pages_collected"] == (3 if act == 1 else 5)
    assert state.player.flask_charges == FLASK_MAX_CHARGES
    if act == 2:
        assert state.player.attack_speed_buff_timer > 0.0

    state_fail = _make_active_run_state(act=act)
    state_fail.player.hp = 5.0
    ev_f = state_fail.marginalia_engine.start_event(state_fail, "unbound_folio", act_variant=act)
    ev_f.time_remaining = 0.0
    state_fail.marginalia_engine.update(0.1, state_fail)
    assert ev_f.status == "FAILED"
    assert state_fail.player.hp >= 1.0  # Non-lethal burst

    # 2. The Running Errata (Full-Cradle Rule on Completion & Puddle/Flask Drain on Failure)
    state = _make_active_run_state(act=act)
    if act == 2:
        state.player.weapons.append({"name": "Second Quill", "damage": 14})
    ev = state.marginalia_engine.start_event(state, "running_errata", act_variant=act)
    state.enemies.clear()
    ev.wisp_pos = ev.wisp_target
    state.marginalia_engine.update(0.1, state)
    assert ev.status == "COMPLETED"
    pickups = [o for o in state.world.interactables if isinstance(o, WeaponPickup)]
    assert len(pickups) == 1
    if act == 2:
        assert "modifiers" in pickups[0].weapon_data  # Full-Cradle Anomalous drop
    else:
        assert pickups[0].weapon_data["name"] == "Refined Quill"

    state_fail = _make_active_run_state(act=act)
    ev_f = state_fail.marginalia_engine.start_event(state_fail, "running_errata", act_variant=act)
    ev_f.wisp_hp = 0.0
    state_fail.marginalia_engine.update(0.1, state_fail)
    assert ev_f.status == "FAILED"
    assert state_fail.player.flask_charges == FLASK_MAX_CHARGES - 1
    assert any(o.name == "Inkwell Puddle" for o in state_fail.world.interactables)

    # 3. The Censored Passage (Heal + Pages, No Direct Edification, Failure Vignette)
    state = _make_active_run_state(act=act)
    state.player.hp = 20.0
    state.player.stats["edification"] = 1
    ev = state.marginalia_engine.start_event(state, "censored_passage", act_variant=act)
    state.marginalia_engine.update(MARGINALIA_CENSORED_TARGET_CHARGE + 0.5, state)
    assert ev.status == "COMPLETED"
    assert state.player.hp > 20.0
    assert state.player.stats["edification"] == 1

    state_fail = _make_active_run_state(act=act)
    ev_f = state_fail.marginalia_engine.start_event(state_fail, "censored_passage", act_variant=act)
    state_fail.player.x += 900.0
    ev_f.time_remaining = 0.0
    state_fail.marginalia_engine.update(0.1, state_fail)
    assert ev_f.status == "FAILED"
    assert state_fail.ink_mist_vignette_timer > 0.0

    # 4. The Palimpsest Duel (+15/+25 run max_hp, Full-Cradle in Act 2, Debuff on Failure)
    state = _make_active_run_state(act=act)
    if act == 2:
        state.player.weapons.append({"name": "Second Quill", "damage": 14})
    base_max_hp = state.player.max_hp
    ev = state.marginalia_engine.start_event(state, "palimpsest_duel", act_variant=act)
    state.enemies.clear()
    state.marginalia_engine.update(0.1, state)
    assert ev.status == "COMPLETED"
    assert state.player.max_hp == base_max_hp + (15 if act == 1 else 25)
    if act == 2:
        pickups = [o for o in state.world.interactables if isinstance(o, WeaponPickup)]
        assert len(pickups) == 1 and "modifiers" in pickups[0].weapon_data

    state_fail = _make_active_run_state(act=act)
    ev_f = state_fail.marginalia_engine.start_event(state_fail, "palimpsest_duel", act_variant=act)
    ev_f.time_remaining = 0.0
    state_fail.marginalia_engine.update(0.1, state_fail)
    assert ev_f.status == "FAILED"
    assert state_fail.player.duel_debuff_timer > 0.0

    # 5. The Margin Toll (3/4 Seals -> Storm Immunity; Failure strips 1-2 Pages clamped >= 0)
    state = _make_active_run_state(act=act)
    ev = state.marginalia_engine.start_event(state, "margin_toll", act_variant=act)
    seals = [o for o in list(state.world.interactables) if o.name == "Ink Seal"]
    assert len(seals) == (3 if act == 1 else 4)
    for seal in seals:
        seal.take_damage(100.0)
        state.marginalia_engine.on_prop_struck(state, seal)
    assert ev.status == "COMPLETED"
    assert state.player.storm_immunity_timer > 0.0

    state_fail = _make_active_run_state(act=act)
    adjust_torn_pages(state_fail, 1)
    ev_f = state_fail.marginalia_engine.start_event(state_fail, "margin_toll", act_variant=act)
    ev_f.time_remaining = 0.0
    state_fail.marginalia_engine.update(0.1, state_fail)
    assert ev_f.status == "FAILED"
    assert state_fail.stats.data["lifetime_stats"]["pages_collected"] == 0  # Clamped >= 0

    # 6. The Barrel Mimic Cluster (8/12 mimics -> Pages, Flask refill, Weapon & Heal drop)
    state = _make_active_run_state(act=act)
    ev = state.marginalia_engine.seed_map_anchor(state, "barrel_mimic_cluster", act_variant=act)
    barrel = next(o for o in state.world.interactables if o.name == "Barrel")
    barrel.take_damage(10.0)
    assert state.marginalia_engine.on_prop_struck(state, barrel) is True
    assert ev.status == "ACTIVE"
    assert len(state.enemies) == (8 if act == 1 else 12)
    state.enemies.clear()
    state.marginalia_engine.update(0.1, state)
    assert ev.status == "COMPLETED"
    assert len(state.loot) == 1

    # 8. The Relentless Censor (Slay vs Survive 40s vs Lethal Setback)
    state_slay = _make_active_run_state(act=act)
    ev = state_slay.marginalia_engine.start_event(state_slay, "relentless_censor", act_variant=act)
    censor = state_slay.enemies[-1]
    assert censor.persistent_pursuit is True
    state_slay.enemies.clear()
    state_slay.marginalia_engine.update(0.1, state_slay)
    assert ev.status == "COMPLETED"
    assert state_slay.stats.data["lifetime_stats"]["pages_collected"] == (4 if act == 1 else 6)

    state_surv = _make_active_run_state(act=act)
    state_surv.player.hp = 50.0
    ev_s = state_surv.marginalia_engine.start_event(state_surv, "relentless_censor", act_variant=act)
    state_surv.marginalia_engine.update(MARGINALIA_CENSOR_HUNT_DURATION + 0.5, state_surv)
    assert ev_s.status == "COMPLETED"
    assert state_surv.player.hp == 80.0
    assert len(state_surv.enemies) == 0

    state_hit = _make_active_run_state(act=act)
    ev_h = state_hit.marginalia_engine.start_event(state_hit, "relentless_censor", act_variant=act)
    state_hit.player.hp = 0.0
    state_hit.marginalia_engine.update(0.1, state_hit)
    assert ev_h.status == "FAILED"
    assert state_hit.player.hp >= 25.0
    assert len(state_hit.enemies) == 0

    # 9. The Unblotted Margin (Zero-Risk Boon + Act 2 Pristine Ink Shield)
    state = _make_active_run_state(act=act)
    state.player.hp = 12.0
    state.player.flask_charges = 0
    ev = state.marginalia_engine.start_event(state, "unblotted_margin", act_variant=act)
    assert ev.status == "COMPLETED"
    assert state.player.hp == state.player.max_hp
    assert state.player.flask_charges == FLASK_MAX_CHARGES
    assert state.stats.data["lifetime_stats"]["pages_collected"] == (2 if act == 1 else 3)
    if act == 2:
        assert state.player.pristine_ink_shield_timer == pytest.approx(25.0)
        state.player.take_damage(40.0)
        assert state.player.hp == state.player.max_hp

    # Sanctuary return resets Torn Pages to 0
    state.on_enter_sanctuary()
    assert state.stats.data["lifetime_stats"]["pages_collected"] == 0


def test_persistent_pursuit_breadcrumbs_and_lan_coop_sync():
    """Verify persistent_pursuit breadcrumb tracking, Host->Client LAN sync, Waiting Scholar exclusion,
    and Client barrel prop_strike awakening The Barrel Mimic Cluster on Host."""
    host = _make_active_run_state(act=1)
    host.network_manager.network_mode = "HOST"

    # Seed Barrel Mimic Cluster on Host and strike barrel via remote Client DAMAGE_EVENT
    ev = host.marginalia_engine.seed_map_anchor(host, "barrel_mimic_cluster", act_variant=1)
    barrel = next(o for o in host.world.interactables if o.name == "Barrel")
    host.handle_remote_damage("prop", barrel.id, 10.0)
    host._process_pending_remote_actions()
    assert ev.status == "ACTIVE"
    assert host.weather_manager.paused is True
    assert len(host.enemies) == 8

    # Snapshot Host state for 20Hz UDP broadcast
    host_snapshot = host.get_local_state()
    assert host_snapshot["weather"]["paused"] is True
    assert host_snapshot["marginalia_event"]["event_id"] == "barrel_mimic_cluster"
    assert host_snapshot["marginalia_event"]["status"] == "ACTIVE"

    # 1. Active runner Client receives Marginalia event and weather.paused
    runner_client = _make_active_run_state(act=1)
    runner_client.network_manager.network_mode = "CLIENT"
    runner_client.in_sanctuary = False
    runner_client.waiting_for_host_run = False
    runner_client.apply_remote_state(("127.0.0.1", 55557), host_snapshot)
    assert runner_client.weather_manager.paused is True
    assert runner_client.marginalia_engine.active_event is not None
    assert runner_client.marginalia_engine.active_event.event_id == "barrel_mimic_cluster"

    # 2. Waiting Scholar in Sanctuary is excluded from Marginalia event & weather sync
    waiting_client = GameState(stats=StatisticsTracker(), auto_load=False)
    waiting_client.network_manager.stop_network()
    waiting_client.network_manager.network_mode = "CLIENT"
    waiting_client.in_sanctuary = True
    waiting_client.waiting_for_host_run = True
    waiting_client.apply_remote_state(("127.0.0.1", 55557), host_snapshot)
    assert waiting_client.weather_manager.paused is False
    assert waiting_client.marginalia_engine.active_event is None

    # 3. Headless Renderer draws unified Marginalia HUD banner without error
    pygame.init()
    screen = pygame.Surface((1280, 720))
    from rendering.renderer import Renderer

    renderer = Renderer(screen)
    renderer.render(runner_client)
