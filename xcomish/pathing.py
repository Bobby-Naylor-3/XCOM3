from __future__ import annotations

from collections import deque
from typing import Deque, Dict, Iterable, List, Optional, Set, Tuple

from .grid import Grid


def reachable_flood(grid: Grid, start: Tuple[int, int], ap: int) -> Set[Tuple[int, int]]:
    """
    AP-limited reachability on 4-neighborhood.
    Uses deque (no pop(0)) and avoids per-frame structures by reusing locals.
    """
    sx, sy = start
    if not grid.in_bounds(sx, sy):
        return set()

    q: Deque[Tuple[int, int, int]] = deque()
    q.append((sx, sy, 0))
    seen: Set[Tuple[int, int]] = {(sx, sy)}
    out: Set[Tuple[int, int]] = set()

    while q:
        x, y, cost = q.popleft()
        out.add((x, y))
        if cost >= ap:
            continue
        for nx, ny in grid.neighbors4(x, y):
            if (nx, ny) in seen:
                continue
            if not grid.in_bounds(nx, ny):
                continue
            if not grid.walkable[ny][nx]:
                continue
            if (nx, ny) in grid.occupants and (nx, ny) != (sx, sy):
                continue
            seen.add((nx, ny))
            q.append((nx, ny, cost + 1))
    return out


def astar(grid: Grid, start: Tuple[int, int], goal: Tuple[int, int], max_len: int | None = None) -> List[Tuple[int, int]]:
    """
    A* with Manhattan heuristic and closed set.
    Returns path including start and goal. Empty if none.
    """
    if start == goal:
        return [start]

    sx, sy = start
    gx, gy = goal
    if not grid.in_bounds(gx, gy) or not grid.walkable[gy][gx]:
        return []

    open_set: Set[Tuple[int, int]] = {start}
    came_from: Dict[Tuple[int, int], Tuple[int, int]] = {}
    g: Dict[Tuple[int, int], int] = {start: 0}
    f: Dict[Tuple[int, int], int] = {start: abs(gx - sx) + abs(gy - sy)}

    while open_set:
        current = min(open_set, key=lambda p: f.get(p, 10_000_000))
        if current == goal:
            # Reconstruct
            path = [current]
            while current in came_from:
                current = came_from[current]
                path.append(current)
            path.reverse()
            if max_len is not None and len(path) > max_len:
                path = path[:max_len]
            return path

        open_set.remove(current)
        for nx, ny in grid.neighbors4(*current):
            if not grid.in_bounds(nx, ny) or not grid.walkable[ny][nx]:
                continue
            if (nx, ny) in grid.occupants and (nx, ny) != start and (nx, ny) != goal:
                continue
            tentative = g[current] + 1
            if tentative < g.get((nx, ny), 1_000_000):
                came_from[(nx, ny)] = current
                g[(nx, ny)] = tentative
                f[(nx, ny)] = tentative + abs(gx - nx) + abs(gy - ny)
                if (nx, ny) not in open_set:
                    open_set.add((nx, ny))
    return []
