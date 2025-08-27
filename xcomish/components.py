from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Deque, List, Optional, Tuple


# ---- Core spatial components ----
@dataclass
class Position:
    gx: int
    gy: int
    # Render interpolation (previous fractional pixel position)
    px: float = 0.0
    py: float = 0.0


@dataclass
class Motion:
    """Path-based motion in grid cells (gx, gy)."""
    path: Deque[Tuple[int, int]] = field(default_factory=deque)
    # Tiles per second. Using per-entity speed lets us play with dashing later.
    speed_tps: float = 6.0


@dataclass
class Renderable:
    radius_px: int = 12
    color: Tuple[int, int, int] = (255, 255, 255)


# ---- Gameplay ----
@dataclass
class AP:
    current: int
    maximum: int


@dataclass
class Faction:
    name: str  # 'player' or 'enemy'


@dataclass
class Solid:
    """Blocks movement (occupancy)."""
    pass


@dataclass
class Opaque:
    """Blocks line of sight (LoS)."""
    pass


@dataclass
class Selected:
    pass


@dataclass
class PathPlan:
    """Transient UI: preview path + target; not authoritative motion."""
    target: Tuple[int, int] | None = None
    path: List[Tuple[int, int]] = field(default_factory=list)


@dataclass
class Patrol:
    """Tiny enemy patrol AI: looped waypoints."""
    waypoints: List[Tuple[int, int]] = field(default_factory=list)
    idx: int = 0
