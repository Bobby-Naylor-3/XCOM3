from __future__ import annotations

from collections import deque
from typing import Deque, List, Tuple

from ..components import AP, Motion, Patrol, Position
from ..ecs import World
from ..grid import Grid
from ..pathing import astar


class PatrolAI:
    """
    Tiny patrol AI: walks between waypoints, looping. Consumes AP like the player.
    """

    def __init__(self, world: World, grid: Grid) -> None:
        self.world = world
        self.grid = grid

    def update(self) -> None:
        eids, rows = self.world.view(Position, AP, Patrol)
        for eid, (pos, ap, pat) in zip(eids, rows):
            if ap.current <= 0 or not pat.waypoints:
                continue
            target = pat.waypoints[pat.idx % len(pat.waypoints)]
            if (pos.gx, pos.gy) == target:
                pat.idx = (pat.idx + 1) % len(pat.waypoints)
                target = pat.waypoints[pat.idx]

            path = astar(self.grid, (pos.gx, pos.gy), target, max_len=ap.current + 1)
            if len(path) <= 1:
                continue

            motion = self.world.get(eid, Motion)
            if not motion:
                motion = Motion()
                self.world.add(eid, motion)
            motion.path.clear()
            for step in path[1:]:
                motion.path.append(step)
            # Only schedule once per tick; MotionSystem consumes AP.
