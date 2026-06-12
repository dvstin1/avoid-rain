"""
Respite Level-Up Menu UI components.
"""
import pygame
import constants

def draw_respite_menu(screen, font, state):
    """Draw the specialized Respite level-up menu with live data and feedback."""
    player = state.player
    sw, sh = screen.get_width(), screen.get_height()
    mx, my = 100, 100
    w, h = sw - mx * 2, sh - my * 2
    x, y = mx, my
    
    panel = pygame.Rect(x, y, w, h)
    pygame.draw.rect(screen, (10, 10, 30), panel)
    pygame.draw.rect(screen, constants.COLOR_WHITE, panel, 2)
    
    # 1. Header
    prowess = player.stats.get("attack_modifier", 0)
    fort = player.stats.get("max_hp_modifier", 0)
    
    # Calculate 1-based Levels
    prowess_lvl = 1 + (prowess // 5)
    fort_lvl = 1 + (fort // 10)
    
    # Understanding is the Global Level (Sum of upgrades)
    edif_lvl = prowess_lvl + fort_lvl - 1

    pages = 0
    if state.stats:
        pages = state.stats.data["lifetime_stats"].get("pages_collected", 0)
    
    header = font.render(f"Respite - Anchor of the First Edition (Understanding: Lvl {edif_lvl})", True, constants.COLOR_SELECTION)
    screen.blit(header, (x + 20, y + 10))
    
    stats_text = font.render(f"Torn Pages Available: {pages}", True, (200, 200, 255))
    screen.blit(stats_text, (x + 20, y + 45))
    
    y_off = 100
    spacing = 40
    
    # 2. Options
    def draw_option(idx, label, current_lvl, cost, is_available):
        nonlocal y_off
        sel_idx = getattr(state, 'respite_selection_idx', 0)
        mark_idx = getattr(state, 'respite_marked_idx', -1)
        
        is_focused = (sel_idx == idx)
        is_marked = (mark_idx == idx)
        
        # Color Rules
        if is_available:
            color = constants.COLOR_WHITE
            if is_focused:
                color = constants.COLOR_SELECTION # Focused is always selection color
        else:
            color = (80, 80, 80) # Charcoal/Grey
        
        prefix = "> " if is_focused else "  "
        mark_str = "[ MARKED ] " if is_marked else "[        ] "
        
        opt_text = f"{prefix}{mark_str}{label}: Lvl {current_lvl} (Cost: {cost})"
            
        surf = font.render(opt_text, True, color)
        screen.blit(surf, (x + 40, y + y_off))
        
        if not is_available:
            warn = font.render("[ Insufficient Pages ]", True, constants.COLOR_RED)
            screen.blit(warn, (x + 40 + surf.get_width() + 20, y + y_off))
        
        y_off += spacing

    # Calculate costs (Base + ((Level - 1) * Scale))
    prowess_cost = constants.EDIFICATION_BASE_COST + ((prowess_lvl - 1) * constants.EDIFICATION_COST_SCALE)
    fort_cost = constants.EDIFICATION_BASE_COST + ((fort_lvl - 1) * constants.EDIFICATION_COST_SCALE)

    sel_idx = getattr(state, 'respite_selection_idx', 0)

    # REST Option (Index 0)
    rest_focused = (sel_idx == 0)
    rest_color = constants.COLOR_WHITE if not player.has_rested_this_session else constants.COLOR_GREY
    if rest_focused: rest_color = constants.COLOR_SELECTION

    rest_text = f"{'> ' if rest_focused else '  '}[R] REST: Restore HP & Refill Flasks"
    if player.has_rested_this_session: rest_text += " (Already Rested)"
        
    screen.blit(font.render(rest_text, True, rest_color), (x + 40, y + y_off))
    y_off += spacing * 1.5

    if player.has_rested_this_session:
        draw_option(1, "Level Up Prowess (+5 Attack)", prowess_lvl, prowess_cost, pages >= prowess_cost)
        draw_option(2, "Level Up Fortification (+10 Max HP)", fort_lvl, fort_cost, pages >= fort_cost)
    else:
        warn_box = font.render("  [ Must Rest to Unblock Level Up ]", True, constants.COLOR_SELECTION)
        screen.blit(warn_box, (x + 40, y + y_off))
        y_off += spacing * 3

    # 4. Finalize Button (Index 4)
    y_off = h - 120
    fin_focused = (sel_idx == 4)
    mark_idx = getattr(state, 'respite_marked_idx', -1)
    fin_available = (mark_idx != -1 and player.has_rested_this_session)
    
    fin_col = constants.COLOR_GREY
    if fin_available:
        fin_col = constants.COLOR_SELECTION if fin_focused else constants.COLOR_WHITE
    elif fin_focused:
        fin_col = (150, 50, 50) # Reddish if focused but unavailable

    fin_text = f"{'> ' if fin_focused else '  '}[ FINALIZE UPGRADE ]"
    if mark_idx == -1 and player.has_rested_this_session:
        fin_text += " (No selection marked)"
        
    screen.blit(font.render(fin_text, True, fin_col), (x + 40, y + y_off))

    # 5. Close Button (Index 5)
    close_focused = (sel_idx == 5)
    close_col = constants.COLOR_SELECTION if close_focused else constants.COLOR_GREY
    close_text = f"{'> ' if close_focused else '  '}[ CLOSE MENU ]"
    screen.blit(font.render(close_text, True, close_col), (x + w - 250, y + h - 40))
