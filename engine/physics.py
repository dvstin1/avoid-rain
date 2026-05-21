"""
Pure math implementation of AABB collision and physics resolution.
"""

def check_aabb_collision(rect_a, rect_b):
    """
    Checks if two rectangles are overlapping.
    rect: (x, y, w, h)
    """
    ax, ay, aw, ah = rect_a
    bx, by, bw, bh = rect_b

    return (ax < bx + bw and
            ax + aw > bx and
            ay < by + bh and
            ay + ah > by)

def resolve_wall_collision(player_rect, wall_rects):
    """
    Resolves collisions between the player and a list of wall rectangles.
    Returns the adjusted (x, y) for the player.
    """
    px, py, pw, ph = player_rect

    for wall in wall_rects:
        wx, wy, ww, wh = wall

        if check_aabb_collision((px, py, pw, ph), wall):
            # Find the overlap on each axis
            overlap_x = min(px + pw, wx + ww) - max(px, wx)
            overlap_y = min(py + ph, wy + wh) - max(py, wy)

            # Resolve on the axis with the smallest overlap
            if overlap_x < overlap_y:
                if px + pw / 2 < wx + ww / 2:
                    px -= overlap_x # Move left
                else:
                    px += overlap_x # Move right
            else:
                if py + ph / 2 < wy + wh / 2:
                    py -= overlap_y # Move up
                else:
                    py += overlap_y # Move down

    return px, py
