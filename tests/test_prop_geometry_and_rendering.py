"""Unit tests for prop collision-vs-visual geometry alignment and dynamic NPC spatial indexing."""
# pylint: disable=no-member,protected-access
from types import SimpleNamespace
import pygame

import constants
from engine.player import Player
from engine.world import Chronicler, GameObject, LevelLoader, LoreFragment, World
from generate_maps import SYMBOL_BOOKCASE, SYMBOL_FLOOR, generate_architectural_biome
from rendering.renderer import Renderer
from tools.edit_map import MASTER_TOOL_REGISTRY


class _SpySurface(pygame.Surface):
    """Real pygame.Surface recording blit source surfaces and positions."""

    def __init__(self, size):
        super().__init__(size)
        self.blits = []

    def blit(self, source, dest, area=None, special_flags=0):
        """Record blit call before delegating to pygame.Surface.blit."""
        self.blits.append((source, dest))
        return super().blit(source, dest, area, special_flags)

    def clear_blits(self):
        """Reset recorded blit list."""
        self.blits.clear()


def _make_render_state(world, world_name="sanctuary"):
    """Build a minimal GameState-like object for headless Renderer.render() calls."""
    world.name = world_name
    world.map_filename = f"{world_name}.json"
    player = Player(0.0, 0.0)
    camera = SimpleNamespace(
        screen_w=320,
        screen_h=240,
        world_w=320,
        world_h=240,
        get_offset=lambda: (0, 0),
    )
    return SimpleNamespace(
        world=world,
        player=player,
        camera=camera,
        enemies=[],
        loot=[],
        world_debris=[],
        fading_entities=[],
        damage_numbers=[],
        parry_effects=[],
        slash_effects=[],
        impact_sparks=[],
        glyph_particles=None,
        network_manager=SimpleNamespace(remote_players={}),
        stats=None,
        debug_text_enabled=False,
        in_sanctuary=(world_name == "sanctuary"),
    )


def test_bench_40x40_collision_and_editor_parity(monkeypatch):
    """Verify Bench ('S') is 40x40 in LevelLoader, map editor registry, PNG cache, and fallback draw."""
    pygame.init()
    proto = ["#####", "#...#", "#.S.#", "#...#", "#####"]
    bench = next(obj for obj in LevelLoader.parse_map(proto)[1] if obj.name == "Bench")
    ts = constants.TILE_SIZE
    assert (bench.width, bench.height) == (ts, ts)
    assert bench.rect == (80.0, 80.0, float(ts), float(ts))
    assert bench.is_solid is True
    assert "40x40" in next(t for t in MASTER_TOOL_REGISTRY if t["char"] == "S")["size"]

    screen = pygame.Surface((320, 240))
    renderer = Renderer(screen)
    assert renderer.prop_cache["Bench"].get_size() == (ts, ts)

    world = World("sanctuary")
    world.load_from_prototype(proto)
    renderer.prop_cache.pop("Bench", None)
    rect_calls = []
    orig_rect = pygame.draw.rect

    def _spy_rect(surf, color, rect, *args, **kwargs):
        if surf is screen:
            rect_calls.append((color, tuple(rect)))
        return orig_rect(surf, color, rect, *args, **kwargs)

    monkeypatch.setattr(pygame.draw, "rect", _spy_rect)
    renderer.render(_make_render_state(world))
    assert ((101, 67, 33), (80.0, 80.0, ts, ts)) in rect_calls


def test_lore_fragment_rendered_centered_in_rect(monkeypatch):
    """Verify LoreFragment ('L') renders visible parchment geometry centered inside its 40x40 rect."""
    pygame.init()
    screen = pygame.Surface((320, 240))
    renderer = Renderer(screen)

    world = World("sanctuary")
    world.grid = [[constants.TILE_EMPTY] * 8 for _ in range(6)]
    lore = LoreFragment((80, 120), (constants.TILE_SIZE, constants.TILE_SIZE), "chronicler_nature", name="Faded Note")
    world.interactables = [lore]

    drawn_rects, drawn_circles = [], []
    orig_rect, orig_circle = pygame.draw.rect, pygame.draw.circle

    def _spy_rect(surf, color, rect, *args, **kwargs):
        if surf is screen:
            drawn_rects.append((color, tuple(rect)))
        return orig_rect(surf, color, rect, *args, **kwargs)

    def _spy_circle(surf, color, center, radius, *args, **kwargs):
        if surf is screen:
            drawn_circles.append((color, tuple(center), radius))
        return orig_circle(surf, color, center, radius, *args, **kwargs)

    monkeypatch.setattr(pygame.draw, "rect", _spy_rect)
    monkeypatch.setattr(pygame.draw, "circle", _spy_circle)

    renderer.render(_make_render_state(world))

    parchment_rects = [r for col, r in drawn_rects if col == (235, 224, 194)]
    assert parchment_rects == [(89, 127, 22, 26)]
    assert any(col == (215, 180, 95) and center == (100, 140) for col, center, _rad in drawn_circles)


def test_rock_non_solid_visual_alignment_and_no_tall_pillars():
    """Verify Rock ('K') stays non-solid, omits tall pillar sprites, and renders with zero jitter."""
    pygame.init()
    assert "non-solid" in next(t for t in MASTER_TOOL_REGISTRY if t["char"] == "K")["desc"].lower()

    proto = ["#####", "#K.T#", "#...#", "#####"]
    parsed = LevelLoader.parse_map(proto)[1]
    rock = next(o for o in parsed if o.name == "Rock")
    struct = next(o for o in parsed if o.name == "Structure")
    assert rock.is_solid is False
    assert struct.is_solid is True

    screen = _SpySurface((320, 240))
    renderer = Renderer(screen)
    rock_pos = (int(rock.x), int(rock.y))
    struct_pos = (int(struct.x), int(struct.y))

    for biome_name, tall_key in (
        ("vitreous_basin", "VitreousSaltSpire"),
        ("sunlit_aqueducts", "AqueductPillar"),
    ):
        world = World(biome_name)
        world.load_from_prototype(proto)
        screen.clear_blits()
        renderer.render(_make_render_state(world, world_name=biome_name))

        tall_surf = renderer.prop_cache[tall_key]
        assert (renderer.prop_cache["Rock"], rock_pos) in screen.blits
        assert not any(src is tall_surf and dest == rock_pos for src, dest in screen.blits)
        assert (tall_surf, struct_pos) in screen.blits


def test_candelabra_glow_centered_and_chronicler_dynamic_spatial_lookup():
    """Verify CandelabraGlow centers via surface dimensions and mobile Chronicler stays trackable >64 items."""
    pygame.init()
    screen = _SpySurface((320, 240))
    renderer = Renderer(screen)

    world = World("sanctuary")
    world.grid = [[constants.TILE_EMPTY] * 8 for _ in range(6)]
    cand = GameObject((80, 80), (constants.TILE_SIZE, constants.TILE_SIZE))
    cand.is_solid = True
    cand.name = "Candelabra"
    world.interactables = [cand]
    renderer.render(_make_render_state(world))

    # Flickering candelabra glow surface must be centered via its own dimensions on (x + 20, y + 5)
    glow_blits = [
        (src, dest)
        for src, dest in screen.blits
        if src.get_width() == src.get_height() and src.get_width() >= 32 and dest != (80, 80)
    ]
    assert glow_blits, f"Expected a centered Candelabra glow blit in {screen.blits}"
    glow_src, glow_dest = glow_blits[0]
    expected_glow_pos = (
        80 + constants.TILE_SIZE // 2 - glow_src.get_width() // 2,
        80 + 5 - glow_src.get_height() // 2,
    )
    assert glow_dest == expected_glow_pos

    # Mobile Chronicler spatial lookup when len(interactables) > 64
    big_world = World("sanctuary")
    big_world.grid = [[constants.TILE_EMPTY] * 25 for _ in range(25)]
    for i in range(70):
        filler = GameObject((800 + (i % 5) * 40, 800 + (i // 5) * 40), (40, 40))
        filler.is_solid = True
        filler.name = "Barrel"
        big_world.interactables.append(filler)

    chron = Chronicler((40, 40), (40, 40))
    big_world.interactables.append(chron)

    old_probe, new_probe = (40, 40, 32, 32), (600, 600, 32, 32)
    assert (40.0, 40.0, 40.0, 40.0) in big_world.get_nearby_walls(old_probe)
    assert chron in big_world.get_nearby_interactables(old_probe)
    assert chron not in big_world.get_nearby_interactables(new_probe)

    chron.x, chron.y = 600.0, 600.0
    assert (40.0, 40.0, 40.0, 40.0) not in big_world.get_nearby_walls(old_probe)
    assert chron not in big_world.get_nearby_interactables(old_probe)
    assert (600.0, 600.0, 40.0, 40.0) in big_world.get_nearby_walls(new_probe)
    assert chron in big_world.get_nearby_interactables(new_probe)


def test_heavy_bookcase_generator_never_overlaps_right_neighbor():
    """Verify architectural map generator always reserves (x+1, y) as open floor for 2x1 bookcases."""
    for seed in (101, 202, 303, 404):
        gmap = generate_architectural_biome(width=40, height=40, biome="tech_tower", seed=seed)
        for row in gmap.grid:
            for x, ch in enumerate(row):
                if ch == SYMBOL_BOOKCASE:
                    assert x + 1 < len(row) - 1
                    assert row[x + 1] == SYMBOL_FLOOR
