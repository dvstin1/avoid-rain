# Testing & Reliability Standards

This document outlines the protocols for ensuring the stability and correctness of the *Avoid Rain* engine.

## 1. Unit Testing Philosophy
We utilize `pytest` for all logic verification. Tests should be:
- **Fast:** Avoid heavy disk I/O or complex initialization.
- **Isolated:** Use mocks for Pygame and filesystem components.
- **Atomic:** Each test should verify exactly one behavior.

## 2. Headless Execution Protocol
To ensure tests can run in environments without a graphical display (CI/CD, remote servers), all tests must initialize Pygame with dummy drivers.

### Standard Test Header:
```python
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
import pygame
pygame.init()
```

## 3. Directory Structure
- `tests/`: Contains all `.py` test files (`136` test modules covering `550+` unit and regression tests, including `tests/test_copyright_headers.py` enforcing GPLv2 headers across tracked `*.py` files).
- `tests/repro_...`: Specialized scripts for reproducing specific reported bugs.
- **Hermetic Disk Isolation:** Tests that touch `save_data.json`, generated assets, or `.desktop` launchers must use pytest's `tmp_path` fixture rather than writing to the live workspace or system paths.

## 4. Mocking & Isolation
- **`unittest.mock`**: Used to intercept calls to `Renderer`, `AudioManager`, or the filesystem.
- **`GameState` Injection**: Most engine components should be tested by injecting a fresh `GameState` object rather than relying on the global singleton.

## 5. Continuous Quality (Linting)
We enforce strict style guidelines via `pylint`.
- **Target Score:** 8.0/10.0 or higher.
- **Line Length:** 120 characters maximum.
- **Command:** `pylint --max-line-length=120 engine/ rendering/ main.py`

## 6. Regression Testing
Whenever a bug is fixed, a corresponding test case must be added to the suite to prevent it from re-emerging. See `tests/repro_warp_failure.py` for an example of a targeted regression test.
