"""Oven scheduling with half-open ferment+bake intervals and next free window."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Interval:
    start: int  # minutes from day origin
    end: int  # exclusive

    def overlaps(self, other: "Interval") -> bool:
        return self.start < other.end and other.start < self.end


@dataclass(frozen=True)
class RecipeDurations:
    ferment_min: int
    bake_min: int

    @property
    def total(self) -> int:
        return self.ferment_min + self.bake_min


@dataclass(frozen=True)
class Occupancy:
    oven_id: int
    interval: Interval
    phase: str  # ferment | bake
    batch_id: int


def build_occupancies(
    oven_id: int,
    batch_id: int,
    start_min: int,
    recipe: RecipeDurations,
) -> list[Occupancy]:
    ferment = Interval(start_min, start_min + recipe.ferment_min)
    bake = Interval(ferment.end, ferment.end + recipe.bake_min)
    return [
        Occupancy(oven_id, ferment, "ferment", batch_id),
        Occupancy(oven_id, bake, "bake", batch_id),
    ]


def find_conflicts(existing: list[Occupancy], candidates: list[Occupancy]) -> list[tuple[Occupancy, Occupancy]]:
    hits: list[tuple[Occupancy, Occupancy]] = []
    for cand in candidates:
        for ex in existing:
            if ex.oven_id != cand.oven_id:
                continue
            if ex.interval.overlaps(cand.interval):
                hits.append((ex, cand))
    return hits


def free_gaps(
    existing: list[Occupancy],
    oven_id: int,
    search_from: int = 0,
    search_to: int = 24 * 60,
) -> list[Interval]:
    """All maximal free half-open intervals on oven within [search_from, search_to)."""
    busy = sorted(
        [o.interval for o in existing if o.oven_id == oven_id],
        key=lambda i: i.start,
    )
    gaps: list[Interval] = []
    cursor = search_from
    for iv in busy:
        if iv.end <= cursor:
            continue
        if iv.start > cursor:
            gaps.append(Interval(cursor, min(iv.start, search_to)))
        cursor = max(cursor, iv.end)
        if cursor >= search_to:
            return gaps
    if cursor < search_to:
        gaps.append(Interval(cursor, search_to))
    return gaps


def find_window_with_skips(
    existing: list[Occupancy],
    oven_id: int,
    duration: int,
    search_from: int = 0,
    search_to: int = 24 * 60,
) -> tuple[Interval | None, list[Interval]]:
    """Earliest fitting window plus the earlier gaps too short to hold it."""
    if duration <= 0:
        return None, []
    skipped: list[Interval] = []
    for gap in free_gaps(existing, oven_id, search_from, search_to):
        if gap.end - gap.start >= duration:
            return Interval(gap.start, gap.start + duration), skipped
        skipped.append(gap)
    return None, skipped


def next_free_window(
    existing: list[Occupancy],
    oven_id: int,
    duration: int,
    search_from: int = 0,
    search_to: int = 24 * 60,
) -> Interval | None:
    """Find earliest half-open [start, start+duration) free on oven."""
    window, _ = find_window_with_skips(existing, oven_id, duration, search_from, search_to)
    return window
