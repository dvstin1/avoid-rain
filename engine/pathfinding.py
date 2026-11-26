# copyright 2026 Dustin Massop, License: GPLv2
"""
Headless A* pathfinding engine for Avoid Rain.
Computes corner-safe 8-way tile routes around static walls and solid GameObjects
(bookcases, candelabras, rocks, pillars, breakable barrels) with bounded search
horizon and cached solid-prop footprints for 60fps performance on 440x440 grids.
"""
# pylint: disable=too-many-locals,too-many-arguments,too-many-positional-arguments
# pylint: disable=too-many-branches,too-many-statements,too-many-return-statements

import heapq
import math
from typing import List, Optional, Set, Tuple

from constants import (
    PATHFINDING_MAX_NODES,
    PATHFINDING_MAX_RADIUS_TILES,
    TILE_SIZE,
    TILE_WALL,
)

# 8-way movement deltas: (dx, dy, movement_cost)
_DIAG_COST = 1.4142135623730951
_NEIGHBORS: Tuple[Tuple[int, int, float], ...] = (
    (1, 0, 1.0),
    (-1, 0, 1.0),
    (0, 1, 1.0),
    (0, -1, 1.0),
    (1, 1, _DIAG_COST),
    (1, -1, _DIAG_COST),
    (-1, 1, _DIAG_COST),
    (-1, -1, _DIAG_COST),
)


def _octile_heuristic(ax: int, ay: int, bx: int, by: int) -> float:
    """Admissible 8-way octile distance heuristic."""
    dx = abs(ax - bx)
    dy = abs(ay - by)
    return (dx + dy) + (_DIAG_COST - 2.0) * min(dx, dy)


def get_solid_obstacle_tiles(world) -> Set[Tuple[int, int]]:
    """Return cached set of grid tiles occupied by active solid GameObjects."""
    interactables = getattr(world, "interactables", None)
    if not interactables:
        return set()

    grid = getattr(world, "grid", None)
    h = len(grid) if grid else 0
    w = len(grid[0]) if h > 0 else 0
    cur_len = len(interactables)
    sig = (
        id(interactables),
        cur_len,
        id(interactables[0]),
        id(interactables[-1]),
        w,
        h,
    )
    prev_sig = getattr(world, "_nav_solid_sig", None)
    if prev_sig == sig:
        return getattr(world, "_nav_solid_tiles", set())

    # Fast incremental check when non-solid items (e.g., Inkwell Puddles) are appended
    if (
        prev_sig is not None
        and prev_sig[0] == sig[0]
        and prev_sig[2] == sig[2]
        and prev_sig[4] == w
        and prev_sig[5] == h
        and cur_len > prev_sig[1]
    ):
        prev_len = prev_sig[1]
        if not any(
            getattr(obj, "is_solid", False) and getattr(obj, "is_active", True)
            for obj in interactables[prev_len:]
        ):
            world._nav_solid_sig = sig  # pylint: disable=protected-access
            return getattr(world, "_nav_solid_tiles", set())

    blocked: Set[Tuple[int, int]] = set()
    for obj in interactables:
        if not (getattr(obj, "is_solid", False) and getattr(obj, "is_active", True)):
            continue
        # Skip mobile patrolling NPCs (Chronicler/Binder) so their spawn tile isn't baked as a permanent wall
        if hasattr(obj, "patrol_route"):
            continue
        rect = getattr(obj, "rect", None)
        if not rect or len(rect) < 4:
            continue
        ox, oy, ow, oh = rect[0], rect[1], rect[2], rect[3]
        if ow <= 0 or oh <= 0:
            continue
        # Inset by 1px so props flush with tile edges don't bleed into adjacent tiles
        tx0 = max(0, int((ox + 1.0) // TILE_SIZE))
        ty0 = max(0, int((oy + 1.0) // TILE_SIZE))
        tx1 = min(w - 1, int((ox + ow - 1.0) // TILE_SIZE))
        ty1 = min(h - 1, int((oy + oh - 1.0) // TILE_SIZE))
        for ty in range(ty0, ty1 + 1):
            for tx in range(tx0, tx1 + 1):
                blocked.add((tx, ty))

    world._nav_solid_sig = sig  # pylint: disable=protected-access
    world._nav_solid_tiles = blocked  # pylint: disable=protected-access
    return blocked


def is_tile_walkable(
    grid: List[List[int]],
    blocked_tiles: Set[Tuple[int, int]],
    tx: int,
    ty: int,
    width: int,
    height: int,
) -> bool:
    """Return True if grid cell (tx, ty) is within bounds and not blocked."""
    if tx < 0 or ty < 0 or tx >= width or ty >= height:
        return False
    if grid[ty][tx] == TILE_WALL:
        return False
    return (tx, ty) not in blocked_tiles


def _tile_line_clear(
    grid: List[List[int]],
    blocked_tiles: Set[Tuple[int, int]],
    start_tile: Tuple[int, int],
    end_tile: Tuple[int, int],
    width: int,
    height: int,
) -> bool:
    """Supercover Bresenham tile check between two grid cells."""
    x0, y0 = start_tile
    x1, y1 = end_tile
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    sx = 1 if x1 >= x0 else -1
    sy = 1 if y1 >= y0 else -1
    err = dx - dy
    cx, cy = x0, y0

    while True:
        if (cx, cy) not in (start_tile, end_tile):
            if not is_tile_walkable(grid, blocked_tiles, cx, cy, width, height):
                return False
        if cx == x1 and cy == y1:
            return True
        e2 = 2 * err
        step_x = e2 > -dy
        step_y = e2 < dx
        if step_x and step_y:
            # Corner-safe diagonal check: both orthogonal adjacents must be clear
            if not is_tile_walkable(grid, blocked_tiles, cx + sx, cy, width, height):
                return False
            if not is_tile_walkable(grid, blocked_tiles, cx, cy + sy, width, height):
                return False
            err -= dy
            err += dx
            cx += sx
            cy += sy
        elif step_x:
            err -= dy
            cx += sx
        else:
            err += dx
            cy += sy


def has_line_of_sight(world, start_px: Tuple[float, float], goal_px: Tuple[float, float]) -> bool:
    """Return True if a straight tile corridor between start_px and goal_px is unobstructed."""
    grid = getattr(world, "grid", None)
    if not grid:
        return True
    height = len(grid)
    width = len(grid[0]) if height > 0 else 0
    if width == 0:
        return True

    sx = max(0, min(width - 1, int(start_px[0] // TILE_SIZE)))
    sy = max(0, min(height - 1, int(start_px[1] // TILE_SIZE)))
    gx = max(0, min(width - 1, int(goal_px[0] // TILE_SIZE)))
    gy = max(0, min(height - 1, int(goal_px[1] // TILE_SIZE)))
    if sx == gx and sy == gy:
        return True

    blocked = get_solid_obstacle_tiles(world)
    if not is_tile_walkable(grid, blocked, gx, gy, width, height):
        return False
    return _tile_line_clear(grid, blocked, (sx, sy), (gx, gy), width, height)


def _find_nearest_walkable_tile(
    grid: List[List[int]],
    blocked: Set[Tuple[int, int]],
    target: Tuple[int, int],
    reference: Tuple[int, int],
    width: int,
    height: int,
) -> Optional[Tuple[int, int]]:
    """If target tile is blocked, snap to the nearest walkable neighbor closest to reference."""
    tx, ty = target
    if is_tile_walkable(grid, blocked, tx, ty, width, height):
        return target

    rx, ry = reference
    best: Optional[Tuple[int, int]] = None
    best_dist_sq = float("inf")
    for radius in (1, 2):
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                nx, ny = tx + dx, ty + dy
                if is_tile_walkable(grid, blocked, nx, ny, width, height):
                    d_sq = (nx - rx) ** 2 + (ny - ry) ** 2
                    if d_sq < best_dist_sq:
                        best_dist_sq = d_sq
                        best = (nx, ny)
        if best is not None:
            return best
    return None


def _smooth_tile_path(
    grid: List[List[int]],
    blocked: Set[Tuple[int, int]],
    tile_path: List[Tuple[int, int]],
    width: int,
    height: int,
) -> List[Tuple[int, int]]:
    """String-pull tile waypoints by skipping intermediate nodes with clear tile LOS."""
    if len(tile_path) <= 2:
        return tile_path
    smoothed = [tile_path[0]]
    anchor_idx = 0
    total = len(tile_path)
    while anchor_idx < total - 1:
        furthest = anchor_idx + 1
        for probe in range(total - 1, anchor_idx + 1, -1):
            if _tile_line_clear(grid, blocked, tile_path[anchor_idx], tile_path[probe], width, height):
                furthest = probe
                break
        smoothed.append(tile_path[furthest])
        anchor_idx = furthest
    return smoothed


def find_path(
    world,
    start_px: Tuple[float, float],
    goal_px: Tuple[float, float],
    max_radius: int = PATHFINDING_MAX_RADIUS_TILES,
    max_nodes: int = PATHFINDING_MAX_NODES,
) -> List[Tuple[float, float]]:
    """Compute a smoothed pixel-space waypoint list from start_px to goal_px using 8-way A*.

    Returns an empty list if no path can be found within the bounded search radius.
    """
    grid = getattr(world, "grid", None)
    if not grid:
        return [(float(goal_px[0]), float(goal_px[1]))]
    height = len(grid)
    width = len(grid[0]) if height > 0 else 0
    if width == 0:
        return [(float(goal_px[0]), float(goal_px[1]))]

    sx = max(0, min(width - 1, int(start_px[0] // TILE_SIZE)))
    sy = max(0, min(height - 1, int(start_px[1] // TILE_SIZE)))
    gx = max(0, min(width - 1, int(goal_px[0] // TILE_SIZE)))
    gy = max(0, min(height - 1, int(goal_px[1] // TILE_SIZE)))

    if sx == gx and sy == gy:
        return [(float(goal_px[0]), float(goal_px[1]))]

    if abs(gx - sx) > max_radius or abs(gy - sy) > max_radius:
        return []

    blocked = get_solid_obstacle_tiles(world)
    start_tile = _find_nearest_walkable_tile(grid, blocked, (sx, sy), (gx, gy), width, height)
    goal_tile = _find_nearest_walkable_tile(grid, blocked, (gx, gy), (sx, sy), width, height)
    if start_tile is None or goal_tile is None:
        return []
    if start_tile == goal_tile:
        return [(float(goal_px[0]), float(goal_px[1]))]

    if _tile_line_clear(grid, blocked, start_tile, goal_tile, width, height):
        return [((goal_tile[0] + 0.5) * TILE_SIZE, (goal_tile[1] + 0.5) * TILE_SIZE)]

    min_x = max(0, min(start_tile[0], goal_tile[0]) - max_radius // 2)
    max_x = min(width - 1, max(start_tile[0], goal_tile[0]) + max_radius // 2)
    min_y = max(0, min(start_tile[1], goal_tile[1]) - max_radius // 2)
    max_y = min(height - 1, max(start_tile[1], goal_tile[1]) + max_radius // 2)

    open_heap: List[Tuple[float, float, Tuple[int, int]]] = []
    start_h = _octile_heuristic(start_tile[0], start_tile[1], goal_tile[0], goal_tile[1])
    heapq.heappush(open_heap, (start_h, 0.0, start_tile))

    came_from = {}
    g_score = {start_tile: 0.0}
    closed: Set[Tuple[int, int]] = set()

    best_node = start_tile
    best_h = start_h
    expanded = 0
    found = False

    while open_heap and expanded < max_nodes:
        _, curr_g, current = heapq.heappop(open_heap)
        if current in closed:
            continue
        closed.add(current)
        expanded += 1

        if current == goal_tile:
            found = True
            best_node = current
            break

        cx, cy = current
        curr_h = _octile_heuristic(cx, cy, goal_tile[0], goal_tile[1])
        if curr_h < best_h:
            best_h = curr_h
            best_node = current

        for dx, dy, step_cost in _NEIGHBORS:
            nx, ny = cx + dx, cy + dy
            if nx < min_x or nx > max_x or ny < min_y or ny > max_y:
                continue
            neighbor = (nx, ny)
            if neighbor in closed:
                continue
            if not is_tile_walkable(grid, blocked, nx, ny, width, height):
                continue
            # Corner-safe diagonal constraint
            if dx != 0 and dy != 0:
                if not is_tile_walkable(grid, blocked, cx + dx, cy, width, height):
                    continue
                if not is_tile_walkable(grid, blocked, cx, cy + dy, width, height):
                    continue

            tentative_g = curr_g + step_cost
            if tentative_g < g_score.get(neighbor, math.inf):
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                f_score = tentative_g + _octile_heuristic(nx, ny, goal_tile[0], goal_tile[1])
                heapq.heappush(open_heap, (f_score, tentative_g, neighbor))

    if found:
        end_node = goal_tile
    elif expanded >= max_nodes and best_node != start_tile:
        # Hit search node budget on a long detour: return best-effort forward progress
        end_node = best_node
    else:
        # Open set exhausted: target is provably unreachable
        return []

    raw_tiles: List[Tuple[int, int]] = []
    node = end_node
    while node in came_from:
        raw_tiles.append(node)
        node = came_from[node]
    raw_tiles.append(start_tile)
    raw_tiles.reverse()

    smoothed = _smooth_tile_path(grid, blocked, raw_tiles, width, height)
    # Skip start_tile and convert remaining tiles to center pixel coordinates
    waypoints = [
        ((tx + 0.5) * TILE_SIZE, (ty + 0.5) * TILE_SIZE)
        for tx, ty in smoothed[1:]
    ]
    return waypoints
