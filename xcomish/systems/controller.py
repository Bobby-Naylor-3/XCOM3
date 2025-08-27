from __future__ import annotations

from typing import Optional, Tuple, List

from ..components import AP, Faction, Motion, PathPlan, Position, Selected
from ..constants import DEFAULT_AP_MAX, FOV_RADIUS
from ..ecs import World
from ..events import HoverTileChanged, MoveCommand, SelectEntity
from ..grid import Grid
from ..pathing import astar, reachable_flood


class ControllerSystem:
    """
    Player selection, AP tracking, reachability, and path preview.
    """

    def __init__(self, world: World, grid: Grid, bus) -> None:
        self.world = world
        self.grid = grid
        self.bus = bus
        # subscriptions
        bus.subscribe(SelectEntity, self._on_select, once=False)
        bus.subscribe(HoverTileChanged, self._on_hover, once=False)
        bus.subscribe(MoveCommand, self._on_move, once=False)

        self._reachable: set[tuple[int, int]] = set()

    # --- Events ---
    def _on_select(self, ev: SelectEntity) -> None:
        # clear previous selection
        eids, _ = self.world.view(Selected)
        for eid in eids:
            self.world.remove(eid, Selected)

        # select only player entities
        fac = self.world.get(ev.entity, Faction)
        if not fac or fac.name != "player":
            return

        self.world.add(ev.entity, Selected())

        # ensure AP exists
        ap = self.world.get(ev.entity, AP)
        if not ap:
            self.world.add(ev.entity, AP(DEFAULT_AP_MAX, DEFAULT_AP_MAX))

        # set FOV from selected entity
        pos = self.world.get(ev.entity, Position)
        if pos:
            self.grid.reveal_from(pos.gx, pos.gy, FOV_RADIUS)

        # compute reachable flood
        ap = self.world.get(ev.entity, AP)
        if ap and pos:
            self._reachable = reachable_flood(self.grid, (pos.gx, pos.gy), ap.current)

        # attach a PathPlan for preview state
        if not self.world.get(ev.entity, PathPlan):
            self.world.add(ev.entity, PathPlan())

    def _on_hover(self, ev: HoverTileChanged) -> None:
        # Preview path for selected entity
        eids, rows = self.world.view(Selected, Position, AP, PathPlan)
        if not eids:
            return
        eid = eids[0]
        _, pos, ap, plan = rows[0]
        if (ev.x, ev.y) not in self._reachable:
            plan.path = []
            plan.target = None
            return

        path = astar(self.grid, (pos.gx, pos.gy), (ev.x, ev.y), max_len=ap.current + 1)
        # Exclude start for a cleaner draw; but keep target.
        plan.path = path[1:] if len(path) > 1 else []
        plan.target = (ev.x, ev.y)

    def _on_move(self, ev: MoveCommand) -> None:
        # Only allow moving the selected entity
        eids, _ = self.world.view(Selected)
        if not eids or eids[0] != ev.entity:
            return

        pos = self.world.get(ev.entity, Position)
        ap = self.world.get(ev.entity, AP)
        if not pos or not ap:
            return

        if (ev.target[0], ev.target[1]) not in self._reachable:
            return

        path = astar(self.grid, (pos.gx, pos.gy), ev.target, max_len=ap.current + 1)
        if len(path) <= 1:
            return

        # Convert to motion path (exclude current cell)
        motion = self.world.get(ev.entity, Motion)
        if not motion:
            motion = Motion()
            self.world.add(ev.entity, motion)

        motion.path.clear()
        for step in path[1:]:
            motion.path.append(step)

        # Clear preview
        plan = self.world.get(ev.entity, PathPlan)
        if plan:
            plan.path = []
            plan.target = None

    # --- Update (called every fixed step) ---
    def update(self) -> None:
        # Keep FOV synced to currently selected unit
        eids, rows = self.world.view(Selected, Position, AP)
        if eids:
            _, pos, ap = rows[0]
            self.grid.reveal_from(pos.gx, pos.gy, FOV_RADIUS)
            self._reachable = reachable_flood(self.grid, (pos.gx, pos.gy), ap.current)

    # Exposed for RenderSystem
    @property
    def reachable(self) -> set[tuple[int, int]]:
        return self._reachable
