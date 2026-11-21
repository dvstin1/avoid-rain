"""
Respite Level-Up Menu UI components.
"""
import pygame
import constants

RESPITE_PANEL_WIDTH = 620
RESPITE_PANEL_HEIGHT = 290


def draw_respite_menu(screen, font, state):
    """Draw the compact, centered Respite level-up modal with live data and feedback."""
    player = state.player
    sw, sh = screen.get_width(), screen.get_height()
    w = min(RESPITE_PANEL_WIDTH, sw - 60)
    h = min(RESPITE_PANEL_HEIGHT, sh - 60)
    x = (sw - w) // 2
    y = (sh - h) // 2

    panel = pygame.Rect(x, y, w, h)
    pygame.draw.rect(screen, (14, 12, 24), panel, border_radius=6)
    pygame.draw.rect(screen, constants.COLOR_WHITE, panel, 2, border_radius=6)

    # 1. Header and staging calculations
    info = state.get_staged_respite_info()
    pages = 0
    if state.stats:
        pages = state.stats.data["lifetime_stats"].get("pages_collected", 0)
    virtual_pages = pages - info["total_staged_cost"]

    prowess = player.stats.get("attack_modifier", 0)
    fort = player.stats.get("max_hp_modifier", 0)
    prowess_lvl = 1 + (prowess // constants.PROWESS_ATTACK_STEP)
    fort_lvl = 1 + (fort // constants.FORTIFICATION_HP_STEP)

    virtual_prowess_lvl = prowess_lvl + info["staged_prowess"]
    virtual_fort_lvl = fort_lvl + info["staged_fort"]
    virtual_edif_lvl = virtual_prowess_lvl + virtual_fort_lvl - 1

    header = font.render(
        f"Respite - Anchor of the First Edition (Understanding: Lvl {virtual_edif_lvl})",
        True,
        constants.COLOR_SELECTION,
    )
    screen.blit(header, (x + 20, y + 14))

    stats_text = font.render(f"Torn Pages Available: {virtual_pages}", True, (200, 200, 255))
    screen.blit(stats_text, (x + 20, y + 42))

    y_off = 78
    spacing = 30

    def draw_option(idx, label, staged_count, current_lvl, cost, is_available):
        nonlocal y_off
        sel_idx = getattr(state, 'respite_selection_idx', 0)
        is_focused = sel_idx == idx

        if is_available:
            color = constants.COLOR_SELECTION if is_focused else constants.COLOR_WHITE
        else:
            color = (85, 85, 95)

        prefix = "> " if is_focused else "  "
        staged_str = f"[ +{staged_count} ] " if staged_count > 0 else "[    ] "
        opt_text = f"{prefix}{staged_str}{label}: Lvl {current_lvl} (Cost: {cost})"
        surf = font.render(opt_text, True, color)
        screen.blit(surf, (x + 24, y + y_off))

        if not is_available:
            warn = font.render("[Insufficient]", True, constants.COLOR_RED)
            screen.blit(warn, (x + 24 + surf.get_width() + 12, y + y_off))

        y_off += spacing

    sel_idx = getattr(state, 'respite_selection_idx', 0)

    # REST Option (Index 0)
    rest_focused = sel_idx == 0
    rest_color = constants.COLOR_WHITE if not player.has_rested_this_session else constants.COLOR_GREY
    if rest_focused:
        rest_color = constants.COLOR_SELECTION

    rest_text = f"{'> ' if rest_focused else '  '}[R] REST: Restore HP & Refill Flasks"
    if player.has_rested_this_session:
        rest_text += " (Already Rested)"

    screen.blit(font.render(rest_text, True, rest_color), (x + 24, y + y_off))
    y_off += spacing + 6

    if player.has_rested_this_session:
        draw_option(
            1,
            f"Level Up Prowess (+{constants.PROWESS_ATTACK_STEP} Attack)",
            info["staged_prowess"],
            virtual_prowess_lvl,
            info["next_prowess_cost"],
            virtual_pages >= info["next_prowess_cost"],
        )
        draw_option(
            2,
            f"Level Up Fortification (+{constants.FORTIFICATION_HP_STEP} Max HP)",
            info["staged_fort"],
            virtual_fort_lvl,
            info["next_fort_cost"],
            virtual_pages >= info["next_fort_cost"],
        )
    else:
        warn_box = font.render("  [ Must Rest to Unblock Level Up ]", True, constants.COLOR_SELECTION)
        screen.blit(warn_box, (x + 24, y + y_off))
        y_off += spacing * 2

    # 4. Finalize Button (Index 4)
    y_off = h - 94
    fin_focused = sel_idx == 4
    fin_available = info["total_staged_cost"] > 0 and player.has_rested_this_session

    fin_col = constants.COLOR_GREY
    if fin_available:
        fin_col = constants.COLOR_SELECTION if fin_focused else constants.COLOR_WHITE
    elif fin_focused:
        fin_col = (150, 50, 50)

    fin_text = f"{'> ' if fin_focused else '  '}[ FINALIZE UPGRADES ]"
    if info["total_staged_cost"] == 0 and player.has_rested_this_session:
        fin_text += " (No upgrades staged)"

    screen.blit(font.render(fin_text, True, fin_col), (x + 24, y + y_off))

    # 5. Close Button (Index 5)
    y_off += spacing - 2
    close_focused = sel_idx == 5
    close_col = constants.COLOR_SELECTION if close_focused else constants.COLOR_GREY
    close_text = f"{'> ' if close_focused else '  '}[ CLOSE MENU ]"
    screen.blit(font.render(close_text, True, close_col), (x + 24, y + y_off))

    hint = font.render(
        "[UP/DOWN] Select   [ENTER/E] Confirm   [R] Rest   [ESC] Close",
        True,
        constants.COLOR_GREY,
    )
    screen.blit(hint, (x + 20, y + h - 30))
    return panel


def draw_chronicle_biome_menu(screen, font, state):
    """Draw the 5-of-7 Unbound Chronicle biome draft modal with theme and Act saturation preview."""
    dialog = getattr(state, 'chronicle_dialog', None)
    if not dialog:
        return

    sw, sh = screen.get_width(), screen.get_height()
    mx, my = 80, 60
    w, h = sw - mx * 2, sh - my * 2
    x, y = mx, my

    panel = pygame.Rect(x, y, w, h)
    pygame.draw.rect(screen, (14, 12, 22), panel, border_radius=6)
    pygame.draw.rect(screen, constants.COLOR_WHITE, panel, 2, border_radius=6)

    step = int(dialog.get("step", 1))
    max_steps = int(dialog.get("max_steps", getattr(constants, "MAX_ACTS", 5)))
    sat = constants.get_act_saturation(step)

    title_str = f"THE UNBOUND CHRONICLE — SELECT ACT {step} OF {max_steps} FOLIO"
    title = font.render(title_str, True, constants.COLOR_SELECTION)
    screen.blit(title, (x + 25, y + 16))

    sat_surf = font.render(f"Escalation: {sat['label']}", True, (215, 180, 95))
    screen.blit(sat_surf, (x + 25, y + 46))

    choices = list(dialog.get("choices") or [None] * max_steps)
    folio_parts = []
    for idx in range(max_steps):
        pick = choices[idx] if idx < len(choices) else None
        if not pick:
            lbl = "[ ? ]"
        elif pick == "random":
            lbl = "Random"
        else:
            lbl = constants.BIOME_DISPLAY_NAMES.get(pick, pick)
        folio_parts.append(f"A{idx + 1}: {lbl}")
    strip_surf = font.render("  |  ".join(folio_parts), True, constants.COLOR_GREY)
    screen.blit(strip_surf, (x + 25, y + 76))

    y_off = 114
    options = state.get_chronicle_dialog_options()
    sel_idx = dialog.get("selection", 0)
    spacing = 34

    for idx, opt in enumerate(options):
        focused = idx == sel_idx
        enabled = opt.get("enabled", True)
        label = opt.get("label", "")
        theme = opt.get("theme", "")
        picked_act = opt.get("selected_act")
        if not enabled:
            color = (85, 85, 95)
            suffix = f" (Drafted for Act {picked_act})" if picked_act else " (Already Drafted)"
            row_str = f"{label}{suffix}"
        else:
            if focused:
                color = constants.COLOR_SELECTION
            elif opt.get("value") in ("cancel", "back"):
                color = constants.COLOR_GREY
            else:
                color = constants.COLOR_WHITE
            row_str = f"{label} — {theme}" if theme else label

        prefix = "> " if focused else "  "
        screen.blit(font.render(f"{prefix}{row_str}", True, color), (x + 35, y + y_off))
        y_off += spacing

    hint = font.render("[UP/DOWN] Navigate   [ENTER/E] Bind Folio   [ESC] Cancel/Back", True, constants.COLOR_GREY)
    screen.blit(hint, (x + 25, y + h - 38))


def _wrap_text_lines(font, text, max_width_px):
    """Word-wrap text into lines that fit within max_width_px without truncation."""
    cleaned = " ".join(str(text or "").split())
    if not cleaned:
        return []

    def _measure(sample):
        if hasattr(font, "size"):
            try:
                return font.size(sample)[0]
            except (TypeError, AttributeError):
                pass
        return len(sample) * 10

    lines = []
    current = ""
    for word in cleaned.split(" "):
        candidate = f"{current} {word}".strip() if current else word
        if not current or _measure(candidate) <= max_width_px:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def draw_binder_weave_menu(screen, font, state):
    """Render The Binder's Script Weaving Loom modal in Sanctuary."""
    dialog = getattr(state, "binder_dialog", None)
    if not dialog:
        return

    from engine.binder_scripts import (
        compile_binder_scripts,
        ensure_binder_persistence,
        format_stitch_sequence_progress,
    )

    sw, sh = screen.get_size()
    w = min(980, sw - 40)
    h = min(650, sh - 30)
    x = (sw - w) // 2
    y = (sh - h) // 2

    panel = pygame.Rect(x, y, w, h)
    pygame.draw.rect(screen, (16, 12, 22), panel, border_radius=6)
    pygame.draw.rect(screen, (218, 178, 92), panel, 2, border_radius=6)

    stats = getattr(state, "stats", None)
    binder_state, story_flags = ensure_binder_persistence(stats)
    scraps = int(stats.data.get("margin_scraps", 0)) if stats else 0
    equipped = list(binder_state.get("equipped") or [])
    comp = compile_binder_scripts(equipped)
    mods = comp["modifiers"]

    header_str = (
        f"THE BINDER'S LOOM  —  Margin Scraps: {scraps}  |  "
        f"Equipped: {len(equipped)}/{constants.BINDER_MAX_EQUIPPED_SCRIPTS}"
    )
    screen.blit(font.render(header_str, True, constants.COLOR_SELECTION), (x + 24, y + 14))

    stitch_str = format_stitch_sequence_progress(binder_state, story_flags)
    stitch_col = (120, 245, 165) if story_flags.get("perfect_stitch_completed") else (220, 185, 110)
    screen.blit(font.render(stitch_str, True, stitch_col), (x + 24, y + 42))

    frame_str = (
        f"Compiled Frame: +{int(mods['max_hp'])} HP   +{int(mods['attack'])} ATK   "
        f"+{int(mods['speed'])} SPD   +{int(round(mods['damage_mitigation'] * 100))}% MIT   "
        f"+{mods['bleed']:.1f} BLEED"
    )
    screen.blit(font.render(frame_str, True, constants.COLOR_WHITE), (x + 24, y + 68))

    status_msg = str(dialog.get("status_msg", "") or "")
    msg_col = (245, 115, 115) if "CONFLICT" in status_msg else constants.COLOR_GREY
    wrapped_status = _wrap_text_lines(font, status_msg, max(200, w - 48))
    font_h = font.get_height() if hasattr(font, "get_height") else 22
    line_step = max(20, min(26, int(font_h)))
    status_y = 90
    for line in wrapped_status:
        screen.blit(font.render(line, True, msg_col), (x + 24, y + status_y))
        status_y += line_step

    options = state.get_binder_dialog_options()
    sel_idx = int(dialog.get("selection", 0))
    y_off = max(126, status_y + 10)
    avail_h = max(120, (h - 40) - y_off)
    spacing = min(36, max(24, avail_h // max(1, len(options))))

    for idx, opt in enumerate(options):
        focused = idx == sel_idx
        act = opt.get("action")
        if act == "script":
            name = opt["name"]
            summary = opt["summary"]
            if opt["equipped"]:
                if opt["compile_status"] == "CONFLICTED":
                    badge = f"[CONFLICTED -> {opt['overridden_by_name']}]"
                    col = (245, 95, 95) if not focused else constants.COLOR_SELECTION
                else:
                    badge = "[STITCHED: ACTIVE]"
                    col = (115, 240, 155) if not focused else constants.COLOR_SELECTION
            elif opt["unlocked"]:
                badge = "[WOVEN — Press ENTER to Stitch]"
                col = constants.COLOR_WHITE if not focused else constants.COLOR_SELECTION
            else:
                cost = opt["cost"]
                badge = f"[WEAVE: {cost} Scraps]"
                can_afford = scraps >= cost
                if focused:
                    col = constants.COLOR_SELECTION
                else:
                    col = (210, 195, 145) if can_afford else (95, 90, 100)
            row_str = f"{name} ({summary}) — {badge}"
        else:
            col = constants.COLOR_SELECTION if focused else constants.COLOR_GREY
            row_str = f"{opt['name']} — {opt.get('summary', '')}"

        prefix = "> " if focused else "  "
        screen.blit(font.render(f"{prefix}{row_str}", True, col), (x + 28, y + y_off))
        y_off += spacing

    hint = font.render(
        "[UP/DOWN] Navigate   [ENTER/E] Weave / Toggle Stitch   [ESC] Close Loom",
        True,
        constants.COLOR_GREY,
    )
    screen.blit(hint, (x + 24, y + h - 34))
