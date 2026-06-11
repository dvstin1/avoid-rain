import pygame
import constants

def draw_lobby_menu(screen, font, state):
    """Draw the LAN Lobby menu showing found hosts and player identity."""
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
    
    # Player Identity Section
    identity = state.network_manager.identity
    is_editing = getattr(state, 'lobby_editing_name', False)
    
    id_color = constants.COLOR_CYAN if not is_editing else constants.COLOR_SELECTION
    id_prefix = "Identity: " if not is_editing else "Editing Name: "
    id_text = font.render(f"{id_prefix}{identity}", True, id_color)
    screen.blit(id_text, (x + 20, y + 60))
    
    if is_editing:
        cursor_flash = "_" if (pygame.time.get_ticks() // 500) % 2 == 0 else ""
        cursor_surf = font.render(cursor_flash, True, constants.COLOR_SELECTION)
        screen.blit(cursor_surf, (x + 20 + id_text.get_width(), y + 60))

    pygame.draw.line(screen, (50, 50, 80), (x + 20, y + 95), (x + w - 20, y + 95), 1)

    # List found hosts
    found_hosts = state.network_manager.found_hosts
    y_off = 110
    
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
    instr = font.render("[SPACE] Connect    [N] Change Name    [ESC] Back", True, constants.COLOR_GREY)
    screen.blit(instr, (x + 20, y + h - 40))
