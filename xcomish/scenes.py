from __future__ import annotations

from typing import Callable, List, Optional

import pygame

from .events import EventBus


class Scene:
    def __init__(self, bus: EventBus) -> None:
        self.bus = bus

    # Lifecycle hooks
    def enter(self) -> None: ...
    def exit(self) -> None: ...
    def pause(self) -> None: ...
    def resume(self) -> None: ...

    # Main handlers
    def handle_event(self, ev: pygame.event.Event) -> None: ...
    def update(self, fixed_dt: float) -> None: ...
    def render(self, screen: pygame.Surface, alpha: float) -> None: ...


class SceneStack:
    """
    Stack with enter/exit/pause/resume semantics and no redundant churn on switch().
    """

    def __init__(self) -> None:
        self._stack: List[Scene] = []

    def push(self, scene: Scene) -> None:
        if self._stack:
            self._stack[-1].pause()
        self._stack.append(scene)
        scene.enter()

    def pop(self) -> None:
        if not self._stack:
            return
        top = self._stack.pop()
        top.exit()
        if self._stack:
            self._stack[-1].resume()

    def switch(self, scene: Scene) -> None:
        if self._stack:
            old = self._stack.pop()
            old.exit()
        self._stack.append(scene)
        scene.enter()

    def peek(self) -> Optional[Scene]:
        return self._stack[-1] if self._stack else None

    # Proxies
    def handle_event(self, ev: pygame.event.Event) -> None:
        top = self.peek()
        if top:
            top.handle_event(ev)

    def update(self, fixed_dt: float) -> None:
        top = self.peek()
        if top:
            top.update(fixed_dt)

    def render(self, screen: pygame.Surface, alpha: float) -> None:
        top = self.peek()
        if top:
            top.render(screen, alpha)
