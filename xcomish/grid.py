from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, Iterator, List, Optional, Set, Tuple

import pygame

from .constants import (
    BLUE,
    FOG_BLACK,
    FOG_DARK,
    GRAY,
    LIGHT_GRAY,
    MAP_H,
    MAP_W,
    TILE,
)
from .components import Opaque, Solid


@dataclass
class Camera:
    x: int = 0  # pixels
    y: int = 0  # pixels
    w: int = 1280
    h: int = 720

    def clamp_to_map(self, map_px_w: int, map_px_h: int) -> None:
        self.x = max(0, min(self.x, max(0, map_px_w - self.w)))
        self.y = max(0, min(self.y, max(0, map_px_h - self.h)))

    def world_to_screen(self, wx: int, wy: int) -> Tuple[int, int]:
        return wx - self.x, wy - self.y

    def screen_to_grid(self, sx: int, sy: int) -> Tuple[int, int]:
        gx = (sx + self.x) // TILE
        gy = (sy + self.y) // TILE
        return int(gx), int(gy)


@dataclass
class Grid:
    w: int = MAP_W
    h: int = MAP_H
    walkable: List[List[bool]] = field(default_factory=list)
    opaque: List[List[bool]] = field(default_factory=list)
    occupants: Dict[Tuple[int, int], int] = field(default_factory=dict)  # (x,y)->entity

    # prerendered
    terrain_surf: Optional[pygame.Surface] = None
    gridlines_surf: Optional[pygame.Surface] = None
    fog_full: Optional[pygame.Surface] = None
    fog_dim: Optional[pygame.Surface] = None

    # fog state
    visible: Set[Tuple[int, int]] = field(default_factory=set)
    explored: Set[Tuple[int, int]] = field(default_factory=set)

    def __post_init__(self) -> None:
        if not self.walkable:
            self.walkable = [[True for _ in range(self.w)] for _ in range(self.h)]
        if not self.opaque:
            self.opaque = [[False for _ in range(self.w)] for _ in range(self.h)]

    # --- Terrain ops ---
    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.w and 0 <= y < self.h

    def is_walkable(self, x: int, y: int) -> bool:
        return self.in_bounds(x, y) and self.walkable[y][x] and (x, y) not in self.occupants

    def is_blocked(self, x: int, y: int) -> bool:
        return not self.in_bounds(x, y) or not self.walkable[y][x]

    def is_opaque(self, x: int, y: int) -> bool:
        return not self.in_bounds(x, y) or self.opaque[y][x]

    def neighbors4(self, x: int, y: int) -> Iterator[Tuple[int, int]]:
        if x > 0:
            yield (x - 1, y)
        if x < self.w - 1:
            yield (x + 1, y)
        if y > 0:
            yield (x, y - 1)
        if y < self.h - 1:
            yield (x, y + 1)

    # --- Occupancy (O(1)) ---
    def occupy(self, x: int, y: int, entity: int) -> bool:
        """Returns True if success; never silently overwrite."""
        key = (x, y)
        if key in self.occupants and self.occupants[key] != entity:
            return False
        self.occupants[key] = entity
        return True

    def vacate(self, x: int, y: int, entity: int) -> None:
        if self.occupants.get((x, y)) == entity:
            del self.occupants[(x, y)]

    # --- LoS ---
    def bresenham(self, x0: int, y0: int, x1: int, y1: int) -> Iterator[Tuple[int, int]]:
        """Yield grid cells along the line from (x0,y0) to (x1,y1)."""
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        x, y = x0, y0
        while True:
            yield x, y
            if x == x1 and y == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x += sx
            if e2 <= dx:
                err += dx
                y += sy

    def has_los(self, x0: int, y0: int, x1: int, y1: int) -> bool:
        """True if opaque tiles don't block between endpoints (endpoints allowed)."""
        for (x, y) in self.bresenham(x0, y0, x1, y1):
            if (x, y) == (x0, y0) or (x, y) == (x1, y1):
                continue
            if self.is_opaque(x, y):
                return False
        return True

    # --- Fog-of-war ---
    def clear_fog(self) -> None:
        self.visible.clear()

    def reveal_from(self, x0: int, y0: int, radius: int) -> None:
        """Naive FOV using Bresenham LoS; good enough for the slice."""
        self.visible.clear()
        r2 = radius * radius
        for y in range(max(0, y0 - radius), min(self.h, y0 + radius + 1)):
            for x in range(max(0, x0 - radius), min(self.w, x0 + radius + 1)):
                dx, dy = x - x0, y - y0
                if dx * dx + dy * dy <= r2 and self.has_los(x0, y0, x, y):
                    self.visible.add((x, y))
                    self.explored.add((x, y))

    # --- Rendering cache ---
    def ensure_surfaces(self, w_px: int, h_px: int) -> None:
        if self.terrain_surf is None:
            self.terrain_surf = pygame.Surface((w_px, h_px))
            self.terrain_surf.fill(GRAY)
            # Draw "terrain blobs"
            for y in range(self.h):
                for x in range(self.w):
                    rect = pygame.Rect(x * TILE, y * TILE, TILE, TILE)
                    color = GRAY if ((x + y) % 2 == 0) else LIGHT_GRAY
                    pygame.draw.rect(self.terrain_surf, color, rect)

        if self.gridlines_surf is None:
            self.gridlines_surf = pygame.Surface((w_px, h_px), pygame.SRCALPHA)
            for x in range(self.w + 1):
                pygame.draw.line(
                    self.gridlines_surf, (0, 0, 0, 40), (x * TILE, 0), (x * TILE, h_px)
                )
            for y in range(self.h + 1):
                pygame.draw.line(
                    self.gridlines_surf, (0, 0, 0, 40), (0, y * TILE), (w_px, y * TILE)
                )

        if self.fog_full is None:
            self.fog_full = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
            self.fog_full.fill(FOG_BLACK)
        if self.fog_dim is None:
            self.fog_dim = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
            self.fog_dim.fill(FOG_DARK)

    # --- Utilities ---
    def map_pixel_size(self) -> Tuple[int, int]:
        return self.w * TILE, self.h * TILE
