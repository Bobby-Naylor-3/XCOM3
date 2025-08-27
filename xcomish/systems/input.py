from __future__ import annotations

import pygame

from ..constants import WIN_H, WIN_W
from ..events import HoverTileChanged, MoveCommand, Quit, SelectEntity, ToggleDebug
from ..grid import Camera, Grid
from ..ecs import World
from ..components import Position, Selected, Faction


class InputSystem:
    """
    Event-driven input; no per-frame allocations for hover.
    """

    def __init__(self, world: World, grid: Grid, camera: Camera, bus) -> None:
        self.world = world
        self.grid = grid
        self.camera = camera
        self.bus = bus
        self._last_hover: tuple[int, int] | None = None

    def handle_event(self, ev: pygame.event.Event) -> None:
        if ev.type == pygame.QUIT:
            self.bus.publish(Quit())
            return

        if ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_ESCAPE:
                self.bus.publish(Quit())
            elif ev.key == pygame.K_F1:
                self.bus.publish(ToggleDebug())

        if ev.type == pygame.MOUSEMOTION:
            mx, my = ev.pos
            gx, gy = self.camera.screen_to_grid(mx, my)
            if self.grid.in_bounds(gx, gy) and (gx, gy) != self._last_hover:
                self._last_hover = (gx, gy)
                self.bus.publish(HoverTileChanged(gx, gy))

        if ev.type == pygame.MOUSEBUTTONDOWN:
            mx, my = ev.pos
            gx, gy = self.camera.screen_to_grid(mx, my)
            if not self.grid.in_bounds(gx, gy):
                return

            # Left-click select player unit on tile, if any
            if ev.button == 1:
                eids, rows = self.world.view(Position, Faction)
                for eid, (pos, fac) in zip(eids, rows):
                    if fac.name == "player" and (pos.gx, pos.gy) == (gx, gy):
                        self.bus.publish(SelectEntity(eid))
                        break
            # Right-click move selected
            elif ev.button == 3:
                # Find selected entity
                eids, rows = self.world.view(Selected, Position)
                if eids:
                    self.bus.publish(MoveCommand(eids[0], (gx, gy)))
