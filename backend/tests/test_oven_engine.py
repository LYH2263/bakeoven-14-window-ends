from app.services.oven_engine import (
    Interval,
    Occupancy,
    RecipeDurations,
    ShortGap,
    build_occupancies,
    find_conflicts,
    next_free_window,
    next_free_window_detail,
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


def test_detail_reports_earlier_short_gap():
    # 08:00–08:30 空隙短于 75 分钟所需时长，须被记录且不被推荐
    existing = [Occupancy(1, Interval(510, 540), "bake", 1)]
    w, shorts = next_free_window_detail(existing, 1, duration=75, search_from=8 * 60, search_to=22 * 60)
    assert w == Interval(540, 615)
    assert shorts == [ShortGap(480, 510, 45)]


def test_detail_reports_multiple_short_gaps():
    existing = [
        Occupancy(1, Interval(500, 520), "bake", 1),
        Occupancy(1, Interval(560, 580), "bake", 2),
        Occupancy(1, Interval(640, 700), "bake", 3),
    ]
    w, shorts = next_free_window_detail(existing, 1, duration=60, search_from=480, search_to=1320)
    assert w == Interval(580, 640)
    assert shorts == [ShortGap(480, 500, 40), ShortGap(520, 560, 20)]


def test_detail_touching_gap_is_usable():
    # 端点相接的空档：空隙恰好等于所需时长即可用，不计入过短空隙
    existing = [
        Occupancy(1, Interval(480, 600), "bake", 1),
        Occupancy(1, Interval(660, 700), "bake", 2),
    ]
    w, shorts = next_free_window_detail(existing, 1, duration=60, search_from=480, search_to=1320)
    assert w == Interval(600, 660)
    assert shorts == []


def test_detail_no_fitting_window():
    existing = [Occupancy(1, Interval(500, 1300), "bake", 1)]
    w, shorts = next_free_window_detail(existing, 1, duration=60, search_from=480, search_to=1320)
    assert w is None
    assert shorts == [ShortGap(480, 500, 40), ShortGap(1300, 1320, 40)]


def test_detail_window_ends_match_gantt_segments():
    # 建议的发酵止/烘烤止必须与同开工真排入甘特的两段端点相同
    recipe = RecipeDurations(40, 35)
    existing = [
        Occupancy(1, Interval(480, 555), "ferment", 1),
        Occupancy(1, Interval(555, 590), "bake", 1),
    ]
    w, _ = next_free_window_detail(existing, 1, duration=recipe.total, search_from=480, search_to=1320)
    assert w is not None
    ferment_occ, bake_occ = build_occupancies(1, 99, w.start, recipe)
    assert ferment_occ.interval.end == w.start + recipe.ferment_min
    assert bake_occ.interval.end == w.end
