from __future__ import annotations

import sys
from time import perf_counter

import pygame

from .components import (
    AP,
    Faction,
    Motion,
    Opaque,
    PathPlan,
    Position,
    Renderable,
    Selected,
    Solid,
    Patrol,
)
from .constants import (
    FIXED_DT,
    DT_CLAMP,
    EPS,
    FOV_RADIUS,
    MAP_H,
    MAP_W,
    MAX_STEPS_PER_FRAME,
    MOVE_SPEED_TILES_PER_SEC,
    TILE,
    WIN_H,
    WIN_W,
    DEBUG,
)
from .ecs import World
from .events import EventBus, Quit, ToggleDebug
from .grid import Camera, Grid
from .pathing import reachable_flood
from .scenes import Scene, SceneStack
from .systems.ai import PatrolAI
from .systems.controller import ControllerSystem
from .systems.input import InputSystem
from .systems.motion import MotionSystem
from .systems.render import RenderSystem


class GameScene(Scene):
    def __init__(self, bus: EventBus, world: World, grid: Grid, camera: Camera, screen: pygame.Surface, clock: pygame.time.Clock) -> None:
        super().__init__(bus)
        self.world = world
        self.grid = grid
        self.camera = camera
        self.screen = screen
        self.clock = clock

        self.input_sys = InputSystem(world, grid, camera, bus)
        self.controller = ControllerSystem(world, grid, bus)
        self.motion_sys = MotionSystem(world, grid)
        self.ai = PatrolAI(world, grid)
        self.font = pygame.font.SysFont("consolas,menlo,monaco,dejavu sans mono", 14)
        self.renderer = RenderSystem(world, grid, camera, screen, self.font)

        self._hud_fps_txt: pygame.Surface | None = None

        # toggle debug
        bus.subscribe(ToggleDebug, self._toggle_debug)

    def _toggle_debug(self, _: ToggleDebug) -> None:
        DEBUG.show_fps = not DEBUG.show_fps
        DEBUG.show_cache_stats = not DEBUG.show_cache_stats

    # Scene hooks
    def enter(self) -> None:
        pass

    def handle_event(self, ev: pygame.event.Event) -> None:
        self.input_sys.handle_event(ev)

    def update(self, fixed_dt: float) -> None:
        # Basic WASD camera controls (not event-driven to keep it responsive)
        keys = pygame.key.get_pressed()
        speed = 12
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            self.camera.x -= speed
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            self.camera.x += speed
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            self.camera.y -= speed
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            self.camera.y += speed
        map_px_w, map_px_h = self.grid.map_pixel_size()
        self.camera.clamp_to_map(map_px_w, map_px_h)

        # Sim order: AI -> Motion -> Controller (recompute reachability/FOV)
        self.ai.update()
        self.motion_sys.update(fixed_dt)
        self.controller.update()

    def render(self, screen: pygame.Surface, alpha: float) -> None:
        self.renderer.render(alpha)
        # HUD: FPS & cache stats (use the real clock)
        if DEBUG.show_fps:
            fps = self.clock.get_fps()
            txt = self.font.render(f"{fps:5.1f} fps", True, (255, 255, 255))
            screen.blit(txt, (8, 6))
        if DEBUG.show_cache_stats:
            cs = self.world.cache_stats
            txt = self.font.render(f"views cache: {cs.hits}/{cs.misses}", True, (200, 200, 240))
            screen.blit(txt, (8, 24))


def build_world(bus: EventBus) -> tuple[World, Grid, Camera]:
    world = World()
    grid = Grid(MAP_W, MAP_H)
    cam = Camera(0, 0, WIN_W, WIN_H)

    # Terrain: carve obstacles
    # Simple walls and a central building
    for x in range(5, 35):
        grid.walkable[10][x] = False
        grid.opaque[10][x] = True
    for y in range(3, 20):
        grid.walkable[y][20] = False
        grid.opaque[y][20] = True

    # Entities
    # Player unit
    p1 = world.create()
    world.add(p1, Position(3, 3))
    world.add(p1, Renderable(12))
    world.add(p1, Faction("player"))
    world.add(p1, AP(12, 12))
    grid.occupy(3, 3, p1)

    # Enemy patroller
    e1 = world.create()
    world.add(e1, Position(30, 18))
    world.add(e1, Renderable(12))
    world.add(e1, Faction("enemy"))
    world.add(e1, AP(12, 12))
    world.add(e1, Patrol(waypoints=[(30, 18), (34, 18), (34, 22), (30, 22)]))
    grid.occupy(30, 18, e1)

    return world, grid, cam


def main() -> None:
    pygame.init()
    pygame.display.set_caption("xcomish – vertical slice")
    screen = pygame.display.set_mode((WIN_W, WIN_H))
    clock = pygame.time.Clock()

    bus = EventBus()
    world, grid, cam = build_world(bus)

    stack = SceneStack()
    game = GameScene(bus, world, grid, cam, screen, clock)
    stack.push(game)

    running = True
    last_time = perf_counter()
    acc = 0.0

    # Select player on start for convenience
    from .events import SelectEntity

    eids, _ = world.view(Faction, Position)
    for eid, (fac, pos) in zip(eids, _):
        if fac.name == "player":
            bus.publish(SelectEntity(eid))
            break

    while running:
        # Events
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False
                break
            stack.handle_event(ev)

        # Quit event (from input)
        # We check pygame.QUIT above and also here via bus if future scenes use it.
        # (No global subscriber needed in this slice.)
        # No need to poll EventBus; quitting handled by direct pygame loop.

        # Timing
        now = perf_counter()
        dt = now - last_time
        last_time = now
        if dt > DT_CLAMP:
            dt = DT_CLAMP
        acc += dt

        steps = 0
        while acc >= FIXED_DT and steps < MAX_STEPS_PER_FRAME:
            stack.update(FIXED_DT)
            acc -= FIXED_DT
            steps += 1
        alpha = 0.0 if FIXED_DT == 0 else (acc / FIXED_DT)

        # Render
        stack.render(screen, alpha)
        pygame.display.flip()

        clock.tick(144)  # allow >60Hz render; sim is fixed-step 60Hz

    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()
