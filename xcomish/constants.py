from __future__ import annotations

from dataclasses import dataclass

# ---- Display & Timestep ----
WIN_W, WIN_H = 1280, 720
TILE = 32
MAP_W, MAP_H = 40, 25

# Fixed-step simulation
FIXED_DT = 1.0 / 60.0
DT_CLAMP = 0.25  # clamp long frame spikes
MAX_STEPS_PER_FRAME = 5  # avoid death spirals

# Interp epsilon tied to tile size (movement precision)
EPS = 1.0 / TILE

# ---- Colors ----
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (40, 40, 45)
LIGHT_GRAY = (90, 90, 98)
GREEN = (70, 200, 120)
RED = (220, 60, 60)
BLUE = (70, 140, 240)
YELLOW = (245, 220, 80)
CYAN = (70, 230, 230)
MAGENTA = (220, 90, 180)
ORANGE = (245, 160, 50)
FOG_DARK = (0, 0, 0, 160)
FOG_BLACK = (0, 0, 0, 220)
REACHABLE = (25, 120, 200, 80)
PATH = (220, 220, 60, 140)
SELECTION = (255, 255, 255, 120)
ENEMY = (230, 90, 90)
PLAYER = (90, 230, 120)

# ---- Gameplay ----
DEFAULT_AP_MAX = 12
MOVE_SPEED_TILES_PER_SEC = 6.0
FOV_RADIUS = 10

# Instrumentation toggles (runtime-togglable)
@dataclass
class DebugFlags:
    show_fps: bool = True
    show_cache_stats: bool = True
    show_los_rays: bool = False
    show_reachable: bool = True
    show_path_preview: bool = True
    show_grid: bool = True

DEBUG = DebugFlags()

# Keybinds (pygame.K_* constants resolved at runtime)
KEY_TOGGLE_DEBUG = "F1"
