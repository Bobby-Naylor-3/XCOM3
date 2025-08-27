from __future__ import annotations

from dataclasses import dataclass
from typing import DefaultDict, Dict, FrozenSet, Iterable, List, Tuple, Type, TypeVar, Any

T = TypeVar("T")


@dataclass
class CacheStats:
    hits: int = 0
    misses: int = 0

    def reset(self) -> None:
        self.hits = 0
        self.misses = 0


class World:
    """
    Simple ECS:
      - Component stores per type: Dict[type, Dict[entity, component]]
      - view() with cached, IMMUTABLE tuples
      - Reverse dirty index: component_type -> affected view keys
      - add/remove/destroy
    """

    def __init__(self) -> None:
        self._next_eid: int = 1
        self.stores: Dict[Type[Any], Dict[int, Any]] = {}
        self._view_cache: Dict[FrozenSet[Type[Any]], Tuple[Tuple[int, ...], Tuple[Tuple[Any, ...], ...]]] = {}
        self._view_dirty: Dict[FrozenSet[Type[Any]], bool] = {}
        self._comp_to_views: DefaultDict[Type[Any], List[FrozenSet[Type[Any]]]] = DefaultDict(list)
        self.cache_stats = CacheStats()

    # ---- Entity & Components ----
    def create(self) -> int:
        eid = self._next_eid
        self._next_eid += 1
        return eid

    def add(self, entity: int, component: Any) -> None:
        store = self.stores.setdefault(type(component), {})
        store[entity] = component
        self._mark_dirty_for(type(component))

    def get(self, entity: int, comp_type: Type[T]) -> T | None:
        store = self.stores.get(comp_type)
        return None if store is None else store.get(entity)

    def remove(self, entity: int, comp_type: Type[Any]) -> None:
        store = self.stores.get(comp_type)
        if store and entity in store:
            del store[entity]
            self._mark_dirty_for(comp_type)

    def destroy(self, entity: int) -> None:
        for comp_type, store in self.stores.items():
            if entity in store:
                del store[entity]
                self._mark_dirty_for(comp_type)

    # ---- Views ----
    def view(self, *comp_types: Type[Any]) -> Tuple[Tuple[int, ...], Tuple[Tuple[Any, ...], ...]]:
        """
        Returns immutable tuple of (entities, components tuples).
        """
        key = frozenset(comp_types)
        cached = self._view_cache.get(key)
        dirty = self._view_dirty.get(key, True)
        if cached is not None and not dirty:
            self.cache_stats.hits += 1
            return cached

        # Build
        entities = None
        for ct in comp_types:
            store = self.stores.get(ct, {})
            ids = set(store.keys())
            entities = ids if entities is None else (entities & ids)

        ent_sorted = tuple(sorted(entities or ()))
        comps_rows: List[Tuple[Any, ...]] = []
        for e in ent_sorted:
            row: List[Any] = []
            for ct in comp_types:
                row.append(self.stores[ct][e])
            comps_rows.append(tuple(row))

        result = (ent_sorted, tuple(comps_rows))
        self._view_cache[key] = result
        self._view_dirty[key] = False

        # Register dirty mapping for each component type in key
        for ct in key:
            lst = self._comp_to_views[ct]
            if key not in lst:
                lst.append(key)

        self.cache_stats.misses += 1
        return result

    def _mark_dirty_for(self, comp_type: Type[Any]) -> None:
        for key in self._comp_to_views.get(comp_type, []):
            self._view_dirty[key] = True
