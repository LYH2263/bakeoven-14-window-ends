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


@dataclass(frozen=True)
class ShortGap:
    """A free gap inside the search range that is too short to use."""

    start: int
    end: int
    short_by: int  # minutes shorter than the needed duration


def next_free_window_detail(
    existing: list[Occupancy],
    oven_id: int,
    duration: int,
    search_from: int = 0,
    search_to: int = 24 * 60,
) -> tuple[Interval | None, list[ShortGap]]:
    """Earliest fitting window plus every earlier in-range gap too short to use.

    Gaps are half-open: a gap ending exactly when a busy interval starts
    (endpoints touching) is fully usable.
    """
    if duration <= 0:
        return None, []
    busy = sorted(
        [o.interval for o in existing if o.oven_id == oven_id],
        key=lambda i: i.start,
    )
    shorts: list[ShortGap] = []
    cursor = search_from
    for iv in busy:
        if iv.end <= cursor:
            continue
        gap_end = min(iv.start, search_to)
        if gap_end > cursor:
            gap_len = gap_end - cursor
            if gap_len >= duration:
                return Interval(cursor, cursor + duration), shorts
            shorts.append(ShortGap(cursor, gap_end, duration - gap_len))
        cursor = max(cursor, iv.end)
        if cursor >= search_to:
            return None, shorts
    if cursor + duration <= search_to:
        return Interval(cursor, cursor + duration), shorts
    if search_to > cursor:
        shorts.append(ShortGap(cursor, search_to, duration - (search_to - cursor)))
    return None, shorts


def next_free_window(
    existing: list[Occupancy],
    oven_id: int,
    duration: int,
    search_from: int = 0,
    search_to: int = 24 * 60,
) -> Interval | None:
    """Find earliest half-open [start, start+duration) free on oven."""
    window, _ = next_free_window_detail(existing, oven_id, duration, search_from, search_to)
    return window
