# Unit Testing Standards & Bulletproof Crash Prevention

This document details our strict requirements for regression prevention, test execution isolation, and target module mocking.

## 1. Absolute Headless Execution (Pygame Isolation)
To guarantee unit tests can run seamlessly under any local terminal environment or CI pipeline without throwing visual rendering crashes, live hardware screens are strictly banned in test scripts:
- **Environment Mocking:** All testing configurations must initialize a dummy headless audio/video driver before processing Pygame blocks:
```python
  import os
  os.environ["SDL_VIDEODRIVER"] = "dummy"
  os.environ["SDL_AUDIODRIVER"] = "dummy"
  import pygame
  pygame.init()
```

Surface Interception: Any unit test verifying structural updates must mock out actual blitting operations (screen.blit) to isolate functional variables from graphic pipeline exceptions.

2. Robust Mocking Protocols for Complex State

Tests must never require real world map file reads or live loop tracking to evaluate unit mutations.

    Weapon & Enemy States: Use unittest.mock.MagicMock or pytest fixtures to mock out complex composite objects.

    Pure Logic Focus: Isolate and test math vectors, swap logic steps, state changes, and damage arrays independently of the global game loop ticker.
