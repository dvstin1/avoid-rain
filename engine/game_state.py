"""
Manages the global game state and coordinates engine components.
"""
# pylint: disable=too-many-locals,too-many-branches,too-many-statements,too-many-instance-attributes
# pylint: disable=too-many-public-methods,broad-exception-caught,multiple-statements,import-outside-toplevel
# pylint: disable=missing-function-docstring,unused-argument,redefined-outer-name,reimported,line-too-long
# pylint: disable=trailing-whitespace,C0302
from typing import Optional
import math
import queue
import threading
import time

from constants import (
    PLAYER_MAX_HP, FLASK_MAX_CHARGES,
    SCREEN_WIDTH, SCREEN_HEIGHT,
    TILE_SIZE, CAMERA_LERP_SPEED,
    INPUT_MODE_KEYBOARD, BOSS_COMBAT_TRACKS
)
from engine.player import Player, PlayerStateEnum
from engine.physics import check_aabb_collision
from engine.camera import Camera
from engine.stats import StatisticsTracker

class GameState:
    """Master state object for the game engine."""
    def __init__(
        self,
        stats: Optional[StatisticsTracker] = None,
        stats_path: Optional[str] = None,
        auto_load: bool = True
    ):
        from engine.maps import create_world
        from engine.world import LevelLoader
        self.world = create_world("sanctuary")
        self.player = Player(self.world.player_start[0], self.world.player_start[1])
        self.enemies = []
        self.loot = []
        self.fading_entities = []
        self.world_debris = []
        self.slime_pools = []
        self.damage_numbers = []
        self.defeated_miniboss_ids = set()
        self.destroyed_prop_ids = set()
        self.respite_upgrades = {1: 0, 2: 0}
        from engine.particles import GlyphSplatterManager
        self.glyph_particles = GlyphSplatterManager()
        from engine.warp_controller import InkWarpController
        self.warp_controller = InkWarpController()
        if self.player:
            self.player.alpha = 255

        # 2. Statistics tracker: prefer injected tracker; otherwise optionally auto-load
        self.stats = stats
        self.stats_path = stats_path
        if self.stats is None and auto_load:
            try:
                if stats_path is not None:
                    self.stats = StatisticsTracker.load(stats_path)
                else:
                    self.stats = StatisticsTracker.load()
            except Exception:
                self.stats = StatisticsTracker()
        
        # Hydration Rule: If we have a suspended run on the current engine revision, restore it now
        if (
            self.stats
            and getattr(self.stats, "is_revision_compatible", True)
            and self.stats.data.get("run_state")
        ):
            self.hydrate_from_disk()

        # 3. Environment and Camera
        from engine.weather import WeatherManager
        world_w = len(self.world.grid[0]) * TILE_SIZE
        world_h = len(self.world.grid) * TILE_SIZE
        self.camera = Camera(SCREEN_WIDTH, SCREEN_HEIGHT, world_w, world_h, lerp_speed=CAMERA_LERP_SPEED)
        if self.player:
            self.camera.instant_center(self.player.get_center())
        self.weather_manager = WeatherManager(boss_coords_list=getattr(self.world, 'boss_coords_list', None))
        
        # Environmental Sync State (Legacy access for Renderer)
        self.active_safe_radius = self.weather_manager.active_safe_radius
        self.bleed_state = self.weather_manager.bleed_state
        self.current_boss_coords = self.weather_manager.get_current_boss_coords()
        
        # UI and Visual State
        self.bloom_text = ""
        self.bloom_timer = 0.0
        self.bloom_priority = 0
        self.last_zone_id = None
        self.zone_cooldown_timer = 0.0
        self.sanctuary_reset_complete = False
        self.sanctuary_door_open: bool = False
        
        self.active_choice = None
        self.active_dialogue = None
        self.active_respite = None
        self.chronicle_dialog: Optional[dict] = None
        self.binder_dialog: Optional[dict] = None
        self.sync_player_binder_scripts(
            refill_in_sanctuary=(getattr(self.world, "name", "sanctuary") == "sanctuary")
        )
        from constants import DEBUG_BIOME_SELECT, MAX_ACTS
        self.debug_biome_select = DEBUG_BIOME_SELECT
        if not hasattr(self, "current_act"):
            self.current_act = 0
        if not hasattr(self, "run_biomes"):
            self.run_biomes = {f"act{i}": None for i in range(1, MAX_ACTS + 1)}
        if not hasattr(self, "act_worlds"):
            self.act_worlds = {}
        if not hasattr(self, "act1_world_data"):
            self.act1_world_data = None
        if not hasattr(self, "act2_world_data"):
            self.act2_world_data = None
        self.act_warp_target = None
        self.night_boss_spawned: bool = False
        if not hasattr(self, "empowered_act"):
            self.empowered_act = False
        self.audio_manager = None
        
        self.hit_stop_timer = 0.0
        self.shake_timer = 0.0
        self.death_timer = 0.0
        self.last_save_elapsed = 9999.0 # Start large to trigger early if needed
        self.inspect_active = False
        self.debug_text_enabled = (
            bool(self.stats.data.get("debug_text_enabled", False)) if self.stats else False
        )
        self.screen_shake_enabled = (
            bool(self.stats.data.get("screen_shake_enabled", True)) if self.stats else True
        )
        from constants import normalize_keybindings
        self.keybindings = normalize_keybindings(
            self.stats.data.get("keybindings") if self.stats else None
        )
        self.parry_effects = [] # Transient VFX sparks
        self.impact_sparks = [] # Transient combat hit sparks
        self.slash_effects = [] # Transient fading visual slash arcs
        self._player_was_attacking = False
        self._hit_sfx_played_this_attack = False
        self.local_swing_seq = 0
        self.local_hit_seq = 0
        self.local_dash_seq = 0
        self._water_step_timer = 0.0
        self.pending_remote_sfx = []
        self._remote_combat_seqs = {}
        self._last_attack_center = None
        self._last_attack_facing = None

        # 4. Input and Navigation State
        self.input_mode = INPUT_MODE_KEYBOARD
        self.input_debounce_timer = 0.0
        self.input_ratchet_latched = False
        self.menu_nav_cooldown = 0.0
        self.lobby_selection_idx = 0
        self.lobby_editing_name = False
        
        # Menu indices
        self.respite_selection_idx = 0 # 0=Rest, 1-3=Edify, 4=Finalize, 5=Close
        self.respite_marked_idx = -1 # Which one is staged for upgrade

        self._save_queue = queue.Queue(maxsize=8)
        self._save_worker_running = True
        self.saving_in_progress = False
        self._save_worker_thread = threading.Thread(target=self._save_worker, daemon=True)
        self._save_worker_thread.start()

        # Link actors to routes after everything is loaded
        LevelLoader.link_actors_to_routes(self)

        # Network Phase 2, 3 & 4: Manager Initialization
        from engine.network_manager import NetworkManager
        from constants import DEFAULT_PLAYER_NAME
        
        p_name = DEFAULT_PLAYER_NAME
        if self.stats:
            p_name = self.stats.data.get("player_name", DEFAULT_PLAYER_NAME)
            
        self.network_manager = NetworkManager(identity=p_name)
        self.network_manager.local_state_provider = self.get_local_state
        self.network_manager.remote_state_handler = self.apply_remote_state
        self.network_manager.on_disconnect_callback = self.on_network_disconnect
        self.network_manager.host_status_provider = self._get_host_status_payload
        self.network_manager.on_handshake_accepted = self._on_handshake_accepted
        self.network_manager.host_return_sanctuary_handler = self.return_party_to_sanctuary
        
        # Phase 3 Callbacks
        self.network_manager.host_map_provider = self.get_host_map_payload
        self.network_manager.host_client_state_restorer = self.host_restorer_callback
        self.network_manager.host_client_state_cacher = self.host_cacher_callback
        self.network_manager.client_restored_state_handler = self.apply_restored_state
        self.network_manager.host_damage_handler = self.handle_remote_damage
        self.network_manager.host_heal_handler = self.handle_remote_heal
        self.network_manager.host_respite_handler = self.handle_remote_respite
        
        self.cached_client_states = {} # {identity: state_dict}
        self.full_state_sync_timer = 0.0
        self.pending_remote_damage = [] # Thread-safe queue for TCP damage events
        self.pending_remote_heals = [] # Thread-safe queue for TCP heal events
        self.pending_remote_respite_actions = [] # Thread-safe queue for TCP respite events

        # Seamless LAN Co-op state
        self.online_mode = bool(self.stats.data.get("online_mode", True)) if self.stats else True
        self.in_sanctuary = getattr(self.world, "name", "") == "sanctuary"
        self.host_in_run = not self.in_sanctuary
        self.waiting_scholars = 0
        self.waiting_for_host_run = False
        self._last_host_in_run = False
        self._seen_host_in_sanctuary = self.in_sanctuary

        # Marginalia Event Engine, ReturnAnchor Warp Stack, & Breadcrumb Trail
        from engine.marginalia_events import MarginaliaEventEngine
        self.marginalia_engine = MarginaliaEventEngine()
        self.forced_marginalia_event_id: Optional[str] = None
        self.return_anchor_stack = []
        self.player_breadcrumbs = []
        self.ink_mist_vignette_timer = 0.0

    def push_return_anchor(self, map_path, x, y, world_ref=None, enemies_ref=None):
        """Push a ReturnAnchor onto the warp stack before entering a pocket sub-arena."""
        from engine.world import ReturnAnchor
        anchor = ReturnAnchor(map_path, x, y, world_ref=world_ref, enemies_ref=enemies_ref)
        self.return_anchor_stack.append(anchor)
        return anchor

    def pop_return_anchor(self):
        """Pop the top ReturnAnchor and restore the party to the saved overworld coordinates."""
        if not self.return_anchor_stack:
            return None
        anchor = self.return_anchor_stack.pop()
        if anchor.world_ref is not None:
            self.world = anchor.world_ref
            self.enemies = list(anchor.enemies_ref or [])
        else:
            from engine.maps import create_world
            self.world = create_world(anchor.map_path, defeated_ids=self.defeated_miniboss_ids)
            self.enemies = list(getattr(self.world, "enemies", []))
        if self.player is not None:
            self.player.x = float(anchor.x)
            self.player.y = float(anchor.y)
            self.player.is_exposed = False
        if hasattr(self, "camera") and getattr(self.world, "grid", None):
            self.camera.world_w = len(self.world.grid[0]) * TILE_SIZE
            self.camera.world_h = len(self.world.grid) * TILE_SIZE
            if self.player:
                self.camera.instant_center(self.player.get_center())
        if hasattr(self, "marginalia_engine") and self.marginalia_engine.active_event:
            self.marginalia_engine.active_event.in_pocket_arena = False
        if hasattr(self, "weather_manager") and self.weather_manager is not None:
            self.weather_manager.paused = False
        return anchor

    def record_player_breadcrumb(self):
        """Record a player movement breadcrumb for persistent_pursuit hunters."""
        if not self.player:
            return
        from constants import MARGINALIA_BREADCRUMB_MIN_DIST, MARGINALIA_BREADCRUMB_MAX_LEN
        cx, cy = self.player.get_center()
        if not self.player_breadcrumbs:
            self.player_breadcrumbs.append((cx, cy))
            return
        lx, ly = self.player_breadcrumbs[-1]
        if (cx - lx) ** 2 + (cy - ly) ** 2 >= MARGINALIA_BREADCRUMB_MIN_DIST ** 2:
            self.player_breadcrumbs.append((cx, cy))
            if len(self.player_breadcrumbs) > MARGINALIA_BREADCRUMB_MAX_LEN:
                del self.player_breadcrumbs[0]

    def _get_host_status_payload(self):
        """Return Host run status and waiting scholar count for TCP HANDSHAKE responses."""
        self.in_sanctuary = getattr(self.world, "name", "") == "sanctuary"
        if self.network_manager.network_mode == "HOST":
            self.host_in_run = not self.in_sanctuary
        waiting = 0
        if self.host_in_run:
            for p_info in self.network_manager.remote_players.values():
                if p_info.get("in_sanctuary", False):
                    waiting += 1
        self.waiting_scholars = waiting
        return {
            "host_in_run": bool(self.host_in_run),
            "waiting_scholars": int(self.waiting_scholars),
        }

    def _on_handshake_accepted(self, response):
        """Initialize Client staging state from the Host's TCP HANDSHAKE response."""
        host_in_run = bool(response.get("host_in_run", False))
        self.host_in_run = host_in_run
        self._last_host_in_run = host_in_run
        self.waiting_scholars = int(response.get("waiting_scholars", 0))
        self.in_sanctuary = getattr(self.world, "name", "") == "sanctuary"
        if host_in_run and self.in_sanctuary:
            self.waiting_for_host_run = True
            self._seen_host_in_sanctuary = False
            self.waiting_scholars = max(1, self.waiting_scholars)
        else:
            self.waiting_for_host_run = False
            self._seen_host_in_sanctuary = True

    def set_online_mode(self, enabled: bool, save: bool = True) -> None:
        """Toggle Online/Offline LAN mode and persist preference."""
        self.online_mode = bool(enabled)
        if self.stats is not None:
            self.stats.data["online_mode"] = self.online_mode
            if save:
                self.save_stats(wait=True)
        if not self.online_mode and hasattr(self, "network_manager"):
            self.network_manager.stop_network()

    def start_seamless_lan(self, probe_duration: float = 1.6, background: bool = False):
        """Probe LAN_PORT in Online mode: auto-join existing Host in Sanctuary or auto-promote to Host."""
        if not getattr(self, "online_mode", True):
            self.network_manager.stop_network()
            return "OFFLINE"

        world_name = getattr(self.world, "name", "sanctuary")
        if world_name != "sanctuary":
            self.in_sanctuary = False
            self.host_in_run = True
            self.network_manager.start_hosting()
            return "HOST"

        def _probe_and_connect():
            self.in_sanctuary = True
            self.network_manager.start_searching()
            deadline = time.time() + max(0.05, float(probe_duration))
            discovered_ip = None
            while time.time() < deadline:
                with self.network_manager._lock:
                    hosts = dict(self.network_manager.found_hosts)
                if hosts:
                    # Prefer lowest peer_id if multiple hosts were heard
                    peers = dict(getattr(self.network_manager, "found_host_peers", {}))
                    if peers:
                        discovered_ip = min(hosts.keys(), key=lambda ip: peers.get(ip, "~"))
                    else:
                        discovered_ip = next(iter(hosts.keys()))
                    break
                time.sleep(0.05)

            if discovered_ip and self.network_manager.connect_to_host(discovered_ip):
                full_state = self.get_full_player_state()
                self.network_manager.send_full_state(full_state)
                return "CLIENT"

            self.host_in_run = False
            self.waiting_for_host_run = False
            self.network_manager.start_hosting()
            return "HOST"

        if background:
            import threading
            threading.Thread(target=_probe_and_connect, name="SeamlessLANProbe", daemon=True).start()
            return None
        return _probe_and_connect()

    def join_host_active_run(self) -> bool:
        """Fetch the Host's active run map and warp the Sanctuary Client into the run alongside the Host."""
        if self.network_manager.network_mode != "CLIENT":
            return False
        if not self.fetch_host_map():
            return False
        self.in_sanctuary = False
        self.waiting_for_host_run = False
        if self.player and getattr(self.world, "player_start", None):
            self.player.x = float(self.world.player_start[0])
            self.player.y = float(self.world.player_start[1])
            self.player.is_exposed = False
        if hasattr(self, "weather_manager"):
            self.weather_manager.reset(boss_coords_list=getattr(self.world, "boss_coords_list", None))
        if hasattr(self, "camera") and getattr(self.world, "grid", None):
            self.camera.world_w = len(self.world.grid[0]) * TILE_SIZE
            self.camera.world_h = len(self.world.grid) * TILE_SIZE
            if self.player:
                self.camera.instant_center(self.player.get_center())
        return True

    def _warp_local_to_sanctuary(self) -> None:
        """Warp the local player instance back into Sanctuary and run purification while keeping LAN active."""
        from engine.maps import create_world
        self.world = create_world("sanctuary", defeated_ids=self.defeated_miniboss_ids)
        self.in_sanctuary = True
        self.waiting_for_host_run = False
        if self.player and getattr(self.world, "player_start", None):
            self.player.x = float(self.world.player_start[0])
            self.player.y = float(self.world.player_start[1])
        if hasattr(self, "camera") and getattr(self.world, "grid", None):
            self.camera.world_w = len(self.world.grid[0]) * TILE_SIZE
            self.camera.world_h = len(self.world.grid) * TILE_SIZE
            if self.player:
                self.camera.instant_center(self.player.get_center())
        self.enemies = []
        self.loot = []
        self.on_enter_sanctuary()

    def return_party_to_sanctuary(self) -> None:
        """Return the active run party to Sanctuary to regroup with Waiting Scholars while preserving LAN."""
        if self.network_manager.network_mode == "CLIENT":
            self.network_manager.send_return_to_sanctuary_event()
            self._warp_local_to_sanctuary()
            return
        self.host_in_run = False
        self.in_sanctuary = True
        self.waiting_scholars = 0
        self.waiting_for_host_run = False
        self._warp_local_to_sanctuary()

    def get_local_state(self):
        """Phase 2 & 4: Returns the local player state for network sync."""
        if not self.player: return {"x": 0, "y": 0, "hp": 0}
        
        self.in_sanctuary = getattr(self.world, "name", "") == "sanctuary"
        state = {
            "x": round(self.player.x, 1),
            "y": round(self.player.y, 1),
            "hp": round(self.player.hp, 1),
            "swing_seq": self.local_swing_seq,
            "hit_seq": self.local_hit_seq,
            "dash_seq": self.local_dash_seq,
            "in_sanctuary": bool(self.in_sanctuary),
        }
        
        # Phase 4: Host Authority Sync
        if self.network_manager.network_mode == "HOST":
            self.host_in_run = not self.in_sanctuary
            waiting_count = 0
            if self.host_in_run:
                for p_val in self.network_manager.remote_players.values():
                    if p_val.get("in_sanctuary", False):
                        waiting_count += 1
            self.waiting_scholars = waiting_count
            state["host_in_run"] = bool(self.host_in_run)
            state["waiting_scholars"] = int(self.waiting_scholars)
            state["weather"] = {
                "radius": round(self.weather_manager.active_safe_radius, 1),
                "state": self.weather_manager.bleed_state,
                "boss_idx": self.weather_manager.current_boss_idx,
                "paused": bool(getattr(self.weather_manager, "paused", False)),
            }
            
            state["enemies"] = [
                {
                    "id": getattr(e, "network_id", -1),
                    "name": getattr(e, "name", "Enemy"),
                    "x": round(e.x, 1), "y": round(e.y, 1), "hp": round(e.hp, 1),
                    "state": e.state.value if hasattr(e, 'state') else 0,
                    "empowered": bool(getattr(e, "is_empowered", False)),
                }
                for e in self.enemies
            ]
            
            # Optimization: Only broadcast dynamic/crucial interactables in high-frequency heartbeat
            dynamic_names = ("Appendix Warp", "Suspicious Leaf Pile", "Exit Ladder", "Ink Seal")
            state["interactables"] = [
                obj.to_dict() for obj in self.world.interactables if obj.name in dynamic_names
            ]
            state["destroyed_props"] = list(self.destroyed_prop_ids)
            state["defeated_miniboss_ids"] = list(self.defeated_miniboss_ids)
            state["current_act"] = self.current_act
            state["act_warp_target"] = self.act_warp_target
            state["empowered_act"] = bool(self.empowered_act)
            state["marginalia_event"] = (
                self.marginalia_engine.to_network_dict()
                if hasattr(self, "marginalia_engine") and self.marginalia_engine
                else None
            )
            
            # Broadcast the Host's view of all remote players AND themselves (authoritative HP)
            state["session_players"] = [
                {
                    "peer_id": self.network_manager.peer_id,
                    "identity": self.network_manager.identity,
                    "addr": "127.0.0.1",
                    "is_host": True,
                    "hp": self.player.hp,
                    "x": self.player.x,
                    "y": self.player.y,
                    "swing_seq": self.local_swing_seq,
                    "hit_seq": self.local_hit_seq,
                    "dash_seq": self.local_dash_seq,
                    "in_sanctuary": bool(self.in_sanctuary),
                }
            ]
            for peer_key, p in self.network_manager.remote_players.items():
                state["session_players"].append(
                    {
                        "peer_id": p.get("peer_id", peer_key),
                        "identity": p["identity"],
                        "addr": p.get("addr", ""),
                        "is_host": bool(p.get("is_host", False)),
                        "hp": p["hp"],
                        "x": p["x"],
                        "y": p["y"],
                        "swing_seq": p.get("swing_seq", 0),
                        "hit_seq": p.get("hit_seq", 0),
                        "dash_seq": p.get("dash_seq", 0),
                        "in_sanctuary": bool(p.get("in_sanctuary", False)),
                    }
                )
            
        return state

    def _resolve_remote_player_key(self, peer_or_id, identity=None):
        """Resolves a peer_id or legacy identity key inside remote_players."""
        if peer_or_id and peer_or_id in self.network_manager.remote_players:
            return peer_or_id
        if identity and identity in self.network_manager.remote_players:
            return identity
        target_identity = identity or peer_or_id
        if target_identity:
            for k, p_data in self.network_manager.remote_players.items():
                if p_data.get("identity") == target_identity:
                    return k
        return None

    def _get_cached_client_state(self, peer_or_id, identity=None):
        """Looks up cached client state by (identity, peer_id) with fallback to identity."""
        if identity and peer_or_id and (identity, peer_or_id) in self.cached_client_states:
            return self.cached_client_states[(identity, peer_or_id)]
        if peer_or_id and peer_or_id in self.cached_client_states:
            return self.cached_client_states[peer_or_id]
        if identity and identity in self.cached_client_states:
            return self.cached_client_states[identity]
        for key, val in self.cached_client_states.items():
            if isinstance(key, tuple) and len(key) == 2 and key[1] == peer_or_id:
                return val
        return {}

    def apply_remote_state(self, addr, data):
        """Phase 2 & 4: Handles incoming remote player state data."""
        addr_ip = addr[0] if isinstance(addr, tuple) else str(addr)
        identity = data.get("identity", "Unknown")
        peer_id = data.get("peer_id")
        peer_key = peer_id or identity
        is_self = (
            (peer_id == self.network_manager.peer_id)
            if peer_id
            else (identity == self.network_manager.identity)
        )
        if not is_self:
            if (
                peer_id
                and peer_key not in self.network_manager.remote_players
                and identity in self.network_manager.remote_players
            ):
                legacy_entry = self.network_manager.remote_players[identity]
                if not legacy_entry.get("peer_id") or legacy_entry.get("peer_id") == peer_id:
                    self.network_manager.remote_players[peer_key] = (
                        self.network_manager.remote_players.pop(identity)
                    )

            is_host_peer = bool(
                data.get("is_host", addr_ip == self.network_manager.server_address)
            )
            # Rule: Host is authoritative for HP.
            # If we are the Host, we only update remote player coordinates, not their HP.
            if self.network_manager.network_mode == "HOST":
                current = self.network_manager.remote_players.get(
                    peer_key, {"hp": float(data.get("hp", 0))}
                )
                rx = float(data.get("x", 0))
                ry = float(data.get("y", 0))
                swing_seq = int(data.get("swing_seq", 0))
                hit_seq = int(data.get("hit_seq", 0))
                dash_seq = int(data.get("dash_seq", 0))
                prev_swing = int(current.get("swing_seq", 0))
                prev_hit = int(current.get("hit_seq", 0))
                prev_dash = int(current.get("dash_seq", 0))
                if swing_seq > prev_swing:
                    self.pending_remote_sfx.append(("sword_swing.ogg", rx, ry))
                if hit_seq > prev_hit:
                    self.pending_remote_sfx.append(("sword_hit.ogg", rx, ry))
                if dash_seq > prev_dash:
                    self.pending_remote_sfx.append(("player_dash.ogg", rx, ry))
                self.network_manager.remote_players[peer_key] = {
                    "peer_id": peer_key,
                    "identity": identity,
                    "addr": addr_ip,
                    "is_host": False,
                    "x": rx,
                    "y": ry,
                    "hp": current["hp"],  # Authoritative Host-side HP
                    "swing_seq": swing_seq,
                    "hit_seq": hit_seq,
                    "dash_seq": dash_seq,
                    "in_sanctuary": bool(data.get("in_sanctuary", False)),
                    "time": time.time(),
                }
                self.in_sanctuary = getattr(self.world, "name", "") == "sanctuary"
                self.host_in_run = not self.in_sanctuary
                if self.host_in_run:
                    self.waiting_scholars = sum(
                        1 for rp in self.network_manager.remote_players.values() if rp.get("in_sanctuary", False)
                    )
                else:
                    self.waiting_scholars = 0
            else:
                self.network_manager.remote_players[peer_key] = {
                    "peer_id": peer_key,
                    "identity": identity,
                    "addr": addr_ip,
                    "is_host": is_host_peer,
                    "x": float(data.get("x", 0)),
                    "y": float(data.get("y", 0)),
                    "hp": float(data.get("hp", 0)),
                    "in_sanctuary": bool(data.get("in_sanctuary", False)),
                    "time": time.time(),
                }

        # Phase 4: Host-Authoritative Overrides (Client only)
        if self.network_manager.network_mode == "CLIENT":
            self.in_sanctuary = getattr(self.world, "name", "") == "sanctuary"
            if "waiting_scholars" in data:
                self.waiting_scholars = int(data.get("waiting_scholars", 0))
            if "host_in_run" in data:
                incoming_host_in_run = bool(data.get("host_in_run", False))
                prev_host_in_run = self._last_host_in_run
                self.host_in_run = incoming_host_in_run
                self._last_host_in_run = incoming_host_in_run
                if not incoming_host_in_run:
                    self._seen_host_in_sanctuary = True
                    self.waiting_for_host_run = False
                    if prev_host_in_run and not self.in_sanctuary:
                        self._warp_local_to_sanctuary()
                        return
                else:
                    if not prev_host_in_run and self._seen_host_in_sanctuary and self.in_sanctuary:
                        self.join_host_active_run()
                    elif self.in_sanctuary:
                        self.waiting_for_host_run = True
            # 1. Weather (only for active runner Clients, never Waiting Scholars in Sanctuary)
            w_data = data.get("weather")
            if w_data and not (self.in_sanctuary and self.waiting_for_host_run):
                self.weather_manager.active_safe_radius = float(
                    w_data.get("radius", self.weather_manager.active_safe_radius)
                )
                self.weather_manager.bleed_state = w_data.get(
                    "state", self.weather_manager.bleed_state
                )
                self.weather_manager.current_boss_idx = int(
                    w_data.get("boss_idx", self.weather_manager.current_boss_idx)
                )
                self.weather_manager.paused = bool(
                    w_data.get("paused", getattr(self.weather_manager, "paused", False))
                )
                if self.weather_manager.paused and self.player:
                    self.player.is_exposed = False

            # 2. Session Players (Authoritative HP from Host)
            session_players = data.get("session_players", [])
            for p_info in session_players:
                p_identity = p_info.get("identity")
                p_peer_id = p_info.get("peer_id")
                p_key = p_peer_id or p_identity
                is_local_player = (
                    (p_peer_id == self.network_manager.peer_id)
                    if p_peer_id
                    else (p_identity == self.network_manager.identity)
                )
                # Update our own health if the host sent it (unless already dying/dead locally)
                if is_local_player:
                    if self.player.hp > 0 and self.death_timer <= 0:
                        self.player.hp = float(p_info.get("hp", self.player.hp))
                else:
                    # Update other scholars for ghost rendering and combat audio cues
                    rx = float(p_info.get("x", 0))
                    ry = float(p_info.get("y", 0))
                    swing_seq = int(p_info.get("swing_seq", 0))
                    hit_seq = int(p_info.get("hit_seq", 0))
                    dash_seq = int(p_info.get("dash_seq", 0))
                    prev_seqs = self._remote_combat_seqs.get(p_key, (0, 0, 0))
                    prev_swing, prev_hit = prev_seqs[0], prev_seqs[1]
                    prev_dash = prev_seqs[2] if len(prev_seqs) > 2 else 0
                    if swing_seq > prev_swing:
                        self.pending_remote_sfx.append(("sword_swing.ogg", rx, ry))
                    if hit_seq > prev_hit:
                        self.pending_remote_sfx.append(("sword_hit.ogg", rx, ry))
                    if dash_seq > prev_dash:
                        self.pending_remote_sfx.append(("player_dash.ogg", rx, ry))
                    self._remote_combat_seqs[p_key] = (swing_seq, hit_seq, dash_seq)
                    is_p_host = bool(p_info.get("is_host", False))
                    p_addr = p_info.get(
                        "addr",
                        self.network_manager.server_address if is_p_host else "",
                    )
                    self.network_manager.remote_players[p_key] = {
                        "peer_id": p_key,
                        "identity": p_identity,
                        "addr": p_addr,
                        "is_host": is_p_host,
                        "x": rx,
                        "y": ry,
                        "hp": float(p_info.get("hp", 0)),
                        "in_sanctuary": bool(p_info.get("in_sanctuary", False)),
                        "time": time.time(),
                    }

            if self.in_sanctuary and self.waiting_for_host_run:
                return
            
            # 3. Enemies
            e_data_list = data.get("enemies", [])
            if e_data_list: self._sync_enemies_from_host(e_data_list)

            # 4. Interactables
            i_data_list = data.get("interactables", [])
            if i_data_list: self._sync_interactables_from_host(i_data_list)

            # 5. Props
            p_data = data.get("destroyed_props")
            if p_data: self._sync_props_from_host(p_data)

            # 6. Defeated Minibosses
            def_bosses = data.get("defeated_miniboss_ids")
            if def_bosses is not None:
                self.defeated_miniboss_ids = set(def_bosses)

            # 7. Synchronized 5-Act Warp Transitions & Act Escalation Flag
            if "empowered_act" in data:
                self.empowered_act = bool(data.get("empowered_act", False))
            if "marginalia_event" in data and hasattr(self, "marginalia_engine"):
                self.marginalia_engine.apply_network_dict(self, data.get("marginalia_event"))
            remote_warp = data.get("act_warp_target")
            if (
                isinstance(remote_warp, str)
                and remote_warp.startswith("act")
                and remote_warp[3:].isdigit()
            ):
                target_act = int(remote_warp[3:])
                has_target_world = (
                    target_act in getattr(self, "act_worlds", {})
                    or (target_act == 2 and self.act2_world_data is not None)
                )
                if self.current_act < target_act and has_target_world:
                    if not (hasattr(self, 'warp_controller') and self.warp_controller.is_active()):
                        self.start_warp(
                            remote_warp,
                            callback=lambda gs, a=target_act: gs.transition_to_act(a),
                            confirmed=True,
                        )
            elif remote_warp == "night_boss_arena" and getattr(self.world, 'name', '') != "night_boss_arena":
                if not (hasattr(self, 'warp_controller') and self.warp_controller.is_active()):
                    self.start_warp("night_boss_arena", confirmed=True)


    def _sync_enemies_from_host(self, enemy_data_list):
        remote_enemies = {int(e_data["id"]): e_data for e_data in enemy_data_list if "id" in e_data}
        local_net_ids = [getattr(e, 'network_id', -1) for e in self.enemies]
        
        # 1. Update/Remove existing
        for enemy in self.enemies[:]:
            net_id = getattr(enemy, "network_id", -1)
            if net_id in remote_enemies:
                e_data = remote_enemies[net_id]
                enemy.x = float(e_data.get("x", enemy.x))
                enemy.y = float(e_data.get("y", enemy.y))
                enemy.hp = float(e_data.get("hp", enemy.hp))
                enemy.is_empowered = bool(e_data.get("empowered", getattr(self, "empowered_act", False)))
                
                # Sync visual state for animations
                if "state" in e_data:
                    from engine.actor import ActorState
                    prev_state = enemy.state
                    try:
                        enemy.state = ActorState(e_data["state"])
                    except ValueError:
                        pass
                    if enemy.name == "Punctuation Wolf" and enemy.state != prev_state:
                        if enemy.state == ActorState.WIND_UP:
                            self.pending_remote_sfx.append(("wolf_telegraph.ogg", enemy.x, enemy.y))
                        elif enemy.state == ActorState.STRIKE:
                            self.pending_remote_sfx.append(("wolf_attack.ogg", enemy.x, enemy.y))
            else:
                if enemy in self.enemies: self.enemies.remove(enemy)

        # 2. Spawn new ones
        for net_id, e_data in remote_enemies.items():
            if net_id not in local_net_ids:
                # We need to map Name back to Class.
                from engine.enemy import (
                    SlugEnemy, BatEnemy, NightBoss, MinibossM2, MinibossM3, SentryEnemy,
                    PunctuationWolfEnemy, BindlingEnemy, SmearEnemy,
                )
                mapping = {
                    "Slug": SlugEnemy, "Bat": BatEnemy, "Night Boss": NightBoss,
                    "Ink-Stained": MinibossM2, "Bleeding Scribe": MinibossM2,
                    "Overwritten Elite": MinibossM2, "Empowered Champion": MinibossM2,
                    "The Relentless Censor": MinibossM2, "Empowered Relentless Censor": MinibossM2,
                    "Forgotten Binder": MinibossM3, "Barrel Mimic": SlugEnemy,
                    "Bindling": BindlingEnemy, "Smear": SmearEnemy,
                    "Techno-Sentry": SentryEnemy, "Punctuation Wolf": PunctuationWolfEnemy,
                }
                cls = mapping.get(e_data.get("name"), SlugEnemy)
                new_e = cls(e_data["x"], e_data["y"], hp=e_data["hp"])
                new_e.network_id = net_id
                new_e.is_empowered = bool(e_data.get("empowered", getattr(self, "empowered_act", False)))
                self.enemies.append(new_e)

    def _sync_interactables_from_host(self, interactable_data_list):
        """Syncs dynamically spawned objects (Warp Portals, Chests)."""
        remote_objs = {obj_data["id"]: obj_data for obj_data in interactable_data_list}
        local_ids = [getattr(obj, 'id', id(obj)) for obj in self.world.interactables]
        
        # 1. Update/Remove
        dynamic_names = ("Appendix Warp", "Loot", "Suspicious Leaf Pile", "Exit Ladder", "Ink Seal")
        for obj in self.world.interactables[:]:
            oid = getattr(obj, 'id', id(obj))
            if oid in remote_objs:
                o_data = remote_objs[oid]
                obj.x, obj.y = o_data["x"], o_data["y"]
                obj.health = o_data.get("hp", 100.0)
            else:
                # Rule: Only remove if it was likely a dynamic object or destroyed
                if obj.name in dynamic_names:
                    self.world.interactables.remove(obj)

        # 2. Spawn New (Appendix Warp & Marginalia dynamic anchors)
        for oid, o_data in remote_objs.items():
            if oid not in local_ids:
                oname = o_data.get("name", "")
                if oname == "Appendix Warp":
                    from engine.world import WarpPortal
                    new_obj = WarpPortal("final_boss", 25, 25, (o_data["x"], o_data["y"], 40, 40), name="Appendix Warp")
                    new_obj.id = oid
                    self.world.interactables.append(new_obj)
                elif oname == "Suspicious Leaf Pile":
                    from engine.world import PitfallTrigger
                    new_obj = PitfallTrigger((o_data["x"], o_data["y"]), anchor_id=str(oid))
                    self.world.interactables.append(new_obj)
                elif oname == "Exit Ladder":
                    from engine.world import ExitLadder
                    new_obj = ExitLadder((o_data["x"], o_data["y"]))
                    new_obj.id = oid
                    self.world.interactables.append(new_obj)
                elif oname == "Ink Seal":
                    from engine.world import InkSeal
                    new_obj = InkSeal((o_data["x"], o_data["y"]), seal_id=str(oid))
                    new_obj.health = float(o_data.get("hp", 20.0))
                    self.world.interactables.append(new_obj)

    def _sync_props_from_host(self, destroyed_ids_list):
        incoming_ids = set(destroyed_ids_list)
        # 1. Update our local set of destroyed IDs
        self.destroyed_prop_ids.update(incoming_ids)
        
        # 2. Reconcile world interactables: remove anything that is in the destroyed set
        for obj in self.world.interactables[:]:
            prop_id = getattr(obj, 'id', None)
            if prop_id and prop_id in self.destroyed_prop_ids:
                try:
                    self.world.interactables.remove(obj)
                    # Trigger a small fade VFX if it was just found
                    self.fading_entities.append({'obj': obj, 'time': 0.1})
                except ValueError: pass

    def fetch_host_map(self):
        if not self.network_manager.is_connected: return False
        map_json = self.network_manager.request_map()
        if map_json:
            import json
            from constants import get_generated_world_path, MAX_ACTS
            raw_act_worlds = map_json.pop("act_worlds", None)
            if isinstance(raw_act_worlds, dict):
                self.act_worlds = {int(k): v for k, v in raw_act_worlds.items()}
            else:
                self.act_worlds = {}
            if "act2_world" in map_json:
                self.act2_world_data = map_json.pop("act2_world")
                self.act_worlds.setdefault(2, self.act2_world_data)
            else:
                self.act2_world_data = self.act_worlds.get(2)
            if "run_biomes" in map_json or raw_act_worlds is not None:
                default_biomes = {f"act{i}": None for i in range(1, MAX_ACTS + 1)}
                self.run_biomes = map_json.pop("run_biomes", default_biomes)
                self.current_act = int(map_json.pop("current_act", 1))
            self.act_worlds[1] = dict(map_json)
            self.act1_world_data = self.act_worlds[1]
            path = get_generated_world_path().replace(".json", "_client.json")
            with open(path, 'w', encoding='utf-8') as f: json.dump(map_json, f)
            print(f"[NETWORK] Received map payload ({len(json.dumps(map_json)) // 1024} KB).")
            
            # Immediately load to set state.enemies etc
            from engine.world import World, LevelLoader
            # Rule: We bypass create_world("generated_world_client") to avoid recursive generative triggers in some contexts
            self.world = World("generated_world_client")
            grid, interactables, warp_tiles, player_start, enemies, boss_coords, module_sockets = LevelLoader.load_json_map(
                path,
                defeated_ids=self.defeated_miniboss_ids
            )
            self.world.grid = grid
            self.world.interactables = interactables
            self.world.warp_tiles = warp_tiles
            self.world.player_start = player_start
            self.world.enemies = enemies
            self.world.boss_coords_list = boss_coords
            self.world.module_sockets = module_sockets
            
            self.enemies = self.world.enemies
            self.in_sanctuary = False
            self.waiting_for_host_run = False
            return True
        return False

    def get_host_map_payload(self):
        from constants import get_generated_world_path
        import os, json
        path = get_generated_world_path()
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                payload = json.load(f)
            if getattr(self, "act_worlds", None):
                payload["act_worlds"] = {
                    str(k): v for k, v in self.act_worlds.items() if int(k) >= 2 and v is not None
                }
            if self.act2_world_data:
                payload["act2_world"] = self.act2_world_data
            if self.act2_world_data or getattr(self, "act_worlds", None):
                payload["run_biomes"] = self.run_biomes
                payload["current_act"] = self.current_act or 1
            return payload
        return None

    def host_restorer_callback(self, identity, ip, peer_id=None):
        """Looks up cached client state by (identity, peer_id) with fallback to identity."""
        del ip
        if peer_id and (identity, peer_id) in self.cached_client_states:
            return self.cached_client_states[(identity, peer_id)]
        return self.cached_client_states.get(identity)

    def host_cacher_callback(self, identity, ip, data, peer_id=None):
        """Caches full client state under both (identity, peer_id) and identity fallback."""
        del ip
        if peer_id:
            self.cached_client_states[(identity, peer_id)] = data
        self.cached_client_states[identity] = data

    def apply_restored_state(self, data):
        if not self.player or not data: return
        self.player.x = float(data.get("x", self.player.x))
        self.player.y = float(data.get("y", self.player.y))
        self.player.flask_charges = int(data.get("flask_charges", self.player.flask_charges))
        self.player.active_weapon_idx = int(data.get("active_weapon_idx", self.player.active_weapon_idx))
        self.player.weapons = data.get("weapons", self.player.weapons)
        self.player.stats = data.get("stats", self.player.stats)
        if "script_modifiers" in data and hasattr(self.player, "apply_script_modifiers"):
            self.player.apply_script_modifiers(data.get("script_modifiers"), refill_in_sanctuary=False)
        self.player.hp = min(float(self.player.max_hp), float(data.get("hp", self.player.hp)))
        if hasattr(self, 'camera'): self.camera.instant_center(self.player.get_center())

    def handle_remote_damage(self, target_type, target_id, amount):
        """Phase 4: Queues damage events sent by remote clients."""
        self.pending_remote_damage.append((target_type, target_id, amount))

    def handle_remote_heal(self, identity, amount):
        """Phase 4: Queues heal events sent by remote clients."""
        self.pending_remote_heals.append((identity, amount))

    def handle_remote_respite(self, identity, action_type, marked_idx, data):
        """Phase 4: Queues respite events (REST, UPGRADE) sent by remote clients."""
        self.pending_remote_respite_actions.append((identity, action_type, marked_idx, data))

    def _process_pending_remote_actions(self):
        """Consumes queued Host-side remote combat/heal/respite events on the main thread."""
        is_client = self.network_manager.network_mode == "CLIENT"
        if is_client:
            return

        if self.pending_remote_damage:
            for target_type, target_id, amount in self.pending_remote_damage:
                if target_type == "enemy":
                    for e in self.enemies:
                        if getattr(e, "network_id", -1) == target_id:
                            e.take_damage(amount)
                            self.damage_numbers.append(
                                {
                                    "val": amount,
                                    "pos": (e.x + 10, e.y - 20),
                                    "time": 1.0,
                                    "color": (255, 255, 0),
                                }
                            )
                            break
                elif target_type == "prop" and self.world:
                    for obj in list(self.world.interactables):
                        if getattr(obj, "id", None) == target_id:
                            obj.take_damage(amount)
                            if hasattr(self, "marginalia_engine") and self.marginalia_engine:
                                self.marginalia_engine.on_prop_struck(self, obj)
                            if obj.is_dead():
                                try:
                                    if hasattr(obj, "id") and obj.id:
                                        self.destroyed_prop_ids.add(obj.id)
                                    self.world.interactables.remove(obj)
                                    self.fading_entities.append(
                                        {
                                            "obj": obj,
                                            "time": 0.16 if obj.name == "Barrel" else 0.1,
                                        }
                                    )
                                    from engine.loot import roll_drop

                                    roll_drop(4, (obj.x, obj.y), self)
                                except (ValueError, AttributeError):
                                    pass
                            break
            self.pending_remote_damage.clear()

        if self.pending_remote_heals:
            for peer_or_id, amount in self.pending_remote_heals:
                resolved_key = self._resolve_remote_player_key(peer_or_id)
                if resolved_key and resolved_key in self.network_manager.remote_players:
                    p_data = self.network_manager.remote_players[resolved_key]
                    p_identity = p_data.get("identity", resolved_key)
                    cached = self._get_cached_client_state(resolved_key, p_identity)
                    m_hp = float(cached.get("max_hp", 100.0))
                    p_data["hp"] = min(m_hp, p_data["hp"] + amount)
            self.pending_remote_heals.clear()

        if self.pending_remote_respite_actions:
            from engine.world import Respite

            for peer_or_id, action_type, _marked_idx, data in self.pending_remote_respite_actions:
                anchor = (
                    next(
                        (obj for obj in self.world.interactables if isinstance(obj, Respite)),
                        None,
                    )
                    if self.world
                    else None
                )
                resolved_key = self._resolve_remote_player_key(peer_or_id)
                if resolved_key and resolved_key in self.network_manager.remote_players:
                    p_data = self.network_manager.remote_players[resolved_key]
                    p_identity = p_data.get("identity", resolved_key)
                    cached = self._get_cached_client_state(resolved_key, p_identity)
                    data_dict = data if isinstance(data, dict) else {}
                    m_hp = float(data_dict.get("max_hp", cached.get("max_hp", 100.0)))

                    if action_type == "REST":
                        p_data["hp"] = m_hp
                        if anchor:
                            anchor.execute_rest(self)
                    elif action_type == "UPGRADE":
                        p_data["hp"] = m_hp
            self.pending_remote_respite_actions.clear()

    def drain_network_events(self):
        """Drains thread-safe network inbox events and applies remote actions on the main thread."""
        if hasattr(self, "network_manager") and self.network_manager:
            self.network_manager.process_inbound_events()
        self._process_pending_remote_actions()

    def get_full_player_state(self):
        if not self.player: return {}
        return {
            "x": self.player.x, "y": self.player.y, "hp": self.player.hp,
            "max_hp": self.player.max_hp, "flask_charges": self.player.flask_charges,
            "active_weapon_idx": self.player.active_weapon_idx,
            "weapons": self.player.weapons, "stats": self.player.stats,
            "script_modifiers": dict(getattr(self.player, "script_modifiers", {})),
        }

    def update(self, dt, actions, audio_manager=None):
        """Update all game logic."""
        if self.player is None: return
        
        self.audio_manager = audio_manager
        self.drain_network_events()

        # 0. Advance Cinematic Warp Controller (if present)
        if hasattr(self, 'warp_controller') and self.warp_controller:
            self.warp_controller.update(dt, self)
            if self.warp_controller.blocks_input():
                actions = {
                    'move': (0, 0),
                    'attack': False,
                    'dash': False,
                    'block': False,
                    'flask': False,
                    'swap': False,
                }

        attack_pressed = actions.get('attack', False)
        ratchet_reset = actions.get('ratchet_reset', False)
        self.inspect_active = actions.get('inspect', False)
        if audio_manager is not None:
            self.audio_manager = audio_manager
        is_client = (self.network_manager.network_mode == "CLIENT")

        if is_client:
            self.full_state_sync_timer += dt
            if self.full_state_sync_timer >= 10.0:
                self.full_state_sync_timer = 0.0
                full_state = self.get_full_player_state()
                self.network_manager.send_full_state(full_state)

        if ratchet_reset: self.input_ratchet_latched = False
        if self.input_debounce_timer > 0: self.input_debounce_timer -= dt
        if self.menu_nav_cooldown > 0: self.menu_nav_cooldown -= dt

        # Dynamically update the is_active status of any gated respites in the world
        if self.world:
            respites = (
                self.world.get_gated_respites()
                if hasattr(self.world, "get_gated_respites")
                else [
                    obj for obj in self.world.interactables
                    if type(obj).__name__ == "Respite" and getattr(obj, "gated_by_miniboss_id", None)
                ]
            )
            for obj in respites:
                is_defeated = (obj.gated_by_miniboss_id in self.defeated_miniboss_ids)
                if obj.is_active != is_defeated:
                    obj.is_active = is_defeated

        # 1. PRE-SYNC: Detection and State Management
        player_rect = (self.player.x, self.player.y, self.player.width, self.player.height)
        nearby = self.world.get_nearby_interactables(player_rect)
        self.player.current_interactable = nearby[0] if nearby else None

        # 2. INTERACTION PHASE
        target = self.player.current_interactable
        warp_blocked = hasattr(self, 'warp_controller') and self.warp_controller.blocks_input()
        hostile_blocked = self.is_interactable_blocked_by_hostiles(target)
        if (
            attack_pressed
            and target
            and getattr(target, 'is_interactive', False)
            and not hostile_blocked
            and not self.active_dialogue
            and not self.active_choice
            and not getattr(self, 'chronicle_dialog', None)
            and not getattr(self, 'binder_dialog', None)
            and not warp_blocked
        ):
            from engine.world import WarpPortal
            if isinstance(target, WarpPortal):
                self.start_warp(target)
            else:
                target.execute_interaction(self)
            attack_pressed = False # Consume input
        
        # HUD Click Interactions
        self._handle_hud_interactions(actions)

        # 3. AI & COMBAT
        if not is_client and not (hasattr(self, 'warp_controller') and self.warp_controller.blocks_enemy_updates()):
            from engine.actor import Actor
            self._frame_runner_positions = Actor.get_active_runner_positions(self)
            try:
                for enemy in self.enemies:
                    enemy.update(dt, self)
            finally:
                self._frame_runner_positions = None

            # --- Phase 1 & 4: Host World Events ---
            self._update_world_events(dt)

        # Tick Sanctuary NPCs (The Chronicler & The Binder) when not halted by active dialogue/Loom
        if (
            self.world
            and not self.active_dialogue
            and not getattr(self, "binder_dialog", None)
        ):
            from engine.world import Binder, Chronicler
            for obj in self.world.interactables:
                if isinstance(obj, (Chronicler, Binder)):
                    obj.update(dt, self)
            
        boss_combat_active = (
            getattr(self.player, 'active_track_name', '') in BOSS_COMBAT_TRACKS
            or self.weather_manager.bleed_state == "BOSS_PHASE"
        )
        self.weather_manager.update(
            dt, self.player, self.world, audio_manager=audio_manager, boss_combat_active=boss_combat_active
        )
        if audio_manager and hasattr(audio_manager, 'update_rain_audio'):
            audio_manager.update_rain_audio(self.weather_manager.rain_audio_intensity)

        # Close Respite instantly if it is getting rained on
        if getattr(self, 'active_respite', None):
            rx = self.active_respite.x + self.active_respite.width / 2
            ry = self.active_respite.y + self.active_respite.height / 2
            if not self.weather_manager.is_pos_safe(rx, ry):
                self.close_respite_menu()
                print("[RESPITE] Closed instantly due to rain exposure.")

        self.update_combat(dt, attack_pressed, actions, audio_manager)
        if hasattr(self, "marginalia_engine") and self.marginalia_engine:
            self.marginalia_engine.update(dt, self)

        # 4. SHARED SYSTEMS (Visuals, Movement, UI)
        self._update_shared_world(dt)
        
        if audio_manager and hasattr(audio_manager, 'update_enemy_sounds'):
            audio_manager.update_enemy_sounds(self)
        
        # Rule: Movement is suppressed if a menu, dialogue, or warp sequence is active
        warp_blocks = hasattr(self, 'warp_controller') and self.warp_controller.blocks_input()
        if (
            not self.active_dialogue
            and not getattr(self, 'active_choice', None)
            and not getattr(self, 'chronicle_dialog', None)
            and not getattr(self, 'binder_dialog', None)
            and not warp_blocks
        ):
            self._update_player_lifecycle(dt, actions, attack_pressed, audio_manager)
        else:
            # Freeze momentum while in menus or warping
            self.player.vx = 0
            self.player.vy = 0
            self._update_audio_track(dt)
            
        self._update_ui_and_menus(dt, actions, attack_pressed, audio_manager)
        self._update_sanctuary_door_state()
        self._update_slime_pools(dt)

        # 5. CAMERA & VIEWPORT
        if hasattr(self, 'camera') and self.player:
            self.camera.update(self.player.get_center(), dt)
        
        # 6. VFX DECAY
        if self.shake_timer > 0:
            self.shake_timer -= dt
            if self.shake_timer < 0: self.shake_timer = 0.0

    def is_interactable_blocked_by_hostiles(self, target) -> bool:
        """Return True if a non-combat interactable is locked out because hostiles are nearby."""
        if target is None or not getattr(target, "is_interactive", False):
            return False
        from constants import INTERACTABLE_HOSTILE_LOCK_RADIUS
        from engine.world import ExitLadder, WeaponPickup
        if isinstance(target, (WeaponPickup, ExitLadder)):
            return False
        enemies = getattr(self, "enemies", None) or ()
        if not enemies:
            return False
        tx = float(getattr(target, "x", 0.0)) + float(getattr(target, "width", 0.0)) * 0.5
        ty = float(getattr(target, "y", 0.0)) + float(getattr(target, "height", 0.0)) * 0.5
        px, py = self.player.get_center() if getattr(self, "player", None) is not None else (tx, ty)
        rad_sq = float(INTERACTABLE_HOSTILE_LOCK_RADIUS) ** 2
        for enemy in enemies:
            if getattr(enemy, "hp", 1) <= 0 or (hasattr(enemy, "is_dead") and enemy.is_dead()):
                continue
            ex, ey = enemy.get_center()
            if (ex - tx) ** 2 + (ey - ty) ** 2 <= rad_sq or (ex - px) ** 2 + (ey - py) ** 2 <= rad_sq:
                return True
        return False

    def _update_sanctuary_door_state(self):
        """Update Sanctuary doorway open state and edge-trigger door_open.ogg on False -> True."""
        if self.world is None or self.player is None or getattr(self.world, "name", "") != "sanctuary":
            self.sanctuary_door_open = False
            return

        from constants import SANCTUARY_DOOR_OPEN_SFX, SANCTUARY_DOOR_PROXIMITY_TILES

        zones = getattr(self.world, "sanctuary_zones", None)
        south_facade = zones.get("south_facade", {}) if isinstance(zones, dict) else {}
        doorways = south_facade.get("doorway") or [[38, 21]]

        px, py = self.player.get_center()
        ptx, pty = int(px // TILE_SIZE), int(py // TILE_SIZE)
        prox_px = float(SANCTUARY_DOOR_PROXIMITY_TILES) * float(TILE_SIZE)

        door_open = False
        for coord in doorways:
            if not isinstance(coord, (list, tuple)) or len(coord) < 2:
                continue
            dx_t, dy_t = int(coord[0]), int(coord[1])
            if (ptx, pty) in ((dx_t, dy_t + 1), (dx_t, dy_t), (dx_t, dy_t - 1)):
                door_open = True
                break
            dcx = (dx_t + 0.5) * TILE_SIZE
            dcy = (dy_t + 0.5) * TILE_SIZE
            if math.hypot(px - dcx, py - dcy) <= prox_px:
                door_open = True
                break

        if door_open and not getattr(self, "sanctuary_door_open", False):
            if getattr(self, "audio_manager", None) is not None:
                self.audio_manager.play_sfx(SANCTUARY_DOOR_OPEN_SFX)
        self.sanctuary_door_open = door_open

    def spawn_slime_pool(self, x, y, radius=None, duration=None, damage=None, style="slime"):
        """Spawn a timed damaging ground hazard pool secreted by SlugBoss ('slime') or MeadowCensorBoss ('tar')."""
        from constants import (
            SLUG_BOSS_SLIME_POOL_DAMAGE,
            SLUG_BOSS_SLIME_POOL_DURATION,
            SLUG_BOSS_SLIME_POOL_RADIUS,
        )
        r_val = float(SLUG_BOSS_SLIME_POOL_RADIUS if radius is None else radius)
        dur_val = float(SLUG_BOSS_SLIME_POOL_DURATION if duration is None else duration)
        dmg_val = float(SLUG_BOSS_SLIME_POOL_DAMAGE if damage is None else damage)
        pool = {
            "x": float(x),
            "y": float(y),
            "radius": r_val,
            "timer": dur_val,
            "max_duration": dur_val,
            "damage": dmg_val,
            "tick_timer": 0.0,
            "style": str(style),
        }
        self.slime_pools.append(pool)
        return pool

    def _update_slime_pools(self, dt):
        """Advance ground slime pools, expire finished pools, and tick damage on standing players."""
        if not getattr(self, "slime_pools", None):
            return
        from constants import SLUG_BOSS_SLIME_POOL_TICK_INTERVAL

        player = getattr(self, "player", None)
        can_damage = (
            player is not None
            and getattr(player, "hp", 0.0) > 0.0
            and getattr(self, "death_timer", 0.0) <= 0.0
            and getattr(self, "active_respite", None) is None
            and getattr(self.network_manager, "network_mode", "OFFLINE") != "CLIENT"
        )
        px, py = player.get_center() if can_damage else (0.0, 0.0)
        alive_pools = []
        for pool in self.slime_pools:
            pool["timer"] -= dt
            if pool["timer"] <= 0.0:
                continue
            if pool["tick_timer"] > 0.0:
                pool["tick_timer"] = max(0.0, pool["tick_timer"] - dt)
            if can_damage and pool["tick_timer"] <= 0.0:
                dist = math.hypot(px - pool["x"], py - pool["y"])
                if dist <= pool["radius"] + 12.0:
                    player.take_damage(
                        pool["damage"],
                        bypass_stagger=True,
                        audio_manager=getattr(self, "audio_manager", None),
                        game_state=self,
                    )
                    pool["tick_timer"] = float(SLUG_BOSS_SLIME_POOL_TICK_INTERVAL)
            alive_pools.append(pool)
        self.slime_pools = alive_pools

    def _update_world_events(self, dt):
        """Host-only logic for boss spawns and environmental transitions."""
        from constants import TILE_SIZE, TILE_STRUCTURE, TILE_RESPITE
        # 0. Weather Damage to Remote Players
        if self.weather_manager.damage_enabled and not getattr(self.weather_manager, "paused", False):
            for identity, p_data in self.network_manager.remote_players.items():
                if p_data.get("in_sanctuary", False):
                    continue
                # Estimate center
                px, py = p_data["x"] + 20, p_data["y"] + 20
                if not self.weather_manager.is_pos_safe(px, py):
                    # Check for shelter
                    tx, ty = int(px // TILE_SIZE), int(py // TILE_SIZE)
                    is_sheltered = False
                    if 0 <= ty < len(self.world.grid) and 0 <= tx < len(self.world.grid[0]):
                        if self.world.grid[ty][tx] in (TILE_STRUCTURE, TILE_RESPITE):
                            is_sheltered = True
                    
                    if not is_sheltered:
                        # Apply authoritative damage
                        rain_dps = float(getattr(self.weather_manager, "rain_dps", 2.0))
                        p_data["hp"] = max(0.0, p_data["hp"] - (rain_dps * dt))

        # 1. Boss Spawn Rule: Only if circle is closed (CLAMPED) and not already spawned
        if self.weather_manager.is_boss_spawn_ready():
            boss_alive = any(getattr(e, 'name', '') == "Night Boss" for e in self.enemies)
            if not boss_alive and self.weather_manager.bleed_state == "CLAMPED":
                from engine.enemy import MeadowCensorBoss, NightBoss, RimecrestArbiterBoss, SlugBoss
                idx = self.weather_manager.current_boss_idx
                boss_list = getattr(self.world, 'boss_coords_list', [])
                if idx < len(boss_list):
                    coords = boss_list[idx]
                    from constants import (
                        TILE_SIZE,
                        ACT2_HP_MULTIPLIER,
                        ACT2_DAMAGE_MULTIPLIER,
                        get_act_saturation,
                    )
                    bx, by = coords['x'] * TILE_SIZE, coords['y'] * TILE_SIZE
                    active_biome = self._resolve_active_biome_key()
                    if active_biome == "swamp_mire":
                        new_boss = SlugBoss(bx, by)
                    elif active_biome == "pastoral_valley":
                        new_boss = MeadowCensorBoss(bx, by)
                    elif active_biome == "frozen_peaks":
                        new_boss = RimecrestArbiterBoss(bx, by)
                    else:
                        new_boss = NightBoss(bx, by)
                    if hasattr(self.world, "find_nearest_walkable_spawn"):
                        bx, by = self.world.find_nearest_walkable_spawn(
                            bx, by, new_boss.width, new_boss.height
                        )
                        new_boss.x, new_boss.y = bx, by
                        new_boss.origin_x, new_boss.origin_y = bx, by
                    new_boss.network_id = 9000 + idx
                    if self.current_act >= 2 or getattr(self, 'empowered_act', False):
                        sat = get_act_saturation(max(2, self.current_act))
                        spd_m = float(sat.get("speed_multiplier", 1.0))
                        cd_m = float(sat.get("cooldown_multiplier", 1.0))
                        if getattr(self, 'empowered_act', False) and self.current_act <= 2:
                            hp_m, dmg_m, emp_flag = ACT2_HP_MULTIPLIER, ACT2_DAMAGE_MULTIPLIER, True
                        else:
                            hp_m = float(sat["hp_multiplier"])
                            dmg_m = float(sat["damage_multiplier"])
                            emp_flag = bool(sat["empowered"])
                        new_boss.apply_act_scaling(
                            hp_m,
                            dmg_m,
                            empowered=emp_flag,
                            speed_multiplier=spd_m,
                            cooldown_multiplier=cd_m,
                        )
                    self.enemies.append(new_boss)
                    self.night_boss_spawned = True
                    if getattr(self, "active_respite", None):
                        self.close_respite_menu()
                    print(f"[THE BLEED] Night Boss manifested at ({bx}, {by}).")
                    boss_alive = True
            self.weather_manager.lock_circle_for_boss(boss_alive)

        # Appendix / Act Transition Rule: After Night Boss defeat & dilution interlude
        if self.weather_manager.bleed_state == "APPENDIX":
            from constants import MAX_ACTS
            warp_active = hasattr(self, 'warp_controller') and self.warp_controller.is_active()
            next_act = self.current_act + 1 if self.current_act >= 1 else 0
            has_next_act_world = (
                1 <= self.current_act < MAX_ACTS
                and (
                    next_act in getattr(self, "act_worlds", {})
                    or (next_act == 2 and self.act2_world_data is not None)
                )
            )
            if has_next_act_world:
                target_key = f"act{next_act}"
                if self.act_warp_target != target_key and not warp_active:
                    self.act_warp_target = target_key
                    self.start_warp(
                        target_key,
                        callback=lambda gs, a=next_act: gs.transition_to_act(a),
                        confirmed=True,
                    )
            elif self.current_act >= 2:
                if self.act_warp_target != "night_boss_arena" and not warp_active:
                    self.act_warp_target = "night_boss_arena"
                    self.start_warp("night_boss_arena", confirmed=True)
            elif not any(e.name == "Appendix Warp" for e in self.world.interactables):
                idx = self.weather_manager.current_boss_idx
                boss_list = getattr(self.world, 'boss_coords_list', []) or []
                if idx < len(boss_list):
                    coords = boss_list[idx]
                    from engine.world import WarpPortal
                    from constants import TILE_SIZE
                    portal_rect = (coords['x'] * TILE_SIZE - 20, coords['y'] * TILE_SIZE - 20, 40, 40)
                    portal = WarpPortal("final_boss", 25, 25, portal_rect, name="Appendix Warp")
                    self.world.interactables.append(portal)
                    self.trigger_bloom("THE APPENDIX REVEALED", priority=2)

    def spawn_impact_sparks(self, x, y, weapon=None, count=None):
        """Spawns subtle directional impact sparks upon landed melee hits."""
        import random
        import math
        from constants import (
            IMPACT_SPARK_COUNT,
            IMPACT_SPARK_LIFETIME,
            IMPACT_SPARK_SPEED_MIN,
            IMPACT_SPARK_SPEED_MAX,
            get_weapon_passive_color,
        )
        tint = get_weapon_passive_color(weapon)
        fx, fy = self.player.facing
        base_angle = math.atan2(fy, fx)
        spark_count = count if count is not None else IMPACT_SPARK_COUNT
        for _ in range(spark_count):
            angle = base_angle + random.uniform(-0.85, 0.85)
            speed = random.uniform(IMPACT_SPARK_SPEED_MIN, IMPACT_SPARK_SPEED_MAX)
            self.impact_sparks.append({
                'x': float(x),
                'y': float(y),
                'vx': math.cos(angle) * speed,
                'vy': math.sin(angle) * speed,
                'time': IMPACT_SPARK_LIFETIME,
                'max_time': IMPACT_SPARK_LIFETIME,
                'color': tint,
            })

    def update_combat(self, dt, attack_pressed, actions, audio_manager):
        """Phase 1: Handles player attacks and damage resolution."""
        if not self.player: return
        
        is_client = (self.network_manager.network_mode == "CLIENT")

        if self.pending_remote_sfx:
            queued = self.pending_remote_sfx[:]
            self.pending_remote_sfx.clear()
            if audio_manager:
                import math
                px, py = self.player.get_center()
                for sfx_name, rx, ry in queued:
                    dist = math.hypot(rx - px, ry - py)
                    vol = audio_manager.calculate_spatial_volume(dist)
                    jitter = 0.06 if sfx_name in ("sword_swing.ogg", "player_dash.ogg") else 0.0
                    audio_manager.play_sfx(sfx_name, volume=vol, pitch_jitter=jitter)

        player_is_attacking = (self.player.state == PlayerStateEnum.ATTACKING)
        if player_is_attacking and not getattr(self, '_player_was_attacking', False):
            self._hit_sfx_played_this_attack = False
            self.local_swing_seq += 1
            if audio_manager:
                audio_manager.play_sfx("sword_swing.ogg", pitch_jitter=0.06)
        if getattr(self, '_player_was_attacking', False) and not player_is_attacking:
            from constants import (
                SWORD_REACH, SWORD_ARC_RADIANS, SLASH_FADE_DURATION, get_weapon_passive_color
            )
            active_wpn = self.player.get_active_weapon() if self.player.weapons else {}
            last_pos = getattr(self, '_last_attack_center', self.player.get_center())
            last_facing = getattr(self, '_last_attack_facing', self.player.facing)
            self.slash_effects.append({
                'pos': last_pos,
                'facing': last_facing,
                'reach': SWORD_REACH,
                'arc_radians': SWORD_ARC_RADIANS,
                'color': get_weapon_passive_color(active_wpn),
                'time': SLASH_FADE_DURATION,
                'max_time': SLASH_FADE_DURATION,
            })

        if player_is_attacking:
            self._last_attack_center = self.player.get_center()
            self._last_attack_facing = self.player.facing
        self._player_was_attacking = player_is_attacking
        
        # 0. Process queued remote damage, heals, and respite actions (Host Only)
        self._process_pending_remote_actions()

        # 1. Local Attacks
        if self.player.state == PlayerStateEnum.ATTACKING:
            from engine.combat import get_sword_hitbox, check_sword_hit
            player_center = self.player.get_center()
            player_facing = self.player.facing
            hitbox = get_sword_hitbox(player_center, player_facing)
            active_weapon = self.player.get_active_weapon()
            bonus_atk = getattr(self.player, 'stats', {}).get('attack_modifier', 0)
            script_atk = int(round(float(getattr(self.player, 'script_modifiers', {}).get('attack', 0.0))))
            from constants import (
                SWORD_DAMAGE, HIT_STOP_DURATION, SCREEN_SHAKE_DURATION,
                DAMAGE_NUMBER_LIFETIME, COLOR_SELECTION
            )
            damage = active_weapon.get("damage", SWORD_DAMAGE) + bonus_atk + script_atk
            hit_landed = False

            # Enemies
            for enemy in list(self.enemies):
                try:
                    net_id = getattr(enemy, 'network_id', id(enemy))
                    if net_id in self.player.hit_entities_this_attack:
                        continue
                    e_rect = enemy.get_rect()
                    if not check_aabb_collision(hitbox, e_rect):
                        continue
                    if check_sword_hit(player_center, player_facing, e_rect, hitbox=hitbox):
                        # Rule: Hit once per attack swing
                        self.player.hit_entities_this_attack.add(net_id)
                        
                        enemy.take_damage(damage, bypass_stagger=is_client)
                        
                        # Glyph Splatter Particle Burst at impact point
                        from constants import COLOR_INK_CHARCOAL
                        impact_x, impact_y = enemy.get_center()
                        enemy_color = getattr(enemy, 'glyph_splatter_color', COLOR_INK_CHARCOAL)
                        self.glyph_particles.spawn_burst(impact_x, impact_y, color=enemy_color)
                        self.spawn_impact_sparks(impact_x, impact_y, weapon=active_weapon)

                        # Apply anomalous weapon & Binder Script bleed modifiers on hit
                        all_mods = self.player.get_all_modifiers()
                        script_bleed = float(getattr(self.player, "script_modifiers", {}).get("bleed", 0.0))
                        total_bleed = float(all_mods.get("bleed", 0.0)) + script_bleed
                        if total_bleed > 0.0 and enemy.hp > 0:
                            enemy.bleed_timer = 5.0
                            enemy.bleed_damage = total_bleed
                            enemy.bleed_tick_timer = 1.0

                        hit_landed = True
                        if is_client:
                            self.network_manager.send_damage_event("enemy", net_id, damage)
                        self.hit_stop_timer = HIT_STOP_DURATION
                        self.trigger_shake(SCREEN_SHAKE_DURATION)
                        self.damage_numbers.append({
                            'val': damage, 'pos': (enemy.x + 10, enemy.y - 20),
                            'time': DAMAGE_NUMBER_LIFETIME, 'color': COLOR_SELECTION
                        })
                except Exception: pass

            # Props
            for obj in list(self.world.interactables):
                if not getattr(obj, 'is_breakable', False):
                    continue
                p_id = getattr(obj, 'id', id(obj))
                if p_id in self.player.hit_props_this_attack:
                    continue
                if not check_aabb_collision(hitbox, obj.rect):
                    continue
                if check_sword_hit(player_center, player_facing, obj.rect, hitbox=hitbox):
                    self.player.hit_props_this_attack.add(p_id)
                    
                    obj.take_damage(damage)
                    if not is_client and hasattr(self, "marginalia_engine") and self.marginalia_engine:
                        self.marginalia_engine.on_prop_struck(self, obj)
                    hit_landed = True
                    prop_cx = obj.rect[0] + obj.rect[2] * 0.5
                    prop_cy = obj.rect[1] + obj.rect[3] * 0.5
                    self.spawn_impact_sparks(prop_cx, prop_cy, weapon=active_weapon)
                    if is_client:
                        self.network_manager.send_damage_event("prop", p_id, damage)
                    
                    # Only the Host officially kills props and spawns loot. Clients wait for the UDP state sync to hide them.
                    if obj.is_dead() and not is_client:
                        try:
                            if hasattr(obj, 'id') and obj.id:
                                self.destroyed_prop_ids.add(obj.id)
                            self.world.interactables.remove(obj)
                            fade_time = 0.16 if obj.name == "Barrel" else 0.1
                            self.fading_entities.append({'obj': obj, 'time': fade_time})
                            if audio_manager: audio_manager.play_sfx("prop_break.ogg")
                            from engine.loot import roll_drop
                            roll_drop(4, (obj.x, obj.y), self)
                        except Exception: pass
            
            if hit_landed and not getattr(self, '_hit_sfx_played_this_attack', False):
                self._hit_sfx_played_this_attack = True
                self.local_hit_seq += 1
                if audio_manager:
                    audio_manager.play_sfx("sword_hit.ogg")

        # 2. Enemy Lifecycle (Death/Cleanup) - Host Only handles death logic
        if not is_client:
            for enemy in list(self.enemies):
                if enemy.is_dead():
                    try:
                        if getattr(enemy, 'is_miniboss', False) and getattr(enemy, 'id', None):
                            self.defeated_miniboss_ids.add(enemy.id)
                        if getattr(enemy, 'name', '') == "Night Boss" and self.stats:
                            from constants import (
                                SCRAPS_REWARD_NIGHT_BOSS_BASE,
                                SCRAPS_REWARD_NIGHT_BOSS_EMPOWERED,
                            )
                            is_emp = self.current_act >= 3 or getattr(self, "empowered_act", False)
                            scrap_reward = (
                                SCRAPS_REWARD_NIGHT_BOSS_EMPOWERED if is_emp else SCRAPS_REWARD_NIGHT_BOSS_BASE
                            )
                            if hasattr(self.stats, "add_margin_scraps"):
                                self.stats.add_margin_scraps(scrap_reward)
                            else:
                                self.stats.data["margin_scraps"] = int(
                                    self.stats.data.get("margin_scraps", 0)
                                ) + scrap_reward
                        if hasattr(enemy, 'on_death'): enemy.on_death(self)
                        self.enemies.remove(enemy)
                        if audio_manager: audio_manager.play_sfx("enemy_death.ogg")
                        from engine.loot import roll_drop
                        tier = getattr(enemy, 'loot_tier', 3)
                        roll_drop(tier, (enemy.x, enemy.y), self)
                    except Exception: pass

        from engine.physics import resolve_enemy_player_collision
        # Rule: Everyone resolves collision locally to prevent clipping.
        # But if we are a client, we don't push the enemies (we trust Host position).
        resolve_enemy_player_collision(self.player, self.enemies, allow_push_enemies=(not is_client))


    def _update_shared_world(self, dt):
        """Logic that runs on both Host and Client for visuals/vfx."""
        self.active_safe_radius = self.weather_manager.active_safe_radius
        self.bleed_state = self.weather_manager.bleed_state
        self.current_boss_coords = self.weather_manager.get_current_boss_coords()

        if self.weather_manager.pending_milestone_text:
            self.trigger_bloom(self.weather_manager.pending_milestone_text, priority=2)
            self.weather_manager.pending_milestone_text = None

        self.update_damage_numbers(dt)
        if hasattr(self, 'glyph_particles'):
            self.glyph_particles.update(dt)
        for fading in self.fading_entities[:]:
            fading['time'] -= dt
            if fading['time'] <= 0:
                if fading['obj'].name == "Barrel":
                    self.world_debris.append({'name': 'BarrelRubble', 'pos': (fading['obj'].x, fading['obj'].y)})
                self.fading_entities.remove(fading)

        # Expire timed ground interactables (e.g., SmearEnemy walking Inkwell Puddles)
        world = getattr(self, "world", None)
        if world is not None and hasattr(world, "interactables"):
            expired_interactable = False
            kept_interactables = []
            for obj in world.interactables:
                life = getattr(obj, "lifetime", None)
                if life is not None:
                    life -= dt
                    obj.lifetime = life
                    if life <= 0.0:
                        expired_interactable = True
                        continue
                kept_interactables.append(obj)
            if expired_interactable:
                world.interactables[:] = kept_interactables
                world._spatial_sig = None

        # Tick timed world_debris entries (e.g., 5.0s fading IceRubble piles)
        if getattr(self, "world_debris", None):
            kept_debris = []
            debris_changed = False
            for entry in self.world_debris:
                if isinstance(entry, dict) and "time" in entry:
                    entry["time"] = float(entry["time"]) - dt
                    if entry["time"] <= 0.0:
                        debris_changed = True
                        continue
                kept_debris.append(entry)
            if debris_changed:
                self.world_debris[:] = kept_debris

        for effect in self.parry_effects[:]:
            effect['time'] -= dt
            if effect['time'] <= 0: self.parry_effects.remove(effect)

        for spark in getattr(self, 'impact_sparks', [])[:]:
            spark['time'] -= dt
            spark['x'] += spark['vx'] * dt
            spark['y'] += spark['vy'] * dt
            if spark['time'] <= 0:
                self.impact_sparks.remove(spark)

        for slash in getattr(self, 'slash_effects', [])[:]:
            slash['time'] -= dt
            if slash['time'] <= 0:
                self.slash_effects.remove(slash)

    def _update_player_lifecycle(self, dt, actions, attack_pressed, audio_manager):
        if self.hit_stop_timer > 0:
            self.hit_stop_timer -= dt
            return
        
        # Check for death initiation
        if self.player.hp <= 0 and self.death_timer <= 0:
            from constants import DEATH_SCREEN_DURATION
            self.death_timer = DEATH_SCREEN_DURATION
            self.player.vx = 0
            self.player.vy = 0
            print("[GAME] Scholar has been redacted.")

        if self.death_timer > 0:
            self.death_timer -= dt
            self._update_audio_track(dt)
            if self.death_timer <= 0: self.respawn_player()
            return

        # Player Movement (Local)
        move_dir = actions.get('move', (0, 0))
        flask_pressed = actions.get('flask', False)
        dash_pressed = actions.get('dash', False)
        block_pressed = actions.get('block', False)
        swap_pressed = actions.get('swap', False)

        if swap_pressed:
            # Rule: Contextual Swap. If standing on a weapon, 'Swap' picks it up.
            target = self.player.current_interactable
            from engine.world import WeaponPickup
            if isinstance(target, WeaponPickup):
                target.execute_interaction(self)
            else:
                self.player.swap_weapon()
                
            if self.network_manager.network_mode == "CLIENT":
                full_state = self.get_full_player_state()
                self.network_manager.send_full_state(full_state)

        player_rect = (self.player.x, self.player.y, self.player.width, self.player.height)
        speed_multiplier = 1.0
        if hasattr(self.world, "has_puddle_collision"):
            if self.world.has_puddle_collision(player_rect):
                speed_multiplier = 0.5
        else:
            for obj in self.world.interactables:
                if obj.name == "Inkwell Puddle":
                    if check_aabb_collision(player_rect, obj.rect):
                        speed_multiplier = 0.5
                        break
        if hasattr(self.world, "is_in_sanctuary_pond") and self.world.is_in_sanctuary_pond(player_rect):
            from constants import SANCTUARY_POND_SPEED_MULTIPLIER
            speed_multiplier = min(speed_multiplier, SANCTUARY_POND_SPEED_MULTIPLIER)
        elif hasattr(self.world, "is_in_aqueduct_water") and self.world.is_in_aqueduct_water(player_rect):
            from constants import AQUEDUCT_WATER_SPEED_MULTIPLIER
            speed_multiplier = min(speed_multiplier, AQUEDUCT_WATER_SPEED_MULTIPLIER)

        # Query walls over a swept bounding rect covering pre-move and projected displacement
        from constants import DASH_SPEED_MULTIPLIER
        eff_speed = self.player.speed + float(getattr(self.player, "script_modifiers", {}).get("speed", 0.0))
        if self.player.state == PlayerStateEnum.DASHING or dash_pressed:
            proj_speed = eff_speed * speed_multiplier * DASH_SPEED_MULTIPLIER
            proj_dx = self.player.facing[0] * proj_speed * dt
            proj_dy = self.player.facing[1] * proj_speed * dt
        else:
            proj_dx = move_dir[0] * eff_speed * speed_multiplier * dt
            proj_dy = move_dir[1] * eff_speed * speed_multiplier * dt
        swept_min_x = min(self.player.x, self.player.x + proj_dx)
        swept_min_y = min(self.player.y, self.player.y + proj_dy)
        swept_max_x = max(self.player.x, self.player.x + proj_dx) + self.player.width
        swept_max_y = max(self.player.y, self.player.y + proj_dy) + self.player.height
        swept_rect = (swept_min_x, swept_min_y, swept_max_x - swept_min_x, swept_max_y - swept_min_y)
        walls = self.world.get_nearby_walls(swept_rect)

        world_grid = getattr(self.world, "grid", None)
        if world_grid and len(world_grid) > 0 and len(world_grid[0]) > 0:
            world_w = len(world_grid[0]) * TILE_SIZE
            world_h = len(world_grid) * TILE_SIZE
        else:
            world_w = None
            world_h = None

        prev_player_state = self.player.state
        encased_crack = bool(getattr(self.player, "just_cracked_ice", False))
        sfx_mgr = audio_manager or getattr(self, "audio_manager", None)
        healed = self.player.update(
            dt, move_dir, walls, actions, attack_pressed, flask_pressed,
            dash_pressed, block_pressed, speed_multiplier,
            audio_manager=sfx_mgr,
            world_width=world_w, world_height=world_h,
        )
        # Quiet wading water-splash footstep cadence when moving in shallow water
        post_rect = (self.player.x, self.player.y, self.player.width, self.player.height)
        in_water = hasattr(self.world, "is_in_shallow_water") and self.world.is_in_shallow_water(post_rect)
        is_moving_water = in_water and (abs(self.player.vx) + abs(self.player.vy) > 10.0)
        if is_moving_water:
            from constants import WATER_STEP_INTERVAL, WATER_STEP_SFX
            self._water_step_timer += dt
            if self._water_step_timer >= float(WATER_STEP_INTERVAL):
                self._water_step_timer = 0.0
                if sfx_mgr is not None:
                    try:
                        sfx_mgr.play_sfx(WATER_STEP_SFX, volume=0.35, pitch_jitter=0.08)
                    except TypeError:
                        sfx_mgr.play_sfx(WATER_STEP_SFX)
        else:
            from constants import WATER_STEP_INTERVAL
            self._water_step_timer = float(WATER_STEP_INTERVAL) * 0.75
        if encased_crack or getattr(self.player, "just_cracked_ice", False):
            if sfx_mgr is not None:
                from constants import ICE_CRACK_SFX
                sfx_mgr.play_sfx(ICE_CRACK_SFX, pitch_jitter=0.05)
        if getattr(self.player, "just_shattered_ice", False):
            from constants import ICE_RUBBLE_DURATION, ICE_SHATTER_SFX
            if sfx_mgr is not None:
                sfx_mgr.play_sfx(ICE_SHATTER_SFX, pitch_jitter=0.04)
            px_c, py_c = self.player.get_center()
            self.world_debris.append(
                {
                    "name": "IceRubble",
                    "pos": (px_c - 24.0, py_c - 12.0),
                    "time": float(ICE_RUBBLE_DURATION),
                    "max_time": float(ICE_RUBBLE_DURATION),
                }
            )
        if self.player.state == PlayerStateEnum.DASHING and prev_player_state != PlayerStateEnum.DASHING:
            self.local_dash_seq += 1
            if audio_manager:
                audio_manager.play_sfx("player_dash.ogg", pitch_jitter=0.06)
        if healed and self.network_manager.network_mode == "CLIENT":
            from constants import FLASK_HEAL_AMOUNT
            self.network_manager.send_heal_event(FLASK_HEAL_AMOUNT)

        self._update_audio_track(dt)
        self._handle_victory_conditions(dt)

    def _handle_hud_interactions(self, actions):
        """Phase 4: Handles mouse clicks on HUD elements."""
        click_pos = actions.get('mouse_click')
        if not click_pos: return
        
        from constants import (
            SCREEN_HEIGHT, HUD_PANEL_H, HUD_SWAP_BTN_RECT, HUD_PICKUP_BTN_RECT
        )
        
        # Calculate HUD base position (matches renderer.py)
        hx = 10
        hy = SCREEN_HEIGHT - HUD_PANEL_H - 10
        
        mx, my = click_pos
        
        # 1. Swap Button (SLOT B card doubles as the swap click target; clicking inactive SLOT A also swaps)
        swr = HUD_SWAP_BTN_RECT
        slot_a_clicked = (
            self.player.active_weapon_idx != 0
            and hx + 8 <= mx <= hx + 8 + swr[2]
            and hy + swr[1] <= my <= hy + swr[1] + swr[3]
        )
        if slot_a_clicked or (hx + swr[0] <= mx <= hx + swr[0] + swr[2] and hy + swr[1] <= my <= hy + swr[1] + swr[3]):
            self.player.swap_weapon()
            if self.network_manager.network_mode == "CLIENT":
                full_state = self.get_full_player_state()
                self.network_manager.send_full_state(full_state)
            return

        # 2. Pickup Button
        pkr = HUD_PICKUP_BTN_RECT
        if hx + pkr[0] <= mx <= hx + pkr[0] + pkr[2] and hy + pkr[1] <= my <= hy + pkr[1] + pkr[3]:
            target = self.player.current_interactable
            warp_blocked = hasattr(self, 'warp_controller') and self.warp_controller.blocks_input()
            if target and getattr(target, 'is_interactive', False) and not warp_blocked:
                from engine.world import WarpPortal
                if isinstance(target, WarpPortal):
                    self.start_warp(target)
                else:
                    target.execute_interaction(self)
            return

    def _resolve_active_biome_key(self, matched_socket=None):
        """Return the active biome identifier for the current world/act."""
        from constants import BIOME_DISPLAY_NAMES
        if isinstance(matched_socket, dict):
            sock_biome = matched_socket.get("biome")
            if sock_biome in BIOME_DISPLAY_NAMES:
                return sock_biome
        current_act = int(getattr(self, "current_act", 0) or 0)
        run_biomes = getattr(self, "run_biomes", None) or {}
        if current_act > 0:
            act_biome = run_biomes.get(f"act{current_act}")
            if act_biome in BIOME_DISPLAY_NAMES:
                return act_biome
        for b_val in run_biomes.values():
            if b_val in BIOME_DISPLAY_NAMES:
                return b_val
        for candidate in (
            getattr(self, "active_biome", None),
            getattr(self.world, "biome", None),
            getattr(self.world, "name", None),
        ):
            if candidate in BIOME_DISPLAY_NAMES:
                return candidate
            if isinstance(candidate, str):
                c_low = candidate.lower()
                for b_key in BIOME_DISPLAY_NAMES:
                    if b_key in c_low:
                        return b_key
        for sock in getattr(self.world, "module_sockets", []) or []:
            plug = str(sock.get("active_plug", "")).lower()
            sock_b = sock.get("biome")
            if sock_b in BIOME_DISPLAY_NAMES:
                return sock_b
            for b_key in BIOME_DISPLAY_NAMES:
                if b_key in plug:
                    return b_key
        return "windy_ridge"

    def _resolve_room_area_name(self, current_room_id):
        """Resolve display area title for current_room_id without falling back to THE UNKNOWN MARGIN."""
        from constants import BIOME_DISPLAY_NAMES
        zone_name = ""
        matched_socket = None
        for s in getattr(self.world, "module_sockets", []):
            s_id = s.get("id") or s.get("name")
            if s_id == current_room_id:
                matched_socket = s
                plug = s.get("active_plug", "").lower()
                if "windy_ridge" in plug:
                    zone_name = "THE ZEPHYR RIDGE"
                elif "pastoral_valley" in plug:
                    zone_name = "THE SCARRED MEADOW"
                elif "swamp_mire" in plug:
                    zone_name = "THE VENOMOUS MIRE"
                elif "frozen_peaks" in plug:
                    zone_name = "THE RIMECREST PASS"
                elif "tech_tower" in plug:
                    zone_name = "THE SKY CITADEL"
                elif "vitreous_basin" in plug or "basin" in plug:
                    zone_name = "THE VITREOUS BASIN"
                elif "sunlit_aqueducts" in plug or "aqueduct" in plug:
                    zone_name = "THE SUNLIT AQUEDUCTS"
                elif "forest" in plug:
                    zone_name = "THE VERDANT SILENCE"
                elif "ruins" in plug:
                    zone_name = "THE SCORCHED MARGIN"
                elif "colophon" in plug:
                    zone_name = "THE COLOPHON"
                elif "boss" in plug:
                    zone_name = "THE CROWN RING"
                break
        if not zone_name:
            active_biome = self._resolve_active_biome_key(matched_socket=matched_socket)
            zone_name = BIOME_DISPLAY_NAMES.get(active_biome, "Windy Ridge").upper()
        return zone_name

    def _update_ui_and_menus(self, dt, actions, attack_pressed, audio_manager):
        # Zone Discovery Bloom
        if getattr(self.world, 'name', '') not in ("", "sanctuary"):
            px, py = self.player.get_center()
            from constants import TILE_SIZE, BLOOM_COOLDOWN
            # Unit logic: 11x11 units of 40x40 tiles. Sub-rooms are indexed by (0, 4, 8)
            cur_unit_x, cur_unit_y = int(px // (TILE_SIZE * 40)), int(py // (TILE_SIZE * 40))
            
            current_room_id = None
            for ru_y in (0, 4, 8):
                for ru_x in (0, 4, 8):
                    if ru_x <= cur_unit_x < ru_x + 3 and ru_y <= cur_unit_y < ru_y + 3:
                        current_room_id = f"Room_{ru_x}_{ru_y}"
                        break
            
            if current_room_id and current_room_id != self.last_zone_id:
                if self.zone_cooldown_timer <= 0:
                    self.last_zone_id = current_room_id
                    self.zone_cooldown_timer = BLOOM_COOLDOWN
                    zone_name = self._resolve_room_area_name(current_room_id)
                    self.trigger_bloom(zone_name, priority=1)
        
        if self.zone_cooldown_timer > 0: self.zone_cooldown_timer -= dt
        if self.bloom_timer > 0: self.bloom_timer -= dt
        else: self.bloom_priority = 0

        # Sanctuary Management
        if getattr(self.world, 'name', '') == "sanctuary":
            if not self.sanctuary_reset_complete:
                self.on_enter_sanctuary()
                self.sanctuary_reset_complete = True
        else: self.sanctuary_reset_complete = False

        if getattr(self, 'chronicle_dialog', None):
            self._handle_chronicle_dialog_ui(actions, attack_pressed)
        elif getattr(self, 'binder_dialog', None):
            self._handle_binder_dialog_ui(actions, attack_pressed, audio_manager)
        elif self.active_dialogue:
            self._handle_dialogue_ui(actions, attack_pressed, audio_manager)
        elif getattr(self, 'active_choice', None):
            self._handle_choice_ui(actions, attack_pressed)
        
        # Pickup Logic
        player_rect = (self.player.x, self.player.y, self.player.width, self.player.height)
        nearby = self.world.get_nearby_interactables(player_rect)
        self.player.current_interactable = nearby[0] if nearby else None
        
        for item in self.loot[:]:
            if check_aabb_collision(player_rect, item.get_rect()):
                item.execute_pickup(self)
                self.loot.remove(item)
                if audio_manager: audio_manager.play_sfx("page_pickup.ogg")

    def _handle_dialogue_ui(self, actions, attack_pressed, audio_manager):
        active_respite = getattr(self, 'active_respite', None)
        if attack_pressed and not active_respite:
            self.active_dialogue = None
            self.input_debounce_timer = 0.2
            self.save_stats(wait=True)
            return
        if active_respite:
            if actions.get("cancel"):
                self.close_respite_menu()
                if self.network_manager.network_mode == "CLIENT":
                    threading.Thread(
                        target=self.network_manager.send_full_state,
                        args=(self.get_full_player_state(),),
                        daemon=True,
                    ).start()
                self.save_stats(wait=True)
                return

            if actions.get("respite_rest"):
                active_respite.execute_rest(self, audio_manager=audio_manager)
                return

            move_dir = actions.get('move', (0, 0))
            if self.menu_nav_cooldown <= 0:
                if move_dir[1] > 0.6:
                    self.respite_selection_idx = self._get_next_respite_idx(self.respite_selection_idx)
                    self.menu_nav_cooldown = 0.10
                elif move_dir[1] < -0.6:
                    self.respite_selection_idx = self._get_prev_respite_idx(self.respite_selection_idx)
                    self.menu_nav_cooldown = 0.10
            if attack_pressed and not self.input_ratchet_latched:
                self.input_ratchet_latched = True
                if self.respite_selection_idx == 0:
                    active_respite.execute_rest(self, audio_manager=audio_manager)
                elif 1 <= self.respite_selection_idx <= 2 and self.player.has_rested_this_session:
                    info = self.get_staged_respite_info()
                    pages = self.stats.data["lifetime_stats"].get("pages_collected", 0) if self.stats else 0
                    available = pages - info["total_staged_cost"]
                    if self.respite_selection_idx == 1:
                        if available >= info["next_prowess_cost"]:
                            self.respite_upgrades[1] += 1
                            if audio_manager:
                                audio_manager.play_sfx("menu_confirm.ogg")
                    elif self.respite_selection_idx == 2:
                        if available >= info["next_fort_cost"]:
                            self.respite_upgrades[2] += 1
                            if audio_manager:
                                audio_manager.play_sfx("menu_confirm.ogg")
                elif self.respite_selection_idx == 4:
                    success = active_respite.execute_finalize_upgrades(self, audio_manager=audio_manager)
                    if success:
                        self.player.has_rested_this_session = False
                        self.respite_selection_idx = 5
                elif self.respite_selection_idx == 5:
                    self.close_respite_menu()
                    if self.network_manager.network_mode == "CLIENT":
                        threading.Thread(
                            target=self.network_manager.send_full_state,
                            args=(self.get_full_player_state(),),
                            daemon=True,
                        ).start()
                    self.save_stats(wait=True)

    def _get_next_respite_idx(self, current_idx):
        """Helper to find the next valid Respite menu index."""
        idx = (current_idx + 1) % 6
        has_rested = self.player.has_rested_this_session
        # Skip rules:
        # 1. Skip 1, 2, 3 if not rested
        # 2. Always skip 3 (unused)
        while True:
            if idx == 3: idx = (idx + 1) % 6; continue
            if not has_rested and (1 <= idx <= 3): idx = (idx + 1) % 6; continue
            break
        return idx

    def _get_prev_respite_idx(self, current_idx):
        """Helper to find the previous valid Respite menu index."""
        idx = (current_idx - 1) % 6
        has_rested = self.player.has_rested_this_session
        while True:
            if idx == 3: idx = (idx - 1) % 6; continue
            if not has_rested and (1 <= idx <= 3): idx = (idx - 1) % 6; continue
            break
        return idx

    def _handle_choice_ui(self, actions, attack_pressed):
        move_dir = actions.get('move', (0, 0))
        if not self.input_ratchet_latched and self.menu_nav_cooldown <= 0:
            if move_dir[0] > 0.5: self.active_choice["selected_index"] = 1; self.input_ratchet_latched = True; self.menu_nav_cooldown = 0.2
            elif move_dir[0] < -0.5: self.active_choice["selected_index"] = 0; self.input_ratchet_latched = True; self.menu_nav_cooldown = 0.2
        if attack_pressed:
            choice = self.active_choice["options"][self.active_choice["selected_index"]]
            for s, v in choice["modifiers"].items(): self.player.stats[s] = self.player.stats.get(s, 0) + v
            self.active_choice = None
            if self.network_manager.network_mode == "CLIENT":
                threading.Thread(target=self.network_manager.send_full_state, args=(self.get_full_player_state(),), daemon=True).start()

    def play_chronicler_mumble(self, emotion="neutral"):
        """Play the Chronicler's closed-mouth mumble cue for the given emotion."""
        from constants import CHRONICLER_MUMBLE_SFX
        if getattr(self, 'audio_manager', None):
            sfx_name = CHRONICLER_MUMBLE_SFX.get(emotion, CHRONICLER_MUMBLE_SFX["neutral"])
            self.audio_manager.play_sfx(sfx_name)

    def sync_player_binder_scripts(self, refill_in_sanctuary=False):
        """Compile equipped Binder Scripts from stats and apply modifiers to self.player."""
        if not getattr(self, "player", None):
            return
        from engine.binder_scripts import (
            compile_binder_scripts,
            ensure_binder_persistence,
            record_syntax_conflicts,
        )
        binder_state, story_flags = ensure_binder_persistence(getattr(self, "stats", None))
        comp = compile_binder_scripts(list(binder_state.get("equipped") or []))
        record_syntax_conflicts(binder_state, story_flags, comp)
        self.player.apply_script_modifiers(comp["modifiers"], refill_in_sanctuary=refill_in_sanctuary)

    def open_binder_dialog(self, binder_npc=None):
        """Open The Binder's Script Weaving Loom modal in Sanctuary."""
        from engine.binder_scripts import ensure_binder_persistence, select_binder_dialogue_node
        ensure_binder_persistence(getattr(self, "stats", None))
        node = select_binder_dialogue_node(getattr(self, "stats", None))
        self.binder_dialog = {
            "mode": "prompt",
            "prompt_selection": 0,
            "selection": 0,
            "status_msg": node.get("text", ""),
            "weave_feedback": "",
            "dialogue_id": node.get("id", "binder_default"),
            "emotion": node.get("emotion", "neutral"),
            "npc": binder_npc,
        }
        self.input_debounce_timer = 0.2
        self.input_ratchet_latched = True
        self.menu_nav_cooldown = 0.2
        self.play_chronicler_mumble(node.get("emotion", "neutral"))

    def close_binder_dialog(self):
        """Close the Binder Weaving modal, sync player modifiers, and persist stats."""
        self.binder_dialog = None
        self.input_debounce_timer = 0.2
        self.sync_player_binder_scripts(refill_in_sanctuary=getattr(self, "in_sanctuary", True))
        if hasattr(self, "network_manager") and self.network_manager.network_mode == "CLIENT":
            threading.Thread(
                target=self.network_manager.send_full_state,
                args=(self.get_full_player_state(),),
                daemon=True,
            ).start()
        self.save_stats(wait=True)

    def get_binder_dialog_options(self):
        """Return interactive rows for the Binder Weaving UI (10 scripts + Close Loom)."""
        from engine.binder_scripts import get_catalog_view
        rows = get_catalog_view(getattr(self, "stats", None))
        options = []
        for row in rows:
            options.append(
                {
                    "action": "script",
                    "script_id": row["id"],
                    "name": row["name"],
                    "stat": row["stat"],
                    "value": row["value"],
                    "cost": row["cost"],
                    "summary": row["summary"],
                    "desc": row["desc"],
                    "unlocked": row["unlocked"],
                    "equipped": row["equipped"],
                    "compile_status": row["compile_status"],
                    "overridden_by_name": row["overridden_by_name"],
                }
            )
        options.append({"action": "close", "name": "Close Loom", "summary": "Return to the Scriptorium"})
        return options

    def _handle_binder_dialog_ui(self, actions, attack_pressed, audio_manager=None):
        """Handle keyboard/gamepad navigation inside the 3-mode Binder modal (prompt / consult / weave)."""
        dialog = getattr(self, "binder_dialog", None)
        if not dialog:
            return

        if actions.get("cancel"):
            self.close_binder_dialog()
            return

        mode = str(dialog.get("mode", "weave") or "weave")
        move_dir = actions.get("move", (0, 0))

        if mode == "prompt":
            if not self.input_ratchet_latched and self.menu_nav_cooldown <= 0:
                if move_dir[1] > 0.6:
                    dialog["prompt_selection"] = (int(dialog.get("prompt_selection", 0)) + 1) % 2
                    self.input_ratchet_latched = True
                    self.menu_nav_cooldown = 0.18
                elif move_dir[1] < -0.6:
                    dialog["prompt_selection"] = (int(dialog.get("prompt_selection", 0)) - 1) % 2
                    self.input_ratchet_latched = True
                    self.menu_nav_cooldown = 0.18

            if attack_pressed and not self.input_ratchet_latched:
                from engine.binder_scripts import select_binder_dialogue_node
                self.input_ratchet_latched = True
                prompt_sel = int(dialog.get("prompt_selection", 0)) % 2
                if prompt_sel == 0:
                    node = select_binder_dialogue_node(getattr(self, "stats", None))
                    dialog["status_msg"] = node.get("text", dialog.get("status_msg", ""))
                    dialog["dialogue_id"] = node.get("id", dialog.get("dialogue_id", "binder_default"))
                    dialog["emotion"] = node.get("emotion", dialog.get("emotion", "neutral"))
                    dialog["mode"] = "consult"
                    self.play_chronicler_mumble(dialog["emotion"])
                else:
                    dialog["mode"] = "weave"
                    dialog["selection"] = 0
                    dialog["weave_feedback"] = ""
                if audio_manager:
                    audio_manager.play_sfx("menu_confirm.ogg")
            return

        if mode == "consult":
            if attack_pressed and not self.input_ratchet_latched:
                self.input_ratchet_latched = True
                self.close_binder_dialog()
            return

        options = self.get_binder_dialog_options()
        if not options:
            self.close_binder_dialog()
            return

        if not self.input_ratchet_latched and self.menu_nav_cooldown <= 0:
            if move_dir[1] > 0.6:
                dialog["selection"] = (int(dialog.get("selection", 0)) + 1) % len(options)
                self.input_ratchet_latched = True
                self.menu_nav_cooldown = 0.18
            elif move_dir[1] < -0.6:
                dialog["selection"] = (int(dialog.get("selection", 0)) - 1) % len(options)
                self.input_ratchet_latched = True
                self.menu_nav_cooldown = 0.18

        if attack_pressed and not self.input_ratchet_latched:
            from engine.binder_scripts import toggle_equip_script, weave_script
            self.input_ratchet_latched = True
            sel_idx = min(max(0, int(dialog.get("selection", 0))), len(options) - 1)
            chosen = options[sel_idx]
            act = chosen.get("action")

            if act == "close":
                self.close_binder_dialog()
                return

            sid = chosen["script_id"]
            if not chosen["unlocked"]:
                ok, msg = weave_script(self.stats, sid)
                if ok:
                    _, eq_msg, _ = toggle_equip_script(
                        self.stats,
                        self.player,
                        sid,
                        in_sanctuary=getattr(self, "in_sanctuary", True),
                    )
                    msg = f"{msg} {eq_msg}"
            else:
                ok, msg, _ = toggle_equip_script(
                    self.stats,
                    self.player,
                    sid,
                    in_sanctuary=getattr(self, "in_sanctuary", True),
                )
            dialog["status_msg"] = msg
            dialog["weave_feedback"] = msg
            if ok and audio_manager:
                audio_manager.play_sfx("menu_confirm.ogg")
            if hasattr(self, "network_manager") and self.network_manager.network_mode == "CLIENT":
                threading.Thread(
                    target=self.network_manager.send_full_state,
                    args=(self.get_full_player_state(),),
                    daemon=True,
                ).start()
            self.save_stats(wait=True)

    def open_chronicle_biome_dialog(self, portal=None):
        """Open the 5-of-7 Unbound Chronicle biome draft dialog (Acts 1–5)."""
        from constants import MAX_ACTS
        self.chronicle_dialog = {
            "step": 1,
            "max_steps": MAX_ACTS,
            "selection": 0,
            "choices": [None] * MAX_ACTS,
            "act1_choice": None,
            "act2_choice": None,
            "portal": portal,
        }
        self.input_debounce_timer = 0.2
        self.input_ratchet_latched = True
        self.menu_nav_cooldown = 0.2
        if getattr(self, 'audio_manager', None):
            self.audio_manager.play_sfx("chronicle_open.ogg")

    def get_chronicle_dialog_options(self):
        """Return selectable options for the active 5-of-7 Unbound Chronicle draft step."""
        dialog = getattr(self, 'chronicle_dialog', None)
        if not dialog:
            return []
        from constants import (
            BIOME_DISPLAY_NAMES,
            BIOME_THEMES,
            CHRONICLE_BIOME_ROSTER,
            MAX_ACTS,
            get_act_saturation,
        )

        step = max(1, min(MAX_ACTS, int(dialog.get("step", 1))))
        choices = list(dialog.get("choices") or [None] * MAX_ACTS)
        while len(choices) < MAX_ACTS:
            choices.append(None)
        if dialog.get("act1_choice") and not choices[0]:
            choices[0] = dialog["act1_choice"]
        if dialog.get("act2_choice") and len(choices) > 1 and not choices[1]:
            choices[1] = dialog["act2_choice"]
        dialog["choices"] = choices

        prior_picks = {
            c: idx + 1
            for idx, c in enumerate(choices[: step - 1])
            if c and c != "random"
        }
        sat = get_act_saturation(step)
        options = [
            {
                "label": "Random",
                "value": "random",
                "enabled": True,
                "theme": "Unbound Chance",
                "saturation_label": sat["label"],
                "selected_act": None,
            }
        ]
        if getattr(self, 'debug_biome_select', True):
            for biome_id in CHRONICLE_BIOME_ROSTER:
                picked_act = prior_picks.get(biome_id)
                enabled = picked_act is None
                options.append({
                    "label": BIOME_DISPLAY_NAMES.get(biome_id, biome_id),
                    "value": biome_id,
                    "enabled": enabled,
                    "theme": BIOME_THEMES.get(biome_id, ""),
                    "saturation_label": sat["label"],
                    "selected_act": picked_act,
                })
        if step == 1:
            options.append({"label": "Cancel", "value": "cancel", "enabled": True})
        else:
            options.append({"label": f"Back to Act {step - 1}", "value": "back", "enabled": True})
        return options

    def cancel_chronicle_dialog(self):
        """Step back to the previous Act folio, or close the Chronicle dialog from Step 1."""
        dialog = getattr(self, 'chronicle_dialog', None)
        if not dialog:
            return
        from constants import MAX_ACTS
        step = int(dialog.get("step", 1))
        if step > 1:
            choices = list(dialog.get("choices") or [None] * MAX_ACTS)
            while len(choices) < MAX_ACTS:
                choices.append(None)
            if 0 <= step - 1 < len(choices):
                choices[step - 1] = None
            dialog["choices"] = choices
            dialog["step"] = step - 1
            dialog["selection"] = 0
            dialog["act1_choice"] = choices[0]
            dialog["act2_choice"] = choices[1] if len(choices) > 1 else None
        else:
            self.chronicle_dialog = None
        self.input_debounce_timer = 0.2

    def _step_chronicle_selection(self, options, current_idx, delta):
        """Advance selection index over enabled options."""
        if not options:
            return 0
        count = len(options)
        idx = (current_idx + delta) % count
        for _ in range(count):
            if options[idx].get("enabled", True):
                return idx
            idx = (idx + delta) % count
        return current_idx

    def _handle_chronicle_dialog_ui(self, actions, attack_pressed):
        """Handle keyboard/gamepad navigation for the 5-step Unbound Chronicle biome draft modal."""
        dialog = getattr(self, 'chronicle_dialog', None)
        if not dialog:
            return
        options = self.get_chronicle_dialog_options()
        if not options:
            self.chronicle_dialog = None
            return

        if actions.get("cancel"):
            self.cancel_chronicle_dialog()
            return

        move_dir = actions.get('move', (0, 0))
        if not self.input_ratchet_latched and self.menu_nav_cooldown <= 0:
            if move_dir[1] > 0.6:
                dialog["selection"] = self._step_chronicle_selection(options, dialog.get("selection", 0), 1)
                self.input_ratchet_latched = True
                self.menu_nav_cooldown = 0.2
            elif move_dir[1] < -0.6:
                dialog["selection"] = self._step_chronicle_selection(options, dialog.get("selection", 0), -1)
                self.input_ratchet_latched = True
                self.menu_nav_cooldown = 0.2

        if attack_pressed and not self.input_ratchet_latched:
            from constants import MAX_ACTS
            self.input_ratchet_latched = True
            sel_idx = min(max(0, dialog.get("selection", 0)), len(options) - 1)
            chosen = options[sel_idx]
            if not chosen.get("enabled", True):
                return
            val = chosen["value"]
            step = int(dialog.get("step", 1))
            max_steps = int(dialog.get("max_steps", MAX_ACTS))
            if val == "cancel":
                self.chronicle_dialog = None
                self.input_debounce_timer = 0.2
                return
            if val == "back":
                self.cancel_chronicle_dialog()
                self.input_debounce_timer = 0.15
                return

            choices = list(dialog.get("choices") or [None] * max_steps)
            while len(choices) < max_steps:
                choices.append(None)
            choices[step - 1] = val
            dialog["choices"] = choices
            dialog["act1_choice"] = choices[0]
            dialog["act2_choice"] = choices[1] if len(choices) > 1 else None

            if step < max_steps:
                dialog["step"] = step + 1
                dialog["selection"] = 0
                self.input_debounce_timer = 0.15
            else:
                self.confirm_chronicle_run(choices, portal=dialog.get("portal"))

    def confirm_chronicle_run(self, act1_choice="random", act2_choice="random", portal=None):
        """Close the Chronicle dialog and launch the 5-Act Unbound Chronicle run with Ink & Fog warp."""
        self.chronicle_dialog = None
        self.input_debounce_timer = 0.2
        if getattr(self, 'audio_manager', None):
            self.audio_manager.play_sfx("chronicle_open.ogg")

        def _launch(gs):
            if isinstance(act1_choice, (list, tuple, dict)):
                gs.start_chronicle_run(act1_choice)
            else:
                gs.start_two_act_run(act1_choice, act2_choice)

        target = portal if portal is not None else "macro_world"
        started = self.start_warp(target, callback=_launch, confirmed=True)
        if not started:
            _launch(self)

    def _load_generated_world_from_path(
        self,
        path,
        world_name,
        reset_progress=True,
        hp_multiplier=1.0,
        damage_multiplier=1.0,
        empowered=None,
        speed_multiplier=1.0,
        cooldown_multiplier=1.0,
    ):
        """Load a serialized world JSON into self.world and reset weather/camera."""
        from engine.world import World, LevelLoader
        from constants import TILE_SIZE

        if reset_progress:
            self.world_debris = []
            self.slime_pools = []
            self.loot = []
            self.destroyed_prop_ids.clear()
            self.defeated_miniboss_ids.clear()

        self.world = World(world_name)
        (
            self.world.grid,
            self.world.interactables,
            self.world.warp_tiles,
            self.world.player_start,
            self.world.enemies,
            self.world.boss_coords_list,
            self.world.module_sockets,
        ) = LevelLoader.load_json_map(
            path,
            defeated_ids=self.defeated_miniboss_ids,
            hp_multiplier=hp_multiplier,
            damage_multiplier=damage_multiplier,
            empowered=empowered,
            speed_multiplier=speed_multiplier,
            cooldown_multiplier=cooldown_multiplier,
        )
        self.enemies = self.world.enemies

        if self.player:
            self.player.x, self.player.y = self.world.player_start
            self.player.vx = 0
            self.player.vy = 0
            self.player.is_exposed = False
            self.player.alpha = 255

        if hasattr(self, 'weather_manager'):
            self.weather_manager.reset(boss_coords_list=self.world.boss_coords_list)
            self.active_safe_radius = self.weather_manager.active_safe_radius
            self.bleed_state = self.weather_manager.bleed_state
            self.current_boss_coords = self.weather_manager.get_current_boss_coords()

        if hasattr(self, 'camera') and self.world.grid:
            self.camera.world_w = len(self.world.grid[0]) * TILE_SIZE
            self.camera.world_h = len(self.world.grid) * TILE_SIZE
            if self.player:
                self.camera.instant_center(self.player.get_center())

        LevelLoader.link_actors_to_routes(self)

    def start_chronicle_run(self, choices=None):
        """Generate all 5 Act single-biome worlds upfront and enter Act 1."""
        import json
        from constants import get_generated_world_path, get_act_saturation
        from engine.world_generator import generate_chronicle_worlds

        bundle = generate_chronicle_worlds(choices)
        self.act_worlds = dict(bundle["act_worlds"])
        self.act1_world_data = self.act_worlds.get(1)
        self.act2_world_data = self.act_worlds.get(2)
        self.run_biomes = dict(bundle["run_biomes"])
        self.current_act = 1
        sat1 = get_act_saturation(1)
        self.empowered_act = bool(sat1["empowered"])
        self.act_warp_target = None
        self.night_boss_spawned = False
        self.last_zone_id = None
        if hasattr(self, "marginalia_engine") and self.marginalia_engine:
            self.marginalia_engine.reset(self)

        path = get_generated_world_path()
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.act1_world_data, f)

        self._load_generated_world_from_path(
            path,
            "generated_world",
            reset_progress=True,
            hp_multiplier=float(sat1["hp_multiplier"]),
            damage_multiplier=float(sat1["damage_multiplier"]),
            empowered=bool(sat1["empowered"]),
            speed_multiplier=float(sat1.get("speed_multiplier", 1.0)),
            cooldown_multiplier=float(sat1.get("cooldown_multiplier", 1.0)),
        )
        if hasattr(self, "weather_manager") and self.weather_manager:
            self.weather_manager.rain_dps = float(sat1["rain_dps"])
        self.in_sanctuary = False
        self.host_in_run = True
        self.waiting_for_host_run = False
        if self.stats:
            self.stats.data["active_session_in_progress"] = True
            self.stats.data.pop("last_death_event", None)
            story_flags = self.stats.data.get("story_flags")
            if isinstance(story_flags, dict):
                story_flags.pop("last_death_event", None)
        self.trigger_bloom("ACT I: THE FIRST DRAFT", priority=2)
        return self.run_biomes

    def start_two_act_run(self, act1_choice="random", act2_choice="random", *extra_choices):
        """Generate Act 1..5 single-biome worlds upfront and enter Act 1."""
        if isinstance(act1_choice, (list, tuple, dict)) and act2_choice == "random" and not extra_choices:
            return self.start_chronicle_run(act1_choice)
        return self.start_chronicle_run([act1_choice, act2_choice] + list(extra_choices))

    def transition_to_act(self, act_number: int, legacy_act2_scaling: bool = False):
        """Warp into the pre-generated Act N world (2..5) while preserving player progression."""
        import json
        from constants import (
            get_generated_world_path,
            get_act_saturation,
            ACT2_HP_MULTIPLIER,
            ACT2_DAMAGE_MULTIPLIER,
            ACT2_ESCALATION_BANNER,
            ACT2_ESCALATION_SFX,
            MAX_ACTS,
        )

        target_act = max(2, min(MAX_ACTS, int(act_number)))
        world_data = getattr(self, "act_worlds", {}).get(target_act)
        if world_data is None and target_act == 2:
            world_data = self.act2_world_data
        if not world_data:
            return False

        is_client = (self.network_manager.network_mode == "CLIENT")
        world_name = "generated_world_client" if is_client else "generated_world"
        path = get_generated_world_path()
        if is_client:
            path = path.replace(".json", "_client.json")

        with open(path, 'w', encoding='utf-8') as f:
            json.dump(world_data, f)

        sat = get_act_saturation(target_act)
        spd_mult = float(sat.get("speed_multiplier", 1.0))
        cd_mult = float(sat.get("cooldown_multiplier", 1.0))
        if legacy_act2_scaling and target_act == 2:
            hp_mult = ACT2_HP_MULTIPLIER
            dmg_mult = ACT2_DAMAGE_MULTIPLIER
            empowered = True
            banner = ACT2_ESCALATION_BANNER
        else:
            hp_mult = float(sat["hp_multiplier"])
            dmg_mult = float(sat["damage_multiplier"])
            empowered = bool(sat["empowered"])
            banner = str(sat["banner"])

        self.empowered_act = empowered
        self._load_generated_world_from_path(
            path,
            world_name,
            reset_progress=True,
            hp_multiplier=hp_mult,
            damage_multiplier=dmg_mult,
            empowered=empowered,
            speed_multiplier=spd_mult,
            cooldown_multiplier=cd_mult,
        )
        if hasattr(self, "weather_manager") and self.weather_manager:
            self.weather_manager.rain_dps = float(sat["rain_dps"])
        self.current_act = target_act
        self.act_warp_target = None
        self.night_boss_spawned = False
        self.last_zone_id = None
        if (
            hasattr(self, "warp_controller")
            and self.warp_controller
            and getattr(self.warp_controller, "stage", "IDLE") == "DEPARTURE"
        ):
            self.warp_controller.stage = "IDLE"
        if hasattr(self, "marginalia_engine") and self.marginalia_engine:
            self.marginalia_engine.active_event = None
        self.return_anchor_stack.clear()
        self.player_breadcrumbs.clear()
        if hasattr(self, "weather_manager") and self.weather_manager:
            self.weather_manager.paused = False
        self.trigger_bloom(banner, priority=3)
        if getattr(self, 'audio_manager', None):
            self.audio_manager.play_sfx(ACT2_ESCALATION_SFX)
        return True

    def transition_to_act2(self):
        """Legacy helper: transition into Act 2 with 2.0x escalation scaling and banner."""
        return self.transition_to_act(2, legacy_act2_scaling=True)

    def _handle_victory_conditions(self, dt):
        del dt
        if getattr(self.world, 'name', '') not in ("final_boss", "night_boss_arena"):
            return

        final_boss_dead = not any(getattr(e, 'name', '') == "The Final Author" for e in self.enemies)
        last_res = getattr(self.stats, 'data', {}).get("last_run_result")
        if final_boss_dead and last_res not in ("VICTORY", "STITCH_VICTORY"):
            if self.stats:
                from constants import SCRAPS_REWARD_FINAL_AUTHOR
                from engine.binder_scripts import ensure_binder_persistence
                _, story_flags = ensure_binder_persistence(self.stats)
                if hasattr(self.stats, "add_margin_scraps"):
                    self.stats.add_margin_scraps(SCRAPS_REWARD_FINAL_AUTHOR)
                else:
                    self.stats.data["margin_scraps"] = int(
                        self.stats.data.get("margin_scraps", 0)
                    ) + SCRAPS_REWARD_FINAL_AUTHOR
                self.stats.increment("wins_chapters_cleared", 1)
                self.weather_manager.trigger_dilution()
                if story_flags.get("perfect_stitch_completed", False):
                    self.stats.data["last_run_result"] = "STITCH_VICTORY"
                    story_flags["ink_bleed_halted"] = True
                    self.trigger_bloom("THE INK-BLEED HALTED", priority=3)
                else:
                    self.stats.data["last_run_result"] = "VICTORY"
                    self.trigger_bloom("CHAPTER COMPLETE", priority=2)
        if getattr(self.stats, 'data', {}).get("last_run_result") in ("VICTORY", "STITCH_VICTORY"):
            if (self.bleed_state in ("DILUTION", "APPENDIX")) and self.weather_manager.timer <= 0:
                if not (hasattr(self, 'warp_controller') and self.warp_controller.is_active()):
                    self.start_warp("sanctuary")

    def close_respite_menu(self) -> None:
        """Close any open Respite modal and reset staged session state."""
        had_respite = getattr(self, "active_respite", None) is not None
        self.active_respite = None
        if had_respite or (
            isinstance(getattr(self, "active_dialogue", None), dict)
            and self.active_dialogue.get("speaker") == "Respite Anchor"
        ):
            self.active_dialogue = None
        self.respite_upgrades = {1: 0, 2: 0}
        self.respite_selection_idx = 0
        self.respite_marked_idx = -1
        if getattr(self, "player", None) is not None:
            self.player.has_rested_this_session = False

    def start_warp(self, target, callback=None, confirmed=False):
        """Initiate the three-stage Ink & Fog transit sequence."""
        self.close_respite_menu()
        target_name = getattr(target, 'target_name', target if isinstance(target, str) else None)
        is_client = hasattr(self, 'network_manager') and self.network_manager.network_mode == "CLIENT"
        if not confirmed and not is_client and target_name == "macro_world":
            portal_obj = target if hasattr(target, 'target_name') else None
            if getattr(self, "debug_text_enabled", False):
                self.open_chronicle_biome_dialog(portal=portal_obj)
                return False
            from constants import MAX_ACTS
            self.confirm_chronicle_run(["random"] * MAX_ACTS, portal=portal_obj)
            return bool(
                hasattr(self, "warp_controller")
                and self.warp_controller
                and self.warp_controller.is_active()
            )
        if hasattr(self, 'warp_controller') and self.warp_controller and self.player:
            return self.warp_controller.start_warp(self.player, target, callback=callback)
        return False

    def on_enter_sanctuary(self):
        """Rule: Absolute state purification upon entering the Sanctuary hub."""
        from constants import PLAYER_MAX_HP, FLASK_MAX_CHARGES, SWORD_DAMAGE
        self.player.is_exposed = False
        self.player.alpha = 255
        self.player.damage_mitigation = 0.0
        if hasattr(self.player, "reset_frost_state"):
            self.player.reset_frost_state()
        
        # Reset stats/level to starting levels
        self.player.stats = {
            "attack_modifier": 0,
            "max_hp_modifier": 0,
            "edification": 1
        }
        
        self.player.weapons = [{"name": "Initial Quill", "damage": SWORD_DAMAGE}]
        self.player.active_weapon_idx = 0
        self.sync_player_binder_scripts(refill_in_sanctuary=True)
        self.player.hp = float(self.player.max_hp)
        self.player.flask_charges = int(FLASK_MAX_CHARGES)
        self.in_sanctuary = True
        if not (
            hasattr(self, "network_manager")
            and self.network_manager.network_mode == "CLIENT"
            and getattr(self, "host_in_run", False)
        ):
            self.waiting_for_host_run = False
        if hasattr(self, "network_manager") and self.network_manager.network_mode != "CLIENT":
            self.host_in_run = False
            self.waiting_scholars = 0
        
        # Purification: Clear run state and persistent world changes when entering Hub
        from constants import MAX_ACTS
        self.world_debris = []
        self.slime_pools = []
        self.destroyed_prop_ids.clear()
        self.chronicle_dialog = None
        self.binder_dialog = None
        self.current_act = 0
        self.run_biomes = {f"act{i}": None for i in range(1, MAX_ACTS + 1)}
        self.act_worlds = {}
        self.act1_world_data = None
        self.act2_world_data = None
        self.act_warp_target = None
        self.night_boss_spawned = False
        self.empowered_act = False
        self.audio_manager = None
        self.pending_remote_sfx.clear()
        self._remote_combat_seqs.clear()
        if hasattr(self, "marginalia_engine") and self.marginalia_engine:
            self.marginalia_engine.reset(self)
        for attr_t in (
            "storm_immunity_timer",
            "pristine_ink_shield_timer",
            "attack_speed_buff_timer",
            "duel_debuff_timer",
        ):
            setattr(self.player, attr_t, 0.0)

        if self.stats:
            if "lifetime_stats" in self.stats.data:
                self.stats.data["lifetime_stats"]["pages_collected"] = 0
            self.stats.data["run_state"] = None
            self.stats.data["active_session_in_progress"] = False

        # Weather Reset: Full system restore for hub safety
        if hasattr(self, 'weather_manager'):
            self.weather_manager.reset(boss_coords_list=None)
            
        self.sanctuary_reset_complete = True
        self.sanctuary_door_open = False
        self.save_stats(wait=True)

    def on_network_disconnect(self):
        print("[NETWORK] Connection lost. Warping to Sanctuary.")
        self.trigger_bloom("CONNECTION LOST", priority=2)
        survivors = list(getattr(self.network_manager, "last_survivor_peer_ids", []))
        if self.network_manager.peer_id not in survivors:
            survivors.append(self.network_manager.peer_id)
        survivors = sorted(set(survivors))
        survivor_addrs = dict(getattr(self.network_manager, "last_survivor_addrs", {}))
        was_connected = bool(getattr(self.network_manager, "_ever_connected", False))
        last_server_addr = self.network_manager.server_address

        if self.network_manager.network_mode != "OFFLINE":
            self.network_manager.stop_network(clear_inbox=False)

        from engine.maps import create_world
        self.world = create_world("sanctuary")
        self.in_sanctuary = True
        self.host_in_run = False
        self.waiting_for_host_run = False
        self.waiting_scholars = 0
        # Phase 4: Sync camera bounds
        if hasattr(self, 'camera'):
            self.camera.world_w = len(self.world.grid[0]) * TILE_SIZE
            self.camera.world_h = len(self.world.grid) * TILE_SIZE
            self.camera.instant_center(self.player.get_center())
        
        self.on_enter_sanctuary()
        self.respawn_player()

        # Disruptive Host Promotion: lowest peer_id survivor auto-hosts; others reconnect
        if getattr(self, "online_mode", True) and was_connected and survivors:
            lowest_peer_id = survivors[0]
            if self.network_manager.peer_id == lowest_peer_id:
                print(f"[NETWORK] Promoting self ({self.network_manager.peer_id}) to HOST in Sanctuary.")
                self.network_manager.start_hosting()
            else:
                target_ip = survivor_addrs.get(lowest_peer_id) or last_server_addr or "127.0.0.1"
                print(
                    f"[NETWORK] Waiting for promoted Host {lowest_peer_id} at {target_ip} "
                    f"(self={self.network_manager.peer_id})."
                )
                import threading

                def _reconnect_to_promoted():
                    deadline = time.time() + 3.0
                    while time.time() < deadline:
                        if self.network_manager.connect_to_host(target_ip):
                            self.network_manager.send_full_state(self.get_full_player_state())
                            return
                        time.sleep(0.1)

                threading.Thread(
                    target=_reconnect_to_promoted, name="NetReconnectPromotedHost", daemon=True
                ).start()

    def deallocate(self):
        self.player = self.world = None
        self.enemies = self.loot = self.world_debris = []
        self.slime_pools = []
        self.destroyed_prop_ids = set()
        self.active_dialogue = self.active_choice = self.active_respite = None

    def trigger_bloom(self, text, priority=1):
        if priority >= self.bloom_priority or self.bloom_timer <= 0:
            from constants import BLOOM_TOTAL_DURATION
            self.bloom_text = text
            self.bloom_timer = BLOOM_TOTAL_DURATION
            self.bloom_priority = priority

    def hydrate_from_disk(self):
        """Phase 2: Hydrate runtime objects from StatisticsTracker.data['run_state']."""
        from engine.stats import StatisticsTracker
        from engine.maps import create_world
        
        # Priority: If we already have stats with a run, use it. Otherwise load from disk.
        if not self.stats or not self.stats.data.get("run_state"):
            try:
                if getattr(self, "stats_path", None) is not None:
                    self.stats = StatisticsTracker.load(self.stats_path)
                else:
                    self.stats = StatisticsTracker.load()
            except Exception:
                self.stats = StatisticsTracker()

        # Engine Revision Guard: Do not hydrate incompatible saves from older engine revisions
        if self.stats and not getattr(self.stats, "is_revision_compatible", True):
            self.reset_to_new_game()
            return
        
        # Update Network Identity and reset Debug Text Preference to OFF on Continue/hydrate
        self.sanctuary_door_open = False
        self.debug_text_enabled = False
        self.debug_biome_select = False
        if self.stats:
            from constants import normalize_keybindings
            self.stats.data["debug_text_enabled"] = False
            self.screen_shake_enabled = bool(self.stats.data.get("screen_shake_enabled", True))
            self.keybindings = normalize_keybindings(self.stats.data.get("keybindings"))
            self.stats.data["keybindings"] = dict(self.keybindings)
            self.online_mode = bool(self.stats.data.get("online_mode", getattr(self, "online_mode", True)))
            if hasattr(self, 'network_manager'):
                self.network_manager.identity = self.stats.data.get("player_name", self.network_manager.identity)

        run_data = self.stats.data.get("run_state")
        if run_data:
            import os
            from constants import get_generated_world_path
            world_name = run_data.get("world_name", "sanctuary")
            if world_name == "generated_world" and not os.path.exists(get_generated_world_path()):
                # Generated temp map no longer exists on disk; resume safely in Sanctuary
                world_name = "sanctuary"
                run_data = None

        if run_data:
            world_name = run_data.get("world_name", "sanctuary")
            self.world_debris = run_data.get("world_debris", [])
            self.defeated_miniboss_ids = set(run_data.get("defeated_miniboss_ids", []))
            self.destroyed_prop_ids = set(run_data.get("destroyed_prop_ids", []))
            self.world = create_world(world_name, saved_enemies=run_data.get("enemies", []), defeated_ids=self.defeated_miniboss_ids, destroyed_ids=self.destroyed_prop_ids)
            
            p_data = run_data.get("player", {})
            px = float(p_data.get("x", self.world.player_start[0]))
            py = float(p_data.get("y", self.world.player_start[1]))
            if world_name == "sanctuary":
                px, py = self.world.player_start
            self.player = Player(px, py)
            
            # Phase 4: Sync camera bounds
            if hasattr(self, 'camera'):
                self.camera.world_w = len(self.world.grid[0]) * TILE_SIZE
                self.camera.world_h = len(self.world.grid) * TILE_SIZE
                self.camera.instant_center(self.player.get_center())
            
            self.player.flask_charges = int(p_data.get("flask_charges", FLASK_MAX_CHARGES))
            self.player.active_weapon_idx = int(p_data.get("active_weapon_idx", 0))
            self.player.weapons = p_data.get("weapons", self.player.weapons)
            self.player.stats = p_data.get("stats", {})
            self.sync_player_binder_scripts(refill_in_sanctuary=(world_name == "sanctuary"))
            self.player.hp = min(float(self.player.max_hp), float(p_data.get("hp", self.player.max_hp)))
            self.enemies = [] if world_name == "sanctuary" else list(getattr(self.world, 'enemies', []))
            self.loot = []
            self.fading_entities = []
            self.damage_numbers = []
            from engine.weather import WeatherManager
            self.weather_manager = WeatherManager(boss_coords_list=getattr(self.world, 'boss_coords_list', None))
            self.weather_manager.from_dict(run_data.get("weather"))

            from constants import MAX_ACTS
            self.current_act = int(run_data.get("current_act", 0))
            self.empowered_act = bool(run_data.get("empowered_act", self.current_act >= 3))
            self.night_boss_spawned = bool(run_data.get("night_boss_spawned", False))
            raw_biomes = run_data.get("run_biomes")
            norm_biomes = {f"act{i}": None for i in range(1, MAX_ACTS + 1)}
            if isinstance(raw_biomes, dict):
                for k, v in raw_biomes.items():
                    if k in norm_biomes:
                        norm_biomes[k] = v
            elif isinstance(raw_biomes, (list, tuple)):
                for idx, v in enumerate(raw_biomes[:MAX_ACTS]):
                    norm_biomes[f"act{idx + 1}"] = v
            self.run_biomes = norm_biomes
            raw_worlds = run_data.get("act_worlds")
            if isinstance(raw_worlds, dict):
                self.act_worlds = {int(k): v for k, v in raw_worlds.items() if str(k).isdigit()}
            else:
                self.act_worlds = {}
            self.act1_world_data = self.act_worlds.get(1)
            self.act2_world_data = self.act_worlds.get(2)
            
            self.input_ratchet_latched = False
            self.menu_nav_cooldown = 0.0
            
            self.active_dialogue = None
            self.active_choice = None
            self.active_respite = None
            self.chronicle_dialog = None
            self.binder_dialog = None
            
            # Auto-Host Rule: Start hosting if resuming outside Sanctuary in Online mode
            if world_name not in ("sanctuary", "") and getattr(self, "online_mode", True):
                if hasattr(self, 'network_manager'):
                    if self.network_manager.network_mode == "OFFLINE":
                        self.network_manager.start_hosting()
        else:
            # Resume in Sanctuary while preserving persistent meta-progression stats
            self.defeated_miniboss_ids = set()
            self.destroyed_prop_ids = set()
            self.world = create_world("sanctuary", defeated_ids=self.defeated_miniboss_ids)
            self.player = Player(self.world.player_start[0], self.world.player_start[1])
            if hasattr(self, 'camera'):
                self.camera.world_w = len(self.world.grid[0]) * TILE_SIZE
                self.camera.world_h = len(self.world.grid) * TILE_SIZE
                self.camera.instant_center(self.player.get_center())
            self.enemies = []
            self.loot = []
            self.fading_entities = []
            self.world_debris = []
            self.slime_pools = []
            self.damage_numbers = []
            from engine.weather import WeatherManager
            self.weather_manager = WeatherManager(boss_coords_list=getattr(self.world, 'boss_coords_list', None))
            self.input_ratchet_latched = False
            self.menu_nav_cooldown = 0.0
            self.active_dialogue = None
            self.active_choice = None
            self.active_respite = None
            self.chronicle_dialog = None
            self.binder_dialog = None
            if self.stats:
                self.stats.data["run_state"] = None
                self.stats.data["active_session_in_progress"] = False
            self.sync_player_binder_scripts(refill_in_sanctuary=True)
            self.player.hp = float(self.player.max_hp)
            from engine.world import LevelLoader
            LevelLoader.link_actors_to_routes(self)

    def reset_to_new_game(self):
        from engine.maps import create_world
        from constants import ENGINE_REVISION
        self.debug_text_enabled = False
        self.debug_biome_select = False
        self.sanctuary_door_open = False
        if self.stats:
            from constants import normalize_keybindings
            self.stats.data["engine_revision"] = ENGINE_REVISION
            self.stats.is_revision_compatible = True
            self.stats.data["debug_text_enabled"] = False
            self.stats.data.setdefault("screen_shake_enabled", bool(getattr(self, "screen_shake_enabled", True)))
            self.screen_shake_enabled = bool(self.stats.data.get("screen_shake_enabled", True))
            self.keybindings = normalize_keybindings(
                self.stats.data.get("keybindings", getattr(self, "keybindings", None))
            )
            self.stats.data["keybindings"] = dict(self.keybindings)
            self.stats.data["lifetime_stats"]["pages_collected"] = 0
            self.stats.data["run_state"] = None
            self.stats.data["active_session_in_progress"] = False
            self.stats.data["last_run_result"] = "INIT"
            self.stats.data.pop("last_death_event", None)
            story_flags = self.stats.data.get("story_flags")
            if isinstance(story_flags, dict):
                story_flags.pop("last_death_event", None)
            try: self.stats.increment("runs_started", 1)
            except Exception: pass
        self.defeated_miniboss_ids = set()
        self.destroyed_prop_ids = set()
        self.world = create_world("sanctuary", defeated_ids=self.defeated_miniboss_ids)
        
        self.player = Player(self.world.player_start[0], self.world.player_start[1])
        
        # Phase 4: Sync camera bounds
        if hasattr(self, 'camera'):
            self.camera.world_w = len(self.world.grid[0]) * TILE_SIZE
            self.camera.world_h = len(self.world.grid) * TILE_SIZE
            self.camera.instant_center(self.player.get_center())
        
        self.enemies = list(getattr(self.world, 'enemies', []))
        self.fading_entities = []
        self.world_debris = []
        self.slime_pools = []
        self.pending_remote_sfx = []
        self._remote_combat_seqs = {}
        self.local_swing_seq = 0
        self.local_hit_seq = 0
        self.local_dash_seq = 0
        from constants import MAX_ACTS
        self.current_act = 0
        self.run_biomes = {f"act{i}": None for i in range(1, MAX_ACTS + 1)}
        self.act_worlds = {}
        self.act1_world_data = None
        self.act2_world_data = None
        self.act_warp_target = None
        self.night_boss_spawned = False
        self.empowered_act = False
        self.player.stats = {"attack_modifier": 0, "max_hp_modifier": 0, "edification": 1}
        self.input_ratchet_latched = False
        self.menu_nav_cooldown = 0.0
        from engine.weather import WeatherManager
        self.weather_manager = WeatherManager(boss_coords_list=getattr(self.world, 'boss_coords_list', None))
        if hasattr(self, "marginalia_engine") and self.marginalia_engine:
            self.marginalia_engine.reset(self)
        self.forced_marginalia_event_id = None
        self.loot = []
        self.damage_numbers = []
        if hasattr(self, 'glyph_particles'):
            self.glyph_particles.clear()
        self.active_dialogue = None
        self.active_choice = None
        self.active_respite = None
        self.chronicle_dialog = None
        self.binder_dialog = None
        self.sync_player_binder_scripts(refill_in_sanctuary=True)
        self.player.hp = float(self.player.max_hp)
        from engine.world import LevelLoader
        LevelLoader.link_actors_to_routes(self)

    def get_full_run_state(self):
        """Serializes the complete current world and player state for persistence."""
        if not self.world or not self.player: return None
        return {
            "world_name": getattr(self.world, 'name', 'macro_world'),
            "current_act": int(getattr(self, "current_act", 0)),
            "empowered_act": bool(getattr(self, "empowered_act", False)),
            "night_boss_spawned": bool(getattr(self, "night_boss_spawned", False)),
            "run_biomes": dict(getattr(self, "run_biomes", {})),
            "act_worlds": {
                str(k): v for k, v in getattr(self, "act_worlds", {}).items() if v is not None
            },
            "world_debris": self.world_debris,
            "defeated_miniboss_ids": list(self.defeated_miniboss_ids),
            "destroyed_prop_ids": list(self.destroyed_prop_ids),
            "enemies": [e.to_dict() for e in self.enemies],
            "player": self.get_full_player_state(),
            "weather": self.weather_manager.to_dict() if hasattr(self, 'weather_manager') else None
        }

    def trigger_shake(self, duration: Optional[float] = None) -> None:
        """Start screen shake only when screen_shake_enabled is True."""
        if not getattr(self, "screen_shake_enabled", True):
            self.shake_timer = 0.0
            return
        if duration is None:
            from constants import SCREEN_SHAKE_DURATION
            duration = SCREEN_SHAKE_DURATION
        self.shake_timer = float(duration)

    def set_debug_text_enabled(self, enabled: bool, save: bool = True) -> None:
        """Update the debug text toggle and persist it in the save file."""
        self.debug_text_enabled = bool(enabled)
        self.debug_biome_select = self.debug_text_enabled
        if self.stats is not None:
            self.stats.data["debug_text_enabled"] = self.debug_text_enabled
            if save:
                self.save_stats(wait=True)

    def set_screen_shake_enabled(self, enabled: bool, save: bool = True) -> None:
        """Update the screen shake toggle and persist it in the save file."""
        self.screen_shake_enabled = bool(enabled)
        if not self.screen_shake_enabled:
            self.shake_timer = 0.0
        if self.stats is not None:
            self.stats.data["screen_shake_enabled"] = self.screen_shake_enabled
            if save:
                self.save_stats(wait=True)

    def get_key_label(self, action: str) -> str:
        """Return the concise formatted key label for a remappable action."""
        from constants import DEFAULT_KEYBINDINGS, format_key_name
        bindings = getattr(self, "keybindings", None) or DEFAULT_KEYBINDINGS
        key_code = bindings.get(action, DEFAULT_KEYBINDINGS.get(action))
        return format_key_name(key_code)

    def set_keybinding(self, action: str, key_code: int, save: bool = True) -> bool:
        """Rebind a keyboard action, swapping with any conflicting action so none stays unbound."""
        import pygame
        from constants import DEFAULT_KEYBINDINGS, normalize_keybindings
        if action not in DEFAULT_KEYBINDINGS:
            return False
        if not isinstance(key_code, int) or isinstance(key_code, bool) or key_code <= 0:
            return False
        if key_code == pygame.K_ESCAPE:
            return False
        self.keybindings = normalize_keybindings(getattr(self, "keybindings", None))
        prev_key = self.keybindings[action]
        if prev_key != key_code:
            for other_action, other_key in list(self.keybindings.items()):
                if other_action != action and other_key == key_code:
                    self.keybindings[other_action] = prev_key
                    break
            self.keybindings[action] = int(key_code)
        if self.stats is not None:
            self.stats.data["keybindings"] = dict(self.keybindings)
            if save:
                self.save_stats(wait=True, allow_incompatible=True)
        return True

    def reset_keybindings(self, save: bool = True) -> None:
        """Restore all keyboard bindings to DEFAULT_KEYBINDINGS and optionally persist."""
        from constants import DEFAULT_KEYBINDINGS
        self.keybindings = dict(DEFAULT_KEYBINDINGS)
        if self.stats is not None:
            self.stats.data["keybindings"] = dict(self.keybindings)
            if save:
                self.save_stats(wait=True, allow_incompatible=True)

    def set_forced_marginalia_event_id(self, event_id: Optional[str]) -> None:
        """Set or clear the one-shot forced Marginalia event override for playtesting."""
        from engine.marginalia_events import MARGINALIA_EVENT_CATALOG
        if event_id and event_id in MARGINALIA_EVENT_CATALOG:
            self.forced_marginalia_event_id = str(event_id)
        else:
            self.forced_marginalia_event_id = None

    def reset_margin_scraps(self, save: bool = True) -> None:
        """Reset Margin Scraps, Binder Scripts unlocks/equips, and Binder story flags for debug playtesting."""
        if self.stats is not None:
            self.stats.data["margin_scraps"] = 0
            self.stats.data["binder_scripts"] = {
                "unlocked": [],
                "equipped": [],
                "failed_sequence": [],
                "conflicts_triggered": 0,
            }
            flags = self.stats.data.setdefault("story_flags", {})
            flags["perfect_stitch_completed"] = False
            flags["ink_bleed_halted"] = False

        self.sync_player_binder_scripts(refill_in_sanctuary=False)
        if getattr(self, "player", None) is not None:
            self.player.hp = min(self.player.hp, self.player.max_hp)

        if self.network_manager.network_mode == "CLIENT":
            self.network_manager.send_full_state(self.get_full_player_state())

        if save and self.stats is not None:
            self.save_stats(wait=True)

    def save_stats(self, path: Optional[str] = None, wait: bool = False, allow_incompatible: bool = False) -> None:
        if self.stats is None or not getattr(self, '_save_worker_running', False):
            return
        is_compat = getattr(self.stats, "is_revision_compatible", True)
        if path is None and not is_compat and not allow_incompatible:
            return
        from constants import ENGINE_REVISION
        if is_compat or path is not None:
            self.stats.data["engine_revision"] = ENGINE_REVISION
            self.stats.is_revision_compatible = True
        if hasattr(self, "network_manager") and self.network_manager:
            cur_id = str(getattr(self.network_manager, "identity", "") or "").strip()
            if cur_id:
                self.stats.data["player_name"] = cur_id
        from constants import normalize_keybindings
        self.stats.data["online_mode"] = bool(getattr(self, "online_mode", True))
        self.stats.data["debug_text_enabled"] = bool(getattr(self, "debug_text_enabled", False))
        self.stats.data["screen_shake_enabled"] = bool(getattr(self, "screen_shake_enabled", True))
        self.stats.data["keybindings"] = dict(normalize_keybindings(getattr(self, "keybindings", None)))
        
        # --- Persistence: Sanctuary is the hub; runs are completed/redacted here ---
        # Skip run_state mutation when deallocated (player/world is None on Quit-to-Title) so profile saves still work
        if self.player is not None and self.world is not None:
            world_name = getattr(self.world, 'name', 'sanctuary')
            if world_name not in ("sanctuary", ""):
                self.stats.data["run_state"] = self.get_full_run_state()
                self.stats.data["active_session_in_progress"] = True
            else:
                self.stats.data["run_state"] = None
                self.stats.data["active_session_in_progress"] = False

        resolved_path = path if path is not None else getattr(self, "stats_path", None)
        try: self._save_queue.put_nowait({"stats": self.stats.data, "path": resolved_path})
        except queue.Full: pass
        if wait: self._save_queue.join()

    def _save_worker(self):
        while self._save_worker_running:
            item = self._save_queue.get()
            if item is None: self._save_queue.task_done(); break
            try:
                self.saving_in_progress = True
                from engine.stats import StatisticsTracker
                temp_stats = StatisticsTracker()
                temp_stats.data = item["stats"]
                temp_stats.save(item["path"])
                self.saving_in_progress = False
            except Exception: pass
            finally: self._save_queue.task_done()

    def shutdown_save_worker(self, timeout: float = 2.0) -> None:
        self._save_worker_running = False
        try: self._save_queue.put_nowait(None); self._save_worker_thread.join(timeout)
        except Exception: pass

    def trigger_choice_of_fates(self):
        from constants import (
            CHOICE_OF_FATES_ATTACK_BASE,
            CHOICE_OF_FATES_HP_BASE,
            CHOICE_OF_FATES_MINOR_RATIO,
        )
        level_scale = 1
        if self.stats:
            try: level_scale = 1 + (self.stats.data["lifetime_stats"].get("pages_collected", 0) // 100)
            except Exception: pass
        atk_major = CHOICE_OF_FATES_ATTACK_BASE * level_scale
        hp_major = CHOICE_OF_FATES_HP_BASE * level_scale
        hp_minor = max(1, int(hp_major * CHOICE_OF_FATES_MINOR_RATIO))
        atk_minor = max(1, int(atk_major * CHOICE_OF_FATES_MINOR_RATIO))
        self.active_choice = {
            "title": "The Choice of Fates",
            "options": [
                {
                    "name": "The Quill",
                    "bias": "Offense",
                    "modifiers": {"attack_modifier": atk_major, "max_hp_modifier": hp_minor},
                    "description": f"+{atk_major} Attack, +{hp_minor} Max HP",
                },
                {
                    "name": "The Binding",
                    "bias": "Defense",
                    "modifiers": {"max_hp_modifier": hp_major, "attack_modifier": atk_minor},
                    "description": f"+{hp_major} Max HP, +{atk_minor} Attack",
                },
            ],
            "selected_index": 0
        }
        self.input_debounce_timer = 0.3

    def update_damage_numbers(self, dt):
        from constants import DAMAGE_NUMBER_SPEED
        for num in self.damage_numbers[:]:
            num['time'] -= dt
            x, y = num['pos']
            num['pos'] = (x, y - DAMAGE_NUMBER_SPEED * dt)
            if num['time'] <= 0: self.damage_numbers.remove(num)

    def _update_audio_track(self, dt):
        from constants import (
            MEADOW_CENSOR_PHASE1_MUSIC,
            MEADOW_CENSOR_PHASE2_HP_RATIO,
            MEADOW_CENSOR_PHASE2_MUSIC,
            RIMECREST_ARBITER_PHASE1_MUSIC,
            RIMECREST_ARBITER_PHASE2_HP_RATIO,
            RIMECREST_ARBITER_PHASE2_MUSIC,
            SLUG_BOSS_PHASE1_MUSIC,
            SLUG_BOSS_PHASE2_HP_RATIO,
            SLUG_BOSS_PHASE2_MUSIC,
        )
        world_name = getattr(self.world, 'name', 'sanctuary')
        target_track = "world_exploration.ogg"
        if world_name == "sanctuary":
            target_track = "sanctuary_hub.ogg"
        if (
            getattr(self.stats, 'data', {}).get("last_run_result") == "VICTORY"
            and world_name in ("final_boss", "night_boss_arena")
        ):
            self.player.active_track_name = "victory_theme.ogg"
            return
        if self.player.hp <= 0:
            self.player.active_track_name = "death_theme.ogg"
            return
        proximity_threshold = 15 * TILE_SIZE
        cooldown_limit = 3.0
        near_miniboss = near_night_boss = near_final_author = False
        near_biome_boss_track = None
        px, py = self.player.get_center()
        for enemy in self.enemies:
            if getattr(enemy, "hp", 1) <= 0:
                continue
            if getattr(enemy, 'is_miniboss', False):
                ex, ey = enemy.get_center()
                if (px - ex)**2 + (py - ey)**2 <= proximity_threshold**2:
                    ename = getattr(enemy, 'name', '')
                    if ename == "The Final Author":
                        near_final_author = True
                        break
                    if getattr(enemy, "is_slug_boss", False):
                        max_hp = float(getattr(enemy, "max_hp", 0.0) or 0.0)
                        cur_hp = float(getattr(enemy, "hp", 0.0) or 0.0)
                        in_phase2 = getattr(enemy, "phase", 1) >= 2 or (
                            max_hp > 0.0 and 0.0 < cur_hp <= max_hp * SLUG_BOSS_PHASE2_HP_RATIO
                        )
                        near_biome_boss_track = SLUG_BOSS_PHASE2_MUSIC if in_phase2 else SLUG_BOSS_PHASE1_MUSIC
                    elif getattr(enemy, "is_meadow_censor", False):
                        max_hp = float(getattr(enemy, "max_hp", 0.0) or 0.0)
                        cur_hp = float(getattr(enemy, "hp", 0.0) or 0.0)
                        in_phase2 = getattr(enemy, "phase", 1) >= 2 or (
                            max_hp > 0.0 and 0.0 < cur_hp <= max_hp * MEADOW_CENSOR_PHASE2_HP_RATIO
                        )
                        near_biome_boss_track = MEADOW_CENSOR_PHASE2_MUSIC if in_phase2 else MEADOW_CENSOR_PHASE1_MUSIC
                    elif getattr(enemy, "is_rimecrest_arbiter", False):
                        max_hp = float(getattr(enemy, "max_hp", 0.0) or 0.0)
                        cur_hp = float(getattr(enemy, "hp", 0.0) or 0.0)
                        in_phase2 = getattr(enemy, "phase", 1) >= 2 or (
                            max_hp > 0.0 and 0.0 < cur_hp <= max_hp * RIMECREST_ARBITER_PHASE2_HP_RATIO
                        )
                        near_biome_boss_track = (
                            RIMECREST_ARBITER_PHASE2_MUSIC if in_phase2 else RIMECREST_ARBITER_PHASE1_MUSIC
                        )
                    elif ename == "Night Boss":
                        near_night_boss = True
                    else:
                        near_miniboss = True
        current_active = self.player.active_track_name
        if near_final_author:
            self.player.active_track_name = "final_reckoning.ogg"
            self.player.miniboss_cooldown_accumulator = 0.0
        elif near_biome_boss_track is not None:
            self.player.active_track_name = near_biome_boss_track
            self.player.miniboss_cooldown_accumulator = 0.0
        elif near_night_boss:
            self.player.active_track_name = "night_boss.ogg"
            self.player.miniboss_cooldown_accumulator = 0.0
        elif near_miniboss:
            self.player.active_track_name = "miniboss_combat.ogg"
            self.player.miniboss_cooldown_accumulator = 0.0
        elif current_active in BOSS_COMBAT_TRACKS:
            self.player.miniboss_cooldown_accumulator += dt
            if self.player.miniboss_cooldown_accumulator >= cooldown_limit:
                self.player.active_track_name = target_track
        else:
            self.player.active_track_name = target_track

    def get_staged_respite_info(self):
        """Calculate levels, staged counts, next costs, and total costs for respite upgrades."""
        from constants import (
            EDIFICATION_BASE_COST,
            EDIFICATION_COST_SCALE,
            PROWESS_ATTACK_STEP,
            FORTIFICATION_HP_STEP,
        )

        # 1. Prowess (Attack modifier, steps of PROWESS_ATTACK_STEP)
        prowess = self.player.stats.get("attack_modifier", 0)
        prowess_lvl = 1 + (prowess // PROWESS_ATTACK_STEP)
        staged_prowess = self.respite_upgrades.get(1, 0)

        prowess_staged_cost = 0
        for i in range(staged_prowess):
            lvl = prowess_lvl + i
            prowess_staged_cost += EDIFICATION_BASE_COST + ((lvl - 1) * EDIFICATION_COST_SCALE)

        next_prowess_lvl = prowess_lvl + staged_prowess
        next_prowess_cost = EDIFICATION_BASE_COST + ((next_prowess_lvl - 1) * EDIFICATION_COST_SCALE)

        # 2. Fortification (HP modifier, steps of FORTIFICATION_HP_STEP)
        fort = self.player.stats.get("max_hp_modifier", 0)
        fort_lvl = 1 + (fort // FORTIFICATION_HP_STEP)
        staged_fort = self.respite_upgrades.get(2, 0)

        fort_staged_cost = 0
        for i in range(staged_fort):
            lvl = fort_lvl + i
            fort_staged_cost += EDIFICATION_BASE_COST + ((lvl - 1) * EDIFICATION_COST_SCALE)

        next_fort_lvl = fort_lvl + staged_fort
        next_fort_cost = EDIFICATION_BASE_COST + ((next_fort_lvl - 1) * EDIFICATION_COST_SCALE)

        total_staged_cost = prowess_staged_cost + fort_staged_cost

        return {
            "prowess_lvl": prowess_lvl,
            "staged_prowess": staged_prowess,
            "next_prowess_cost": next_prowess_cost,
            "fort_lvl": fort_lvl,
            "staged_fort": staged_fort,
            "next_fort_cost": next_fort_cost,
            "total_staged_cost": total_staged_cost
        }

    def _handle_upgrade(self, stat_name, amount):
        from constants import (
            EDIFICATION_BASE_COST,
            EDIFICATION_COST_SCALE,
            PROWESS_ATTACK_STEP,
            FORTIFICATION_HP_STEP,
        )
        current_val = self.player.stats.get(stat_name, 0)

        # Calculate current 1-based level
        current_level = 1 + (current_val // amount) if amount > 0 else 1

        # Correct Formula: Base + ((Level - 1) * Scale)
        cost = EDIFICATION_BASE_COST + ((current_level - 1) * EDIFICATION_COST_SCALE)

        pages = self.stats.data["lifetime_stats"].get("pages_collected", 0)
        if pages >= cost:
            self.stats.data["lifetime_stats"]["pages_collected"] -= cost
            self.player.stats[stat_name] = current_val + amount

            if stat_name == "max_hp_modifier":
                self.player.hp = self.player.max_hp

            # Recalculate Global Edification Level
            prowess = self.player.stats.get("attack_modifier", 0)
            fort = self.player.stats.get("max_hp_modifier", 0)
            self.player.stats["edification"] = (prowess // PROWESS_ATTACK_STEP) + (fort // FORTIFICATION_HP_STEP) + 1

            # Sync to persistent stats for UI parity
            if self.stats:
                if "run_state" in self.stats.data and self.stats.data["run_state"]:
                    self.stats.data["run_state"]["player"]["stats"] = self.player.stats

            self.player.has_rested_this_session = False
            if getattr(self, 'active_respite', None): self.active_respite.execute_interaction(self)
            return True
        return False

    def respawn_player(self):
        from engine.maps import create_world
        active_event = getattr(getattr(self, "marginalia_engine", None), "active_event", None)
        active_event_id = getattr(active_event, "event_id", None) if active_event is not None else None
        if self.stats:
            self.stats.data["last_run_result"] = "DEFEAT"
            story_flags = self.stats.data.setdefault("story_flags", {})
            if active_event_id:
                story_flags["last_death_event"] = active_event_id
                self.stats.data["last_death_event"] = active_event_id
            else:
                story_flags.pop("last_death_event", None)
                self.stats.data.pop("last_death_event", None)
        self.world = create_world("sanctuary", defeated_ids=self.defeated_miniboss_ids)
        
        # Reset local player fully
        self.player.x, self.player.y = float(self.world.player_start[0]), float(self.world.player_start[1])
        self.player.hp = self.player.max_hp
        self.player.state = PlayerStateEnum.IDLE
        self.player.damage_mitigation = 0.0
        if hasattr(self.player, "reset_frost_state"):
            self.player.reset_frost_state()
        self.death_timer = 0.0
        
        if hasattr(self, 'camera'): self.camera.instant_center(self.player.get_center())
        self.on_enter_sanctuary()
        self.enemies, self.loot = [], []
        self.save_stats(wait=True)
