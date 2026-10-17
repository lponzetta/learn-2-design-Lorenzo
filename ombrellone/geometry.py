"""Geometria dell'ombrellone: cinematica, proiezione dell'ombra, copertura.

Modello meccanico (terna ENU: x=Est, y=Nord, z=Su; origine alla base del palo)
---------------------------------------------------------------------------------
* Palo fisso verticale di altezza ``H``: la sua cima e' il punto P = (0, 0, H).
* Snodo a 2 gradi di liberta' in P: rotazione in azimut ``alpha`` (da Nord,
  orario) e inclinazione ``theta`` rispetto alla verticale.
* Braccio rigido di lunghezza ``L`` (opzionalmente telescopico fra L_min e L_max).
* Testa a 2 gradi di liberta' in cima al braccio: il tettuccio (disco di raggio
  ``R``) ha normale inclinata di ``beta`` rispetto alla verticale, nella
  direzione di azimut ``gamma``.  Il centro del disco puo' essere spostato di
  ``canopy_offset`` lungo la direzione orizzontale del braccio (sbalzo).

L'ombra di un disco illuminato da raggi paralleli e' un'ellisse sul piano
z=0.  La zona da proteggere e' un cerchio di raggio ``r_t`` centrato in T.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, replace

import numpy as np

_DEG = math.pi / 180.0


@dataclass(frozen=True)
class Umbrella:
    """Parametri geometrici e limiti meccanici (metri, gradi)."""
    H: float = 2.0                 # altezza palo fisso
    L: float = 1.6                 # lunghezza braccio (nominale)
    R: float = 1.5                 # raggio tettuccio
    theta_max_deg: float = 70.0    # inclinazione massima del braccio dalla verticale
    beta_max_deg: float = 70.0     # inclinazione massima del tettuccio dalla verticale
    h_min: float = 1.6             # quota minima del bordo piu' basso del tettuccio
    canopy_offset: float = 0.0     # sbalzo del centro tettuccio lungo il braccio (orizz.)
    L_min: float | None = None     # braccio telescopico: lunghezza minima
    L_max: float | None = None     # braccio telescopico: lunghezza massima
    offset_min: float | None = None  # sbalzo mobile (carrello): minimo
    offset_max: float | None = None  # sbalzo mobile (carrello): massimo
    pole_radius: float = 0.04      # raggio palo (per il controllo collisioni)
    alpha_min_deg: float = -1e9    # fine corsa azimut (default: rotazione libera)
    alpha_max_deg: float = 1e9

    @property
    def telescopic(self) -> bool:
        return self.L_min is not None and self.L_max is not None and self.L_max > self.L_min

    @property
    def mobile_offset(self) -> bool:
        return (self.offset_min is not None and self.offset_max is not None
                and self.offset_max > self.offset_min)

    def with_(self, **kw) -> "Umbrella":
        return replace(self, **kw)


@dataclass
class Pose:
    """Configurazione dei giunti (gradi, metri)."""
    alpha_deg: float = 0.0   # azimut braccio
    theta_deg: float = 0.0   # inclinazione braccio dalla verticale
    beta_deg: float = 0.0    # inclinazione tettuccio dalla verticale
    gamma_deg: float = 0.0   # azimut della normale del tettuccio
    L: float | None = None   # lunghezza braccio (None = nominale)
    offset: float | None = None  # sbalzo (None = nominale)

    def as_array(self) -> np.ndarray:
        return np.array([self.alpha_deg, self.theta_deg, self.beta_deg, self.gamma_deg,
                         self.L if self.L is not None else np.nan,
                         self.offset if self.offset is not None else np.nan])

    def joint_distance_deg(self, other: "Pose") -> float:
        """Somma dei movimenti angolari fra due pose (per stimare consumo/rumore)."""
        da = abs(((self.alpha_deg - other.alpha_deg + 180.0) % 360.0) - 180.0)
        dg = abs(((self.gamma_deg - other.gamma_deg + 180.0) % 360.0) - 180.0)
        return da + abs(self.theta_deg - other.theta_deg) + abs(self.beta_deg - other.beta_deg) + dg


@dataclass
class Target:
    """Zona da tenere in ombra: cerchio di raggio ``r`` centrato in (x, y)."""
    x: float = 0.0
    y: float = 0.0
    r: float = 1.0

    @property
    def center(self) -> np.ndarray:
        return np.array([self.x, self.y])


def horiz_unit(azimuth_deg: float) -> np.ndarray:
    a = azimuth_deg * _DEG
    return np.array([math.sin(a), math.cos(a), 0.0])


def direction(azimuth_deg: float, tilt_from_vertical_deg: float) -> np.ndarray:
    """Versore con azimut dato e inclinazione dalla verticale."""
    a, t = azimuth_deg * _DEG, tilt_from_vertical_deg * _DEG
    return np.array([math.sin(t) * math.sin(a), math.sin(t) * math.cos(a), math.cos(t)])


def forward_kinematics(u: Umbrella, p: Pose) -> dict:
    """Restituisce i punti notevoli della struttura per la posa ``p``."""
    L = p.L if p.L is not None else u.L
    off = p.offset if p.offset is not None else u.canopy_offset
    P = np.array([0.0, 0.0, u.H])
    arm_dir = direction(p.alpha_deg, p.theta_deg)
    E = P + L * arm_dir                                     # estremita' del braccio
    C = E + off * horiz_unit(p.alpha_deg)                   # centro tettuccio
    n = direction(p.gamma_deg, p.beta_deg)                  # normale tettuccio
    return {"P": P, "E": E, "C": C, "n": n, "arm_dir": arm_dir, "L": L, "offset": off}


def canopy_basis(n: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Due versori ortonormali nel piano del disco di normale ``n``."""
    n = n / np.linalg.norm(n)
    ref = np.array([0.0, 0.0, 1.0]) if abs(n[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
    u1 = np.cross(n, ref)
    u1 /= np.linalg.norm(u1)
    u2 = np.cross(n, u1)
    return u1, u2


def canopy_rim(C: np.ndarray, n: np.ndarray, R: float, k: int = 64) -> np.ndarray:
    """Punti sul bordo del tettuccio (k x 3)."""
    u1, u2 = canopy_basis(n)
    phi = np.linspace(0, 2 * np.pi, k, endpoint=False)
    return C[None, :] + R * (np.cos(phi)[:, None] * u1[None, :] + np.sin(phi)[:, None] * u2[None, :])


def shadow_ellipse(C: np.ndarray, n: np.ndarray, R: float, s: np.ndarray):
    """Ombra del disco (C, n, R) proiettata lungo i raggi solari su z=0.

    ``s`` e' il versore verso il sole (s_z > 0).  Restituisce (G, M):
    * G: centro dell'ellisse (2,)
    * M: matrice 2x2 tale che il bordo e' G + M @ [cos phi, sin phi].
    Un punto Q del piano e' dentro l'ombra se ||M^-1 (Q - G)|| <= 1.
    """
    s = np.asarray(s, dtype=float)
    if s[2] <= 1e-6:
        raise ValueError("il sole deve essere sopra l'orizzonte (s_z > 0)")

    def proj(pt3: np.ndarray) -> np.ndarray:
        return (pt3 - s * (pt3[2] / s[2]))[:2]

    u1, u2 = canopy_basis(n)
    G = proj(C)
    # la proiezione e' affine: i vettori del piano si proiettano linearmente
    M = np.column_stack([proj(C + R * u1) - G, proj(C + R * u2) - G])
    return G, M


def ellipse_axes(M: np.ndarray) -> tuple[float, float, float]:
    """Semiassi (a >= b) e orientazione (gradi da Nord, orario) dell'ellisse G + M[cos, sin]."""
    U, S, Vt = np.linalg.svd(M)
    major = U[:, 0]
    ang = math.degrees(math.atan2(major[0], major[1])) % 180.0
    return float(S[0]), float(S[1]), ang


def target_boundary(t: Target, k: int = 72) -> np.ndarray:
    phi = np.linspace(0, 2 * np.pi, k, endpoint=False)
    return np.column_stack([t.x + t.r * np.cos(phi), t.y + t.r * np.sin(phi)])


def target_disk_samples(t: Target, n: int = 400) -> np.ndarray:
    """Campionamento a girasole del disco bersaglio (per la frazione coperta)."""
    i = np.arange(n) + 0.5
    rr = t.r * np.sqrt(i / n)
    ph = i * math.pi * (3.0 - math.sqrt(5.0))
    return np.column_stack([t.x + rr * np.cos(ph), t.y + rr * np.sin(ph)])


def normalized_radius(points: np.ndarray, G: np.ndarray, M: np.ndarray) -> np.ndarray:
    """rho = ||M^-1 (Q - G)||: rho <= 1 significa punto in ombra."""
    try:
        Minv = np.linalg.inv(M)
    except np.linalg.LinAlgError:
        return np.full(len(points), np.inf)
    d = (points - G[None, :]) @ Minv.T
    return np.hypot(d[:, 0], d[:, 1])


@dataclass
class Evaluation:
    """Risultato della valutazione di una posa."""
    coverage: float            # frazione [0,1] del disco bersaglio in ombra
    margin: float              # 1 - max rho sul bordo: >0 copertura totale con margine
    margin_m: float            # margine approssimato in metri (margin * r_t)
    z_low: float               # quota del punto piu' basso del tettuccio
    feasible: bool             # rispetta tutti i vincoli meccanici
    violations: list[str] = field(default_factory=list)
    G: np.ndarray | None = None
    M: np.ndarray | None = None
    fk: dict | None = None


def check_constraints(u: Umbrella, p: Pose, fk: dict) -> tuple[list[str], float]:
    v: list[str] = []
    if p.theta_deg < -1e-9 or p.theta_deg > u.theta_max_deg + 1e-9:
        v.append(f"theta={p.theta_deg:.1f} fuori [0,{u.theta_max_deg}]")
    if p.beta_deg < -1e-9 or p.beta_deg > u.beta_max_deg + 1e-9:
        v.append(f"beta={p.beta_deg:.1f} fuori [0,{u.beta_max_deg}]")
    if not (u.alpha_min_deg - 1e-9 <= p.alpha_deg <= u.alpha_max_deg + 1e-9):
        v.append("alpha fuori fine corsa")
    L = fk["L"]
    if u.telescopic:
        if L < u.L_min - 1e-9 or L > u.L_max + 1e-9:
            v.append(f"L={L:.2f} fuori [{u.L_min},{u.L_max}]")
    if u.mobile_offset:
        off = fk["offset"]
        if off < u.offset_min - 1e-9 or off > u.offset_max + 1e-9:
            v.append(f"sbalzo={off:.2f} fuori [{u.offset_min},{u.offset_max}]")
    C, n = fk["C"], fk["n"]
    sin_tilt = math.sqrt(max(0.0, 1.0 - n[2] ** 2))
    z_low = C[2] - u.R * sin_tilt
    if z_low < u.h_min - 1e-9:
        v.append(f"bordo tettuccio a {z_low:.2f} m < h_min={u.h_min}")
    # collisione con il palo fisso: punti del bordo sotto la cima del palo
    rim = canopy_rim(C, n, u.R, 48)
    below = rim[rim[:, 2] < u.H]
    if len(below):
        dist = np.hypot(below[:, 0], below[:, 1])
        if dist.min() < u.pole_radius + 0.05:
            v.append("tettuccio in collisione con il palo")
    return v, z_low


def evaluate(u: Umbrella, p: Pose, s: np.ndarray, t: Target, n_disk: int = 400,
             n_boundary: int = 72) -> Evaluation:
    """Valuta copertura e vincoli per la posa ``p`` con sole in direzione ``s``."""
    fk = forward_kinematics(u, p)
    violations, z_low = check_constraints(u, p, fk)
    if s[2] <= 1e-6:
        return Evaluation(0.0, -np.inf, -np.inf, z_low, False, violations + ["sole sotto l'orizzonte"], fk=fk)
    G, M = shadow_ellipse(fk["C"], fk["n"], u.R, s)
    rho_b = normalized_radius(target_boundary(t, n_boundary), G, M)
    rho_d = normalized_radius(target_disk_samples(t, n_disk), G, M)
    margin = float(1.0 - rho_b.max())
    return Evaluation(
        coverage=float(np.mean(rho_d <= 1.0)),
        margin=margin,
        margin_m=margin * t.r,
        z_low=z_low,
        feasible=not violations,
        violations=violations,
        G=G, M=M, fk=fk,
    )
