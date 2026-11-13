"""Unit tests for Punctuation Wolf enemy AI, Act 2 scaling, assets, rendering, and editor parity."""
import pygame
import constants
import generate_assets
from engine.actor import ActorState
from engine.enemy import PunctuationWolfEnemy, SYMBOL_REGISTRY
from engine.game_state import GameState
from rendering.renderer import Renderer
from tools.edit_map import MASTER_TOOL_REGISTRY


def test_punctuation_wolf_symbol_and_editor_parity():
    """Verify 'w' is registered in TILE_KEY, SYMBOL_REGISTRY, and MASTER_TOOL_REGISTRY."""
    assert constants.TILE_KEY.get("w") == 110
    assert SYMBOL_REGISTRY.get("w") is PunctuationWolfEnemy
    editor_chars = {entry.get("char"): entry for entry in MASTER_TOOL_REGISTRY if "char" in entry}
    assert "w" in editor_chars
    assert editor_chars["w"]["name"] == "Punctuation Wolf"
    assert editor_chars["w"]["type"] == "enemy"


def test_punctuation_wolf_ai_telegraph_pounce_and_sfx():
    """Verify PunctuationWolfEnemy stalks, telegraphs, pounces, and emits SFX."""
    state = GameState(auto_load=False)
    state.world.load_from_prototype(["............"])
    state.player.x = 200.0
    state.player.y = 40.0

    played_sfx = []

    class DummyAudio:
        """Mock audio manager capturing SFX calls."""
        def calculate_spatial_volume(self, _dist):
            """Return full volume."""
            return 1.0

        def play_sfx(self, name, **_kwargs):
            """Record SFX name."""
            played_sfx.append(name)

    state.audio_manager = DummyAudio()
    state.network_manager.network_mode = "HOST"

    wolf = PunctuationWolfEnemy(60.0, 40.0)
    packmate = PunctuationWolfEnemy(80.0, 60.0)
    state.enemies = [wolf, packmate]

    # 1. Outside pounce range (240px away, inside 400px detect_radius) -> stalks with pack flank
    state.player.x = 300.0
    state.player.y = 40.0
    wolf.state = ActorState.CHASE
    start_x = wolf.x
    wolf.update(0.1, state)
    assert wolf.x > start_x
    assert wolf.state == ActorState.CHASE

    # 2. Within pounce range -> enters WIND_UP and plays wolf_telegraph.ogg
    state.player.x = wolf.x + 100.0
    wolf.cooldown_timer = 0.0
    wolf.update(0.05, state)
    assert wolf.state == ActorState.WIND_UP
    assert "wolf_telegraph.ogg" in played_sfx
    assert any(s[0] == "wolf_telegraph.ogg" for s in state.pending_remote_sfx)

    # 3. Complete wind-up -> transitions to STRIKE, plays wolf_attack.ogg, and lunges
    wolf.update(wolf.wind_up_duration + 0.05, state)
    assert wolf.state == ActorState.STRIKE
    assert "wolf_attack.ogg" in played_sfx
    assert any(s[0] == "wolf_attack.ogg" for s in state.pending_remote_sfx)
    lunge_x = wolf.x
    wolf.update(0.05, state)
    assert wolf.x > lunge_x


def test_punctuation_wolf_act2_scaling():
    """Verify Act 2 escalation scales PunctuationWolfEnemy HP, damage, and empowered flag."""
    wolf = PunctuationWolfEnemy(40.0, 40.0)
    base_hp = wolf.max_hp
    base_dmg = wolf.damage
    wolf.apply_act_scaling(constants.ACT2_HP_MULTIPLIER, constants.ACT2_DAMAGE_MULTIPLIER)
    assert wolf.is_empowered is True
    assert wolf.max_hp == base_hp * constants.ACT2_HP_MULTIPLIER
    assert wolf.hp == base_hp * constants.ACT2_HP_MULTIPLIER
    assert wolf.damage == base_dmg * constants.ACT2_DAMAGE_MULTIPLIER


def test_punctuation_wolf_assets_and_rendering():
    """Verify generate_punctuation_wolf_empowered and Renderer Act 1/Act 2 wolf rendering."""
    pygame.init()
    emp = generate_assets.generate_punctuation_wolf_empowered(40, 40)
    assert emp.get_size() == (40, 40)
    assert emp.get_flags() & pygame.SRCALPHA != 0
    non_empty = sum(1 for x in range(40) for y in range(40) if emp.get_at((x, y)).a > 0)
    assert non_empty > 100

    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)
    assert "punctuation_wolf_empowered.png" in renderer.image_cache

    wolf = PunctuationWolfEnemy(80.0, 80.0)
    draw_rect = pygame.Rect(80, 80, 36, 36)
    assert renderer.draw_procedural_enemy(wolf, draw_rect, wolf.get_visual_packet(), constants.COLOR_WHITE) is True
    act1_bytes = pygame.image.tobytes(screen.subsurface((70, 70, 56, 56)), "RGB")

    screen.fill((0, 0, 0))
    wolf.apply_act_scaling(constants.ACT2_HP_MULTIPLIER, constants.ACT2_DAMAGE_MULTIPLIER)
    assert renderer.draw_procedural_enemy(wolf, draw_rect, wolf.get_visual_packet(), constants.COLOR_WHITE) is True
    act2_bytes = pygame.image.tobytes(screen.subsurface((70, 70, 56, 56)), "RGB")

    assert act1_bytes != act2_bytes
