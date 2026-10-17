"""Algoritmo di controllo: data la direzione del sole e la zona da coprire,
trova la posa dei giunti che la copre rispettando i limiti meccanici.

Strategia
---------
1. **Soluzione analitica** (veloce, usata anche sul microcontrollore): il
   centro del tettuccio deve stare sulla retta che dal centro del bersaglio T
   va verso il sole, a distanza L dalla cima del palo P.  E' l'intersezione
   retta-sfera: un'equazione di 2 grado.  Il tettuccio viene orientato verso
   il sole (ombra massima, ellisse allungata lungo l'azimut solare).
2. **Saturazione**: se la soluzione analitica viola un limite (theta_max,
   quota minima, ...) si sfrutta la ridondanza: inclinazione del tettuccio e
   (se c'e') braccio telescopico.
3. **Ottimizzazione numerica** (Nelder-Mead multi-start) del *margine*:
   ``margin = 1 - max rho`` sui punti del bordo del bersaglio, con penalita'
   sui vincoli.  margin >= 0 significa cerchio bersaglio interamente in ombra.
   Quando la copertura totale e' impossibile l'ottimizzatore massimizza la
   frazione coperta (ombra "il piu' possibile sul bersaglio").

Pianificazione giornaliera con isteresi: l'ombrellone si muove solo quando il
margine scende sotto una soglia, cosi' chi dorme non sente motori ogni minuto.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

import numpy as np
from scipy.optimize import minimize

from .geometry import Umbrella, Pose, Target, evaluate, forward_kinematics, Evaluation
from .solar import sun_position, SunPosition, vector_to_elev_az

_DEG = math.pi / 180.0


# ----------------------------------------------------------------------------
# soluzione analitica
# ----------------------------------------------------------------------------
def analytic_pose(u: Umbrella, s: np.ndarray, t: Target, L: float | None = None,
                  face_sun: bool = True, offset: float | None = None) -> Pose | None:
    """Posa che mette il centro dell'ombra esattamente sul centro del bersaglio.

    Restituisce ``None`` se la retta T->sole non interseca la sfera di raggio L
    attorno alla cima del palo (bersaglio irraggiungibile a prescindere dai
    fine corsa).  Non controlla i limiti dei giunti: usare ``evaluate``.
    """
    L = L if L is not None else u.L
    e_off = offset if offset is not None else u.canopy_offset
    P = np.array([0.0, 0.0, u.H])
    T3 = np.array([t.x, t.y, 0.0])
    s = np.asarray(s, dtype=float)
    # Il centro del tettuccio C = T3 + lam*s deve soddisfare |E - P| = L dove
    # E = C - offset*horiz(alpha).  Per offset=0: |T3 + lam s - P|^2 = L^2.
    # Con sbalzo si risolve iterativamente (converge in 2-3 passi).
    off = np.zeros(3)
    alpha = None
    for _ in range(6 if e_off else 1):
        d = T3 - P - off
        b = 2.0 * float(d @ s)
        c = float(d @ d) - L * L
        disc = b * b - 4.0 * c
        if disc < 0:
            return None
        lam = (-b + math.sqrt(disc)) / 2.0          # radice con C piu' in alto / verso il sole
        if lam <= 0:
            return None
        E = T3 + lam * s - off
        v = E - P
        alpha = math.degrees(math.atan2(v[0], v[1])) % 360.0
        if e_off:
            off = e_off * np.array([math.sin(alpha * _DEG), math.cos(alpha * _DEG), 0.0])
    theta = math.degrees(math.acos(max(-1.0, min(1.0, v[2] / L))))
    if face_sun:
        elev, az = vector_to_elev_az(s)
        beta, gamma = 90.0 - elev, az
    else:
        beta, gamma = 0.0, 0.0
    return Pose(alpha, theta, beta, gamma, L if u.telescopic else None,
                e_off if u.mobile_offset else None)


# ----------------------------------------------------------------------------
# ottimizzazione numerica
# ----------------------------------------------------------------------------
@dataclass
class Solution:
    pose: Pose
    eval: Evaluation
    method: str
    sun_elev_deg: float
    sun_az_deg: float

    @property
    def full_coverage(self) -> bool:
        return self.eval.feasible and self.eval.margin >= 0.0


def _unpack(x: np.ndarray, u: Umbrella) -> Pose:
    L = float(x[4]) if u.telescopic else None
    off = float(x[5]) if u.mobile_offset else None
    return Pose(float(x[0]) % 360.0, float(x[1]), float(x[2]), float(x[3]) % 360.0, L, off)


def _clip_pose(p: Pose, u: Umbrella) -> Pose:
    return Pose(p.alpha_deg, min(max(p.theta_deg, 0.0), u.theta_max_deg),
                min(max(p.beta_deg, 0.0), u.beta_max_deg), p.gamma_deg,
                None if not u.telescopic else min(max(p.L, u.L_min), u.L_max),
                None if not u.mobile_offset else min(max(p.offset, u.offset_min), u.offset_max))


def _objective(x: np.ndarray, u: Umbrella, s: np.ndarray, t: Target, prev: Pose | None,
               w_move: float) -> float:
    p = _unpack(x, u)
    # penalita' morbide per i vincoli dei giunti (cosi' Nelder-Mead resta nel dominio)
    pen = 0.0
    pen += max(0.0, -p.theta_deg) + max(0.0, p.theta_deg - u.theta_max_deg)
    pen += max(0.0, -p.beta_deg) + max(0.0, p.beta_deg - u.beta_max_deg)
    if u.telescopic:
        pen += 10.0 * (max(0.0, u.L_min - p.L) + max(0.0, p.L - u.L_max))
    if u.mobile_offset:
        pen += 10.0 * (max(0.0, u.offset_min - p.offset) + max(0.0, p.offset - u.offset_max))
    pc = _clip_pose(p, u)
    ev = evaluate(u, pc, s, t, n_disk=200, n_boundary=48)
    fk = ev.fk
    # quota minima e collisione: penalita' proporzionale alla violazione
    pen += 5.0 * max(0.0, u.h_min - ev.z_low)
    if any("collisione" in v for v in ev.violations):
        pen += 2.0
    # obiettivo: max rho sul bordo (<=1 significa coperto) + frazione scoperta
    f = max(0.0, -ev.margin) * 3.0 + (1.0 - ev.coverage) + 0.2 * max(0.0, -ev.margin)
    # quando e' tutto coperto, cerchiamo comunque di aumentare il margine, ma poco
    f += -0.05 * min(ev.margin, 0.5) if ev.margin > 0 else 0.0
    if prev is not None and w_move > 0:
        f += w_move * p.joint_distance_deg(prev) / 360.0
    return f + 10.0 * pen


def solve_pose(u: Umbrella, s: np.ndarray, t: Target, prev: Pose | None = None,
               w_move: float = 0.0, n_starts: int = 6, seed: int = 0) -> Solution:
    """Trova la posa migliore per il sole ``s`` e il bersaglio ``t``."""
    elev, az = vector_to_elev_az(s)
    if s[2] <= 1e-6:
        p = prev or Pose(az, 0.0, 0.0, az)
        return Solution(p, evaluate(u, p, np.array([0, 0, 1.0]), t), "sole-sotto-orizzonte", elev, az)

    best: Solution | None = None

    # 1) analitica, campionando i gradi di liberta' lineari (braccio telescopico, sbalzo mobile)
    Ls = list(np.linspace(u.L_min, u.L_max, 5)) if u.telescopic else [None]
    offs = list(np.linspace(u.offset_min, u.offset_max, 5)) if u.mobile_offset else [None]
    for L in Ls:
        for off in offs:
            for face in (True, False):
                p = analytic_pose(u, s, t, L, face_sun=face, offset=off)
                if p is None:
                    continue
                if p.theta_deg > u.theta_max_deg:
                    continue
                # satura beta al limite se serve
                p.beta_deg = min(p.beta_deg, u.beta_max_deg)
                ev = evaluate(u, p, s, t)
                cand = Solution(p, ev, "analitica", elev, az)
                if ev.feasible and ev.margin >= 0 and (best is None or ev.margin > best.eval.margin):
                    best = cand
    if best is not None and (prev is None or w_move == 0.0):
        return best

    # 2) numerica multi-start
    rng = np.random.default_rng(seed)
    starts = []
    base_alpha = az
    if t.x or t.y:
        # il braccio deve puntare circa dal palo verso il bersaglio spostato verso il sole
        base_alpha = math.degrees(math.atan2(t.x + 2 * s[0], t.y + 2 * s[1])) % 360.0
    L0 = u.L if not u.telescopic else u.L_max
    O0 = u.canopy_offset if not u.mobile_offset else u.offset_max
    starts.append([base_alpha, u.theta_max_deg, min(90 - elev, u.beta_max_deg), az, L0, O0])
    starts.append([base_alpha, u.theta_max_deg * 0.6, min(90 - elev, u.beta_max_deg) * 0.5, az, L0, O0])
    starts.append([az, u.theta_max_deg * 0.8, 0.0, az, L0, O0])
    if prev is not None:
        starts.append([prev.alpha_deg, prev.theta_deg, prev.beta_deg, prev.gamma_deg,
                       prev.L if prev.L is not None else L0,
                       prev.offset if prev.offset is not None else O0])
    while len(starts) < n_starts:
        starts.append([base_alpha + rng.uniform(-40, 40), rng.uniform(0, u.theta_max_deg),
                       rng.uniform(0, u.beta_max_deg), az + rng.uniform(-30, 30),
                       L0 if not u.telescopic else rng.uniform(u.L_min, u.L_max),
                       O0 if not u.mobile_offset else rng.uniform(u.offset_min, u.offset_max)])

    for x0 in starts:
        res = minimize(_objective, np.array(x0, dtype=float), args=(u, s, t, prev, w_move),
                       method="Nelder-Mead",
                       options={"xatol": 0.05, "fatol": 1e-4, "maxiter": 1500, "maxfev": 3000})
        p = _clip_pose(_unpack(res.x, u), u)
        ev = evaluate(u, p, s, t)
        cand = Solution(p, ev, "numerica", elev, az)
        if best is None or _better(cand, best):
            best = cand
    assert best is not None
    return best


def _better(a: Solution, b: Solution) -> bool:
    """Ordine: fattibile > non fattibile; poi copertura totale; poi margine/copertura."""
    if a.eval.feasible != b.eval.feasible:
        return a.eval.feasible
    fa, fb = a.eval.margin >= 0, b.eval.margin >= 0
    if fa != fb:
        return fa
    if fa:
        return a.eval.margin > b.eval.margin
    if abs(a.eval.coverage - b.eval.coverage) > 1e-3:
        return a.eval.coverage > b.eval.coverage
    return a.eval.margin > b.eval.margin


# ----------------------------------------------------------------------------
# pianificazione giornaliera
# ----------------------------------------------------------------------------
@dataclass
class Step:
    time: datetime
    sun: SunPosition
    ideal: Solution          # posa ottima istantanea
    held: Pose               # posa effettivamente tenuta (con isteresi)
    held_eval: Evaluation
    moved: bool


@dataclass
class DayPlan:
    umbrella: Umbrella
    target: Target
    steps: list[Step] = field(default_factory=list)

    # ---- metriche ---------------------------------------------------------
    def times(self):
        return [s.time for s in self.steps]

    def full_coverage_mask(self) -> np.ndarray:
        return np.array([s.ideal.full_coverage for s in self.steps])

    def coverage_window(self) -> tuple[datetime, datetime] | None:
        """Primo e ultimo istante in cui la copertura TOTALE e' possibile."""
        m = self.full_coverage_mask()
        if not m.any():
            return None
        idx = np.where(m)[0]
        return self.steps[idx[0]].time, self.steps[idx[-1]].time

    def coverage_gaps(self) -> list[tuple[datetime, datetime]]:
        """Intervalli diurni (sole > 0) in cui la copertura totale NON e' possibile."""
        gaps = []
        start = None
        for st in self.steps:
            ok = st.ideal.full_coverage
            if not ok and start is None:
                start = st.time
            if ok and start is not None:
                gaps.append((start, st.time))
                start = None
        if start is not None:
            gaps.append((start, self.steps[-1].time))
        return gaps

    def n_moves(self) -> int:
        return sum(1 for s in self.steps if s.moved)

    def total_travel_deg(self) -> float:
        tot = 0.0
        for a, b in zip(self.steps, self.steps[1:]):
            if b.moved:
                tot += b.held.joint_distance_deg(a.held)
        return tot

    def summary(self) -> dict:
        w = self.coverage_window()
        cov = np.array([s.held_eval.coverage for s in self.steps])
        return {
            "finestra_copertura_totale": w,
            "buchi": self.coverage_gaps(),
            "ore_sole": len(self.steps) * self._step_minutes() / 60.0,
            "ore_copertura_totale_ideale": self.full_coverage_mask().sum() * self._step_minutes() / 60.0,
            "copertura_media_tenuta": float(cov.mean()) if len(cov) else 0.0,
            "copertura_minima_tenuta": float(cov.min()) if len(cov) else 0.0,
            "movimenti": self.n_moves(),
            "corsa_totale_gradi": self.total_travel_deg(),
        }

    def _step_minutes(self) -> float:
        if len(self.steps) < 2:
            return 0.0
        return (self.steps[1].time - self.steps[0].time).total_seconds() / 60.0


def plan_day(u: Umbrella, t: Target, date: datetime, lat: float, lon: float,
             tz: timezone | None = None, step_minutes: int = 5, min_elev_deg: float = 5.0,
             margin_move: float = 0.05, min_hold_minutes: float = 10.0) -> DayPlan:
    """Simula una giornata intera.

    * ``margin_move``: l'ombrellone si muove quando il margine della posa tenuta
      scende sotto questa frazione del raggio bersaglio (0.05 = 5 cm su 1 m).
    * ``min_hold_minutes``: tempo minimo fra due movimenti (silenzio per chi dorme),
      salvo che la copertura stia crollando.
    """
    tz = tz or timezone.utc
    start = datetime(date.year, date.month, date.day, tzinfo=tz)
    plan = DayPlan(u, t)
    held: Pose | None = None
    last_move: datetime | None = None
    tt = start
    while tt < start + timedelta(days=1):
        sp = sun_position(tt, lat, lon)
        if sp.elevation_deg >= min_elev_deg:
            s = sp.vector_enu
            ideal = solve_pose(u, s, t, prev=held, w_move=0.02 if held else 0.0)
            if held is None:
                held, moved = ideal.pose, True
                last_move = tt
            else:
                ev_held = evaluate(u, held, s, t)
                waited = (tt - last_move).total_seconds() / 60.0 if last_move else 1e9
                need = (ev_held.margin < margin_move) or (not ev_held.feasible)
                urgent = ev_held.coverage < 0.97
                better = ideal.eval.coverage > ev_held.coverage + 0.02 or ideal.eval.margin > ev_held.margin + 0.02
                if need and better and (waited >= min_hold_minutes or urgent):
                    held, moved = ideal.pose, True
                    last_move = tt
                else:
                    moved = False
            plan.steps.append(Step(tt, sp, ideal, held, evaluate(u, held, s, t), moved))
        tt += timedelta(minutes=step_minutes)
    return plan


# ----------------------------------------------------------------------------
# analisi dei limiti
# ----------------------------------------------------------------------------
def min_elevation_for_full_coverage(u: Umbrella, t: Target, az_deg: float = 180.0,
                                    elev_grid: np.ndarray | None = None) -> float | None:
    """Elevazione solare minima (gradi) a cui la copertura totale e' possibile.

    Scansiona tutta la griglia (possono esserci "buchi" anche con sole alto,
    ad esempio con sbalzo fisso e zona vicina al palo); ``None`` se mai.
    """
    oks = feasible_elevations(u, t, az_deg, elev_grid)
    return min(oks) if oks else None


def feasible_elevations(u: Umbrella, t: Target, az_deg: float = 180.0,
                        elev_grid: np.ndarray | None = None) -> list[float]:
    """Elevazioni della griglia (gradi) in cui la copertura totale e' possibile."""
    from .solar import sun_vector_enu
    grid = elev_grid if elev_grid is not None else np.arange(89.0, 4.0, -1.0)
    oks = []
    for e in grid:
        sol = solve_pose(u, sun_vector_enu(float(e), az_deg), t, n_starts=4)
        if sol.full_coverage:
            oks.append(float(e))
    return oks


def full_coverage_hours(u: Umbrella, t: Target, date: datetime, lat: float, lon: float,
                        tz: timezone | None = None, step_minutes: int = 15,
                        min_elev_deg: float = 5.0) -> dict:
    """Ore di copertura totale in un giorno reale (senza isteresi): finestra e buchi."""
    from .solar import sun_path
    path = sun_path(date, lat, lon, step_minutes, tz)
    ok_times = []
    for tt, sp in path:
        if sp.elevation_deg < min_elev_deg:
            continue
        sol = solve_pose(u, sp.vector_enu, t, n_starts=4)
        if sol.full_coverage:
            ok_times.append(tt)
    gaps = []
    for a, b in zip(ok_times, ok_times[1:]):
        if (b - a).total_seconds() / 60.0 > step_minutes * 1.5:
            gaps.append((a + timedelta(minutes=step_minutes), b))
    return {"ore": len(ok_times) * step_minutes / 60.0,
            "da": ok_times[0] if ok_times else None, "a": ok_times[-1] if ok_times else None,
            "buchi": gaps}
