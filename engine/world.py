"""
Handles world grid, map sections, and static obstacles.
"""
import os
import json
import random
from constants import (
    GRID_WIDTH, GRID_HEIGHT, TILE_WALL, TILE_EMPTY, TILE_SIZE, TILE_WARP,
    PLAYER_START_X, PLAYER_START_Y, POOL_MONTHLY_REPORT, POOL_SPECIAL_EDITION,
    TILE_PATROL, RESPITE_HOSTILE_BLOCK_RADIUS
)
from engine.actor import Actor, ActorState

class GameObject:
    """
    Unified base class for all physical props, breakables, doors, and mechanisms.
    Follows the schema defined in docs/architecture.md but without pygame dependency
    to maintain engine decoupling as per docs/file_blueprint.md.
    """
    def __init__(self, position, dimensions):
        self.x, self.y = float(position[0]), float(position[1])
        self.width, self.height = float(dimensions[0]), float(dimensions[1])
        self.rect = (self.x, self.y, self.width, self.height)
        self.is_solid = False
        self.is_interactive = False
        self.is_breakable = False
        self.health = 100.0
        self.name = "Object"
        self.prop_type = None

    def update(self, dt, game_state):
        """Standard per-frame logic hook."""
        pass

    def execute_interaction(self, game_state):
        """Hook for when a player interacts with this object."""
        pass

    def take_damage(self, amount):
        """Hook for breakable logic."""
        if self.is_breakable:
            self.health -= amount

    def to_dict(self):
        """Serialize object state for networking."""
        return {
            "id": getattr(self, 'id', id(self)),
            "name": self.name,
            "x": round(self.x, 1),
            "y": round(self.y, 1),
            "w": self.width,
            "h": self.height,
            "hp": round(self.health, 1),
            "active": True
        }

    def is_dead(self):
        """Check if object is destroyed."""
        return self.is_breakable and self.health <= 0

class WarpPortal(GameObject):
    """An interactable object that warps the player to another map."""
    def __init__(self, target_name, spawn_x, spawn_y, rect, name="Warp"):
        super().__init__((rect[0], rect[1]), (rect[2], rect[3]))
        self.target_name = target_name
        self.spawn_x = spawn_x
        self.spawn_y = spawn_y
        self.name = name
        self.is_interactive = True
        self.is_solid = False # Usually can stand on warp tiles

    def apply_transfer(self, game_state):
        """Perform the physical map transition and player/camera repositioning."""
        try:
            from engine.maps import create_world
            print(f"[DEBUG] WarpPortal targeting: {self.target_name}")
            
            # Universal Reset: Clear visual debris & active slime pools on every map transition
            game_state.world_debris = []
            if hasattr(game_state, "slime_pools"):
                game_state.slime_pools = []

            from constants import ACT2_HP_MULTIPLIER, ACT2_DAMAGE_MULTIPLIER, get_act_saturation
            cur_act = int(getattr(game_state, 'current_act', 0) or 0)
            is_empowered_arena = (
                self.target_name in ("night_boss_arena", "final_boss")
                and (
                    getattr(game_state, 'empowered_act', False)
                    or cur_act >= 2
                )
            )
            if is_empowered_arena:
                if cur_act >= 3:
                    sat = get_act_saturation(cur_act)
                    hp_mult = max(ACT2_HP_MULTIPLIER, float(sat["hp_multiplier"]))
                    dmg_mult = max(ACT2_DAMAGE_MULTIPLIER, float(sat["damage_multiplier"]))
                    spd_mult = float(sat.get("speed_multiplier", 1.0))
                    cd_mult = float(sat.get("cooldown_multiplier", 1.0))
                else:
                    sat2 = get_act_saturation(2)
                    hp_mult = ACT2_HP_MULTIPLIER
                    dmg_mult = ACT2_DAMAGE_MULTIPLIER
                    spd_mult = float(sat2.get("speed_multiplier", 1.0))
                    cd_mult = float(sat2.get("cooldown_multiplier", 1.0))
                game_state.empowered_act = True
                emp_override = True
            else:
                hp_mult = 1.0
                dmg_mult = 1.0
                spd_mult = 1.0
                cd_mult = 1.0
                emp_override = None

            # Phase 3 Intercept: If Client entering macro-world, fetch host map
            is_client = (game_state.network_manager.network_mode == "CLIENT")
            if is_client and self.target_name in ("macro_world", "outside"):
                if not game_state.fetch_host_map():
                    print("[NETWORK] Map fetch failed. Falling back to local generation.")
                    game_state.world = create_world(
                        self.target_name,
                        defeated_ids=game_state.defeated_miniboss_ids,
                        hp_multiplier=hp_mult,
                        damage_multiplier=dmg_mult,
                        empowered=emp_override,
                        speed_multiplier=spd_mult,
                        cooldown_multiplier=cd_mult,
                    )
            else:
                game_state.world = create_world(
                    self.target_name,
                    defeated_ids=game_state.defeated_miniboss_ids,
                    hp_multiplier=hp_mult,
                    damage_multiplier=dmg_mult,
                    empowered=emp_override,
                    speed_multiplier=spd_mult,
                    cooldown_multiplier=cd_mult,
                )

            # Weather Sync Rule: Update boss center coordinates for the safe circle
            new_boss_list = getattr(game_state.world, 'boss_coords_list', None)
            game_state.weather_manager.set_boss_coords_list(new_boss_list)

            # Sanctuary Reset Rule: Enforce absolute state purification
            if self.target_name == "sanctuary":
                game_state.in_sanctuary = True
                game_state.host_in_run = False
                game_state.waiting_for_host_run = False
                game_state.on_enter_sanctuary()
            else:
                game_state.in_sanctuary = False
                if hasattr(game_state, "network_manager") and game_state.network_manager.network_mode != "CLIENT":
                    game_state.host_in_run = True
                # Auto-Host Rule: Start hosting when entering the macro-world in Online mode
                if hasattr(game_state, 'network_manager') and getattr(game_state, 'online_mode', True):
                    if game_state.network_manager.network_mode == "OFFLINE":
                        game_state.network_manager.start_hosting()
                
                # State Reset Rule: When starting a new run through the book, reset result to INIT
                if game_state.stats:
                    game_state.stats.data["last_run_result"] = "INIT"
                    game_state.stats.data["active_session_in_progress"] = True
                    game_state.stats.data.pop("last_death_event", None)
                    story_flags = game_state.stats.data.get("story_flags")
                    if isinstance(story_flags, dict):
                        story_flags.pop("last_death_event", None)

            # Position player at spawn coords (Priority: World default/player_start, then WarpPortal explicit)
            # Procedural Generation Rule: If create_world returned a world with a valid player_start, use it.
            game_state.player.is_exposed = False
            target_x = float(self.spawn_x)
            target_y = float(self.spawn_y)
            
            # Universal Player Start Override: If target world has a defined spawn, prefer it
            if game_state.world.player_start:
                target_x, target_y = game_state.world.player_start
                print(f"[DEBUG] Using destination player_start override: ({target_x}, {target_y})")

            print(f"[DEBUG] Setting player physical position: ({target_x}, {target_y})")
            game_state.player.x = float(target_x)
            game_state.player.y = float(target_y)
            # Phase 4: Sync camera bounds to new world
            if hasattr(game_state, 'camera'):
                game_state.camera.world_w = len(game_state.world.grid[0]) * TILE_SIZE
                game_state.camera.world_h = len(game_state.world.grid) * TILE_SIZE
                game_state.camera.instant_center(game_state.player.get_center())
            
            # Update enemies list from the new world
            if hasattr(game_state.world, 'enemies'):
                game_state.enemies = getattr(game_state.world, 'enemies', [])
            else:
                game_state.enemies = []

            # Link new world actors to patrol routes
            LevelLoader.link_actors_to_routes(game_state)

            # [Milestone] Flush state immediately upon returning to sanctuary
            is_to_sanctuary = self.target_name == "sanctuary"
            game_state.save_stats(wait=is_to_sanctuary)
            print(f"[DEBUG] Warp to {self.target_name} complete.")
        except Exception as e:
            print(f"[ERROR] Warp failed: {e}")
            import traceback
            traceback.print_exc()

    def execute_interaction(self, game_state, instant=True):
        """Perform the map transition, delegating to cinematic warp if available."""
        if not instant and hasattr(game_state, 'start_warp'):
            game_state.start_warp(self)
            return
        self.apply_transfer(game_state)


class ReturnAnchor:
    """Saved overworld map coordinate entry for sub-arena pitfall and Exit Ladder returns."""

    def __init__(self, map_path, x, y, world_ref=None, enemies_ref=None):
        self.map_path = str(map_path)
        self.x = float(x)
        self.y = float(y)
        self.world_ref = world_ref
        self.enemies_ref = list(enemies_ref) if enemies_ref is not None else None

    def to_dict(self):
        return {
            "map_path": self.map_path,
            "x": round(self.x, 1),
            "y": round(self.y, 1),
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            data.get("map_path", "generated_world"),
            data.get("x", 0.0),
            data.get("y", 0.0),
        )


class ExitLadder(GameObject):
    """Interactable ladder that returns the party from a pocket sub-arena via ReturnAnchor."""

    def __init__(self, position, dimensions=(TILE_SIZE, TILE_SIZE), name="Exit Ladder"):
        super().__init__(position, dimensions)
        self.name = name
        self.target_name = "return_anchor"
        self.is_interactive = True
        self.is_solid = False
        self.id = f"exit_ladder:{int(position[0])},{int(position[1])}"

    def apply_transfer(self, game_state):
        if hasattr(game_state, "pop_return_anchor"):
            return game_state.pop_return_anchor()
        return None

    def execute_interaction(self, game_state, instant=True):
        del instant
        return self.apply_transfer(game_state)


class PitfallTrigger(GameObject):
    """Disguised map anchor (Suspicious Leaf Pile) that warps the party into a pocket arena."""

    def __init__(self, position, dimensions=(TILE_SIZE, TILE_SIZE), anchor_id=None, name="Suspicious Leaf Pile"):
        super().__init__(position, dimensions)
        self.name = name
        self.anchor_id = anchor_id or f"pitfall:{int(position[0])},{int(position[1])}"
        self.id = self.anchor_id
        self.is_interactive = True
        self.is_solid = False

    def execute_interaction(self, game_state):
        if hasattr(game_state, "marginalia_engine") and game_state.marginalia_engine:
            return game_state.marginalia_engine.trigger_pitfall_anchor(game_state, self)
        return False


class InkSeal(GameObject):
    """Breakable ward seal spawned during The Margin Toll event."""

    def __init__(self, position, dimensions=(TILE_SIZE, TILE_SIZE), seal_id=None):
        super().__init__(position, dimensions)
        self.name = "Ink Seal"
        self.id = seal_id or f"ink_seal:{int(position[0])},{int(position[1])}"
        self.is_breakable = True
        self.is_solid = True
        self.health = 20.0

class PatrolPoint(GameObject):
    """Marker symbol for the Stanza system."""
    def __init__(self, position, route_id, symbol_idx, caste_filter=None, wait_min=2.0, wait_max=5.0):
        super().__init__(position, (TILE_SIZE, TILE_SIZE))
        self.route_id = route_id
        self.symbol_idx = symbol_idx
        self.caste_filter = caste_filter or []
        self.wait_min = wait_min
        self.wait_max = wait_max
        self.is_interactive = False
        self.is_solid = False
        self.name = f"PatrolPoint_{route_id}_{symbol_idx}"

class Chronicler(Actor):
    """NPC that provides dialogue and follows a research stanza."""
    def __init__(self, position, dimensions=None, name="The Chronicler"):
        super().__init__(position[0], position[1], 40, 40, 9999, name=name)
        self.is_interactive = True
        self.is_solid = True
        self.current_dialogue = None
        self.patrol_speed_multiplier = 0.4

    def execute_interaction(self, game_state):
        """Select dialogue based on state and display it."""
        from constants import DIALOGUE_MANIFEST
        manifest = DIALOGUE_MANIFEST.get("chronicler", [])

        # Get current state from stats
        last_result = "INIT"
        if game_state.stats:
            last_result = game_state.stats.data.get("last_run_result", "INIT")

        # Filter and sort by priority
        valid_nodes = []
        for node in manifest:
            conditions = node.get("conditions", {})
            match = True
            for key, value in conditions.items():
                if key == "last_run_result":
                    if value != last_result:
                        match = False
                        break
                elif game_state.stats:
                    story_flags = game_state.stats.data.get("story_flags", {})
                    flag_val = (
                        story_flags.get(key, game_state.stats.data.get(key))
                        if isinstance(story_flags, dict)
                        else game_state.stats.data.get(key)
                    )
                    if flag_val != value:
                        match = False
                        break
                else:
                    match = False
                    break

            if match:
                valid_nodes.append(node)

        if not valid_nodes: return
        valid_nodes.sort(key=lambda x: int(x.get("priority", 0)), reverse=True)
        node = valid_nodes[0]

        emotion = node.get("emotion", "neutral")
        game_state.active_dialogue = {
            "speaker": self.name,
            "text": node["text"],
            "emotion": emotion,
        }
        if hasattr(game_state, "play_chronicler_mumble"):
            game_state.play_chronicler_mumble(emotion)
        print(f"[NPC] {self.name} triggered dialogue: {node['id']} (emotion={emotion})")


class Binder(Actor):
    """Sanctuary artisan NPC who weaves Binder Scripts into the player's frame."""
    def __init__(self, position, dimensions=None, name="The Binder"):
        from constants import BINDER_PATROL_SPEED_MULTIPLIER
        del dimensions
        super().__init__(position[0], position[1], 40, 40, 9999, name=name)
        self.is_interactive = True
        self.is_solid = True
        self.is_stationary = False
        self.patrol_speed_multiplier = BINDER_PATROL_SPEED_MULTIPLIER

    def execute_interaction(self, game_state):
        """Open the Binder Script Weaving Loom modal in Sanctuary."""
        if hasattr(game_state, "open_binder_dialog"):
            game_state.open_binder_dialog(binder_npc=self)

class FlavorProp(GameObject):
    """Atmospheric Sanctuary prop displaying flavor dialogue on inspect with zero mechanical reward."""
    def __init__(self, position, dimensions, name, dialogue_text, prop_type=None, is_solid=True):
        super().__init__(position, dimensions)
        self.name = name
        self.dialogue_text = dialogue_text
        self.prop_type = prop_type
        self.is_solid = is_solid
        self.is_interactive = True

    def execute_interaction(self, game_state):
        """Display non-reward atmospheric flavor text in active_dialogue."""
        game_state.active_dialogue = {
            "speaker": self.name,
            "text": self.dialogue_text,
        }


class Wellspring(GameObject):
    """Refill station for flasks."""
    def __init__(self, position, dimensions):
        super().__init__(position, dimensions)
        self.name = "The Wellspring"
        self.is_interactive = True
        self.is_solid = True
        self.night_boss_used = False

    def execute_interaction(self, game_state):
        from constants import FLASK_MAX_CHARGES, WELLSPRING_NIGHT_BOSS_FLASK_GRANT
        enemies = getattr(game_state, "enemies", None) or []
        night_boss_active = bool(getattr(game_state, "night_boss_spawned", False)) or any(
            (getattr(e, "name", "") == "Night Boss" or e.__class__.__name__ == "NightBoss")
            and getattr(e, "hp", 1) > 0
            for e in enemies
        )
        if night_boss_active:
            if self.night_boss_used:
                game_state.trigger_bloom("WELLSPRING DRY", priority=1)
                print("[WELLSPRING] Wellspring is dry during Night Boss encounter.")
                return
            if game_state.player.flask_charges < FLASK_MAX_CHARGES:
                game_state.player.flask_charges = min(
                    FLASK_MAX_CHARGES,
                    game_state.player.flask_charges + WELLSPRING_NIGHT_BOSS_FLASK_GRANT,
                )
                self.night_boss_used = True
                game_state.trigger_bloom("HYDRATION RESTORED", priority=1)
                print("[WELLSPRING] Granted +1 flask charge; wellspring is now dry.")
            else:
                game_state.trigger_bloom("HYDRATION FULL", priority=1)
                print("[WELLSPRING] Flasks already full.")
            return

        if game_state.player.flask_charges < FLASK_MAX_CHARGES:
            game_state.player.flask_charges = FLASK_MAX_CHARGES
            game_state.trigger_bloom("HYDRATION RESTORED", priority=1)
            print("[WELLSPRING] Flasks refilled.")
        else:
            game_state.trigger_bloom("HYDRATION FULL", priority=1)
            print("[WELLSPRING] Flasks already full.")

class LoreFragment(GameObject):
    """Collectable piece of text that reveals world history."""
    def __init__(self, position, dimensions, fragment_id, name="Lost Page"):
        super().__init__(position, dimensions)
        self.fragment_id = fragment_id
        self.name = name
        self.is_interactive = True
        self.is_solid = False

    def _resolve_biome_chronicle_id(self, game_state):
        """Resolve an unmapped ('unknown' / empty) fragment_id to <biome>_chronicle outside Sanctuary."""
        from constants import BIOME_DISPLAY_NAMES
        world = getattr(game_state, "world", None)
        w_name = str(getattr(world, "name", "") or "").lower()
        if w_name == "sanctuary" or bool(getattr(game_state, "in_sanctuary", False)):
            return self.fragment_id

        tx = int(self.x // TILE_SIZE)
        ty = int(self.y // TILE_SIZE)
        for sock in getattr(world, "module_sockets", None) or ():
            if not isinstance(sock, dict):
                continue
            b = sock.get("bounds")
            if isinstance(b, dict) and all(k in b for k in ("x", "y", "width", "height")):
                if not (b["x"] <= tx < b["x"] + b["width"] and b["y"] <= ty < b["y"] + b["height"]):
                    continue
            sock_b = sock.get("biome")
            if sock_b in BIOME_DISPLAY_NAMES:
                return f"{sock_b}_chronicle"
            plug = str(sock.get("active_plug", "")).lower()
            for b_key in BIOME_DISPLAY_NAMES:
                if b_key in plug:
                    return f"{b_key}_chronicle"

        resolve_fn = getattr(game_state, "_resolve_active_biome_key", None)
        if callable(resolve_fn):
            active_biome = resolve_fn()
            if active_biome in BIOME_DISPLAY_NAMES:
                return f"{active_biome}_chronicle"

        run_biomes = getattr(game_state, "run_biomes", None) or {}
        cur_act = int(getattr(game_state, "current_act", 0) or 0)
        if cur_act > 0 and run_biomes.get(f"act{cur_act}") in BIOME_DISPLAY_NAMES:
            return f"{run_biomes[f'act{cur_act}']}_chronicle"
        for b_val in run_biomes.values():
            if b_val in BIOME_DISPLAY_NAMES:
                return f"{b_val}_chronicle"
        for b_key in BIOME_DISPLAY_NAMES:
            if b_key in w_name:
                return f"{b_key}_chronicle"
        return "windy_ridge_chronicle"

    def execute_interaction(self, game_state):
        from constants import DIALOGUE_MANIFEST
        frag_id = self.fragment_id
        if frag_id in (None, "", "unknown"):
            frag_id = self._resolve_biome_chronicle_id(game_state)
        raw_entry = DIALOGUE_MANIFEST.get("lore_fragments", {}).get(
            frag_id, "The text has faded into illegibility."
        )
        if isinstance(raw_entry, (list, tuple)):
            if raw_entry:
                tx = int(self.x) // TILE_SIZE if int(self.x) >= TILE_SIZE else int(self.x)
                ty = int(self.y) // TILE_SIZE if int(self.y) >= TILE_SIZE else int(self.y)
                idx = abs(int(self.x) * 31 + int(self.y) * 17 + tx * 13 + ty * 7) % len(raw_entry)
                lore_text = str(raw_entry[idx])
            else:
                lore_text = "The text has faded into illegibility."
        else:
            lore_text = str(raw_entry)

        game_state.active_dialogue = {
            "speaker": self.name,
            "text": lore_text
        }
        print(f"[LORE] Read fragment: {frag_id}")

class WeaponPickup(GameObject):
    """Dropped weapon from miniboss or chest."""
    def __init__(self, position, weapon_data):
        super().__init__(position, (TILE_SIZE, TILE_SIZE))
        self.weapon_data = weapon_data
        self.name = weapon_data.get("name", "Unknown Quill")
        self.is_interactive = True
        self.is_solid = False

    def execute_interaction(self, game_state):
        """Pick up or swap with current active weapon."""
        player = game_state.player
        current_idx = player.active_weapon_idx
        
        if len(player.weapons) < 2:
            # Slot available: simple pickup
            player.weapons.append(self.weapon_data)
            player.active_weapon_idx = len(player.weapons) - 1
            print(f"[PLAYER] Picked up {self.name} into Slot B")
            if self in game_state.world.interactables:
                game_state.world.interactables.remove(self)
        else:
            # Both slots full: perform a swap
            old_weapon = player.weapons[current_idx]
            player.weapons[current_idx] = self.weapon_data
            
            # Put the old weapon into this pickup object
            self.weapon_data = old_weapon
            self.name = old_weapon.get("name", "Unknown Quill")
            print(f"[PLAYER] Swapped {self.name} onto floor, picked up {player.weapons[current_idx]['name']}")
            # NOTE: self is NOT removed from interactables in this case


class SlugBossCrown(GameObject):
    """Non-interactive tarnished golden crown left permanently on the floor after SlugBoss death."""
    def __init__(self, position):
        from constants import SLUG_BOSS_CROWN_HEIGHT, SLUG_BOSS_CROWN_WIDTH
        super().__init__(position, (SLUG_BOSS_CROWN_WIDTH, SLUG_BOSS_CROWN_HEIGHT))
        self.name = "SlugBossCrown"
        self.is_interactive = False
        self.is_solid = False

    def execute_interaction(self, game_state):
        """Non-interactive floor trophy prop: intentionally performs no action."""
        return None


class MeadowCensorScythe(GameObject):
    """Non-interactive hooked redaction scythe planted upright in the turf after MeadowCensorBoss death."""
    def __init__(self, position):
        from constants import MEADOW_CENSOR_SCYTHE_HEIGHT, MEADOW_CENSOR_SCYTHE_WIDTH
        super().__init__(position, (MEADOW_CENSOR_SCYTHE_WIDTH, MEADOW_CENSOR_SCYTHE_HEIGHT))
        self.name = "MeadowCensorScythe"
        self.is_interactive = False
        self.is_solid = False

    def execute_interaction(self, game_state):
        """Non-interactive floor trophy prop: intentionally performs no action."""
        return None


class RimecrestHalberd(GameObject):
    """Non-interactive shattered mirror-ice halberd planted upright in rime slate after RimecrestArbiterBoss death."""
    def __init__(self, position):
        from constants import RIMECREST_ARBITER_HALBERD_HEIGHT, RIMECREST_ARBITER_HALBERD_WIDTH
        super().__init__(position, (RIMECREST_ARBITER_HALBERD_WIDTH, RIMECREST_ARBITER_HALBERD_HEIGHT))
        self.name = "RimecrestHalberd"
        self.is_interactive = False
        self.is_solid = False

    def execute_interaction(self, game_state):
        """Non-interactive floor trophy prop: intentionally performs no action."""
        return None


class Respite(GameObject):
    """Ancient anchor fragment that allows resting and character edification."""
    def __init__(self, position, dimensions):
        super().__init__(position, dimensions)
        self.name = "Respite Anchor"
        self.is_interactive = True
        self.is_solid = True
        self.is_active = True
        self.gated_by_miniboss_id = None

    @staticmethod
    def _has_blocking_hostiles(game_state) -> bool:
        """Return True if any alive enemy is within block radius of the player or actively aggroed."""
        player = getattr(game_state, "player", None)
        if player is None:
            return False
        px, py = player.get_center()
        block_r_sq = RESPITE_HOSTILE_BLOCK_RADIUS ** 2
        for enemy in getattr(game_state, "enemies", None) or []:
            if getattr(enemy, "hp", 0) <= 0:
                continue
            ex, ey = enemy.get_center()
            if (ex - px) ** 2 + (ey - py) ** 2 <= block_r_sq:
                return True
            if getattr(enemy, "state", None) in (
                ActorState.CHASE,
                ActorState.WIND_UP,
                ActorState.STRIKE,
                ActorState.RECOVERY,
            ):
                return True
        return False

    def execute_interaction(self, game_state):
        """Trigger the Respite Level-Up UI in GameState."""
        rx = self.x + self.width / 2
        ry = self.y + self.height / 2
        if hasattr(game_state, 'weather_manager') and not game_state.weather_manager.is_pos_safe(rx, ry):
            game_state.active_dialogue = {
                "speaker": "Respite Anchor",
                "text": (
                    "The glyphs are smothered under a thick layer of liquid ink. "
                    "The sanctuary's power is drowned until the rain clears."
                )
            }
            game_state.active_respite = None
            return

        wm_state = getattr(getattr(game_state, "weather_manager", None), "bleed_state", "")
        enemies = getattr(game_state, "enemies", None) or []
        has_night_boss = any(
            (getattr(e, "name", "") == "Night Boss" or e.__class__.__name__ == "NightBoss")
            and getattr(e, "hp", 1) > 0
            for e in enemies
        )
        if (
            getattr(game_state, "night_boss_spawned", False)
            or has_night_boss
            or wm_state in ("BOSS_PHASE", "DILUTION", "APPENDIX")
        ):
            game_state.active_dialogue = {
                "speaker": "Respite Anchor",
                "text": (
                    "The Night Boss has broken the anchor's seal. "
                    "This Respite cannot be used for the remainder of the Act."
                ),
            }
            game_state.active_respite = None
            return

        if getattr(game_state, "active_respite", None) != self and self._has_blocking_hostiles(game_state):
            game_state.active_dialogue = {
                "speaker": "Respite Anchor",
                "text": (
                    "Hostile ink presses too close to the anchor. "
                    "Clear nearby threats before resting."
                ),
            }
            game_state.active_respite = None
            return

        # Only reset and log if first opening
        if getattr(game_state, 'active_respite', None) != self:
            game_state.respite_selection_idx = 0
            game_state.respite_marked_idx = -1
            print("[RESPITE] Interaction engaged.")
        
        game_state.active_dialogue = {
            "speaker": "Respite Anchor",
            "text": "" # Menu will override text rendering
        }
        game_state.active_respite = self

    def execute_rest(self, game_state, audio_manager=None):
        """Restore player and respawn standard enemies from world.initial_enemy_spawns."""
        from constants import (
            ACT2_DAMAGE_MULTIPLIER,
            ACT2_HP_MULTIPLIER,
            FLASK_MAX_CHARGES,
            get_act_saturation,
        )
        from engine.enemy import ENEMY_REGISTRY

        # 0. Trigger SFX
        if audio_manager:
            audio_manager.play_sfx("respite_rest.ogg")

        # 1. Character Restoration
        game_state.player.hp = float(game_state.player.max_hp)
        game_state.player.flask_charges = int(FLASK_MAX_CHARGES)
        game_state.player.has_rested_this_session = True

        # Phase 4: Network Notify
        if game_state.network_manager.network_mode == "CLIENT":
            game_state.network_manager.send_respite_event("REST")
            return  # Exit early: Host will handle world respawn and sync back

        # 2. World Re-population from world.initial_enemy_spawns
        world = getattr(game_state, "world", None)
        world_name = getattr(world, "name", "unknown") if world is not None else "unknown"
        print(f"[DEBUG] Respite resting: Re-manifesting threats in {world_name}")

        if world is not None and not getattr(world, "initial_enemy_spawns", None):
            seed_enemies = getattr(game_state, "enemies", None) or getattr(world, "enemies", None) or []
            if seed_enemies:
                world.initial_enemy_spawns = World.build_initial_enemy_spawns(seed_enemies)
            elif getattr(world, "name", "") not in ("", "sanctuary"):
                from engine.maps import create_world
                temp_world = create_world(
                    world.name, defeated_ids=getattr(game_state, "defeated_miniboss_ids", None)
                )
                if getattr(temp_world, "initial_enemy_spawns", None):
                    world.initial_enemy_spawns = list(temp_world.initial_enemy_spawns)

        preserved_bosses = [
            e
            for e in getattr(game_state, "enemies", [])
            if not e.is_dead()
            and (
                getattr(e, "name", "") == "Night Boss"
                or getattr(e, "is_slug_boss", False)
                or getattr(e, "is_meadow_censor", False)
                or getattr(e, "is_rimecrest_arbiter", False)
                or e.__class__.__name__ in ("NightBoss", "SlugBoss", "MeadowCensorBoss", "RimecrestArbiterBoss")
            )
        ]

        current_act = int(getattr(game_state, "current_act", 0) or 0)
        empowered_act = bool(getattr(game_state, "empowered_act", False))
        hp_mult = 1.0
        dmg_mult = 1.0
        spd_mult = 1.0
        cd_mult = 1.0
        emp_flag = None
        if current_act >= 1 or empowered_act:
            sat = get_act_saturation(max(1, current_act if current_act >= 1 else 2))
            spd_mult = float(sat.get("speed_multiplier", 1.0))
            cd_mult = float(sat.get("cooldown_multiplier", 1.0))
            if empowered_act and current_act <= 2:
                hp_mult = float(max(ACT2_HP_MULTIPLIER, float(sat["hp_multiplier"])))
                dmg_mult = float(max(ACT2_DAMAGE_MULTIPLIER, float(sat["damage_multiplier"])))
                emp_flag = True
            else:
                hp_mult = float(sat["hp_multiplier"])
                dmg_mult = float(sat["damage_multiplier"])
                emp_flag = bool(sat["empowered"])

        defeated_ids = getattr(game_state, "defeated_miniboss_ids", None) or set()
        respawned_enemies = []
        next_enemy_id = 0

        def get_next_id():
            nonlocal next_enemy_id
            id_val = next_enemy_id
            next_enemy_id += 1
            return id_val

        for spec in (getattr(world, "initial_enemy_spawns", None) or ()):
            enemy_cls = spec.get("cls")
            if enemy_cls is None:
                enemy_cls = ENEMY_REGISTRY.get(spec.get("type"))
            if enemy_cls is None:
                continue
            enemy_id = spec.get("id") if spec.get("id") is not None else spec.get("enemy_id")
            raw_x = float(spec.get("x", 0.0))
            raw_y = float(spec.get("y", 0.0))
            temp_enemy = enemy_cls(raw_x, raw_y, id=enemy_id)
            if spec.get("is_stationary"):
                temp_enemy.is_stationary = True
            if (temp_enemy.is_miniboss or spec.get("is_miniboss")) and enemy_id and enemy_id in defeated_ids:
                continue

            if world is not None and hasattr(world, "find_nearest_walkable_spawn"):
                wx, wy = world.find_nearest_walkable_spawn(
                    temp_enemy.x, temp_enemy.y, temp_enemy.width, temp_enemy.height
                )
            elif world is not None:
                wx, wy = World.find_walkable_spawn_in_grid(
                    world.grid,
                    world.interactables,
                    temp_enemy.x,
                    temp_enemy.y,
                    temp_enemy.width,
                    temp_enemy.height,
                )
            else:
                wx, wy = temp_enemy.x, temp_enemy.y

            temp_enemy.x, temp_enemy.y = float(wx), float(wy)
            temp_enemy.origin_x, temp_enemy.origin_y = float(wx), float(wy)

            if (
                hp_mult != 1.0
                or dmg_mult != 1.0
                or emp_flag is not None
                or spd_mult != 1.0
                or cd_mult != 1.0
            ):
                temp_enemy.apply_act_scaling(
                    hp_mult,
                    dmg_mult,
                    empowered=emp_flag,
                    speed_multiplier=spd_mult,
                    cooldown_multiplier=cd_mult,
                )

            temp_enemy.network_id = get_next_id()
            respawned_enemies.append(temp_enemy)

        for idx, boss in enumerate(preserved_bosses):
            if getattr(boss, "network_id", -1) < 0:
                boss.network_id = 9000 + idx
            respawned_enemies.append(boss)

        game_state.enemies = respawned_enemies
        if world is not None:
            world._enemies = list(respawned_enemies)

        # Re-link routes after respawn
        LevelLoader.link_actors_to_routes(game_state)
        if hasattr(game_state, "marginalia_engine") and game_state.marginalia_engine:
            game_state.marginalia_engine.on_respite_rest(game_state)

        print(f"[DEBUG] Rest complete. {len(game_state.enemies)} threats re-manifested.")
        game_state.save_stats(wait=True)

    def execute_finalize_upgrades(self, game_state, audio_manager=None):
        """Apply all staged upgrades permanently, deduct cost, heal player, and lock upgrades."""
        info = game_state.get_staged_respite_info()
        total_cost = info["total_staged_cost"]
        if total_cost <= 0:
            return False

        pages = game_state.stats.data["lifetime_stats"].get("pages_collected", 0) if game_state.stats else 0
        if pages < total_cost:
            return False

        # Deduct pages
        if game_state.stats:
            game_state.stats.data["lifetime_stats"]["pages_collected"] -= total_cost

        # Apply prowess
        from constants import PROWESS_ATTACK_STEP, FORTIFICATION_HP_STEP
        staged_prowess = info["staged_prowess"]
        if staged_prowess > 0:
            current_prowess = game_state.player.stats.get("attack_modifier", 0)
            game_state.player.stats["attack_modifier"] = current_prowess + (staged_prowess * PROWESS_ATTACK_STEP)

        # Apply fort
        staged_fort = info["staged_fort"]
        if staged_fort > 0:
            current_fort = game_state.player.stats.get("max_hp_modifier", 0)
            game_state.player.stats["max_hp_modifier"] = current_fort + (staged_fort * FORTIFICATION_HP_STEP)

        # Heal player to new max HP
        game_state.player.hp = game_state.player.max_hp

        # Recalculate edification level
        prowess = game_state.player.stats.get("attack_modifier", 0)
        fort = game_state.player.stats.get("max_hp_modifier", 0)
        game_state.player.stats["edification"] = (prowess // PROWESS_ATTACK_STEP) + (fort // FORTIFICATION_HP_STEP) + 1

        # Sync to persistent stats
        if game_state.stats:
            if "run_state" in game_state.stats.data and game_state.stats.data["run_state"]:
                game_state.stats.data["run_state"]["player"]["stats"] = game_state.player.stats

        game_state.player.has_rested_this_session = False
        game_state.respite_upgrades = {1: 0, 2: 0}

        # Phase 4: Network Notify
        if game_state.network_manager.network_mode == "CLIENT":
            data = {"max_hp": game_state.player.max_hp}
            game_state.network_manager.send_respite_event("UPGRADE", marked_idx=None, data=data)

        if audio_manager:
            audio_manager.play_sfx("menu_confirm.ogg")

        return True

    def execute_upgrade(self, game_state, marked_idx, audio_manager=None):
        """Legacy upgrade method. Stages the marked index once and immediately finalizes."""
        if marked_idx in (1, 2):
            game_state.respite_upgrades = {1: 0, 2: 0}
            game_state.respite_upgrades[marked_idx] = 1
            return self.execute_finalize_upgrades(game_state, audio_manager=audio_manager)
        return False

class LevelLoader:
    """
    Dedicated parser for 2D text matrix strings or JSON map definitions.
    Translates symbols into spatial entities and initial layout.
    """
    @staticmethod
    def load_json_map(
        file_path,
        saved_enemies=None,
        defeated_ids=None,
        destroyed_ids=None,
        hp_multiplier=1.0,
        damage_multiplier=1.0,
        empowered=None,
        speed_multiplier=1.0,
        cooldown_multiplier=1.0,
    ):
        """Loads a JSON map file and parses it, supporting modular stitching."""
        import os
        map_filename = os.path.basename(file_path)
        map_name = map_filename.replace(".json", "").replace(".txt", "")
        if "generated_world" in map_name:
            map_name = "avoid_rain_generated_world"

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if content.startswith("{"):
                data = json.loads(content)
            else:
                lines = [line.rstrip("\r\n") for line in content.splitlines() if line.strip()]
                data = {
                    "map_id": map_name,
                    "dimensions": {"width": len(lines[0]) if lines else 0, "height": len(lines)},
                    "grid": lines,
                    "entities": {},
                    "module_sockets": [],
                }

        grid = [list(row) for row in data["grid"]]
        raw_entities = data.get("entities", {})

        # 1. Modular Assembly Pass
        module_sockets = data.get("module_sockets", [])
        for socket in module_sockets:
            # Override Rule: If the map JSON already defines an active_plug, use it
            active_plug = socket.get("active_plug")
            
            if not active_plug:
                # Independent Anomaly Roll: Each socket has a 10% chance to be Special Edition
                if random.random() < 0.1 and POOL_SPECIAL_EDITION:
                    active_plug = random.choice(POOL_SPECIAL_EDITION)
                else:
                    active_plug = random.choice(POOL_MONTHLY_REPORT)

            # Load and stitch the plug
            try:
                with open(active_plug, 'r', encoding='utf-8') as f_plug:
                    plug_data = json.load(f_plug)
                    
                b = socket["bounds"]
                for y_p, row_p in enumerate(plug_data["grid"]):
                    for x_p, char_p in enumerate(row_p):
                        grid[b["y"] + y_p][b["x"] + x_p] = char_p
                
                # Stitch entities (namespace patrol route_ids per socket to prevent cross-room collisions)
                socket_id = socket.get("name") or f"{b['x']}_{b['y']}"
                for key, e_val in plug_data.get("entities", {}).items():
                    px_p, py_p = map(int, key.split(','))
                    new_key = f"{b['x'] + px_p},{b['y'] + py_p}"
                    if isinstance(e_val, dict) and e_val.get("route_id") and e_val.get("route_id") != "default":
                        scoped = dict(e_val)
                        scoped["route_id"] = f"{socket_id}:{e_val['route_id']}"
                        raw_entities[new_key] = scoped
                    else:
                        raw_entities[new_key] = e_val
            except Exception as e:
                print(f"[ERROR] Modular stitch failed for {active_plug}: {e}")

        # 1b. Seal 1-tile outer perimeter border of stitched macro-worlds so no edge exposes raw void
        if (module_sockets or data.get("seal_outer_perimeter")) and grid and grid[0]:
            gh = len(grid)
            gw = len(grid[0])
            for x_b in range(gw):
                grid[0][x_b] = "#"
                grid[gh - 1][x_b] = "#"
            for y_b in range(gh):
                grid[y_b][0] = "#"
                grid[y_b][gw - 1] = "#"
                if gw >= 2 and grid[y_b][gw - 2] == "h":
                    grid[y_b][gw - 2] = "."

        # 2. Conversion Pass: Symbols -> Entity Objects
        entity_data = {}
        for key, val in raw_entities.items():
            try:
                kx, ky = map(int, key.split(','))
                entity_data[(kx, ky)] = val
            except ValueError:
                continue

        grid, interactables, warp_tiles, player_start, enemies = LevelLoader.parse_map(
            ["".join(row) for row in grid],
            entity_data,
            saved_enemies=saved_enemies,
            map_name=map_name,
            defeated_ids=defeated_ids,
            destroyed_ids=destroyed_ids,
            map_filename=map_filename,
            hp_multiplier=hp_multiplier,
            damage_multiplier=damage_multiplier,
            empowered=empowered,
            speed_multiplier=speed_multiplier,
            cooldown_multiplier=cooldown_multiplier,
        )

        # Apply procedural spawn override if present
        spawn_override = data.get("spawn_coords")
        if spawn_override:
            player_start = (spawn_override["x"] * TILE_SIZE, spawn_override["y"] * TILE_SIZE)
            print(f"[DEBUG] Applied spawn override: {player_start}")

        print(f"[DEBUG] Final player_start for {map_name}: {player_start}")
        boss_coords_list = data.get("boss_coords_list") or []
        module_sockets = data.get("module_sockets", [])

        return grid, interactables, warp_tiles, player_start, enemies, boss_coords_list, module_sockets

    @staticmethod
    def load_map_zones(file_path):
        """Return optional 'zones' metadata dict from a JSON map file (e.g., Sanctuary floor/roof zones)."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            zones = data.get("zones")
            return zones if isinstance(zones, dict) else {}
        except Exception:
            return {}

    @staticmethod
    def parse_map(
        prototype_array,
        entity_data=None,
        saved_enemies=None,
        map_name="unknown",
        defeated_ids=None,
        destroyed_ids=None,
        map_filename=None,
        hp_multiplier=1.0,
        damage_multiplier=1.0,
        empowered=None,
        speed_multiplier=1.0,
        cooldown_multiplier=1.0,
    ):
        """
        Parses a string array and returns (grid, interactables, warp_tiles, player_start, enemies).
        If saved_enemies is provided, default spawner symbols for enemies are bypassed.
        """
        if map_filename is None:
            map_filename = map_name
        from engine.enemy import SYMBOL_REGISTRY
        
        h = len(prototype_array)
        w = len(prototype_array[0]) if h > 0 else 0
        grid = [[TILE_EMPTY for _ in range(w)] for _ in range(h)]
        interactables = []
        enemies = []
        warp_tiles = {}
        player_start = (PLAYER_START_X, PLAYER_START_Y)
        entity_data = entity_data or {}
        defeated_ids = defeated_ids or set()
        destroyed_ids = destroyed_ids or set()

        # Phase 4 Network Rule: Assign numeric IDs to enemies for synchronization
        # These are used to match Host enemies to Client enemies in the UDP sync.
        next_enemy_id = 0
        def get_next_id():
            nonlocal next_enemy_id
            id_val = next_enemy_id
            next_enemy_id += 1
            return id_val

        # If we have saved enemies, reconstruct them directly (The Override Rule)
        if saved_enemies:
            from engine.enemy import ENEMY_REGISTRY
            for e_data in saved_enemies:
                e_type = e_data.get("type")
                if e_type in ENEMY_REGISTRY:
                    enemy = ENEMY_REGISTRY[e_type].from_dict(e_data)
                    # Phase 4 Network Rule: Assign numeric ID for sync
                    enemy.network_id = get_next_id()
                    enemies.append(enemy)
        
        # Check for Lotus Topography symbols
        has_lotus = any('M' in row or 'X' in row for row in prototype_array)
        if has_lotus:
            print("[DEBUG] LevelLoader actively building Lotus Topography Grid")

        # Check for Chapter 1 specifically for Production Grid verification
        if any('T' in row for row in prototype_array) and not has_lotus:
            print("[DEBUG] Actively rendering Chapter 1 Production Grid")

        for y, row in enumerate(prototype_array):
            for x, char in enumerate(row):

                # 1. Tile Grid Assignment (Static Topography)
                if char in ('#', 'X'):
                    grid[y][x] = TILE_WALL
                elif char == 'M':
                    from constants import TILE_LOTUS_FRAME
                    grid[y][x] = TILE_LOTUS_FRAME
                elif char == 'g':
                    from constants import TILE_GRASS
                    grid[y][x] = TILE_GRASS
                elif char == 'G':
                    from constants import TILE_THICKET
                    grid[y][x] = TILE_THICKET
                else:
                    # Every other symbol defaults to empty floor for collision/base grid purposes
                    grid[y][x] = TILE_EMPTY

                pos = (x * TILE_SIZE, y * TILE_SIZE)
                dim = (TILE_SIZE, TILE_SIZE)

                # 2. Entity & Interaction Spawning (Dynamic Overlay)
                # Separated from tile block to prevent character consumption
                if char == 'W':
                    # Warp Portal
                    data = entity_data.get((x, y), {})
                    target = data.get('target', 'sanctuary')
                    sx = data.get('spawn_x', PLAYER_START_X)
                    sy = data.get('spawn_y', PLAYER_START_Y)

                    warp_tiles[(x, y)] = (target, sx, sy)
                    interactables.append(WarpPortal(
                        target, sx, sy, (pos[0], pos[1], dim[0], dim[1]),
                        name=data.get('name', "The Chronicle")
                    ))

                elif char == 'R':
                    # Respite
                    respite = Respite(pos, dim)
                    gated_id = None
                    search_range = 5
                    h_grid = len(prototype_array)
                    w_grid = len(prototype_array[0]) if h_grid > 0 else 0
                    for dy in range(-search_range, search_range + 1):
                        for dx in range(-search_range, search_range + 1):
                            ny, nx = y + dy, x + dx
                            if 0 <= ny < h_grid and 0 <= nx < w_grid:
                                nearby_char = prototype_array[ny][nx]
                                if nearby_char in ('E', '2', '3'):
                                    gated_id = f"{map_name}:{nx},{ny}"
                                    break
                        if gated_id:
                            break

                    if gated_id:
                        respite.gated_by_miniboss_id = gated_id
                        respite.is_active = (gated_id in defeated_ids)
                    else:
                        respite.is_active = True
                    interactables.append(respite)

                elif char == 'T':
                    # Static Obstacle / Tree / Sanctuary prop_type override (in-place, no duplicates)
                    edata = entity_data.get((x, y), {})
                    ptype = edata.get("prop_type") if isinstance(edata, dict) else None
                    if ptype in ("locked_shed_door", "mossy_gravestone"):
                        default_name = "Weathered Shed Door" if ptype == "locked_shed_door" else "Mossy Gravestone"
                        default_dlg = (
                            "A heavy brass padlock holds the shed shut."
                            if ptype == "locked_shed_door"
                            else "Weathered stone covered in quiet moss."
                        )
                        prop_obj = FlavorProp(
                            pos,
                            dim,
                            name=edata.get("name", default_name),
                            dialogue_text=edata.get("dialogue", default_dlg),
                            prop_type=ptype,
                            is_solid=True,
                        )
                        interactables.append(prop_obj)
                    else:
                        tree = GameObject(pos, dim)
                        tree.is_solid = True
                        tree.prop_type = ptype
                        tree.name = "SanctuaryTreeCanopy" if ptype == "sanctuary_tree" else "Structure"
                        interactables.append(tree)

                elif char == 'C':
                    # The Chronicler NPC
                    chronicler = Chronicler(pos, dim)
                    interactables.append(chronicler)

                elif char == '&':
                    # The Binder NPC
                    binder = Binder(pos, dim)
                    interactables.append(binder)

                elif char == 'F':
                    # The Wellspring (Fountain)
                    wellspring = Wellspring(pos, dim)
                    interactables.append(wellspring)

                elif char == 'L':
                    # Lore Fragment
                    data = entity_data.get((x, y), {})
                    frag_id = data.get('fragment_id', 'unknown')
                    frag_name = data.get('name', 'Lost Passage')
                    fragment = LoreFragment(pos, dim, frag_id, name=frag_name)
                    interactables.append(fragment)

                elif char == 'B':
                    # Placeholder Prop / Barrel
                    prop_id = f"{map_name}:prop:{x},{y}"
                    if prop_id in destroyed_ids:
                        continue # Already redacted

                    prop = GameObject(pos, dim)
                    prop.is_solid = True
                    prop.is_breakable = True
                    prop.health = 1.0
                    prop.name = "Barrel"
                    prop.id = prop_id
                    interactables.append(prop)

                elif char == 'h':
                    # Heavy Bookcase - Horizontal 2x1
                    bookcase_dim = (TILE_SIZE * 2, TILE_SIZE)
                    bookcase = GameObject(pos, bookcase_dim)
                    bookcase.is_solid = True
                    bookcase.name = "Heavy Bookcase"
                    interactables.append(bookcase)

                elif char == 'd':
                    # Ink-Drip Urn - 1x1
                    urn = GameObject(pos, dim)
                    urn.is_solid = True
                    urn.name = "Ink Urn"
                    interactables.append(urn)

                elif char == 'v':
                    # Spilled Inkwell Puddle or Sanctuary Pond Lily/Reeds prop_type override
                    edata = entity_data.get((x, y), {})
                    ptype = edata.get("prop_type") if isinstance(edata, dict) else None
                    puddle = GameObject(pos, dim)
                    puddle.is_solid = False
                    puddle.prop_type = ptype
                    puddle.name = "PondLilyReeds" if ptype == "pond_lily_reeds" else "Inkwell Puddle"
                    interactables.append(puddle)

                elif char == 'l':
                    # Iron Candelabra - 1x1 Light Source
                    candelabra = GameObject(pos, dim)
                    candelabra.is_solid = True
                    candelabra.name = "Candelabra"
                    interactables.append(candelabra)

                elif char == 'S':
                    # Seat / Bench - 1x1 (40x40 matching bench.png)
                    bench = GameObject(pos, dim)
                    bench.is_solid = True
                    bench.name = "Bench"
                    interactables.append(bench)

                elif char == 'K':
                    # Rock or Sanctuary GardenFlora prop_type override (in-place, non-solid)
                    edata = entity_data.get((x, y), {})
                    ptype = edata.get("prop_type") if isinstance(edata, dict) else None
                    rock = GameObject(pos, dim)
                    rock.is_solid = False
                    rock.prop_type = ptype
                    rock.name = "GardenFlora" if ptype == "garden_flora" else "Rock"
                    interactables.append(rock)

                elif char == 'P':
                    # Player Start hook
                    player_start = (pos[0], pos[1])

                elif char in ('1','2','3','4','5','6','7','8','9'):
                    # Patrol Point
                    data = entity_data.get((x, y), {})
                    rid = data.get("route_id", "default")
                    caste = data.get("caste_filter", [])
                    wmin = data.get("wait_min", 2.0)
                    wmax = data.get("wait_max", 5.0)
                    point = PatrolPoint(pos, rid, int(char), caste, wmin, wmax)
                    interactables.append(point)

                elif char in SYMBOL_REGISTRY:
                    # Generic Enemy Spawner (Bypassed if loading from save)
                    if not saved_enemies:
                        # Generate Unique ID based on position and map
                        enemy_id = f"{map_name}:{x},{y}"
                        
                        # Filter Rule: If it's a miniboss and already defeated, skip spawning
                        enemy_cls = SYMBOL_REGISTRY[char]
                        
                        data = entity_data.get((x, y), {})
                        temp_enemy = enemy_cls(pos[0], pos[1], id=enemy_id)
                        if (
                            hp_multiplier != 1.0
                            or damage_multiplier != 1.0
                            or empowered is not None
                            or speed_multiplier != 1.0
                            or cooldown_multiplier != 1.0
                        ):
                            temp_enemy.apply_act_scaling(
                                hp_multiplier,
                                damage_multiplier,
                                empowered=empowered,
                                speed_multiplier=speed_multiplier,
                                cooldown_multiplier=cooldown_multiplier,
                            )
                        
                        # Phase 4 Network Rule: Assign numeric ID for sync
                        temp_enemy.network_id = get_next_id()
                        
                        # Custom Instance Attributes
                        if data.get("is_stationary"):
                            temp_enemy.is_stationary = True
                        
                        if temp_enemy.is_miniboss and enemy_id in defeated_ids:
                            print(f"[DEBUG] Elite {enemy_id} already redacted; skipping spawn.")
                        else:
                            enemies.append(temp_enemy)

        if not saved_enemies and enemies:
            for enemy in enemies:
                wx, wy = World.find_walkable_spawn_in_grid(
                    grid, interactables, enemy.x, enemy.y, enemy.width, enemy.height
                )
                enemy.x, enemy.y = wx, wy
                enemy.origin_x, enemy.origin_y = wx, wy

        return grid, interactables, warp_tiles, player_start, enemies

    @staticmethod
    def _tile_line_clear_of_walls(grid, x0_px, y0_px, x1_px, y1_px) -> bool:
        """Return True if the straight tile line between two pixel positions contains no TILE_WALL."""
        if not grid or not grid[0]:
            return True
        grid_h = len(grid)
        grid_w = len(grid[0])
        tx0, ty0 = int(x0_px // TILE_SIZE), int(y0_px // TILE_SIZE)
        tx1, ty1 = int(x1_px // TILE_SIZE), int(y1_px // TILE_SIZE)
        steps = max(abs(tx1 - tx0), abs(ty1 - ty0), 1) * 4
        for i in range(steps + 1):
            t = i / float(steps)
            px = x0_px + (x1_px - x0_px) * t
            py = y0_px + (y1_px - y0_px) * t
            tx = int(px // TILE_SIZE)
            ty = int(py // TILE_SIZE)
            if tx < 0 or ty < 0 or tx >= grid_w or ty >= grid_h:
                return False
            if grid[ty][tx] in (TILE_WALL, "#", "X"):
                return False
        return True

    @staticmethod
    def link_actors_to_routes(game_state):
        """Find and assign patrol routes to nearby actors using proximity discovery."""
        all_actors = list(game_state.enemies)
        # Search for NPCs who are Actors
        for obj in game_state.world.interactables:
            if isinstance(obj, Actor):
                all_actors.append(obj)

        markers = [obj for obj in game_state.world.interactables if isinstance(obj, PatrolPoint)]
        if not markers:
            return

        grid = getattr(game_state.world, "grid", None)

        route_by_id = {}
        for m in markers:
            if m.route_id != "default":
                route_by_id.setdefault(m.route_id, []).append(m)
        for r_list in route_by_id.values():
            r_list.sort(key=lambda x: x.symbol_idx)

        linked_count = 0
        for actor in all_actors:
            # Rule: Only if actor has no route and is not stationary
            if actor.patrol_route or actor.is_stationary:
                continue

            ax, ay = actor.get_center()
            # 1. Find nearest marker (within 20 tiles for robustness)
            nearest = None
            min_dist_sq = (20 * TILE_SIZE) ** 2

            for m in markers:
                # Caste Filter Check
                if m.caste_filter and actor.__class__.__name__ not in m.caste_filter:
                    continue

                mx, my = m.x + m.width / 2, m.y + m.height / 2
                if m.route_id == "default" and not LevelLoader._tile_line_clear_of_walls(
                    grid, ax, ay, mx, my
                ):
                    continue
                dist_sq = (ax - mx) ** 2 + (ay - my) ** 2
                if dist_sq < min_dist_sq:
                    min_dist_sq = dist_sq
                    nearest = m

            if nearest:
                # 2. Gather all markers in the same logical route
                if nearest.route_id != "default":
                    route = list(route_by_id.get(nearest.route_id, [nearest]))
                else:
                    # Spatially Connected Discovery:
                    # Find all 'default' markers reachable in steps of 10 tiles without crossing a wall
                    route = []
                    to_check = [nearest]
                    while to_check:
                        curr = to_check.pop(0)
                        if curr in route:
                            continue
                        route.append(curr)

                        cx, cy = curr.x + curr.width / 2, curr.y + curr.height / 2
                        for m in markers:
                            if m.route_id == "default" and m not in route:
                                mx, my = m.x + m.width / 2, m.y + m.height / 2
                                d_sq = (cx - mx) ** 2 + (cy - my) ** 2
                                if d_sq <= (10 * TILE_SIZE) ** 2 and LevelLoader._tile_line_clear_of_walls(
                                    grid, cx, cy, mx, my
                                ):
                                    to_check.append(m)
                    route.sort(key=lambda x: x.symbol_idx)
                    if len(route) > 1:
                        chained = [route[0]]
                        for cand in route[1:]:
                            prev = chained[-1]
                            pcx, pcy = prev.x + prev.width / 2, prev.y + prev.height / 2
                            mcx, mcy = cand.x + cand.width / 2, cand.y + cand.height / 2
                            if LevelLoader._tile_line_clear_of_walls(grid, pcx, pcy, mcx, mcy):
                                chained.append(cand)
                        if nearest not in chained:
                            chained = [nearest]
                        route = chained

                actor.patrol_route = route
                # Start at the nearest marker
                actor.patrol_idx = route.index(nearest)
                linked_count += 1
        if linked_count:
            print(f"[STANZA] Linked {linked_count} actors to patrol routes.")


class World:
    """Manages the tile-based world map.

    Supports loading from string-based prototypes for rapid level design.
    """
    def __init__(self, name='sanctuary'):
        self.name = name.replace(".json", "").replace(".txt", "") if isinstance(name, str) else name
        self.map_filename = (
            os.path.basename(name) if (isinstance(name, str) and ("." in name)) else f"{self.name}.txt"
        )
        self.grid = [[TILE_EMPTY for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]
        self.warp_tiles = {}  # Legacy mapping (x,y) -> (target_name, spawn_x_px, spawn_y_px)
        self.interactables = []
        self._enemies = []
        self.initial_enemy_spawns = []
        self.player_start = (PLAYER_START_X, PLAYER_START_Y)
        self.module_sockets = []
        self.boss_coords_list = []
        self.grass_decorations = {}
        self.sanctuary_zones = {}
        self._zone_cache_id = None
        self._zone_tile_sets = {}
        self._spatial_sig = None
        self._solid_buckets = {}
        self._interactive_buckets = {}
        self._puddle_buckets = {}
        self._dynamic_actors = []
        self._gated_respites = []

    @property
    def enemies(self):
        """Return active enemies in this World."""
        return self._enemies

    @enemies.setter
    def enemies(self, value):
        """Set active enemies and record initial_enemy_spawns on first population."""
        self._enemies = list(value) if value is not None else []
        if self._enemies and not self.initial_enemy_spawns:
            self.initial_enemy_spawns = self.build_initial_enemy_spawns(self._enemies)

    @staticmethod
    def build_initial_enemy_spawns(enemies):
        """Capture spawn descriptors for enemies so Respite.execute_rest() can re-manifest them cleanly."""
        spawns = []
        for enemy in (enemies or ()):
            if (
                getattr(enemy, "name", "") == "Night Boss"
                or getattr(enemy, "is_slug_boss", False)
                or getattr(enemy, "is_meadow_censor", False)
                or getattr(enemy, "is_rimecrest_arbiter", False)
            ):
                continue
            spawns.append(
                {
                    "cls": enemy.__class__,
                    "type": enemy.__class__.__name__,
                    "x": float(getattr(enemy, "origin_x", enemy.x)),
                    "y": float(getattr(enemy, "origin_y", enemy.y)),
                    "id": getattr(enemy, "id", None),
                    "is_miniboss": bool(getattr(enemy, "is_miniboss", False)),
                    "is_stationary": bool(getattr(enemy, "is_stationary", False)),
                }
            )
        return spawns

    @staticmethod
    def find_walkable_spawn_in_grid(grid, interactables, x, y, width, height, max_radius_tiles=6):
        """Return the nearest walkable (wx, wy) in grid where (wx, wy, width, height) avoids walls and solid props."""
        fx, fy = float(x), float(y)
        if not grid or not grid[0]:
            return (fx, fy)

        from engine.physics import check_aabb_collision

        grid_h = len(grid)
        grid_w = len(grid[0])
        map_w_px = grid_w * TILE_SIZE
        map_h_px = grid_h * TILE_SIZE
        w_val = max(1.0, float(width))
        h_val = max(1.0, float(height))
        solid_props = [
            getattr(obj, "rect", (obj.x, obj.y, obj.width, obj.height))
            for obj in (interactables or ())
            if getattr(obj, "is_solid", False) and getattr(obj, "is_active", True)
        ]

        def _is_clear(cx_px, cy_px):
            if cx_px < 0.0 or cy_px < 0.0 or (cx_px + w_val) > map_w_px or (cy_px + h_val) > map_h_px:
                return False
            tx0 = int(cx_px // TILE_SIZE)
            ty0 = int(cy_px // TILE_SIZE)
            tx1 = int((cx_px + max(0.0, w_val - 1e-4)) // TILE_SIZE)
            ty1 = int((cy_px + max(0.0, h_val - 1e-4)) // TILE_SIZE)
            if tx0 < 0 or ty0 < 0 or tx1 >= grid_w or ty1 >= grid_h:
                return False
            for ty in range(ty0, ty1 + 1):
                row = grid[ty]
                for tx in range(tx0, tx1 + 1):
                    if row[tx] in (TILE_WALL, "#", "X"):
                        return False
            cand_rect = (cx_px, cy_px, w_val, h_val)
            for p_rect in solid_props:
                if check_aabb_collision(cand_rect, p_rect):
                    return False
            return True

        if _is_clear(fx, fy):
            return (fx, fy)

        base_tx = max(0, min(grid_w - 1, int(fx // TILE_SIZE)))
        base_ty = max(0, min(grid_h - 1, int(fy // TILE_SIZE)))
        search_radius = max(1, int(max_radius_tiles))

        candidates = []
        for radius in range(0, search_radius + 1):
            for dy in range(-radius, radius + 1):
                for dx in range(-radius, radius + 1):
                    if max(abs(dx), abs(dy)) != radius:
                        continue
                    tx = base_tx + dx
                    ty = base_ty + dy
                    if tx < 0 or ty < 0 or tx >= grid_w or ty >= grid_h:
                        continue
                    cand_x = float(tx * TILE_SIZE)
                    cand_y = float(ty * TILE_SIZE)
                    dist_sq = (cand_x - fx) ** 2 + (cand_y - fy) ** 2
                    candidates.append((dist_sq, radius, abs(dy) + abs(dx), dy, dx, cand_x, cand_y))
        candidates.sort()
        for _, _, _, _, _, cand_x, cand_y in candidates:
            if _is_clear(cand_x, cand_y):
                return (cand_x, cand_y)

        return (fx, fy)

    def find_nearest_walkable_spawn(self, x, y, width, height, max_radius_tiles=6):
        """Instance wrapper around find_walkable_spawn_in_grid using this World's grid and interactables."""
        return self.find_walkable_spawn_in_grid(
            self.grid,
            self.interactables,
            x,
            y,
            width,
            height,
            max_radius_tiles=max_radius_tiles,
        )

    def _ensure_zone_index(self):
        """Build cached tile sets from self.sanctuary_zones for O(1) floor/roof zone lookup."""
        zones = self.sanctuary_zones if isinstance(self.sanctuary_zones, dict) else {}
        sig = (id(zones), tuple((k, len(v) if isinstance(v, list) else 0) for k, v in zones.items()))
        if self._zone_cache_id == sig:
            return
        self._zone_cache_id = sig
        tile_sets = {}
        for z_name in ("pond_water", "wood_floor", "dirt_path", "roof_zones"):
            coords = set()
            for entry in zones.get(z_name, ()):
                if isinstance(entry, dict) and all(k in entry for k in ("x", "y", "w", "h")):
                    ex, ey, ew, eh = int(entry["x"]), int(entry["y"]), int(entry["w"]), int(entry["h"])
                    for ty in range(ey, ey + eh):
                        for tx in range(ex, ex + ew):
                            coords.add((tx, ty))
                elif isinstance(entry, (list, tuple)):
                    if len(entry) == 2:
                        coords.add((int(entry[0]), int(entry[1])))
                    elif len(entry) == 4:
                        ex, ey, ew, eh = int(entry[0]), int(entry[1]), int(entry[2]), int(entry[3])
                        for ty in range(ey, ey + eh):
                            for tx in range(ex, ex + ew):
                                coords.add((tx, ty))
            tile_sets[z_name] = coords
        self._zone_tile_sets = tile_sets

    def get_sanctuary_zone_type(self, tx, ty):
        """Return 'pond_water', 'wood_floor', 'dirt_path', or None for Sanctuary tile (tx, ty)."""
        if not self.sanctuary_zones:
            return None
        self._ensure_zone_index()
        pt = (int(tx), int(ty))
        for z_name in ("pond_water", "wood_floor", "dirt_path"):
            if pt in self._zone_tile_sets.get(z_name, ()):
                return z_name
        return None

    def is_in_sanctuary_pond(self, rect):
        """Return True if rect overlaps any tile in sanctuary_zones['pond_water']."""
        if not self.sanctuary_zones:
            return False
        self._ensure_zone_index()
        pond_set = self._zone_tile_sets.get("pond_water")
        if not pond_set:
            return False
        rx, ry, rw, rh = rect
        x0 = int(rx // TILE_SIZE)
        y0 = int(ry // TILE_SIZE)
        x1 = int((rx + max(0.0, rw - 1e-4)) // TILE_SIZE)
        y1 = int((ry + max(0.0, rh - 1e-4)) // TILE_SIZE)
        for ty in range(y0, y1 + 1):
            for tx in range(x0, x1 + 1):
                if (tx, ty) in pond_set:
                    return True
        return False

    def _ensure_spatial_index(self):
        """Build or refresh spatial hash buckets when self.interactables changes."""
        items = self.interactables
        sig = (
            id(items),
            len(items),
            id(items[0]) if items else 0,
            id(items[-1]) if items else 0,
        )
        if self._spatial_sig == sig:
            return
        self._spatial_sig = sig
        cell_size = TILE_SIZE * 4  # 160x160 pixel buckets
        solid_b = {}
        inter_b = {}
        puddle_b = {}
        dynamic_actors = []
        respites = []
        for obj in items:
            if type(obj).__name__ == "Respite" and getattr(obj, "gated_by_miniboss_id", None):
                respites.append(obj)
            # Keep mobile Actor instances (e.g., patrolling Chronicler) out of static buckets
            if isinstance(obj, Actor):
                dynamic_actors.append(obj)
                continue
            ox, oy, ow, oh = obj.rect
            cx0, cy0 = int(ox // cell_size), int(oy // cell_size)
            cx1, cy1 = int((ox + ow) // cell_size), int((oy + oh) // cell_size)
            is_solid = getattr(obj, "is_solid", False)
            is_inter = getattr(obj, "is_interactive", False)
            is_puddle = getattr(obj, "name", "") == "Inkwell Puddle"
            if not (is_solid or is_inter or is_puddle):
                continue
            for cy in range(cy0, cy1 + 1):
                for cx in range(cx0, cx1 + 1):
                    key = (cx, cy)
                    if is_solid:
                        solid_b.setdefault(key, []).append(obj)
                    if is_inter:
                        inter_b.setdefault(key, []).append(obj)
                    if is_puddle:
                        puddle_b.setdefault(key, []).append(obj)
        self._solid_buckets = solid_b
        self._interactive_buckets = inter_b
        self._puddle_buckets = puddle_b
        self._dynamic_actors = dynamic_actors
        self._gated_respites = respites

    def load_from_prototype(self, prototype_array, entity_data=None, saved_enemies=None):
        """
        Populates the world from a string array using LevelLoader.
        """
        self.initial_enemy_spawns = []
        self.grid, self.interactables, self.warp_tiles, self.player_start, self.enemies = \
            LevelLoader.parse_map(prototype_array, entity_data, saved_enemies)
        self.initial_enemy_spawns = self.build_initial_enemy_spawns(self.enemies)
        self.generate_grass_decorations()

    def generate_grass_decorations(self):
        """Scan the grid for TILE_GRASS/TILE_THICKET and generate random grass instances."""
        from constants import TILE_GRASS, TILE_THICKET
        self.grass_decorations = {}
        h = len(self.grid)
        w = len(self.grid[0]) if h > 0 else 0
        
        for y in range(h):
            for x in range(w):
                tile = self.grid[y][x]
                if tile == TILE_GRASS:
                    num_instances = random.randint(2, 6)
                    instances = []
                    for _ in range(num_instances):
                        variant = random.randint(0, 2)
                        dx = random.randint(-12, 12)
                        dy = random.randint(-12, 12)
                        # 95% small, 5% rare medium/tall overgrowth
                        roll = random.random()
                        if roll < 0.95:
                            pool_key = "small"
                        else:
                            pool_key = random.choice(["medium", "tall"])
                        instances.append((pool_key, variant, dx, dy))
                    self.grass_decorations[(x, y)] = instances
                elif tile == TILE_THICKET:
                    num_instances = random.randint(5, 10)
                    instances = []
                    for _ in range(num_instances):
                        variant = random.randint(0, 2)
                        dx = random.randint(-12, 12)
                        dy = random.randint(-12, 12)
                        # 10% small, 45% medium, 45% tall
                        roll = random.random()
                        if roll < 0.10:
                            pool_key = "small"
                        elif roll < 0.55:
                            pool_key = "medium"
                        else:
                            pool_key = "tall"
                        instances.append((pool_key, variant, dx, dy))
                    self.grass_decorations[(x, y)] = instances

    def get_gated_respites(self):
        """Return Respite objects that are gated by a miniboss ID."""
        if len(self.interactables) <= 64:
            return [
                obj for obj in self.interactables
                if type(obj).__name__ == "Respite" and getattr(obj, "gated_by_miniboss_id", None)
            ]
        self._ensure_spatial_index()
        return self._gated_respites

    def has_puddle_collision(self, player_rect):
        """Return True if player_rect overlaps any Inkwell Puddle."""
        from engine.physics import check_aabb_collision
        if len(self.interactables) <= 64:
            for obj in self.interactables:
                if obj.name == "Inkwell Puddle" and check_aabb_collision(player_rect, obj.rect):
                    return True
            return False
        self._ensure_spatial_index()
        px, py, pw, ph = player_rect
        cell_size = TILE_SIZE * 4
        cx0, cy0 = int(px // cell_size), int(py // cell_size)
        cx1, cy1 = int((px + pw) // cell_size), int((py + ph) // cell_size)
        for cy in range(cy0, cy1 + 1):
            for cx in range(cx0, cx1 + 1):
                for obj in self._puddle_buckets.get((cx, cy), ()):
                    if check_aabb_collision(player_rect, obj.rect):
                        return True
        return False

    def get_nearby_walls(self, player_rect, exclude_obj=None):
        """Returns wall rectangles (grid or solid GameObjects) near the player."""
        px, py, pw, ph = player_rect
        h = len(self.grid)
        w = len(self.grid[0]) if h > 0 else 0
        start_x = max(0, int(px // TILE_SIZE))
        start_y = max(0, int(py // TILE_SIZE))
        end_x = min(w, int((px + pw) // TILE_SIZE) + 1)
        end_y = min(h, int((py + ph) // TILE_SIZE) + 1)

        walls = []
        # Grid-based walls
        for y in range(start_y, end_y):
            for x in range(start_x, end_x):
                if self.grid[y][x] == TILE_WALL:
                    walls.append((x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE))

        # Solid GameObjects
        from engine.physics import check_aabb_collision
        if len(self.interactables) <= 64:
            for obj in self.interactables:
                if obj is exclude_obj:
                    continue
                if obj.is_solid and getattr(obj, 'is_active', True) and check_aabb_collision(player_rect, obj.rect):
                    walls.append((obj.rect[0], obj.rect[1], obj.rect[2], obj.rect[3]))
            return walls

        self._ensure_spatial_index()
        cell_size = TILE_SIZE * 4
        cx0, cy0 = int(px // cell_size), int(py // cell_size)
        cx1, cy1 = int((px + pw) // cell_size), int((py + ph) // cell_size)
        seen = set()
        for cy in range(cy0, cy1 + 1):
            for cx in range(cx0, cx1 + 1):
                for obj in self._solid_buckets.get((cx, cy), ()):
                    if obj is exclude_obj:
                        continue
                    oid = id(obj)
                    if oid in seen:
                        continue
                    seen.add(oid)
                    if obj.is_solid and getattr(obj, 'is_active', True) and check_aabb_collision(player_rect, obj.rect):
                        walls.append((obj.rect[0], obj.rect[1], obj.rect[2], obj.rect[3]))

        for obj in self._dynamic_actors:
            if obj is exclude_obj:
                continue
            oid = id(obj)
            if oid in seen:
                continue
            seen.add(oid)
            if obj.is_solid and getattr(obj, 'is_active', True) and check_aabb_collision(player_rect, obj.rect):
                walls.append((obj.rect[0], obj.rect[1], obj.rect[2], obj.rect[3]))

        return walls

    def get_nearby_interactables(self, player_rect):
        """Returns interactables that overlap with an expanded player rect."""
        px, py, pw, ph = player_rect
        margin = 10
        expanded_rect = (px - margin, py - margin, pw + margin * 2, ph + margin * 2)

        from engine.physics import check_aabb_collision
        if len(self.interactables) <= 64:
            nearby = []
            for obj in self.interactables:
                if (
                    obj.is_interactive
                    and getattr(obj, 'is_active', True)
                    and check_aabb_collision(expanded_rect, obj.rect)
                ):
                    nearby.append(obj)
            return nearby

        self._ensure_spatial_index()
        cell_size = TILE_SIZE * 4
        ex, ey, ew, eh = expanded_rect
        cx0, cy0 = int(ex // cell_size), int(ey // cell_size)
        cx1, cy1 = int((ex + ew) // cell_size), int((ey + eh) // cell_size)
        nearby = []
        seen = set()
        for cy in range(cy0, cy1 + 1):
            for cx in range(cx0, cx1 + 1):
                for obj in self._interactive_buckets.get((cx, cy), ()):
                    oid = id(obj)
                    if oid in seen:
                        continue
                    seen.add(oid)
                    if (
                        obj.is_interactive
                        and getattr(obj, 'is_active', True)
                        and check_aabb_collision(expanded_rect, obj.rect)
                    ):
                        nearby.append(obj)

        for obj in self._dynamic_actors:
            oid = id(obj)
            if oid in seen:
                continue
            seen.add(oid)
            if (
                obj.is_interactive
                and getattr(obj, 'is_active', True)
                and check_aabb_collision(expanded_rect, obj.rect)
            ):
                nearby.append(obj)
        return nearby
