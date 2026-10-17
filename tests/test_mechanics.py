import math

import numpy as np

from ombrellone.geometry import Umbrella, Pose
from ombrellone.mechanics import (MassModel, Tube, MATERIALS, joint_loads, worst_case_loads,
                                  required_base_mass, arm_beam_check, frame_fem, size_motor,
                                  size_linear_actuator, wind_force_on_disk)


def test_wind_force_magnitude():
    F = wind_force_on_disk(1.5, np.array([0, 1.0, 0]), 0.0, 10.0)  # vento da Nord su disco verticale
    q = 0.5 * 1.225 * 100
    assert abs(np.linalg.norm(F) - q * 1.17 * math.pi * 2.25) < 1e-6


def test_parked_pose_has_small_torques():
    u, mm = Umbrella(), MassModel()
    park = worst_case_loads(u, Pose(0, 0, 0, 0), mm, 8.0)
    work = worst_case_loads(u, Pose(180, 70, 39, 180), mm, 8.0)
    assert park.tilt_torque_Nm < 0.2 * work.tilt_torque_Nm
    assert required_base_mass(u, Pose(0, 0, 0, 0), mm, 8.0, 0.5) < required_base_mass(u, Pose(180, 70, 39, 180), mm, 8.0, 0.5)


def test_beam_and_fem_agree_roughly():
    u, mm = Umbrella(), MassModel()
    p = Pose(180, 70, 39, 180)
    bc = arm_beam_check(u, p, mm, mm.arm_tube, mm.arm_material, 8.0)
    fr = frame_fem(u, p, mm, 8.0)
    assert bc.safety_factor > 3
    # il FEM include la cedevolezza del palo, quindi la freccia e' maggiore o simile
    assert fr.tip_deflection_mm > 0.5 * bc.tip_deflection_mm
    assert fr.max_stress_MPa.max() < MATERIALS["Al 6061-T6"].sigma_y / 1e6


def test_motor_sizing():
    m = size_motor("tilt", 80, 70, 40, 60, 0.45)
    assert m.design_torque_Nm == 160
    a = size_linear_actuator("tilt", 80, 0.15, 70, 40)
    assert 500 < a["forza_N"] < 1500
