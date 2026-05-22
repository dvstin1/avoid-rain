Title Menu behavior

Purpose:
The title screen menu adapts to presence of saved data. This keeps the UX intuitive and reduces accidental data loss.

Behavior:
- If no valid save data exists: the menu options are ["New Game", "Quit"].
  - "New Game" starts a fresh run immediately.
- If valid save data exists: the menu options are ["New Game", "Continue", "Quit"].
  - "Continue" is the default selection and resumes the saved run.
  - "New Game" will show a confirmation screen (Y/N) because it will replace the existing save data permanently. If confirmed, a fresh profile_metrics.json is created and persisted.

Implementation notes:
- TitleMenu is a low-coupled controller (engine/title_menu.py) that manages options and selection.
- main.py handles the confirmation prompt and save-file replacement logic. The confirmation screen uses Renderer.draw_loading_screen to ensure a minimum visible time.

Safety:
- New Game confirmation enforces a 2 second minimum display before accepting input to avoid accidental keypresses.
- Deleting and replacing save data is atomic via the StatisticsTracker save logic (writes to a temp file and uses os.replace).

References:
- engine/title_menu.py
- engine/game_state.py
- engine/stats.py
- rendering/renderer.py
