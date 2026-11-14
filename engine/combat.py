"""
Handles combat logic, hitboxes, and damage resolution.
"""
import math
from constants import SWORD_REACH, SWORD_ARC_RADIANS
from engine.physics import check_aabb_collision


def get_sword_hitbox(player_center, facing):
    """
    Calculates the sword attack bounding box based on player position and facing direction.
    Accurately encompasses the visual 120-degree crescent slash for both cardinal and diagonal facings.
    Returns (x, y, w, h) with integer coordinates.
    """
    cx, cy = player_center
    fx, fy = facing
    mag = math.hypot(fx, fy)
    if mag == 0:
        fx, fy = 1.0, 0.0
    else:
        fx, fy = fx / mag, fy / mag

    base_angle = math.atan2(fy, fx)
    half_angle = SWORD_ARC_RADIANS / 2.0
    reach = SWORD_REACH

    min_x = max_x = cx
    min_y = max_y = cy
    num_samples = 9
    step = (2.0 * half_angle) / (num_samples - 1)
    start_angle = base_angle - half_angle
    for i in range(num_samples):
        theta = start_angle + step * i
        px = cx + reach * math.cos(theta)
        py = cy + reach * math.sin(theta)
        if px < min_x:
            min_x = px
        elif px > max_x:
            max_x = px
        if py < min_y:
            min_y = py
        elif py > max_y:
            max_y = py

    for card_ang in (0.0, math.pi / 2.0, math.pi, -math.pi / 2.0):
        diff = (card_ang - base_angle + math.pi) % (2.0 * math.pi) - math.pi
        if abs(diff) <= half_angle:
            px = cx + reach * math.cos(card_ang)
            py = cy + reach * math.sin(card_ang)
            if px < min_x:
                min_x = px
            elif px > max_x:
                max_x = px
            if py < min_y:
                min_y = py
            elif py > max_y:
                max_y = py

    return (int(round(min_x)), int(round(min_y)), int(round(max_x - min_x)), int(round(max_y - min_y)))


def check_sword_hit(
    player_center, facing, target_rect, reach=SWORD_REACH, arc_radians=SWORD_ARC_RADIANS, hitbox=None
):
    """
    Checks if a target rectangle intersects the player's active sword attack.
    Matches the visual crescent slash arc (120-degree sweep, ~64px reach)
    and supports all cardinal and diagonal directions accurately.
    """
    cx, cy = player_center
    rx, ry, rw, rh = target_rect

    # 0. Ultra-fast reach AABB rejection before any trigonometry
    if rx > cx + reach or rx + rw < cx - reach or ry > cy + reach or ry + rh < cy - reach:
        return False

    fx, fy = facing
    mag = math.hypot(fx, fy)
    if mag == 0:
        fx, fy = 1.0, 0.0
    else:
        fx, fy = fx / mag, fy / mag

    # 1. Fast AABB rejection using attack bounding box
    if hitbox is None and reach == SWORD_REACH and arc_radians == SWORD_ARC_RADIANS:
        hitbox = get_sword_hitbox(player_center, (fx, fy))
    if hitbox is not None and not check_aabb_collision(hitbox, target_rect):
        return False

    # 2. Point-blank check: target contains or touches player center
    if rx <= cx <= rx + rw and ry <= cy <= ry + rh:
        return True

    # 3. Distance check: closest point on target rect to player center
    closest_x = max(rx, min(cx, rx + rw))
    closest_y = max(ry, min(cy, ry + rh))
    dist_sq = (closest_x - cx) ** 2 + (closest_y - cy) ** 2
    if dist_sq > reach ** 2:
        return False

    base_angle = math.atan2(fy, fx)
    # Generous half angle slightly above visual arc (~65 deg) to account for blade thickness
    half_angle = (arc_radians / 2.0) + 0.10

    # 4. Check angle of closest point
    ang_closest = math.atan2(closest_y - cy, closest_x - cx)
    diff = (ang_closest - base_angle + math.pi) % (2.0 * math.pi) - math.pi
    if abs(diff) <= half_angle:
        return True

    # 5. Check corners of target rectangle that are within reach
    corners = [(rx, ry), (rx + rw, ry), (rx, ry + rh), (rx + rw, ry + rh)]
    for kx, ky in corners:
        if (kx - cx) ** 2 + (ky - cy) ** 2 <= reach ** 2:
            ang = math.atan2(ky - cy, kx - cx)
            diff = (ang - base_angle + math.pi) % (2.0 * math.pi) - math.pi
            if abs(diff) <= half_angle:
                return True

    # 6. Check ray samples along the sweep cone intersecting the rectangle
    num_rays = 7
    for i in range(num_rays):
        ray_ang = (base_angle - half_angle) + (2.0 * half_angle) * (i / (num_rays - 1))
        cos_a = math.cos(ray_ang)
        sin_a = math.sin(ray_ang)
        for step in (0.35, 0.70, 1.0):
            sx = cx + cos_a * reach * step
            sy = cy + sin_a * reach * step
            if rx <= sx <= rx + rw and ry <= sy <= ry + rh:
                return True

    return False
