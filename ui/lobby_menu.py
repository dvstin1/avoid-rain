import pygame
import constants

def draw_lobby_menu(screen, font, state):
    """Draw the LAN Lobby menu showing found hosts."""
    sw, sh = screen.get_width(), screen.get_height()
    mx, my = 150, 100
    w, h = sw - mx * 2, sh - my * 2
    x, y = mx, my
    
    panel = pygame.Rect(x, y, w, h)
    # Background: dark ink blue
    pygame.draw.rect(screen, (15, 15, 25), panel)
    pygame.draw.rect(screen, constants.COLOR_WHITE, panel, 2)
    
    header = font.render("LOCAL NETWORK LOBBY", True, constants.COLOR_SELECTION)
    screen.blit(header, (x + 20, y + 20))
    
    # List found hosts
    found_hosts = state.network_manager.found_hosts
    y_off = 80
    
    if not found_hosts:
        msg = font.render("Searching for hosts on LAN...", True, (150, 150, 150))
        screen.blit(msg, (x + 40, y + y_off))
    else:
        sel_idx = getattr(state, 'lobby_selection_idx', 0)
        hosts_list = list(found_hosts.items())
        
        # Clamping selection
        if sel_idx >= len(hosts_list):
            state.lobby_selection_idx = max(0, len(hosts_list) - 1)
            sel_idx = state.lobby_selection_idx

        for i, (addr, identity) in enumerate(hosts_list):
            is_focused = (i == sel_idx)
            color = constants.COLOR_SELECTION if is_focused else constants.COLOR_WHITE
            prefix = "> " if is_focused else "  "
            
            host_text = font.render(f"{prefix}{identity} ({addr})", True, color)
            screen.blit(host_text, (x + 40, y + y_off))
            y_off += 40

    # Instructions
    instr = font.render("[SPACE] Connect    [ESC] Back", True, constants.COLOR_GREY)
    screen.blit(instr, (x + 20, y + h - 40))
