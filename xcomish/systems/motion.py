from __future__ import annotations

from collections import deque
from typing import Deque, Tuple

from ..components import AP, Motion, Position
from ..constants import EPS
from ..ecs import World
from ..grid import Grid


class MotionSystem:
    """
    Spike-resilient motion:
      - consumes multiple path segments if speed allows within fixed step
      - updates occupancy index defensively (no silent overwrite)
    """

    def __init__(self, world: World, grid: Grid) -> None:
        self.world = world
        self.grid = grid

    def update(self, dt: float) -> None:
        eids, rows = self.world.view(Position, Motion, AP)
        for eid, (pos, motion, ap) in zip(eids, rows):
            remaining = motion.speed_tps * dt  # tiles to travel this step
            # record previous pixel pos for interpolation (integer tile -> pixel)
            pos.px = pos.gx
            pos.py = pos.gy

            while remaining > 0.0 and motion.path and ap.current > 0:
                nx, ny = motion.path[0]
                dx = nx - pos.gx
                dy = ny - pos.gy
                dist = abs(dx) + abs(dy)  # Manhattan, but steps are axis-aligned
                if dist <= EPS:
                    # Arrived at cell boundary; update occupancy & AP
                    if not self._step_to(eid, pos.gx, pos.gy, nx, ny):
                        # Occupied unexpectedly: abort motion
                        motion.path.clear()
                        break
                    pos.gx, pos.gy = nx, ny
                    motion.path.popleft()
                    ap.current = max(0, ap.current - 1)
                    continue
                # "Consume" the entire segment in one go (grid steps only)
                # We only move full tiles, so just snap to next node.
                if self._step_to(eid, pos.gx, pos.gy, nx, ny):
                    pos.gx, pos.gy = nx, ny
                    motion.path.popleft()
                    ap.current = max(0, ap.current - 1)
                    remaining -= 1.0
                else:
                    motion.path.clear()
                    break

    def _step_to(self, eid: int, x0: int, y0: int, x1: int, y1: int) -> bool:
        # Defensively ensure we vacate source and occupy dest.
        self.grid.vacate(x0, y0, eid)
        if not self.grid.occupy(x1, y1, eid):
            # Re-occupy original to keep index consistent
            self.grid.occupy(x0, y0, eid)
            return False
        return True
