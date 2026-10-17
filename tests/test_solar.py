import math
from datetime import datetime, timezone, timedelta

import numpy as np
import pytest

from ombrellone.solar import sun_position, sun_vector_enu, solar_noon, vector_to_elev_az

RIMINI = (44.06, 12.57)


def test_noon_elevation_matches_declination():
    lat, lon = RIMINI
    d = datetime(2026, 6, 21, tzinfo=timezone.utc)
    noon = solar_noon(d, lat, lon)
    sp = sun_position(noon, lat, lon)
    expected = 90.0 - (lat - sp.declination_deg)
    assert abs(sp.elevation_deg - expected) < 0.1
    assert abs(sp.azimuth_deg - 180.0) < 0.5
    assert 23.3 < sp.declination_deg < 23.5


def test_morning_is_east_afternoon_is_west():
    lat, lon = RIMINI
    am = sun_position(datetime(2026, 7, 15, 6, 0, tzinfo=timezone.utc), lat, lon)
    pm = sun_position(datetime(2026, 7, 15, 16, 0, tzinfo=timezone.utc), lat, lon)
    assert 60 < am.azimuth_deg < 120
    assert 240 < pm.azimuth_deg < 300
    assert am.is_up and pm.is_up


def test_night():
    sp = sun_position(datetime(2026, 7, 15, 23, 30, tzinfo=timezone.utc), *RIMINI)
    assert not sp.is_up


def test_vector_roundtrip():
    v = sun_vector_enu(37.5, 123.0)
    assert abs(np.linalg.norm(v) - 1) < 1e-12
    e, a = vector_to_elev_az(v)
    assert abs(e - 37.5) < 1e-9 and abs(a - 123.0) < 1e-9


def test_against_pvlib_if_available():
    pvlib = pytest.importorskip("pvlib")
    import pandas as pd
    lat, lon = RIMINI
    times = pd.date_range("2026-07-15 04:00", "2026-07-15 19:00", freq="30min", tz="UTC")
    ref = pvlib.solarposition.get_solarposition(times, lat, lon)
    for t, row in ref.iterrows():
        if row["apparent_elevation"] < 2:
            continue
        sp = sun_position(t.to_pydatetime(), lat, lon)
        assert abs(sp.elevation_deg - row["apparent_elevation"]) < 0.05, t
        daz = abs(((sp.azimuth_deg - row["azimuth"]) + 180) % 360 - 180)
        assert daz < 0.05, t
