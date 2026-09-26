from app.services.oven_engine import (
    Interval,
    Occupancy,
    RecipeDurations,
    build_occupancies,
    find_conflicts,
    find_window_with_skips,
    free_gaps,
    next_free_window,
)


def test_half_open_no_touch_conflict():
    a = Occupancy(1, Interval(0, 30), "bake", 1)
    b = Occupancy(1, Interval(30, 60), "bake", 2)
    assert find_conflicts([a], [b]) == []


def test_overlap_detected():
    recipe = RecipeDurations(20, 30)
    cand = build_occupancies(1, 9, 10, recipe)
    existing = [Occupancy(1, Interval(25, 40), "bake", 1)]
    assert find_conflicts(existing, cand)


def test_next_free_window_after_busy():
    existing = [
        Occupancy(1, Interval(0, 40), "ferment", 1),
        Occupancy(1, Interval(40, 70), "bake", 1),
    ]
    w = next_free_window(existing, 1, duration=30, search_from=0)
    assert w == Interval(70, 100)


def test_next_free_in_gap():
    existing = [
        Occupancy(1, Interval(0, 20), "bake", 1),
        Occupancy(1, Interval(80, 100), "bake", 2),
    ]
    w = next_free_window(existing, 1, duration=30, search_from=0)
    assert w == Interval(20, 50)


def test_free_gaps_within_search_range():
    existing = [
        Occupancy(1, Interval(0, 40), "ferment", 1),
        Occupancy(1, Interval(40, 70), "bake", 1),
        Occupancy(1, Interval(100, 120), "bake", 2),
        Occupancy(2, Interval(500, 600), "bake", 3),  # 别的炉不影响
    ]
    assert free_gaps(existing, 1, search_from=0, search_to=200) == [
        Interval(70, 100),
        Interval(120, 200),
    ]
    # 忙段都在 8:00 前结束，搜索范围内只剩一段整空档
    assert free_gaps(existing, 1, search_from=8 * 60, search_to=22 * 60) == [
        Interval(8 * 60, 22 * 60),
    ]


def test_find_window_reports_earlier_short_gaps():
    existing = [
        Occupancy(1, Interval(8 * 60, 9 * 60), "bake", 1),   # 空隙 08:00 无，09:00–09:30
        Occupancy(1, Interval(9 * 60 + 30, 10 * 60), "bake", 2),
        Occupancy(1, Interval(10 * 60 + 40, 22 * 60), "bake", 3),
    ]
    w, skipped = find_window_with_skips(
        existing, 1, duration=75, search_from=8 * 60, search_to=22 * 60
    )
    assert skipped == [Interval(9 * 60, 9 * 60 + 30), Interval(10 * 60, 10 * 60 + 40)]
    assert w is None  # 空隙 30/40 分钟都短于 75，无可排窗口


def test_find_window_skips_short_gap_then_fits():
    existing = [
        Occupancy(1, Interval(8 * 60, 8 * 60 + 50), "bake", 1),
        Occupancy(1, Interval(9 * 60, 9 * 60 + 30), "bake", 2),
    ]
    w, skipped = find_window_with_skips(
        existing, 1, duration=45, search_from=8 * 60, search_to=22 * 60
    )
    assert skipped == [Interval(8 * 60 + 50, 9 * 60)]  # 10 分钟空隙太短
    assert w == Interval(9 * 60 + 30, 9 * 60 + 75)


def test_find_window_touching_endpoints_usable():
    existing = [Occupancy(1, Interval(8 * 60, 10 * 60), "bake", 1)]
    w, skipped = find_window_with_skips(
        existing, 1, duration=60, search_from=8 * 60, search_to=22 * 60
    )
    assert skipped == []
    assert w == Interval(10 * 60, 11 * 60)  # 端点相接即可开工


def test_find_window_exact_fit_and_search_to_boundary():
    # 空档 8:00–21:00 长 780 分钟，恰好等于所需时长：可排，端点相接
    existing = [Occupancy(1, Interval(21 * 60, 22 * 60), "bake", 1)]
    w, skipped = find_window_with_skips(
        existing, 1, duration=13 * 60, search_from=8 * 60, search_to=22 * 60
    )
    assert skipped == []
    assert w == Interval(8 * 60, 21 * 60)
    # 再长 1 分钟就排不下，该空隙进入过短清单
    w, skipped = find_window_with_skips(
        existing, 1, duration=13 * 60 + 1, search_from=8 * 60, search_to=22 * 60
    )
    assert w is None
    assert skipped == [Interval(8 * 60, 21 * 60)]
    # 窗口终点恰好顶到 22:00 搜索边界也可排
    w, skipped = find_window_with_skips(
        [], 1, duration=14 * 60, search_from=8 * 60, search_to=22 * 60
    )
    assert skipped == []
    assert w == Interval(8 * 60, 22 * 60)


def test_find_window_no_gap_at_all():
    existing = [Occupancy(1, Interval(7 * 60, 23 * 60), "bake", 1)]
    w, skipped = find_window_with_skips(
        existing, 1, duration=30, search_from=8 * 60, search_to=22 * 60
    )
    assert w is None
    assert skipped == []  # 没有空档：调用方不出建议行


def test_window_endpoints_match_gantt_segments():
    recipe = RecipeDurations(40, 35)
    w, _ = find_window_with_skips([], 1, recipe.total, search_from=8 * 60, search_to=22 * 60)
    assert w is not None
    ferment, bake = build_occupancies(1, -1, w.start, recipe)
    assert ferment.interval.end == w.start + recipe.ferment_min
    assert bake.interval.end == w.start + recipe.total == w.end
