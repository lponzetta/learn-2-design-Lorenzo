import math

import numpy as np

from ombrellone.geometry import (Umbrella, Pose, Target, forward_kinematics, shadow_ellipse,
                                 ellipse_axes, evaluate, normalized_radius)
from ombrellone.solar import sun_vector_enu


def test_horizontal_disk_shadow_is_translated_circle():
    C = np.array([0.0, 0.0, 3.0])
    n = np.array([0.0, 0.0, 1.0])
    s = sun_vector_enu(30.0, 180.0)  # sole a Sud, 30 gradi
    G, M = shadow_ellipse(C, n, 1.5, s)
    a, b, _ = ellipse_axes(M)
    assert abs(a - 1.5) < 1e-9 and abs(b - 1.5) < 1e-9
    # il centro dell'ombra e' spostato verso Nord di C_z / tan(h)
    assert abs(G[0]) < 1e-9
    assert abs(G[1] - 3.0 / math.tan(math.radians(30))) < 1e-9


def test_sun_facing_disk_shadow_elongated_by_1_over_sin_h():
    h = 40.0
    s = sun_vector_enu(h, 200.0)
    C = np.array([0.0, 0.0, 2.5])
    G, M = shadow_ellipse(C, s, 1.0, s)  # normale = direzione del sole
    a, b, ang = ellipse_axes(M)
    assert abs(b - 1.0) < 1e-9
    assert abs(a - 1.0 / math.sin(math.radians(h))) < 1e-9
    assert abs(ang - 20.0) < 1e-6  # asse maggiore lungo l'azimut del sole (mod 180)


def test_inside_outside():
    G = np.array([0.0, 0.0])
    M = np.diag([2.0, 1.0])
    pts = np.array([[1.9, 0.0], [0.0, 0.99], [0.0, 1.01], [2.1, 0.0]])
    rho = normalized_radius(pts, G, M)
    assert (rho[:2] <= 1).all() and (rho[2:] > 1).all()


def test_forward_kinematics_vertical_arm():
    u = Umbrella(H=2.0, L=1.5)
    fk = forward_kinematics(u, Pose(0, 0, 0, 0))
    assert np.allclose(fk["C"], [0, 0, 3.5])


def test_evaluate_full_coverage_at_zenith_like_sun():
    u = Umbrella()
    s = sun_vector_enu(85.0, 180.0)
    ev = evaluate(u, Pose(180, 5, 0, 0), s, Target(0, 0, 1.0))
    assert ev.feasible
    assert ev.coverage > 0.99
    assert ev.margin > 0


def test_constraints_detect_theta_limit():
    u = Umbrella(theta_max_deg=60)
    ev = evaluate(u, Pose(180, 75, 0, 0), sun_vector_enu(60, 180), Target())
    assert not ev.feasible and any("theta" in v for v in ev.violations)
