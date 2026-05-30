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
    edif = player.stats.get("edification", 0)
    pages = 0
    if state.stats:
        pages = state.stats.data["lifetime_stats"].get("pages_collected", 0)
    
    header = font.render(f"Respite - Anchor of the First Edition (Understanding: Lvl {edif})", True, constants.COLOR_YELLOW)
    screen.blit(header, (x + 20, y + 10))
    
    stats_text = font.render(f"Torn Pages Available: {pages}", True, (200, 200, 255))
    screen.blit(stats_text, (x + 20, y + 45))
    
    y_off = 100
    spacing = 40
    
    # 2. Options
    def draw_option(idx, label, current_lvl, cost, is_available):
        nonlocal y_off
        is_selected = getattr(state, 'respite_selection_idx', 0) == idx
        
        # Color Rules
        if is_available:
            color = constants.COLOR_WHITE
            if is_selected and state.input_mode == constants.INPUT_MODE_GAMEPAD:
                color = constants.COLOR_YELLOW # Highlight selected
        else:
            color = (80, 80, 80) # Charcoal/Grey
        
        opt_text = f"[{idx}] {label}: Lvl {current_lvl} (Cost: {cost})"
        # Add selection indicator for Gamepad
        if is_selected and state.input_mode == constants.INPUT_MODE_GAMEPAD:
            opt_text = "> " + opt_text
            
        surf = font.render(opt_text, True, color)
        screen.blit(surf, (x + 40, y + y_off))
        
        if not is_available:
            warn = font.render("[ Insufficient Pages ]", True, constants.COLOR_RED)
            screen.blit(warn, (x + 40 + surf.get_width() + 20, y + y_off))
        
        y_off += spacing

    # Calculate costs (matching Respite.execute_interaction logic)
    prowess = player.stats.get("attack_modifier", 0)
    fort = player.stats.get("max_hp_modifier", 0)
    
    edif_cost = constants.EDIFICATION_BASE_COST + (edif * constants.EDIFICATION_COST_SCALE)
    prowess_cost = constants.EDIFICATION_BASE_COST + (prowess // 5 * constants.EDIFICATION_COST_SCALE)
    fort_cost = constants.EDIFICATION_BASE_COST + (fort // 10 * constants.EDIFICATION_COST_SCALE)

    # REST Option (Index 0)
    is_rest_selected = getattr(state, 'respite_selection_idx', 0) == 0
    rest_color = constants.COLOR_WHITE
    if not player.has_rested_this_session:
        if is_rest_selected and state.input_mode == constants.INPUT_MODE_GAMEPAD:
            rest_color = constants.COLOR_YELLOW
    else:
        rest_color = constants.COLOR_GREY

    rest_text = "[R] REST: Restore HP & Refill Flasks"
    if player.has_rested_this_session: rest_text += " (Already Rested)"
    if is_rest_selected and state.input_mode == constants.INPUT_MODE_GAMEPAD:
        rest_text = "> " + rest_text
        
    screen.blit(font.render(rest_text, True, rest_color), (x + 40, y + y_off))
    y_off += spacing * 1.5

    if player.has_rested_this_session:
        draw_option(1, "Edify Understanding (Passive Defense)", edif, edif_cost, pages >= edif_cost)
        draw_option(2, "Edify Prowess (+5 Attack)", prowess, prowess_cost, pages >= prowess_cost)
        draw_option(3, "Edify Fortification (+10 Max HP)", fort, fort_cost, pages >= fort_cost)
    else:
        warn_box = font.render("[ Must Rest to Unblock Level Up ]", True, constants.COLOR_YELLOW)
        screen.blit(warn_box, (x + 40, y + y_off))
    
    # 3. Footer
    close = font.render("Press [SPACE] to Close", True, constants.COLOR_GREY)
    screen.blit(close, (x + w - close.get_width() - 20, y + h - 30))

