"""Posizione del sole (algoritmo NOAA / Meeus semplificato).

Precisione tipica: < 0.05 gradi su elevazione e azimut per gli anni 1900-2100,
ampiamente sufficiente per un ombrellone (il disco solare e' largo 0.53 gradi e
il margine geometrico del progetto e' di decine di centimetri).

Convenzioni
-----------
* Istanti in UTC (``datetime`` con ``tzinfo`` oppure naive = gia' UTC).
* Latitudine positiva a Nord, longitudine positiva a Est (gradi).
* Azimut misurato da Nord, in senso orario (N=0, E=90, S=180, W=270).
* Elevazione: angolo sopra l'orizzonte (gia' corretta per la rifrazione).
* Vettore solare in terna ENU (x=Est, y=Nord, z=Su): punta VERSO il sole.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import numpy as np

_DEG = math.pi / 180.0


@dataclass(frozen=True)
class SunPosition:
    elevation_deg: float          # gradi sopra l'orizzonte (con rifrazione)
    azimuth_deg: float            # gradi da Nord, orario
    declination_deg: float
    equation_of_time_min: float   # minuti
    hour_angle_deg: float

    @property
    def vector_enu(self) -> np.ndarray:
        """Versore che punta verso il sole in terna ENU."""
        return sun_vector_enu(self.elevation_deg, self.azimuth_deg)

    @property
    def is_up(self) -> bool:
        return self.elevation_deg > 0.0


def sun_vector_enu(elevation_deg: float, azimuth_deg: float) -> np.ndarray:
    h = elevation_deg * _DEG
    a = azimuth_deg * _DEG
    return np.array([math.cos(h) * math.sin(a), math.cos(h) * math.cos(a), math.sin(h)])


def vector_to_elev_az(v: np.ndarray) -> tuple[float, float]:
    v = np.asarray(v, dtype=float)
    v = v / np.linalg.norm(v)
    elev = math.degrees(math.asin(max(-1.0, min(1.0, v[2]))))
    az = math.degrees(math.atan2(v[0], v[1])) % 360.0
    return elev, az


def _to_utc(t: datetime) -> datetime:
    if t.tzinfo is None:
        return t.replace(tzinfo=timezone.utc)
    return t.astimezone(timezone.utc)


def julian_day(t: datetime) -> float:
    t = _to_utc(t)
    y, m = t.year, t.month
    d = t.day + (t.hour + (t.minute + (t.second + t.microsecond / 1e6) / 60.0) / 60.0) / 24.0
    if m <= 2:
        y -= 1
        m += 12
    a = y // 100
    b = 2 - a + a // 4
    return math.floor(365.25 * (y + 4716)) + math.floor(30.6001 * (m + 1)) + d + b - 1524.5


def _refraction_deg(elev_deg: float) -> float:
    """Correzione per rifrazione atmosferica (formula NOAA), in gradi."""
    if elev_deg > 85.0:
        return 0.0
    te = math.tan(elev_deg * _DEG)
    if elev_deg > 5.0:
        r = 58.1 / te - 0.07 / te**3 + 0.000086 / te**5
    elif elev_deg > -0.575:
        r = 1735.0 + elev_deg * (-518.2 + elev_deg * (103.4 + elev_deg * (-12.79 + elev_deg * 0.711)))
    else:
        r = -20.774 / te
    return r / 3600.0


def sun_position(t: datetime, lat_deg: float, lon_deg: float) -> SunPosition:
    """Posizione del sole all'istante ``t`` (UTC) per l'osservatore (lat, lon)."""
    jd = julian_day(t)
    jc = (jd - 2451545.0) / 36525.0  # secoli giuliani da J2000

    gml = (280.46646 + jc * (36000.76983 + jc * 0.0003032)) % 360.0        # long. media geom.
    gma = 357.52911 + jc * (35999.05029 - 0.0001537 * jc)                   # anomalia media
    ecc = 0.016708634 - jc * (0.000042037 + 0.0000001267 * jc)
    gma_r = gma * _DEG
    ceq = (math.sin(gma_r) * (1.914602 - jc * (0.004817 + 0.000014 * jc))
           + math.sin(2 * gma_r) * (0.019993 - 0.000101 * jc)
           + math.sin(3 * gma_r) * 0.000289)                                # equazione del centro
    true_long = gml + ceq
    omega = 125.04 - 1934.136 * jc
    app_long = true_long - 0.00569 - 0.00478 * math.sin(omega * _DEG)
    mean_obliq = 23.0 + (26.0 + (21.448 - jc * (46.815 + jc * (0.00059 - jc * 0.001813))) / 60.0) / 60.0
    obliq = mean_obliq + 0.00256 * math.cos(omega * _DEG)

    decl = math.degrees(math.asin(math.sin(obliq * _DEG) * math.sin(app_long * _DEG)))

    y = math.tan(obliq * _DEG / 2.0) ** 2
    eot = 4.0 * math.degrees(
        y * math.sin(2 * gml * _DEG)
        - 2 * ecc * math.sin(gma_r)
        + 4 * ecc * y * math.sin(gma_r) * math.cos(2 * gml * _DEG)
        - 0.5 * y * y * math.sin(4 * gml * _DEG)
        - 1.25 * ecc * ecc * math.sin(2 * gma_r)
    )  # minuti

    tu = _to_utc(t)
    minutes_utc = tu.hour * 60.0 + tu.minute + tu.second / 60.0 + tu.microsecond / 6e7
    true_solar_min = (minutes_utc + eot + 4.0 * lon_deg) % 1440.0
    ha = true_solar_min / 4.0 - 180.0  # angolo orario, gradi (negativo di mattina)

    lat_r, dec_r, ha_r = lat_deg * _DEG, decl * _DEG, ha * _DEG
    cos_zen = math.sin(lat_r) * math.sin(dec_r) + math.cos(lat_r) * math.cos(dec_r) * math.cos(ha_r)
    cos_zen = max(-1.0, min(1.0, cos_zen))
    zen = math.degrees(math.acos(cos_zen))
    elev_geom = 90.0 - zen
    elev = elev_geom + _refraction_deg(elev_geom)

    sin_zen = math.sin(zen * _DEG)
    if sin_zen < 1e-9:
        az = 180.0
    else:
        cos_az = (math.sin(lat_r) * cos_zen - math.sin(dec_r)) / (math.cos(lat_r) * sin_zen)
        cos_az = max(-1.0, min(1.0, cos_az))
        az = math.degrees(math.acos(cos_az))
        if ha > 0:
            az = (az + 180.0) % 360.0
        else:
            az = (540.0 - az) % 360.0
    return SunPosition(elev, az, decl, eot, ha)


def sun_path(date: datetime, lat_deg: float, lon_deg: float, step_minutes: int = 10,
             tz: timezone | None = None) -> list[tuple[datetime, SunPosition]]:
    """Posizioni del sole lungo un giorno (solo quando e' sopra l'orizzonte).

    ``date`` indica il giorno (ora ignorata); ``tz`` e' il fuso locale in cui
    restituire gli orari (default: UTC).
    """
    tz = tz or timezone.utc
    start = datetime(date.year, date.month, date.day, tzinfo=tz)
    out = []
    t = start
    while t < start + timedelta(days=1):
        sp = sun_position(t, lat_deg, lon_deg)
        if sp.is_up:
            out.append((t, sp))
        t += timedelta(minutes=step_minutes)
    return out


def solar_noon(date: datetime, lat_deg: float, lon_deg: float, tz: timezone | None = None) -> datetime:
    """Istante del mezzogiorno solare locale (massima elevazione)."""
    tz = tz or timezone.utc
    base = datetime(date.year, date.month, date.day, 12, tzinfo=timezone.utc)
    sp = sun_position(base, lat_deg, lon_deg)
    # mezzogiorno solare: true_solar_min = 720  ->  minutes_utc = 720 - eot - 4*lon
    minutes_utc = (720.0 - sp.equation_of_time_min - 4.0 * lon_deg) % 1440.0
    noon = datetime(date.year, date.month, date.day, tzinfo=timezone.utc) + timedelta(minutes=minutes_utc)
    return noon.astimezone(tz)
