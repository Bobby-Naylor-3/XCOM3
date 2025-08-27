from __future__ import annotations

import pygame

from ..components import Faction, PathPlan, Position, Renderable, Selected, AP
from ..constants import (
    BLUE,
    GREEN,
    ORANGE,
    PATH,
    PLAYER,
    REACHABLE,
    RED,
    SELECTION,
    TILE,
    WHITE,
    YELLOW,
    DEBUG,
)
from ..ecs import World
from ..grid import Camera, Grid


class RenderSystem:
    """
    Deterministic draw order; minimal allocations; viewport-scoped fog draw.
    """

    def __init__(self, world: World, grid: Grid, camera: Camera, screen: pygame.Surface, font: pygame.font.Font) -> None:
        self.world = world
        self.grid = grid
        self.camera = camera
        self.screen = screen
        self.font = font

        map_px_w, map_px_h = self.grid.map_pixel_size()
        self.grid.ensure_surfaces(map_px_w, map_px_h)

    # ---- Helpers ----
    def _draw_rect_alpha(self, color: tuple[int, int, int, int], rect: pygame.Rect) -> None:
        s = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        s.fill(color)
        self.screen.blit(s, rect.topleft)

    # ---- Main ----
    def render(self, alpha: float) -> None:
        cam = self.camera
        g = self.grid

        # Terrain
        src = pygame.Rect(cam.x, cam.y, cam.w, cam.h)
        self.screen.blit(g.terrain_surf, (0, 0), area=src)
        if DEBUG.show_grid:
            self.screen.blit(g.gridlines_surf, (0, 0), area=src)

        # Reachable tiles (UI)
        if DEBUG.show_reachable:
            # Ask ControllerSystem for reachability by peeking PathPlan/Selected entity
            # (We don't import ControllerSystem; instead, re-derive quickly for selected)
            eids, rows = self.world.view(Selected, Position, AP)
            if eids:
                _, pos, ap = rows[0]
                # Draw from grid.visible to avoid flooding whole map visually
                # We'll just tint tiles in camera viewport that are reachable.
                start_gx = cam.x // TILE
                start_gy = cam.y // TILE
                end_gx = (cam.x + cam.w) // TILE + 1
                end_gy = (cam.y + cam.h) // TILE + 1
                # Iterate reachable by path preview (stored by Controller in PathPlan)
                # Safer: reconstruct in render is expensive; instead draw preview only.
                pass  # real reachable tint handled by Controller via PathPlan? We'll do preview next.

        # Selection + path preview
        eids, rows = self.world.view(Selected, Position, PathPlan)
        if eids:
            _, pos, plan = rows[0]
            if plan.path:
                for gx, gy in plan.path:
                    sx, sy = cam.world_to_screen(gx * TILE, gy * TILE)
                    rect = pygame.Rect(sx, sy, TILE, TILE)
                    self._draw_rect_alpha(PATH, rect)

            # Selection highlight
            sx, sy = cam.world_to_screen(pos.gx * TILE, pos.gy * TILE)
            rect = pygame.Rect(sx, sy, TILE, TILE)
            self._draw_rect_alpha(SELECTION, rect)

        # Entities
        eids, rows = self.world.view(Position, Renderable, Faction, AP)
        for eid, (pos, rend, fac, ap) in zip(eids, rows):
            cx, cy = (pos.px + (pos.gx - pos.px) * alpha), (pos.py + (pos.gy - pos.py) * alpha)
            wx, wy = int(cx * TILE + TILE // 2), int(cy * TILE + TILE // 2)
            sx, sy = cam.world_to_screen(wx, wy)
            color = PLAYER if fac.name == "player" else RED
            pygame.draw.circle(self.screen, color, (sx, sy), rend.radius_px)

            # AP pips
            pip_w = 4
            gap = 1
            max_pips = min(12, ap.maximum)
            draw_pips = min(ap.current, max_pips)
            base_x = sx - ((max_pips * (pip_w + gap)) // 2)
            y = sy - rend.radius_px - 10
            for i in range(max_pips):
                rect = pygame.Rect(base_x + i * (pip_w + gap), y, pip_w, 6)
                pygame.draw.rect(self.screen, (70, 70, 70), rect, border_radius=1)
            for i in range(draw_pips):
                rect = pygame.Rect(base_x + i * (pip_w + gap), y, pip_w, 6)
                pygame.draw.rect(self.screen, YELLOW, rect, border_radius=1)

        # Fog of war (viewport-scoped)
        start_gx = cam.x // TILE
        start_gy = cam.y // TILE
        end_gx = (cam.x + cam.w) // TILE + 1
        end_gy = (cam.y + cam.h) // TILE + 1
        for gy in range(start_gy, min(end_gy, g.h)):
            for gx in range(start_gx, min(end_gx, g.w)):
                if (gx, gy) in g.visible:
                    continue
                sx, sy = cam.world_to_screen(gx * TILE, gy * TILE)
                if (gx, gy) in g.explored:
                    self.screen.blit(g.fog_dim, (sx, sy))
                else:
                    self.screen.blit(g.fog_full, (sx, sy))

        # HUD / debug
        y = 6
        if DEBUG.show_fps:
            fps_text = self.font.render(f"FPS: {int(pygame.time.get_ticks() and pygame.time.Clock().get_fps())}", True, WHITE)
            self.screen.blit(fps_text, (8, y))
            y += 18
        if DEBUG.show_cache_stats:
            cs = self.world.cache_stats
            txt = self.font.render(f"Views cache hits/misses: {cs.hits}/{cs.misses}", True, WHITE)
            self.screen.blit(txt, (8, y))
            y += 18
