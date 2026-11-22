"""
Headless Marginalia Event Engine (Section 10).
Manages per-Act event rolls, spatial/trigger modes, weather locking,
ReturnAnchor pocket sub-arenas, and LAN co-op state serialization.
"""
# pylint: disable=too-many-lines,too-many-instance-attributes,too-many-branches
# pylint: disable=too-many-statements,too-many-arguments,too-many-positional-arguments
# pylint: disable=import-outside-toplevel,broad-exception-caught,too-many-locals,too-many-return-statements

from __future__ import annotations

import math
import random
from typing import Any, Dict, Optional, Set, Tuple, Union

from constants import (
    ACT2_DAMAGE_MULTIPLIER,
    ACT2_HP_MULTIPLIER,
    FLASK_MAX_CHARGES,
    MARGINALIA_ATTACK_SPEED_BUFF_DURATION,
    MARGINALIA_BANNER_HOLD_DURATION,
    MARGINALIA_CELLAR_GRID_SIZE,
    MARGINALIA_CENSOR_HUNT_DURATION,
    MARGINALIA_CENSORED_DURATION,
    MARGINALIA_CENSORED_RADIUS_ACT1,
    MARGINALIA_CENSORED_RADIUS_MIN_ACT2,
    MARGINALIA_CENSORED_TARGET_CHARGE,
    MARGINALIA_DEBUFF_DURATION,
    MARGINALIA_DUEL_DURATION,
    MARGINALIA_DUEL_RADIUS,
    MARGINALIA_ERRATA_DIST,
    MARGINALIA_ERRATA_DURATION,
    MARGINALIA_FOLIO_DURATION,
    MARGINALIA_FOLIO_RADIUS,
    MARGINALIA_MAX_STEP_IDX,
    MARGINALIA_PRISTINE_SHIELD_DURATION,
    MARGINALIA_STORM_IMMUNITY_DURATION,
    MARGINALIA_TOLL_DURATION,
    MARGINALIA_TRIGGER_CHANCE,
    MARGINALIA_UNBLOTTED_WEIGHT,
    MARGINALIA_VIGNETTE_DURATION,
    MAX_ACTS,
    TILE_EMPTY,
    TILE_SIZE,
    TILE_WALL,
)
from engine.physics import check_aabb_collision


MARGINALIA_EVENT_CATALOG: Dict[str, Dict[str, Any]] = {
    "unbound_folio": {
        "title": "The Unbound Folio",
        "spatial_mode": "local",
        "trigger_mode": "auto_safe_zone",
        "weight": (1.0 - MARGINALIA_UNBLOTTED_WEIGHT) / 8.0,
    },
    "running_errata": {
        "title": "The Running Errata",
        "spatial_mode": "local",
        "trigger_mode": "auto_safe_zone",
        "weight": (1.0 - MARGINALIA_UNBLOTTED_WEIGHT) / 8.0,
    },
    "censored_passage": {
        "title": "The Censored Passage",
        "spatial_mode": "local",
        "trigger_mode": "auto_safe_zone",
        "weight": (1.0 - MARGINALIA_UNBLOTTED_WEIGHT) / 8.0,
    },
    "palimpsest_duel": {
        "title": "The Palimpsest Duel",
        "spatial_mode": "local",
        "trigger_mode": "auto_safe_zone",
        "weight": (1.0 - MARGINALIA_UNBLOTTED_WEIGHT) / 8.0,
    },
    "margin_toll": {
        "title": "The Margin Toll",
        "spatial_mode": "local",
        "trigger_mode": "auto_safe_zone",
        "weight": (1.0 - MARGINALIA_UNBLOTTED_WEIGHT) / 8.0,
    },
    "barrel_mimic_cluster": {
        "title": "The Barrel Mimic Cluster",
        "spatial_mode": "map_anchor",
        "trigger_mode": "prop_strike",
        "weight": (1.0 - MARGINALIA_UNBLOTTED_WEIGHT) / 8.0,
    },
    "sunken_margin": {
        "title": "The Sunken Margin",
        "spatial_mode": "map_anchor",
        "trigger_mode": "pitfall_warp",
        "weight": (1.0 - MARGINALIA_UNBLOTTED_WEIGHT) / 8.0,
    },
    "relentless_censor": {
        "title": "The Relentless Censor",
        "spatial_mode": "global_pursuit",
        "trigger_mode": "hunt_timer",
        "weight": (1.0 - MARGINALIA_UNBLOTTED_WEIGHT) / 8.0,
    },
    "unblotted_margin": {
        "title": "The Unblotted Margin",
        "spatial_mode": "local",
        "trigger_mode": "auto_safe_zone",
        "weight": MARGINALIA_UNBLOTTED_WEIGHT,
    },
}


def adjust_torn_pages(state: Any, delta: int) -> int:
    """Mutate the active run's single Torn Pages pool, clamped at >= 0."""
    if not getattr(state, "stats", None):
        return 0
    lifetime = state.stats.data.setdefault("lifetime_stats", {})
    current = int(lifetime.get("pages_collected", 0))
    updated = max(0, current + int(delta))
    lifetime["pages_collected"] = updated
    return updated


def build_full_cradle_weapon_data(player: Any, rng: Optional[random.Random] = None) -> Dict[str, Any]:
    """Build a weapon reward dictionary obeying the two-slot Full-Cradle Rule."""
    chooser = rng or random
    weapons = getattr(player, "weapons", []) if player else []
    if len(weapons) < 2:
        return {"name": "Refined Quill", "damage": 15}

    variants = [
        {
            "name": "Anomalous Ink-Bleed",
            "modifiers": {"bleed": 5.0},
            "description": "Inflicts ink-bleed, dealing 5 damage per second on hit.",
        },
        {
            "name": "Anomalous Life-Thread",
            "modifiers": {"slow_hp_regen": 1.0},
            "description": "Slowly mends the Reader, regenerating 1 HP per second.",
        },
        {
            "name": "Anomalous Iron-Nib",
            "modifiers": {"damage_negation_on_hit": 5.0},
            "description": "Taking damage temporarily reduces next damage taken by 5.",
        },
        {
            "name": "Anomalous Stout-Draft",
            "modifiers": {"max_hp_boost": 20.0},
            "description": "Gives the Reader a small boost of +20 Max HP.",
        },
    ]
    chosen = chooser.choice(variants)
    return {
        "name": chosen["name"],
        "damage": 20 + chooser.randint(0, 10),
        "modifiers": dict(chosen["modifiers"]),
        "description": chosen["description"],
    }


def spawn_full_cradle_weapon_reward(
    state: Any, position: Tuple[float, float], rng: Optional[random.Random] = None
) -> Any:
    """Spawn a WeaponPickup in the world obeying the two-slot Full-Cradle Rule."""
    from engine.world import WeaponPickup

    weapon_data = build_full_cradle_weapon_data(getattr(state, "player", None), rng=rng)
    pickup = WeaponPickup(position, weapon_data)
    pickup.id = f"marginalia_wpn:{int(position[0])},{int(position[1])}"
    if getattr(state, "world", None) is not None:
        state.world.interactables.append(pickup)
    return pickup


class MarginaliaEvent:
    """Shared state contract for a single Marginalia event instance."""

    def __init__(
        self,
        event_id: str,
        act_variant: int = 1,
        trigger_mode: Optional[str] = None,
        spatial_mode: Optional[str] = None,
        time_remaining: Optional[float] = None,
        progress: Union[float, Tuple[int, int]] = 0.0,
        status: str = "PENDING",
    ) -> None:
        meta = MARGINALIA_EVENT_CATALOG.get(event_id, {})
        self.event_id: str = str(event_id)
        self.act_number: int = max(1, min(MAX_ACTS, int(act_variant or 1)))
        self.act_variant: int = 2 if self.act_number >= 2 else 1
        self.trigger_mode: str = trigger_mode or str(meta.get("trigger_mode", "auto_safe_zone"))
        self.spatial_mode: str = spatial_mode or str(meta.get("spatial_mode", "local"))
        self.time_remaining: Optional[float] = (
            float(time_remaining) if time_remaining is not None else None
        )
        self.progress: Union[float, Tuple[int, int]] = progress
        self.status: str = str(status)

        base_title = str(meta.get("title", event_id.replace("_", " ").title()))
        if self.event_id == "unblotted_margin":
            sub = "A Clear Footnote" if self.act_variant == 1 else "The Author's Grace"
            self.title: str = f"{base_title}: {sub}"
        elif self.event_id == "sunken_margin":
            self.title = "The Sunken Margin: Ink Well Cellar"
        else:
            self.title = base_title

        self.zone_center: Optional[Tuple[float, float]] = None
        self.zone_radius: float = 0.0
        self.anchor_id: Optional[str] = None
        self.anchored_prop_ids: Set[str] = set()
        self.spawned_enemy_ids: Set[int] = set()
        self.spawned_seal_ids: Set[str] = set()
        self.wave_idx: int = 0
        self.total_waves: int = 0
        self.total_targets: int = 0
        self.shattered_seals: int = 0
        self.wisp_pos: Optional[Tuple[float, float]] = None
        self.wisp_target: Optional[Tuple[float, float]] = None
        self.wisp_start: Optional[Tuple[float, float]] = None
        self.wisp_hp: float = 60.0
        self.cleanse_charge: float = 0.0
        self.banner_hold_timer: float = 0.0
        self.in_pocket_arena: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Serialize compact event state for LAN co-op sync and HUD rendering."""
        prog_val: Any = self.progress
        if isinstance(prog_val, tuple):
            prog_val = [int(prog_val[0]), int(prog_val[1])]
        elif isinstance(prog_val, (int, float)):
            prog_val = round(float(prog_val), 3)
        return {
            "event_id": self.event_id,
            "title": self.title,
            "act_variant": int(self.act_variant),
            "act_number": int(self.act_number),
            "trigger_mode": self.trigger_mode,
            "spatial_mode": self.spatial_mode,
            "time_remaining": (
                round(float(self.time_remaining), 2) if self.time_remaining is not None else None
            ),
            "progress": prog_val,
            "status": self.status,
            "zone_center": (
                [round(self.zone_center[0], 1), round(self.zone_center[1], 1)]
                if self.zone_center
                else None
            ),
            "zone_radius": round(float(self.zone_radius), 1),
            "wisp_pos": (
                [round(self.wisp_pos[0], 1), round(self.wisp_pos[1], 1)]
                if self.wisp_pos
                else None
            ),
            "wisp_target": (
                [round(self.wisp_target[0], 1), round(self.wisp_target[1], 1)]
                if self.wisp_target
                else None
            ),
            "in_pocket_arena": bool(self.in_pocket_arena),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MarginaliaEvent":
        """Reconstruct a MarginaliaEvent from a network payload."""
        raw_prog = data.get("progress", 0.0)
        if isinstance(raw_prog, list) and len(raw_prog) == 2:
            progress: Union[float, Tuple[int, int]] = (int(raw_prog[0]), int(raw_prog[1]))
        else:
            progress = float(raw_prog or 0.0)
        ev = cls(
            event_id=str(data.get("event_id", "unbound_folio")),
            act_variant=int(data.get("act_number", data.get("act_variant", 1))),
            trigger_mode=data.get("trigger_mode"),
            spatial_mode=data.get("spatial_mode"),
            time_remaining=data.get("time_remaining"),
            progress=progress,
            status=str(data.get("status", "ACTIVE")),
        )
        if data.get("title"):
            ev.title = str(data["title"])
        zc = data.get("zone_center")
        if isinstance(zc, (list, tuple)) and len(zc) == 2:
            ev.zone_center = (float(zc[0]), float(zc[1]))
        ev.zone_radius = float(data.get("zone_radius", 0.0))
        wp = data.get("wisp_pos")
        if isinstance(wp, (list, tuple)) and len(wp) == 2:
            ev.wisp_pos = (float(wp[0]), float(wp[1]))
        wt = data.get("wisp_target")
        if isinstance(wt, (list, tuple)) and len(wt) == 2:
            ev.wisp_target = (float(wt[0]), float(wt[1]))
        ev.in_pocket_arena = bool(data.get("in_pocket_arena", False))
        return ev


class MarginaliaEventEngine:
    """Coordinates Marginalia event rolls, lifecycle updates, and LAN synchronization."""

    def __init__(
        self,
        rng: Optional[random.Random] = None,
        trigger_chance: float = MARGINALIA_TRIGGER_CHANCE,
    ) -> None:
        self.rng: random.Random = rng or random.Random()
        self.trigger_chance: float = float(trigger_chance)
        self.active_event: Optional[MarginaliaEvent] = None
        self.rolled_acts: Set[int] = set()
        self.triggered_acts: Set[int] = set()
        self.consumed_anchors: Set[Tuple[int, str]] = set()
        self._next_net_id: int = 7000
        self._last_client_arena_state: Optional[str] = None

    def reset(self, state: Optional[Any] = None) -> None:
        """Clear all Marginalia state, consumed anchors, and restore weather pause = False."""
        self.active_event = None
        self.rolled_acts.clear()
        self.triggered_acts.clear()
        self.consumed_anchors.clear()
        self._last_client_arena_state = None
        if state is not None:
            if hasattr(state, "weather_manager") and state.weather_manager is not None:
                state.weather_manager.paused = False
            if hasattr(state, "return_anchor_stack"):
                state.return_anchor_stack.clear()
            if hasattr(state, "player_breadcrumbs"):
                state.player_breadcrumbs.clear()
            if hasattr(state, "ink_mist_vignette_timer"):
                state.ink_mist_vignette_timer = 0.0

    def _allocate_enemy_net_id(self) -> int:
        nid = self._next_net_id
        self._next_net_id += 1
        return nid

    @staticmethod
    def is_within_trigger_window(state: Any) -> bool:
        """Return True if weather is before the second contraction and not in Boss/Dilution."""
        wm = getattr(state, "weather_manager", None)
        if wm is None:
            return False
        if getattr(wm, "current_step_idx", 0) >= MARGINALIA_MAX_STEP_IDX:
            return False
        if getattr(wm, "bleed_state", "") in ("BOSS_PHASE", "DILUTION", "CLAMPED", "APPENDIX"):
            return False
        return True

    def can_trigger_event(self, state: Any, allow_pending: bool = False) -> bool:
        """Check whether an event is eligible to roll/activate in the current Act."""
        if getattr(state, "in_sanctuary", False):
            return False
        world_name = getattr(getattr(state, "world", None), "name", "sanctuary")
        if world_name in ("sanctuary", "final_boss", "night_boss_arena"):
            return False
        if not self.is_within_trigger_window(state):
            return False
        act = int(getattr(state, "current_act", 0) or 1)
        if not allow_pending and act in self.triggered_acts:
            return False
        return True

    def choose_weighted_event_id(self) -> str:
        """Pick one event ID from the 9-event catalog using canonical weights."""
        items = list(MARGINALIA_EVENT_CATALOG.items())
        total = sum(float(meta["weight"]) for _, meta in items)
        pick = self.rng.random() * total
        acc = 0.0
        for event_id, meta in items:
            acc += float(meta["weight"])
            if pick <= acc:
                return event_id
        return items[-1][0]

    def try_roll_for_act(self, state: Any, force_act: Optional[int] = None) -> Optional[MarginaliaEvent]:
        """Perform the once-per-Act 20% Marginalia roll if eligible (Acts 1..MAX_ACTS)."""
        act = int(force_act if force_act is not None else (getattr(state, "current_act", 0) or 1))
        if not 1 <= act <= MAX_ACTS:
            return None
        if act in self.rolled_acts or act in self.triggered_acts:
            return None
        if not self.can_trigger_event(state):
            return None

        self.rolled_acts.add(act)
        forced_id = getattr(state, "forced_marginalia_event_id", None)
        if forced_id and forced_id in MARGINALIA_EVENT_CATALOG:
            chosen_id = str(forced_id)
            meta = MARGINALIA_EVENT_CATALOG[chosen_id]
            if meta["spatial_mode"] == "map_anchor":
                ev = self.seed_map_anchor(state, chosen_id, act_variant=act)
            else:
                ev = self.start_event(state, chosen_id, act_variant=act)
            if ev is not None:
                state.forced_marginalia_event_id = None
            return ev

        roll = self.rng.random()
        if roll >= self.trigger_chance:
            return None

        chosen_id = self.choose_weighted_event_id()
        meta = MARGINALIA_EVENT_CATALOG[chosen_id]
        if meta["spatial_mode"] == "map_anchor":
            return self.seed_map_anchor(state, chosen_id, act_variant=act)
        return self.start_event(state, chosen_id, act_variant=act)

    def seed_map_anchor(
        self, state: Any, event_id: str, act_variant: Optional[int] = None
    ) -> Optional[MarginaliaEvent]:
        """Seed a PENDING map_anchor event (Barrel Mimic Cluster or Sunken Margin Pitfall)."""
        if not self.can_trigger_event(state, allow_pending=True):
            return None
        act_num = int(act_variant if act_variant is not None else (getattr(state, "current_act", 0) or 1))
        act_num = max(1, min(MAX_ACTS, act_num))
        anchor_id = f"{event_id}:act{act_num}"
        if (act_num, anchor_id) in self.consumed_anchors:
            return None

        ev = MarginaliaEvent(event_id=event_id, act_variant=act_num, status="PENDING")
        ev.anchor_id = anchor_id
        px, py = state.player.get_center() if getattr(state, "player", None) else (400.0, 400.0)

        if event_id == "barrel_mimic_cluster":
            total_mimics = 8 if ev.act_variant == 1 else 12
            ev.total_targets = total_mimics
            ev.progress = (0, total_mimics)
            barrels = [
                obj for obj in getattr(state.world, "interactables", []) if obj.name == "Barrel"
            ]
            if not barrels and getattr(state, "world", None) is not None:
                from engine.world import GameObject

                for idx in range(3):
                    b_obj = GameObject((px + 80 + idx * 40, py), (TILE_SIZE, TILE_SIZE))
                    b_obj.is_solid = True
                    b_obj.is_breakable = True
                    b_obj.health = 1.0
                    b_obj.name = "Barrel"
                    b_obj.id = f"mimic_barrel:{act_num}:{idx}"
                    state.world.interactables.append(b_obj)
                    barrels.append(b_obj)
            for b_obj in barrels[:8]:
                ev.anchored_prop_ids.add(str(getattr(b_obj, "id", id(b_obj))))
        elif event_id == "sunken_margin":
            from engine.world import PitfallTrigger

            total_cellar = 4 if ev.act_variant == 1 else 6
            ev.total_targets = total_cellar
            ev.progress = (0, total_cellar)
            if getattr(state, "world", None) is not None:
                existing = [
                    obj
                    for obj in state.world.interactables
                    if getattr(obj, "name", "") == "Suspicious Leaf Pile"
                ]
                if not existing:
                    trigger = PitfallTrigger((px + 80.0, py), anchor_id=anchor_id)
                    state.world.interactables.append(trigger)

        self.active_event = ev
        self.triggered_acts.add(act_num)
        return ev

    def start_event(
        self,
        state: Any,
        event_id: str,
        act_variant: Optional[int] = None,
        ignore_window: bool = False,
    ) -> Optional[MarginaliaEvent]:
        """Start any of the 9 Marginalia events in Acts 1..MAX_ACTS."""
        if not ignore_window and not self.can_trigger_event(state, allow_pending=True):
            return None

        act_num = int(act_variant if act_variant is not None else (getattr(state, "current_act", 0) or 1))
        act_num = max(1, min(MAX_ACTS, act_num))
        self.rolled_acts.add(act_num)
        self.triggered_acts.add(act_num)

        ev = MarginaliaEvent(event_id=event_id, act_variant=act_num, status="ACTIVE")
        act = ev.act_variant
        px, py = state.player.get_center() if getattr(state, "player", None) else (400.0, 400.0)
        ev.zone_center = (px, py)
        self.active_event = ev

        if event_id == "unblotted_margin":
            ev.progress = 1.0
            ev.time_remaining = None
            self._apply_unblotted_margin_boon(state, ev)
            self._complete_event(state, ev, already_rewarded=True)
            return ev

        # Lock weather for all active combat/timed Marginalia events
        if hasattr(state, "weather_manager") and state.weather_manager is not None:
            state.weather_manager.paused = True
        if getattr(state, "player", None) is not None:
            state.player.is_exposed = False

        if event_id == "unbound_folio":
            ev.time_remaining = MARGINALIA_FOLIO_DURATION
            ev.zone_radius = MARGINALIA_FOLIO_RADIUS
            ev.total_waves = 2 if act == 1 else 3
            ev.wave_idx = 0
            ev.progress = (0, ev.total_waves)
            self._spawn_folio_wave(state, ev, wave_num=1)

        elif event_id == "running_errata":
            ev.time_remaining = MARGINALIA_ERRATA_DURATION
            ev.wisp_start = (px, py)
            ev.wisp_pos = (px, py)
            ev.wisp_target = (px + MARGINALIA_ERRATA_DIST, py)
            ev.wisp_hp = 60.0
            ev.progress = 0.0
            self._spawn_errata_interceptors(state, ev)

        elif event_id == "censored_passage":
            ev.time_remaining = MARGINALIA_CENSORED_DURATION
            ev.zone_radius = MARGINALIA_CENSORED_RADIUS_ACT1
            ev.cleanse_charge = 0.0
            ev.progress = 0.0
            self._spawn_censored_defenders(state, ev)

        elif event_id == "palimpsest_duel":
            ev.time_remaining = MARGINALIA_DUEL_DURATION
            ev.zone_radius = MARGINALIA_DUEL_RADIUS
            ev.total_targets = 1
            ev.progress = (0, 1)
            self._spawn_duel_challenger(state, ev)

        elif event_id == "margin_toll":
            ev.time_remaining = MARGINALIA_TOLL_DURATION
            total_seals = 3 if act == 1 else 4
            ev.total_targets = total_seals
            ev.shattered_seals = 0
            ev.progress = (0, total_seals)
            self._spawn_margin_toll_seals(state, ev, total_seals)

        elif event_id == "barrel_mimic_cluster":
            ev.time_remaining = None
            ev.anchor_id = ev.anchor_id or f"barrel_mimic_cluster:act{ev.act_number}"
            self.consumed_anchors.add((ev.act_number, ev.anchor_id))
            total_mimics = 8 if act == 1 else 12
            ev.total_targets = total_mimics
            ev.progress = (0, total_mimics)
            self._spawn_barrel_mimics(state, ev, total_mimics)

        elif event_id == "sunken_margin":
            ev.time_remaining = None
            ev.anchor_id = ev.anchor_id or f"sunken_margin:act{ev.act_number}"
            self.consumed_anchors.add((ev.act_number, ev.anchor_id))
            total_cellar = 4 if act == 1 else 6
            ev.total_targets = total_cellar
            ev.progress = (0, total_cellar)
            self._enter_pocket_cellar(state, ev, total_cellar)

        elif event_id == "relentless_censor":
            ev.time_remaining = MARGINALIA_CENSOR_HUNT_DURATION
            ev.progress = 0.0
            self._spawn_relentless_censor(state, ev)

        if hasattr(state, "trigger_bloom"):
            state.trigger_bloom(ev.title.upper(), priority=2)
        return ev

    def _spawn_enemy(
        self, state: Any, enemy_cls: Any, x: float, y: float, act: int, name: Optional[str] = None
    ) -> Any:
        enemy = enemy_cls(x, y)
        world = getattr(state, "world", None)
        if world is not None and hasattr(world, "find_nearest_walkable_spawn"):
            wx, wy = world.find_nearest_walkable_spawn(x, y, enemy.width, enemy.height)
            enemy.x, enemy.y = wx, wy
            enemy.origin_x, enemy.origin_y = wx, wy
        if name:
            enemy.name = name
        enemy.network_id = self._allocate_enemy_net_id()
        if act >= 2:
            enemy.apply_act_scaling(ACT2_HP_MULTIPLIER, ACT2_DAMAGE_MULTIPLIER)
        state.enemies.append(enemy)
        return enemy

    def _spawn_folio_wave(self, state: Any, ev: MarginaliaEvent, wave_num: int) -> None:
        from engine.enemy import BindlingEnemy, PunctuationWolfEnemy, SlugEnemy, SmearEnemy

        cx, cy = ev.zone_center or (400.0, 400.0)
        ev.spawned_enemy_ids.clear()
        if ev.act_variant == 1:
            classes = [SlugEnemy, SlugEnemy] if wave_num == 1 else [PunctuationWolfEnemy, BindlingEnemy]
        else:
            if wave_num == 1:
                classes = [PunctuationWolfEnemy, SmearEnemy]
            elif wave_num == 2:
                classes = [PunctuationWolfEnemy, PunctuationWolfEnemy, SmearEnemy]
            else:
                classes = [PunctuationWolfEnemy, SmearEnemy, BindlingEnemy]
        for idx, cls in enumerate(classes):
            ang = (2.0 * math.pi * idx) / max(1, len(classes))
            ex = cx + math.cos(ang) * 110.0
            ey = cy + math.sin(ang) * 110.0
            enemy = self._spawn_enemy(state, cls, ex, ey, ev.act_variant)
            ev.spawned_enemy_ids.add(enemy.network_id)

    def _spawn_errata_interceptors(self, state: Any, ev: MarginaliaEvent) -> None:
        from engine.enemy import BatEnemy, PunctuationWolfEnemy, SlugEnemy

        cx, cy = ev.wisp_pos or (400.0, 400.0)
        classes = [BatEnemy, SlugEnemy] if ev.act_variant == 1 else [PunctuationWolfEnemy, BatEnemy, BatEnemy]
        for idx, cls in enumerate(classes):
            enemy = self._spawn_enemy(state, cls, cx + 90.0 + idx * 35.0, cy + 50.0, ev.act_variant)
            if ev.act_variant >= 2:
                enemy.speed *= 1.2
            ev.spawned_enemy_ids.add(enemy.network_id)

    def _spawn_censored_defenders(self, state: Any, ev: MarginaliaEvent) -> None:
        from engine.enemy import BindlingEnemy, SlugEnemy

        cx, cy = ev.zone_center or (400.0, 400.0)
        for idx, cls in enumerate((SlugEnemy, BindlingEnemy)):
            enemy = self._spawn_enemy(state, cls, cx + (idx * 2 - 1) * 90.0, cy - 70.0, ev.act_variant)
            ev.spawned_enemy_ids.add(enemy.network_id)

    def _spawn_duel_challenger(self, state: Any, ev: MarginaliaEvent) -> None:
        from engine.enemy import MinibossM2

        cx, cy = ev.zone_center or (400.0, 400.0)
        name = "Overwritten Elite" if ev.act_variant == 1 else "Empowered Champion"
        challenger = self._spawn_enemy(state, MinibossM2, cx + 100.0, cy, ev.act_variant, name=name)
        challenger.loot_tier = 0
        # Suppress standard Miniboss.on_death weapon drop so Palimpsest Duel controls exact reward
        challenger.on_death = lambda _s: None
        ev.spawned_enemy_ids.add(challenger.network_id)

    def _spawn_margin_toll_seals(self, state: Any, ev: MarginaliaEvent, count: int) -> None:
        from engine.world import InkSeal

        cx, cy = ev.zone_center or (400.0, 400.0)
        ev.spawned_seal_ids.clear()
        if getattr(state, "world", None) is None:
            return
        for idx in range(count):
            ang = (2.0 * math.pi * idx) / max(1, count)
            sx = cx + math.cos(ang) * 95.0
            sy = cy + math.sin(ang) * 95.0
            seal_id = f"ink_seal:act{ev.act_variant}:{idx}"
            seal = InkSeal((sx, sy), seal_id=seal_id)
            state.world.interactables.append(seal)
            ev.spawned_seal_ids.add(seal_id)

    def _spawn_barrel_mimics(self, state: Any, ev: MarginaliaEvent, count: int) -> None:
        from engine.enemy import BindlingEnemy, SlugEnemy

        cx, cy = ev.zone_center or (400.0, 400.0)
        ev.spawned_enemy_ids.clear()
        if getattr(state, "world", None) is not None and ev.anchored_prop_ids:
            for obj in list(state.world.interactables):
                if str(getattr(obj, "id", id(obj))) in ev.anchored_prop_ids:
                    state.world.interactables.remove(obj)
        for idx in range(count):
            ang = (2.0 * math.pi * idx) / max(1, count)
            mx = cx + math.cos(ang) * 85.0
            my = cy + math.sin(ang) * 85.0
            cls = BindlingEnemy if idx % 3 == 0 else SlugEnemy
            mimic = self._spawn_enemy(state, cls, mx, my, ev.act_variant, name="Barrel Mimic")
            ev.spawned_enemy_ids.add(mimic.network_id)

    def _enter_pocket_cellar(self, state: Any, ev: MarginaliaEvent, count: int) -> None:
        from engine.enemy import BindlingEnemy, PunctuationWolfEnemy, SlugEnemy
        from engine.world import World

        if getattr(state, "world", None) is not None:
            for obj in list(state.world.interactables):
                if getattr(obj, "name", "") == "Suspicious Leaf Pile":
                    state.world.interactables.remove(obj)
            state.push_return_anchor(
                state.world.name,
                state.player.x,
                state.player.y,
                world_ref=state.world,
                enemies_ref=state.enemies,
            )

        cellar = World("ink_well_cellar")
        size = MARGINALIA_CELLAR_GRID_SIZE
        grid = []
        for y in range(size):
            row = []
            for x in range(size):
                if x == 0 or y == 0 or x == size - 1 or y == size - 1:
                    row.append(TILE_WALL)
                else:
                    row.append(TILE_EMPTY)
            grid.append(row)
        cellar.grid = grid
        spawn_px = (size // 2) * TILE_SIZE
        spawn_py = (size - 4) * TILE_SIZE
        cellar.player_start = (spawn_px, spawn_py)
        state.world = cellar
        state.enemies = []
        ev.in_pocket_arena = True
        if getattr(state, "player", None) is not None:
            state.player.x = float(spawn_px)
            state.player.y = float(spawn_py)
            state.player.is_exposed = False
        if hasattr(state, "camera") and state.camera is not None:
            state.camera.world_w = size * TILE_SIZE
            state.camera.world_h = size * TILE_SIZE
            if getattr(state, "player", None) is not None:
                state.camera.instant_center(state.player.get_center())

        ev.spawned_enemy_ids.clear()
        center_px = (size // 2) * TILE_SIZE
        center_py = (size // 2) * TILE_SIZE
        for idx in range(count):
            ang = (2.0 * math.pi * idx) / max(1, count)
            ex = center_px + math.cos(ang) * 120.0
            ey = center_py + math.sin(ang) * 120.0
            cls = PunctuationWolfEnemy if (ev.act_variant >= 2 and idx % 2 == 0) else (
                BindlingEnemy if idx % 2 == 1 else SlugEnemy
            )
            enemy = self._spawn_enemy(state, cls, ex, ey, ev.act_variant)
            ev.spawned_enemy_ids.add(enemy.network_id)
        cellar.enemies = state.enemies

    def _spawn_relentless_censor(self, state: Any, ev: MarginaliaEvent) -> None:
        from engine.enemy import MinibossM2

        cx, cy = ev.zone_center or (400.0, 400.0)
        name = "The Relentless Censor" if ev.act_variant == 1 else "Empowered Relentless Censor"
        censor = self._spawn_enemy(state, MinibossM2, cx + 180.0, cy, ev.act_variant, name=name)
        censor.persistent_pursuit = True
        censor.detect_radius = 99999.0
        censor.loot_tier = 0
        censor.on_death = lambda _s: None
        ev.spawned_enemy_ids.add(censor.network_id)

    def _apply_unblotted_margin_boon(self, state: Any, ev: MarginaliaEvent) -> None:
        from constants import UNBLOTTED_MARGIN_MITIGATION_BONUS
        player = getattr(state, "player", None)
        if player is not None:
            player.damage_mitigation = float(getattr(player, "damage_mitigation", 0.0)) + float(
                UNBLOTTED_MARGIN_MITIGATION_BONUS
            )
            if ev.act_variant >= 2:
                player.pristine_ink_shield_timer = MARGINALIA_PRISTINE_SHIELD_DURATION
        pages_bonus = 2 if ev.act_variant == 1 else 3
        adjust_torn_pages(state, pages_bonus)

    def on_prop_struck(self, state: Any, prop_obj: Any) -> bool:
        """Handle local or remote Client strikes on breakable props (Barrel Mimics & Ink Seals)."""
        ev = self.active_event
        if ev is None:
            return False

        prop_id = str(getattr(prop_obj, "id", id(prop_obj)))
        prop_name = getattr(prop_obj, "name", "")

        # 1. Pending Barrel Mimic Cluster awakening on barrel strike
        if (
            ev.event_id == "barrel_mimic_cluster"
            and ev.status == "PENDING"
            and prop_name == "Barrel"
        ):
            anchor_key = (ev.act_number, ev.anchor_id or f"barrel_mimic_cluster:act{ev.act_number}")
            if anchor_key in self.consumed_anchors:
                return False
            if not self.is_within_trigger_window(state):
                return False
            if not ev.anchored_prop_ids or prop_id in ev.anchored_prop_ids:
                ev.status = "ACTIVE"
                ev.zone_center = (float(prop_obj.x), float(prop_obj.y))
                self.consumed_anchors.add(anchor_key)
                if hasattr(state, "weather_manager") and state.weather_manager is not None:
                    state.weather_manager.paused = True
                if getattr(state, "player", None) is not None:
                    state.player.is_exposed = False
                self._spawn_barrel_mimics(state, ev, ev.total_targets or (8 if ev.act_variant == 1 else 12))
                return True

        # 2. Active Margin Toll Ink Seal shattering
        if (
            ev.event_id == "margin_toll"
            and ev.status == "ACTIVE"
            and (prop_name == "Ink Seal" or prop_id in ev.spawned_seal_ids)
            and prop_obj.is_dead()
        ):
            if prop_id in ev.spawned_seal_ids:
                ev.spawned_seal_ids.discard(prop_id)
                ev.shattered_seals += 1
                ev.progress = (ev.shattered_seals, ev.total_targets)
                from engine.enemy import BatEnemy, SlugEnemy

                for idx in range(2):
                    cls = BatEnemy if idx % 2 == 0 else SlugEnemy
                    ambusher = self._spawn_enemy(
                        state, cls, float(prop_obj.x) + idx * 24.0, float(prop_obj.y), ev.act_variant
                    )
                    ev.spawned_enemy_ids.add(ambusher.network_id)
                if ev.shattered_seals >= ev.total_targets:
                    self._complete_event(state, ev)
                return True

        return False

    def trigger_pitfall_anchor(self, state: Any, trigger_obj: Optional[Any] = None) -> bool:
        """Activate a PENDING sunken_margin pitfall warp into the Ink Well Cellar."""
        ev = self.active_event
        act_num = int(getattr(state, "current_act", 0) or (ev.act_number if ev else 1))
        act_num = max(1, min(MAX_ACTS, act_num))
        anchor_id = (
            getattr(trigger_obj, "anchor_id", None)
            or (ev.anchor_id if ev else None)
            or f"sunken_margin:act{act_num}"
        )
        if (act_num, anchor_id) in self.consumed_anchors:
            return False
        if not self.is_within_trigger_window(state):
            return False

        if ev is None or ev.event_id != "sunken_margin":
            ev = MarginaliaEvent(event_id="sunken_margin", act_variant=act_num, status="PENDING")
            ev.anchor_id = anchor_id
            ev.total_targets = 4 if ev.act_variant == 1 else 6
            ev.progress = (0, ev.total_targets)
            self.active_event = ev
            self.rolled_acts.add(act_num)
            self.triggered_acts.add(act_num)

        if ev.status != "PENDING":
            return False

        ev.status = "ACTIVE"
        self.consumed_anchors.add((ev.act_number, anchor_id))
        if hasattr(state, "weather_manager") and state.weather_manager is not None:
            state.weather_manager.paused = True
        if getattr(state, "player", None) is not None:
            state.player.is_exposed = False
        self._enter_pocket_cellar(state, ev, ev.total_targets or (4 if ev.act_variant == 1 else 6))
        return True

    def on_respite_rest(self, state: Any) -> None:
        """Enforce anti-farming rule across Respite.execute_rest()."""
        act_num = int(getattr(state, "current_act", 0) or 1)
        act_num = max(1, min(MAX_ACTS, act_num))
        # Remove any pitfall triggers or mimic anchors that were already consumed in this Act
        if getattr(state, "world", None) is not None:
            for obj in list(state.world.interactables):
                if getattr(obj, "name", "") == "Suspicious Leaf Pile":
                    aid = getattr(obj, "anchor_id", f"sunken_margin:act{act_num}")
                    if (act_num, aid) in self.consumed_anchors:
                        state.world.interactables.remove(obj)

    def update(self, dt: float, state: Any) -> None:
        """Advance active Marginalia event logic or roll for the current Act."""
        if getattr(state, "in_sanctuary", False) or getattr(state, "world", None) is None:
            return
        if getattr(state.world, "name", "") == "sanctuary":
            return
        if hasattr(state, "warp_controller") and state.warp_controller and state.warp_controller.is_active():
            return

        # Record player movement breadcrumbs for persistent_pursuit hunters
        if getattr(state, "player", None) is not None and hasattr(state, "record_player_breadcrumb"):
            state.record_player_breadcrumb()

        # Tick ink-mist vignette debuff timer if active
        vig = getattr(state, "ink_mist_vignette_timer", 0.0)
        if vig > 0.0:
            state.ink_mist_vignette_timer = max(0.0, vig - dt)

        is_client = (
            hasattr(state, "network_manager")
            and state.network_manager is not None
            and state.network_manager.network_mode == "CLIENT"
        )
        if is_client:
            return

        ev = self.active_event
        if ev is None:
            if 1 <= int(getattr(state, "current_act", 0) or 0) <= MAX_ACTS:
                self.try_roll_for_act(state)
            return

        if ev.status in ("COMPLETED", "FAILED"):
            if ev.banner_hold_timer > 0.0:
                ev.banner_hold_timer = max(0.0, ev.banner_hold_timer - dt)
            return

        if ev.status == "PENDING":
            # Check if player stepped onto a PitfallTrigger for sunken_margin
            if ev.event_id == "sunken_margin" and getattr(state, "player", None) is not None:
                p_rect = state.player.rect
                for obj in list(getattr(state.world, "interactables", [])):
                    if getattr(obj, "name", "") == "Suspicious Leaf Pile" and check_aabb_collision(
                        p_rect, obj.rect
                    ):
                        self.trigger_pitfall_anchor(state, obj)
                        break
            return

        # Event is ACTIVE: maintain weather pause and exposure suppression
        if hasattr(state, "weather_manager") and state.weather_manager is not None:
            state.weather_manager.paused = True
        if getattr(state, "player", None) is not None:
            state.player.is_exposed = False

        if ev.time_remaining is not None:
            ev.time_remaining = max(0.0, ev.time_remaining - dt)

        self._update_active_event(dt, state, ev)

    def _update_active_event(self, dt: float, state: Any, ev: MarginaliaEvent) -> None:
        alive_event_enemies = [
            e for e in getattr(state, "enemies", []) if getattr(e, "network_id", -1) in ev.spawned_enemy_ids
        ]

        if ev.event_id == "unbound_folio":
            if not alive_event_enemies:
                ev.wave_idx += 1
                ev.progress = (ev.wave_idx, ev.total_waves)
                if ev.wave_idx >= ev.total_waves:
                    self._complete_event(state, ev)
                    return
                self._spawn_folio_wave(state, ev, wave_num=ev.wave_idx + 1)
            elif ev.time_remaining is not None and ev.time_remaining <= 0.0:
                self._fail_event(state, ev)

        elif ev.event_id == "running_errata":
            if ev.wisp_pos and ev.wisp_target and ev.wisp_start:
                wx, wy = ev.wisp_pos
                tx, ty = ev.wisp_target
                dx, dy = tx - wx, ty - wy
                dist = math.hypot(dx, dy)
                speed = 48.0 if not alive_event_enemies else 26.0
                if dist <= speed * dt or dist < 2.0:
                    ev.wisp_pos = (tx, ty)
                    ev.progress = 1.0
                    self._complete_event(state, ev)
                    return
                ev.wisp_pos = (wx + (dx / dist) * speed * dt, wy + (dy / dist) * speed * dt)
                total_d = math.hypot(tx - ev.wisp_start[0], ty - ev.wisp_start[1]) or 1.0
                traveled = math.hypot(ev.wisp_pos[0] - ev.wisp_start[0], ev.wisp_pos[1] - ev.wisp_start[1])
                ev.progress = min(1.0, traveled / total_d)

                for enemy in alive_event_enemies:
                    ex, ey = enemy.get_center()
                    if math.hypot(ex - ev.wisp_pos[0], ey - ev.wisp_pos[1]) <= 48.0:
                        dps = 8.0 if ev.act_variant == 1 else 12.0
                        ev.wisp_hp -= dps * dt

                if ev.wisp_hp <= 0.0 or (ev.time_remaining is not None and ev.time_remaining <= 0.0):
                    self._fail_event(state, ev)

        elif ev.event_id == "censored_passage":
            if ev.act_variant >= 2 and ev.time_remaining is not None:
                elapsed = MARGINALIA_CENSORED_DURATION - ev.time_remaining
                pulse = (math.sin(elapsed * 2.5) + 1.0) * 0.5
                ev.zone_radius = MARGINALIA_CENSORED_RADIUS_MIN_ACT2 + pulse * (
                    MARGINALIA_CENSORED_RADIUS_ACT1 - MARGINALIA_CENSORED_RADIUS_MIN_ACT2
                )
            cx, cy = ev.zone_center or (0.0, 0.0)
            px, py = state.player.get_center() if getattr(state, "player", None) else (0.0, 0.0)
            in_zone = math.hypot(px - cx, py - cy) <= ev.zone_radius
            if not in_zone and hasattr(state, "network_manager"):
                for rp in state.network_manager.remote_players.values():
                    if not rp.get("in_sanctuary", False):
                        if math.hypot((rp.get("x", 0.0) + 20.0) - cx, (rp.get("y", 0.0) + 20.0) - cy) <= ev.zone_radius:
                            in_zone = True
                            break
            if in_zone:
                ev.cleanse_charge += dt
            ev.progress = min(1.0, ev.cleanse_charge / MARGINALIA_CENSORED_TARGET_CHARGE)
            if ev.progress >= 1.0:
                self._complete_event(state, ev)
            elif ev.time_remaining is not None and ev.time_remaining <= 0.0:
                self._fail_event(state, ev)

        elif ev.event_id == "palimpsest_duel":
            if not alive_event_enemies:
                ev.progress = (1, 1)
                self._complete_event(state, ev)
                return
            cx, cy = ev.zone_center or (0.0, 0.0)
            px, py = state.player.get_center() if getattr(state, "player", None) else (0.0, 0.0)
            fled_ring = math.hypot(px - cx, py - cy) > ev.zone_radius * 1.6
            if fled_ring or (ev.time_remaining is not None and ev.time_remaining <= 0.0):
                self._fail_event(state, ev)

        elif ev.event_id == "margin_toll":
            # Also reconcile any seals removed directly from world.interactables
            if getattr(state, "world", None) is not None and ev.spawned_seal_ids:
                present_ids = {
                    str(getattr(obj, "id", id(obj))) for obj in state.world.interactables
                }
                missing = ev.spawned_seal_ids - present_ids
                if missing:
                    ev.spawned_seal_ids -= missing
                    ev.shattered_seals = ev.total_targets - len(ev.spawned_seal_ids)
                    ev.progress = (ev.shattered_seals, ev.total_targets)
            if ev.shattered_seals >= ev.total_targets:
                self._complete_event(state, ev)
            elif ev.time_remaining is not None and ev.time_remaining <= 0.0:
                self._fail_event(state, ev)

        elif ev.event_id == "barrel_mimic_cluster":
            slain = max(0, ev.total_targets - len(alive_event_enemies))
            ev.progress = (slain, ev.total_targets)
            if slain >= ev.total_targets:
                self._complete_event(state, ev)

        elif ev.event_id == "sunken_margin":
            slain = max(0, ev.total_targets - len(alive_event_enemies))
            ev.progress = (slain, ev.total_targets)
            if slain >= ev.total_targets:
                self._complete_event(state, ev)

        elif ev.event_id == "relentless_censor":
            if getattr(state, "player", None) is not None and state.player.hp <= 0.0:
                # Intercept lethal redaction hit: apply recoverable setback and banish hunter
                self._fail_event(state, ev)
                return
            if not alive_event_enemies:
                ev.progress = 1.0
                self._complete_event(state, ev, censor_slain=True)
                return
            if ev.time_remaining is not None:
                ev.progress = min(
                    1.0,
                    (MARGINALIA_CENSOR_HUNT_DURATION - ev.time_remaining) / MARGINALIA_CENSOR_HUNT_DURATION,
                )
                if ev.time_remaining <= 0.0:
                    self._complete_event(state, ev, censor_slain=False)

    def _cleanup_event_entities(self, state: Any, ev: MarginaliaEvent) -> None:
        if ev.spawned_enemy_ids and hasattr(state, "enemies"):
            state.enemies[:] = [
                e for e in state.enemies if getattr(e, "network_id", -1) not in ev.spawned_enemy_ids
            ]
        if ev.spawned_seal_ids and getattr(state, "world", None) is not None:
            state.world.interactables[:] = [
                obj
                for obj in state.world.interactables
                if str(getattr(obj, "id", id(obj))) not in ev.spawned_seal_ids
            ]
            ev.spawned_seal_ids.clear()

    def _complete_event(
        self,
        state: Any,
        ev: MarginaliaEvent,
        already_rewarded: bool = False,
        censor_slain: bool = True,
    ) -> None:
        ev.status = "COMPLETED"
        ev.banner_hold_timer = MARGINALIA_BANNER_HOLD_DURATION
        if hasattr(state, "weather_manager") and state.weather_manager is not None:
            state.weather_manager.paused = False

        player = getattr(state, "player", None)
        px, py = player.get_center() if player is not None else (ev.zone_center or (400.0, 400.0))

        from constants import SCRAPS_REWARD_MARGINALIA_EVENT
        stats_obj = getattr(state, "stats", None)
        if stats_obj is not None and hasattr(stats_obj, "add_margin_scraps"):
            stats_obj.add_margin_scraps(SCRAPS_REWARD_MARGINALIA_EVENT)
        elif stats_obj is not None and hasattr(stats_obj, "data"):
            cur_s = int(stats_obj.data.get("margin_scraps", 0))
            stats_obj.data["margin_scraps"] = cur_s + SCRAPS_REWARD_MARGINALIA_EVENT

        if already_rewarded:
            return

        if ev.event_id == "unbound_folio":
            adjust_torn_pages(state, 3 if ev.act_variant == 1 else 5)
            if player is not None:
                player.flask_charges = int(FLASK_MAX_CHARGES)
                if ev.act_variant >= 2:
                    player.attack_speed_buff_timer = MARGINALIA_ATTACK_SPEED_BUFF_DURATION

        elif ev.event_id == "running_errata":
            self._cleanup_event_entities(state, ev)
            adjust_torn_pages(state, 3 if ev.act_variant == 1 else 5)
            drop_pos = ev.wisp_pos or (px, py)
            spawn_full_cradle_weapon_reward(state, drop_pos, rng=self.rng)

        elif ev.event_id == "censored_passage":
            self._cleanup_event_entities(state, ev)
            adjust_torn_pages(state, 3 if ev.act_variant == 1 else 5)
            if player is not None:
                heal_frac = 0.50 if ev.act_variant == 1 else 0.75
                player.hp = min(float(player.max_hp), float(player.hp) + float(player.max_hp) * heal_frac)

        elif ev.event_id == "palimpsest_duel":
            self._cleanup_event_entities(state, ev)
            hp_gain = 15 if ev.act_variant == 1 else 25
            pages_gain = 4 if ev.act_variant == 1 else 6
            adjust_torn_pages(state, pages_gain)
            if player is not None:
                player.stats["max_hp_modifier"] = int(player.stats.get("max_hp_modifier", 0)) + hp_gain
                player.hp = min(float(player.max_hp), float(player.hp) + float(hp_gain))
            if ev.act_variant >= 2:
                spawn_full_cradle_weapon_reward(state, (px, py), rng=self.rng)

        elif ev.event_id == "margin_toll":
            self._cleanup_event_entities(state, ev)
            adjust_torn_pages(state, 4 if ev.act_variant == 1 else 6)
            if player is not None:
                player.storm_immunity_timer = MARGINALIA_STORM_IMMUNITY_DURATION

        elif ev.event_id == "barrel_mimic_cluster":
            adjust_torn_pages(state, 4 if ev.act_variant == 1 else 6)
            if player is not None:
                player.flask_charges = int(FLASK_MAX_CHARGES)
            spawn_full_cradle_weapon_reward(state, (px, py), rng=self.rng)
            from engine.loot import HealItem

            state.loot.append(HealItem(px + 20.0, py))

        elif ev.event_id == "sunken_margin":
            adjust_torn_pages(state, 4 if ev.act_variant == 1 else 6)
            if getattr(state, "world", None) is not None:
                from engine.world import ExitLadder

                size = MARGINALIA_CELLAR_GRID_SIZE
                ladder_pos = ((size // 2) * TILE_SIZE, (size // 2) * TILE_SIZE)
                if not any(getattr(o, "name", "") == "Exit Ladder" for o in state.world.interactables):
                    state.world.interactables.append(ExitLadder(ladder_pos))

        elif ev.event_id == "relentless_censor":
            self._cleanup_event_entities(state, ev)
            if censor_slain:
                adjust_torn_pages(state, 4 if ev.act_variant == 1 else 6)
                if player is not None:
                    player.flask_charges = int(FLASK_MAX_CHARGES)
                spawn_full_cradle_weapon_reward(state, (px, py), rng=self.rng)
            else:
                adjust_torn_pages(state, 2 if ev.act_variant == 1 else 3)
                if player is not None:
                    player.hp = min(float(player.max_hp), float(player.hp) + 30.0)

    def _fail_event(self, state: Any, ev: MarginaliaEvent) -> None:
        ev.status = "FAILED"
        ev.banner_hold_timer = MARGINALIA_BANNER_HOLD_DURATION
        self._cleanup_event_entities(state, ev)
        if hasattr(state, "weather_manager") and state.weather_manager is not None:
            state.weather_manager.paused = False

        player = getattr(state, "player", None)
        if ev.event_id == "unbound_folio":
            if player is not None:
                player.hp = max(1.0, float(player.hp) - 10.0)
                cx, cy = ev.zone_center or player.get_center()
                dx = player.x - cx
                dy = player.y - cy
                mag = math.hypot(dx, dy) or 1.0
                player.x += (dx / mag) * 48.0
                player.y += (dy / mag) * 48.0

        elif ev.event_id == "running_errata":
            if player is not None:
                player.flask_charges = max(0, int(player.flask_charges) - 1)
            if getattr(state, "world", None) is not None:
                from engine.world import GameObject

                wx, wy = ev.wisp_pos or (player.get_center() if player else (400.0, 400.0))
                for idx in range(2):
                    puddle = GameObject((wx + idx * 40.0, wy), (TILE_SIZE, TILE_SIZE))
                    puddle.is_solid = False
                    puddle.name = "Inkwell Puddle"
                    state.world.interactables.append(puddle)

        elif ev.event_id == "censored_passage":
            state.ink_mist_vignette_timer = MARGINALIA_VIGNETTE_DURATION

        elif ev.event_id == "palimpsest_duel":
            if player is not None:
                player.duel_debuff_timer = MARGINALIA_DEBUFF_DURATION

        elif ev.event_id == "margin_toll":
            penalty = 1 if ev.act_variant == 1 else 2
            adjust_torn_pages(state, -penalty)

        elif ev.event_id == "relentless_censor":
            if player is not None:
                player.hp = max(25.0, float(player.max_hp) * 0.35)
                player.flask_charges = max(0, int(player.flask_charges) - 1)
                player.duel_debuff_timer = 8.0
            state.death_timer = 0.0

    def to_network_dict(self) -> Optional[Dict[str, Any]]:
        """Return compact dict for 20Hz UDP broadcast from Host to active runner Clients."""
        if self.active_event is None:
            return None
        return self.active_event.to_dict()

    def apply_network_dict(self, state: Any, payload: Optional[Dict[str, Any]]) -> None:
        """Synchronize Marginalia event state on an active runner Client (excluding Waiting Scholars)."""
        if getattr(state, "in_sanctuary", False):
            return
        if not payload:
            if self._last_client_arena_state == "ink_well_cellar" and getattr(state, "return_anchor_stack", None):
                state.pop_return_anchor()
                self._last_client_arena_state = None
            self.active_event = None
            return

        ev = MarginaliaEvent.from_dict(payload)
        self.active_event = ev

        # Party-wide sub-arena Pitfall & Exit Ladder warp sync for sunken_margin
        if ev.in_pocket_arena and getattr(state.world, "name", "") != "ink_well_cellar":
            self._last_client_arena_state = "ink_well_cellar"
            self._enter_pocket_cellar(state, ev, count=0)
        elif not ev.in_pocket_arena and self._last_client_arena_state == "ink_well_cellar":
            self._last_client_arena_state = None
            if hasattr(state, "pop_return_anchor"):
                state.pop_return_anchor()

    def get_banner_state(self) -> Optional[Dict[str, Any]]:
        """Return banner dictionary for Renderer when an event is ACTIVE or holding completion/failure."""
        ev = self.active_event
        if ev is None:
            return None
        if ev.status == "PENDING":
            return None
        if ev.status in ("COMPLETED", "FAILED") and ev.banner_hold_timer <= 0.0 and not ev.in_pocket_arena:
            return None
        return ev.to_dict()
