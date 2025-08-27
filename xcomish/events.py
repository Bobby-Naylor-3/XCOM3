from __future__ import annotations

import traceback
import types
import weakref
from dataclasses import dataclass
from typing import Any, Callable, DefaultDict, Dict, List, Optional, Tuple, Type, TypeVar

E = TypeVar("E")  # event type variable
Handler = Callable[[Any], None]


@dataclass(frozen=True)
class Event:
    """Base event marker class."""


# --- Common events ---
@dataclass(frozen=True)
class Quit(Event):
    pass


@dataclass(frozen=True)
class ToggleDebug(Event):
    pass


@dataclass(frozen=True)
class HoverTileChanged(Event):
    x: int
    y: int


@dataclass(frozen=True)
class SelectEntity(Event):
    entity: int


@dataclass(frozen=True)
class MoveCommand(Event):
    entity: int
    target: Tuple[int, int]


class EventBus:
    """
    Decoupled, safe EventBus with once=True support and optional weakrefs.

    - try/except around handlers (no global crash)
    - unsubscribe by handler or handle id
    - avoids leaks via optional weakrefs for bound methods
    """

    def __init__(self) -> None:
        self._subs: DefaultDict[Type[Event], List[Tuple[int, bool, Any]]] = DefaultDict(list)
        self._next_id: int = 1

    def subscribe(
        self, event_type: Type[E], handler: Handler, *, once: bool = False, weak: bool = False
    ) -> int:
        handle_id = self._next_id
        self._next_id += 1

        wrapped: Any
        if weak and isinstance(handler, types.MethodType):
            wrapped = weakref.WeakMethod(handler)  # returns None if dead
        else:
            wrapped = handler

        self._subs[event_type].append((handle_id, once, wrapped))
        return handle_id

    def unsubscribe(self, event_type: Type[E], handle_id: Optional[int] = None, handler: Optional[Handler] = None) -> None:
        subs = self._subs.get(event_type)
        if not subs:
            return
        keep: List[Tuple[int, bool, Any]] = []
        for hid, once, wrapped in subs:
            if handle_id is not None and hid == handle_id:
                continue
            if handler is not None:
                # Match both direct and weak wrapped
                target = wrapped() if isinstance(wrapped, weakref.WeakMethod) else wrapped
                if target is handler:
                    continue
            keep.append((hid, once, wrapped))
        self._subs[event_type] = keep

    def publish(self, event: Event) -> None:
        subs = self._subs.get(type(event), [])
        if not subs:
            return

        remove_ids: List[int] = []
        for handle_id, once, wrapped in list(subs):
            try:
                callback = wrapped() if isinstance(wrapped, weakref.WeakMethod) else wrapped
                if callback is None:
                    remove_ids.append(handle_id)
                    continue
                callback(event)
                if once:
                    remove_ids.append(handle_id)
            except Exception:
                # Keep going, but print a traceback for dev sanity
                traceback.print_exc()

        if remove_ids:
            self._subs[type(event)] = [t for t in self._subs[type(event)] if t[0] not in remove_ids]
