from datetime import datetime, timezone, timedelta

import numpy as np

from ombrellone.geometry import Umbrella, Target, evaluate
from ombrellone.planner import analytic_pose, solve_pose, plan_day, min_elevation_for_full_coverage
from ombrellone.solar import sun_vector_enu


def test_analytic_pose_centers_shadow():
    u = Umbrella()
    t = Target(0.3, -0.5, 1.0)
    s = sun_vector_enu(65.0, 210.0)
    p = analytic_pose(u, s, t)
    ev = evaluate(u, p, s, t)
    assert np.allclose(ev.G, t.center, atol=1e-6)
    assert ev.margin > 0


def test_analytic_pose_with_offset_centers_shadow():
    u = Umbrella(canopy_offset=0.5)
    t = Target(0, 0, 1.0)
    s = sun_vector_enu(60.0, 180.0)
    p = analytic_pose(u, s, t)
    ev = evaluate(u, p, s, t)
    assert np.allclose(ev.G, t.center, atol=1e-4)


def test_solver_full_coverage_high_sun_and_degrades_low_sun():
    u = Umbrella()
    t = Target()
    hi = solve_pose(u, sun_vector_enu(65, 180), t)
    lo = solve_pose(u, sun_vector_enu(25, 180), t)
    assert hi.full_coverage
    assert hi.eval.feasible and lo.eval.feasible
    assert not lo.full_coverage
    assert lo.pose.theta_deg > u.theta_max_deg - 0.5  # braccio a fine corsa verso il sole
    assert lo.eval.coverage > 0.0


def test_min_elevation_is_between_40_and_50_for_default():
    e = min_elevation_for_full_coverage(Umbrella(), Target(), elev_grid=np.arange(89, 20, -2.0))
    assert 38 <= e <= 50


def test_plan_day_july_rimini():
    tz = timezone(timedelta(hours=2))
    plan = plan_day(Umbrella(), Target(), datetime(2026, 7, 15), 44.06, 12.57, tz=tz, step_minutes=30)
    s = plan.summary()
    w = s["finestra_copertura_totale"]
    assert w is not None
    assert 9 <= w[0].hour <= 11 and 15 <= w[1].hour <= 18
    assert s["movimenti"] >= 3
    assert s["copertura_media_tenuta"] > 0.6
