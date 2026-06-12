"""
Pure math implementation of AABB collision and physics resolution.
"""

import random

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

def resolve_enemy_player_collision(player, enemies, allow_push_enemies=True):
    """
    Implement a soft-body repulsion loop to prevent enemies from clipping directly inside the player.
    If allow_push_enemies is False (Clients), the player is pushed but the enemy is not.
    """
    player_rect = (player.x, player.y, player.width, player.height)
    
    for enemy in enemies:
        enemy_rect = enemy.get_rect()
        if check_aabb_collision(player_rect, enemy_rect):
            dx = (player.x + player.width / 2) - (enemy.x + enemy.width / 2)
            dy = (player.y + player.height / 2) - (enemy.y + enemy.height / 2)
            
            if dx == 0 and dy == 0:
                dx = random.uniform(-0.1, 0.1)
                dy = random.uniform(-0.1, 0.1)
                
            dist = (dx * dx + dy * dy) ** 0.5
            push_x = (dx / dist) * 2.0
            push_y = (dy / dist) * 2.0
            
            iterations = 0
            while check_aabb_collision(
                (player.x, player.y, player.width, player.height),
                (enemy.x, enemy.y, enemy.width, enemy.height)
            ) and iterations < 20:
                # Always push player
                player.x += push_x
                player.y += push_y
                
                # Push enemy only if authoritative
                if allow_push_enemies:
                    enemy.x -= push_x
                    enemy.y -= push_y
                
                iterations += 1
