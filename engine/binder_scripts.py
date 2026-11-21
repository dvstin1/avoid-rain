"""
Headless Binder Scripts upgrade & syntax conflict compiler (Section 7).
Compiles equipped scripts into player stat modifiers, resolves syntax conflicts
when multiple scripts touch the same stat (stronger magnitude wins; weaker fails),
and tracks the Binder's 3-step failed-script sequence toward the Perfect Stitch.
"""
# pylint: disable=too-many-locals

from typing import Any, Dict, List, Tuple

from constants import (
    BINDER_MAX_EQUIPPED_SCRIPTS,
    BINDER_PERFECT_STITCH_SEQUENCE,
    BINDER_SCRIPTS_BY_ID,
    BINDER_SCRIPT_CATALOG,
    BINDER_STITCH_STEP_LABELS,
    DIALOGUE_MANIFEST,
)

STAT_KEYS: Tuple[str, ...] = ("max_hp", "attack", "speed", "damage_mitigation", "bleed")


def default_binder_state() -> Dict[str, Any]:
    """Return a clean default binder_scripts persistence dictionary."""
    return {
        "unlocked": [],
        "equipped": [],
        "failed_sequence": [],
        "conflicts_triggered": 0,
    }


def default_story_flags() -> Dict[str, bool]:
    """Return default story_flags persistence dictionary."""
    return {
        "perfect_stitch_completed": False,
        "ink_bleed_halted": False,
    }


def ensure_binder_persistence(stats_tracker) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Ensure margin_scraps, binder_scripts, and story_flags exist on stats_tracker.data."""
    if stats_tracker is None or not hasattr(stats_tracker, "data"):
        return default_binder_state(), default_story_flags()

    data = stats_tracker.data
    if "margin_scraps" not in data or not isinstance(data.get("margin_scraps"), (int, float)):
        data["margin_scraps"] = 0
    else:
        data["margin_scraps"] = max(0, int(data["margin_scraps"]))

    raw_bs = data.get("binder_scripts")
    if not isinstance(raw_bs, dict):
        raw_bs = default_binder_state()
        data["binder_scripts"] = raw_bs
    else:
        for k, default_val in default_binder_state().items():
            if k not in raw_bs or not isinstance(raw_bs[k], type(default_val)):
                raw_bs[k] = list(default_val) if isinstance(default_val, list) else default_val

    raw_flags = data.get("story_flags")
    if not isinstance(raw_flags, dict):
        raw_flags = default_story_flags()
        data["story_flags"] = raw_flags
    else:
        for k, default_val in default_story_flags().items():
            if k not in raw_flags:
                raw_flags[k] = default_val

    return raw_bs, raw_flags


def compile_binder_scripts(equipped_ids: List[str]) -> Dict[str, Any]:
    """Compile an ordered list of equipped script IDs into active modifiers and syntax conflicts.

    Rule: When multiple equipped scripts target the same stat, a syntax conflict occurs.
    The script with the strictly highest magnitude wins (ties broken by later slot order);
    all overridden scripts on that stat are marked CONFLICTED and contribute 0.
    """
    modifiers: Dict[str, float] = {k: 0.0 for k in STAT_KEYS}
    valid_specs: List[Tuple[int, Dict[str, Any]]] = []
    seen_ids = set()

    for slot_idx, sid in enumerate(equipped_ids or []):
        if sid in seen_ids:
            continue
        spec = BINDER_SCRIPTS_BY_ID.get(sid)
        if spec is not None:
            seen_ids.add(sid)
            valid_specs.append((slot_idx, spec))

    by_stat: Dict[str, List[Tuple[int, Dict[str, Any]]]] = {}
    for slot_idx, spec in valid_specs:
        by_stat.setdefault(spec["stat"], []).append((slot_idx, spec))

    winners_by_stat: Dict[str, Dict[str, Any]] = {}
    for stat_key, group in by_stat.items():
        # Higher magnitude wins; ties broken by later slot index
        winner_slot, winner_spec = max(group, key=lambda item: (abs(float(item[1]["value"])), item[0]))
        del winner_slot
        winners_by_stat[stat_key] = winner_spec
        modifiers[stat_key] = float(winner_spec["value"])

    entries: List[Dict[str, Any]] = []
    conflicts: List[Dict[str, Any]] = []

    for _, spec in valid_specs:
        stat_key = spec["stat"]
        winner = winners_by_stat[stat_key]
        if winner["id"] == spec["id"]:
            entries.append(
                {
                    "id": spec["id"],
                    "name": spec["name"],
                    "stat": stat_key,
                    "value": float(spec["value"]),
                    "effective_value": float(spec["value"]),
                    "status": "ACTIVE",
                    "overridden_by": None,
                }
            )
        else:
            conflict_entry = {
                "id": spec["id"],
                "name": spec["name"],
                "stat": stat_key,
                "value": float(spec["value"]),
                "effective_value": 0.0,
                "status": "CONFLICTED",
                "overridden_by": winner["id"],
                "overridden_by_name": winner["name"],
            }
            entries.append(conflict_entry)
            conflicts.append(conflict_entry)

    return {
        "modifiers": modifiers,
        "entries": entries,
        "conflicts": conflicts,
    }


def record_syntax_conflicts(
    binder_state: Dict[str, Any],
    story_flags: Dict[str, Any],
    compilation: Dict[str, Any],
) -> bool:
    """Advance the Binder's required failed-script sequence when syntax conflicts occur.

    Returns True if this compilation newly completed or already completed the Perfect Stitch.
    """
    conflicts = compilation.get("conflicts", [])
    if not conflicts:
        return bool(story_flags.get("perfect_stitch_completed", False))

    seq: List[str] = list(binder_state.get("failed_sequence") or [])
    required = list(BINDER_PERFECT_STITCH_SEQUENCE)

    for conf in conflicts:
        stat_key = conf.get("stat")
        next_idx = len(seq)
        if next_idx < len(required) and stat_key == required[next_idx]:
            seq.append(stat_key)
            binder_state["conflicts_triggered"] = int(binder_state.get("conflicts_triggered", 0)) + 1

    binder_state["failed_sequence"] = seq
    if len(seq) >= len(required):
        story_flags["perfect_stitch_completed"] = True
    return bool(story_flags.get("perfect_stitch_completed", False))


def format_stitch_sequence_progress(binder_state: Dict[str, Any], story_flags: Dict[str, Any]) -> str:
    """Return a concise UI status string for the 3-step Perfect Stitch sequence."""
    if story_flags.get("perfect_stitch_completed", False):
        return "PERFECT STITCH COMPLETE — DEFEAT THE FINAL AUTHOR TO HALT THE BLEED"

    seq = list(binder_state.get("failed_sequence") or [])
    parts = []
    for idx, stat_key in enumerate(BINDER_PERFECT_STITCH_SEQUENCE):
        label = BINDER_STITCH_STEP_LABELS.get(stat_key, stat_key)
        done = idx < len(seq) and seq[idx] == stat_key
        parts.append(f"[{'X' if done else ' '}] {idx + 1}. {label}")
    return "Stitch Sequence: " + "  ->  ".join(parts)


def weave_script(stats_tracker, script_id: str) -> Tuple[bool, str]:
    """Spend margin_scraps to unlock a Binder Script in stats_tracker."""
    spec = BINDER_SCRIPTS_BY_ID.get(script_id)
    if spec is None:
        return False, "Unknown script."
    binder_state, _ = ensure_binder_persistence(stats_tracker)
    unlocked = binder_state["unlocked"]
    if script_id in unlocked:
        return False, f"{spec['name']} is already woven."

    scraps = int(stats_tracker.data.get("margin_scraps", 0))
    cost = int(spec["cost"])
    if scraps < cost:
        return False, f"Need {cost} Margin Scraps (have {scraps})."

    stats_tracker.data["margin_scraps"] = scraps - cost
    unlocked.append(script_id)
    return True, f"Wove {spec['name']} (-{cost} Margin Scraps)."


def toggle_equip_script(
    stats_tracker,
    player,
    script_id: str,
    in_sanctuary: bool = True,
) -> Tuple[bool, str, Dict[str, Any]]:
    """Equip or unequip an unlocked script, compile syntax conflicts, and update player stats."""
    spec = BINDER_SCRIPTS_BY_ID.get(script_id)
    binder_state, story_flags = ensure_binder_persistence(stats_tracker)
    equipped: List[str] = binder_state["equipped"]

    if spec is None:
        comp = compile_binder_scripts(equipped)
        return False, "Unknown script.", comp

    if script_id not in binder_state["unlocked"]:
        comp = compile_binder_scripts(equipped)
        return False, f"{spec['name']} must be woven first.", comp

    if script_id in equipped:
        equipped.remove(script_id)
        action_msg = f"Unstitched {spec['name']}."
    else:
        if len(equipped) >= BINDER_MAX_EQUIPPED_SCRIPTS:
            comp = compile_binder_scripts(equipped)
            return False, f"Frame full (max {BINDER_MAX_EQUIPPED_SCRIPTS} scripts).", comp
        equipped.append(script_id)
        action_msg = f"Stitched {spec['name']} into frame."

    comp = compile_binder_scripts(equipped)
    was_complete = bool(story_flags.get("perfect_stitch_completed", False))
    now_complete = record_syntax_conflicts(binder_state, story_flags, comp)

    if player is not None and hasattr(player, "apply_script_modifiers"):
        player.apply_script_modifiers(comp["modifiers"], refill_in_sanctuary=in_sanctuary)

    if comp["conflicts"]:
        c0 = comp["conflicts"][-1]
        action_msg += f" SYNTAX CONFLICT: {c0['overridden_by_name']} overrides {c0['name']}!"
    if now_complete and not was_complete:
        action_msg = "PERFECT STITCH COMPLETED! The counter-manuscript is ready for The Final Author."

    return True, action_msg, comp


def select_binder_dialogue_node(stats_tracker) -> Dict[str, Any]:
    """Select the highest-priority Binder dialogue node matching current stats & story_flags."""
    manifest = DIALOGUE_MANIFEST.get("binder", [])
    last_result = "INIT"
    story_flags: Dict[str, Any] = {}
    if stats_tracker is not None and hasattr(stats_tracker, "data"):
        _, story_flags = ensure_binder_persistence(stats_tracker)
        last_result = stats_tracker.data.get("last_run_result", "INIT")

    valid_nodes = []
    for node in manifest:
        conditions = node.get("conditions", {})
        match = True
        for key, value in conditions.items():
            if key == "last_run_result":
                if last_result != value:
                    match = False
                    break
            elif story_flags.get(key) != value:
                match = False
                break
        if match:
            valid_nodes.append(node)

    if not valid_nodes:
        return {
            "id": "binder_default",
            "emotion": "neutral",
            "text": "Bring me Margin Scraps and we shall stitch your frame.",
        }
    valid_nodes.sort(key=lambda n: int(n.get("priority", 0)), reverse=True)
    return valid_nodes[0]


def get_catalog_view(stats_tracker) -> List[Dict[str, Any]]:
    """Build an ordered view of all catalog scripts with unlocked/equipped/conflict status."""
    binder_state, _ = ensure_binder_persistence(stats_tracker)
    unlocked = set(binder_state.get("unlocked") or [])
    equipped = list(binder_state.get("equipped") or [])
    comp = compile_binder_scripts(equipped)
    status_by_id = {entry["id"]: entry for entry in comp["entries"]}

    rows: List[Dict[str, Any]] = []
    for spec in BINDER_SCRIPT_CATALOG:
        sid = spec["id"]
        is_unlocked = sid in unlocked
        is_equipped = sid in equipped
        compiled_entry = status_by_id.get(sid)
        rows.append(
            {
                "id": sid,
                "name": spec["name"],
                "stat": spec["stat"],
                "value": spec["value"],
                "cost": spec["cost"],
                "summary": spec["summary"],
                "desc": spec["desc"],
                "unlocked": is_unlocked,
                "equipped": is_equipped,
                "compile_status": compiled_entry["status"] if compiled_entry else None,
                "overridden_by_name": compiled_entry.get("overridden_by_name") if compiled_entry else None,
            }
        )
    return rows
