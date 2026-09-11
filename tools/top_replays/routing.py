"""Deterministic shadow-route optimisation for observed task chains."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Mapping, Sequence


@dataclass(frozen=True)
class Waypoint:
    """One observed task location and its route-order constraints."""

    waypoint_id: str
    x: int
    y: int
    intent: str = "task"
    precedes: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class RouteSolution:
    order: tuple[str, ...]
    distance: int
    algorithm: str
    feasible: bool
    deadline_steps: int | None = None


def manhattan(a: tuple[int, int], b: tuple[int, int]) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def route_distance(
    start: tuple[int, int],
    end: tuple[int, int],
    order: Sequence[str],
    by_id: Mapping[str, Waypoint],
) -> int:
    points = [start, *((by_id[item].x, by_id[item].y) for item in order), end]
    return sum(manhattan(a, b) for a, b in zip(points, points[1:]))


def _normalise_waypoints(waypoints: Iterable[Waypoint | Mapping]) -> tuple[Waypoint, ...]:
    result = []
    for value in waypoints:
        if isinstance(value, Waypoint):
            result.append(value)
        else:
            result.append(
                Waypoint(
                    waypoint_id=str(value["waypoint_id"]),
                    x=int(value["x"]),
                    y=int(value["y"]),
                    intent=str(value.get("intent", "task")),
                    precedes=tuple(str(item) for item in value.get("precedes", ())),
                )
            )
    ids = [item.waypoint_id for item in result]
    if len(ids) != len(set(ids)):
        raise ValueError("waypoint ids must be unique")
    unknown = sorted({dep for item in result for dep in item.precedes} - set(ids))
    if unknown:
        raise ValueError(f"unknown waypoint precedence ids: {unknown}")
    return tuple(result)


def _predecessors(waypoints: Sequence[Waypoint]) -> dict[str, set[str]]:
    """Convert each ``a.precedes=(b,)`` edge into predecessors for b."""
    pred = {item.waypoint_id: set() for item in waypoints}
    for item in waypoints:
        for later in item.precedes:
            pred[later].add(item.waypoint_id)
    return pred


def _valid_order(order: Sequence[str], predecessors: Mapping[str, set[str]]) -> bool:
    positions = {item: index for index, item in enumerate(order)}
    return len(positions) == len(order) and all(
        positions[earlier] < positions[item]
        for item, required in predecessors.items()
        for earlier in required
    )


def _exact_route(
    start: tuple[int, int], end: tuple[int, int], waypoints: Sequence[Waypoint]
) -> tuple[tuple[str, ...], int] | None:
    if not waypoints:
        return (), manhattan(start, end)
    ids = tuple(item.waypoint_id for item in waypoints)
    index = {item: i for i, item in enumerate(ids)}
    pred = _predecessors(waypoints)
    pred_masks = {
        item: sum(1 << index[required] for required in pred[item]) for item in ids
    }
    positions = {item.waypoint_id: (item.x, item.y) for item in waypoints}
    # (visited mask, last index) -> (distance, lexicographically stable order)
    states: dict[tuple[int, int], tuple[int, tuple[str, ...]]] = {}
    for i, item in enumerate(ids):
        if pred_masks[item] == 0:
            states[(1 << i, i)] = (manhattan(start, positions[item]), (item,))
    for mask_size in range(1, len(ids) + 1):
        for (mask, last), (cost, order) in list(states.items()):
            if mask.bit_count() != mask_size:
                continue
            for nxt, item in enumerate(ids):
                bit = 1 << nxt
                if mask & bit or pred_masks[item] & ~mask:
                    continue
                candidate = (
                    cost + manhattan(positions[ids[last]], positions[item]),
                    order + (item,),
                )
                key = (mask | bit, nxt)
                if key not in states or candidate < states[key]:
                    states[key] = candidate
    full = (1 << len(ids)) - 1
    candidates = [
        (cost + manhattan(positions[ids[last]], end), order)
        for (mask, last), (cost, order) in states.items()
        if mask == full
    ]
    if not candidates:
        return None
    distance, order = min(candidates)
    return order, distance


def _topological_ids(waypoints: Sequence[Waypoint]) -> tuple[str, ...] | None:
    pred = _predecessors(waypoints)
    remaining = set(pred)
    result = []
    while remaining:
        ready = sorted(item for item in remaining if pred[item].isdisjoint(remaining))
        if not ready:
            return None
        item = ready[0]
        result.append(item)
        remaining.remove(item)
    return tuple(result)


def _approximate_route(
    start: tuple[int, int], end: tuple[int, int], waypoints: Sequence[Waypoint]
) -> tuple[tuple[str, ...], int] | None:
    """Deterministic cheapest insertion followed by precedence-safe 2-opt."""
    topo = _topological_ids(waypoints)
    if topo is None:
        return None
    by_id = {item.waypoint_id: item for item in waypoints}
    pred = _predecessors(waypoints)
    order: list[str] = []
    # Insert in stable topological order at the least expensive legal position.
    for item in topo:
        candidates = []
        for position in range(len(order) + 1):
            candidate = order[:position] + [item] + order[position:]
            if _valid_order(candidate, {k: pred[k] for k in candidate}):
                candidates.append((route_distance(start, end, candidate, by_id), tuple(candidate)))
        if not candidates:
            return None
        order = list(min(candidates)[1])

    improved = True
    while improved:
        improved = False
        baseline = route_distance(start, end, order, by_id)
        best = (baseline, tuple(order))
        for left in range(len(order) - 1):
            for right in range(left + 2, len(order) + 1):
                candidate = order[:left] + list(reversed(order[left:right])) + order[right:]
                if not _valid_order(candidate, pred):
                    continue
                scored = (route_distance(start, end, candidate, by_id), tuple(candidate))
                if scored < best:
                    best = scored
        if best[0] < baseline:
            order = list(best[1])
            improved = True
    return tuple(order), route_distance(start, end, order, by_id)


def optimise_route(
    start: tuple[int, int],
    end: tuple[int, int],
    waypoints: Iterable[Waypoint | Mapping],
    *,
    deadline_steps: int | None = None,
    exact_limit: int = 12,
) -> RouteSolution:
    """Find a constrained shadow route without changing any observed action.

    Up to ``exact_limit`` waypoints, Held-Karp dynamic programming gives the
    exact shortest Manhattan route.  Longer chains use deterministic cheapest
    insertion and precedence-safe 2-opt.
    """
    normalised = _normalise_waypoints(waypoints)
    if len(normalised) <= exact_limit:
        result = _exact_route(start, end, normalised)
        algorithm = "exact_dp"
    else:
        result = _approximate_route(start, end, normalised)
        algorithm = "insertion_2opt"
    if result is None:
        return RouteSolution((), 0, algorithm, False, deadline_steps)
    order, distance = result
    feasible = deadline_steps is None or distance <= deadline_steps
    return RouteSolution(order, distance, algorithm, feasible, deadline_steps)

