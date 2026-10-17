"""Simulazione completa: giornata tipo, inviluppo dei limiti, meccanica,
materiali e FEM.  Genera le figure in ``docs/figure`` e un riepilogo in
``docs/risultati.json`` / ``docs/risultati.md``.

Uso:  python -m ombrellone.simulate [--fast]
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Ellipse

from .geometry import Umbrella, Target, Pose, evaluate, forward_kinematics, canopy_rim, ellipse_axes
from .planner import plan_day, solve_pose, min_elevation_for_full_coverage, DayPlan
from .solar import sun_position, sun_path, sun_vector_enu
from .mechanics import (MassModel, Tube, MATERIALS, worst_case_loads, required_base_mass,
                        size_motor, size_linear_actuator, arm_beam_check, material_sweep, frame_fem,
                        scale_report)

# palette (validata, vedi skill dataviz): blu, arancio, acqua, giallo, magenta, verde
C1, C2, C3, C4, C5, C6 = "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e6e4df"
plt.rcParams.update({"font.size": 10, "axes.edgecolor": INK2, "axes.labelcolor": INK2,
                     "xtick.color": INK2, "ytick.color": INK2, "axes.grid": True,
                     "grid.color": GRID, "grid.linewidth": 0.6, "axes.spines.top": False,
                     "axes.spines.right": False, "figure.dpi": 130, "savefig.bbox": "tight"})

ROOT = Path(__file__).resolve().parent.parent
FIG = ROOT / "docs" / "figure"
LAT, LON = 44.06, 12.57            # Rimini
TZ = timezone(timedelta(hours=2))  # ora legale italiana (CEST)
WIND_WORK = 8.0                    # m/s: vento massimo in esercizio (~29 km/h)
WIND_PARK = 15.0                   # m/s: vento di sopravvivenza in posizione di parcheggio


def hours(ts):
    return [t.hour + t.minute / 60 for t in ts]


def fmt(t):
    return t.strftime("%H:%M") if t else "-"


# ----------------------------------------------------------------------------
def fig_sun_paths():
    fig, ax = plt.subplots(1, 2, figsize=(10, 3.6))
    for d, col, lab in [(datetime(2026, 6, 21), C2, "21 giugno"), (datetime(2026, 7, 15), C1, "15 luglio"),
                        (datetime(2026, 9, 21), C3, "21 settembre")]:
        path = sun_path(d, LAT, LON, 10, TZ)
        ax[0].plot(hours([p[0] for p in path]), [p[1].elevation_deg for p in path], color=col, lw=2, label=lab)
        ax[1].plot(hours([p[0] for p in path]), [p[1].azimuth_deg for p in path], color=col, lw=2, label=lab)
    ax[0].axhline(44, color=INK2, ls="--", lw=1)
    ax[0].text(5.2, 45.5, "soglia copertura totale (progetto base) 44°", color=INK2, fontsize=8)
    ax[0].set(xlabel="ora locale (CEST)", ylabel="elevazione sole [°]", title="Elevazione del sole, Rimini")
    ax[1].set(xlabel="ora locale (CEST)", ylabel="azimut [° da Nord]", title="Azimut del sole")
    ax[0].legend(frameon=False)
    fig.savefig(FIG / "01_sole.png")
    plt.close(fig)


def top_view(ax, u: Umbrella, p: Pose, s, t: Target, title=""):
    ev = evaluate(u, p, s, t)
    reach = u.L + u.R + abs(u.canopy_offset) + 0.5
    ax.set_xlim(-reach, reach); ax.set_ylim(-reach, reach); ax.set_aspect("equal")
    if ev.G is not None:
        a, b, ang = ellipse_axes(ev.M)
        ax.add_patch(Ellipse(ev.G, 2 * a, 2 * b, angle=90 - ang, color=INK2, alpha=0.25, lw=0))
    ax.add_patch(Circle((t.x, t.y), t.r, fill=False, color=C6 if ev.margin >= 0 else C2, lw=2))
    fk = ev.fk
    ax.plot([0, fk["E"][0]], [0, fk["E"][1]], color=INK, lw=3)
    rim = canopy_rim(fk["C"], fk["n"], u.R, 72)
    ax.plot(rim[:, 0], rim[:, 1], color=C1, lw=1.2)
    ax.plot(0, 0, "o", color=INK, ms=6)
    ax.annotate("", xy=(s[0] * 1.2, s[1] * 1.2), xytext=(0, 0), arrowprops=dict(arrowstyle="->", color=C4, lw=2))
    ax.set_title(title, fontsize=9)
    ax.set_xticks([]); ax.set_yticks([])
    return ev


def fig_day(plan: DayPlan, name: str, title: str):
    st = plan.steps
    h = hours([s.time for s in st])
    fig, ax = plt.subplots(3, 1, figsize=(10, 8), sharex=True)
    ax[0].plot(h, [s.sun.elevation_deg for s in st], color=C4, lw=2, label="elevazione sole")
    ax[0].set_ylabel("elevazione sole [°]")
    ax[0].legend(frameon=False, loc="upper left")
    cov_h = [100 * s.held_eval.coverage for s in st]
    cov_i = [100 * s.ideal.eval.coverage for s in st]
    ax[1].fill_between(h, cov_h, 0, color=C3, alpha=0.25, lw=0)
    ax[1].plot(h, cov_h, color=C3, lw=2, label="copertura zona tenuta (con isteresi)")
    ax[1].plot(h, cov_i, color=C1, lw=1.2, ls="--", label="copertura massima possibile")
    mv = [s.time for s in st if s.moved]
    ax[1].plot(hours(mv), [102] * len(mv), "|", color=INK, ms=8, label=f"movimenti ({len(mv)})")
    ax[1].set_ylim(0, 106); ax[1].set_ylabel("zona in ombra [%]")
    ax[1].legend(frameon=False, loc="lower center", ncol=3, fontsize=8)
    w = plan.coverage_window()
    if w:
        for a in ax:
            a.axvspan(w[0].hour + w[0].minute / 60, w[1].hour + w[1].minute / 60, color=C6, alpha=0.06, lw=0)
    ax[2].plot(h, [s.held.theta_deg for s in st], color=C1, lw=2, label="theta braccio")
    ax[2].plot(h, [s.held.beta_deg for s in st], color=C2, lw=2, label="beta tettuccio")
    ax[2].plot(h, [((s.held.alpha_deg + 180) % 360) - 180 for s in st], color=C5, lw=2, label="alpha braccio (±180 da Nord)")
    ax[2].axhline(plan.umbrella.theta_max_deg, color=C1, ls=":", lw=1)
    ax[2].set_ylabel("giunti [°]"); ax[2].set_xlabel("ora locale (CEST)")
    ax[2].legend(frameon=False, ncol=3, fontsize=8)
    fig.suptitle(title, fontsize=11)
    fig.savefig(FIG / name)
    plt.close(fig)


def fig_snapshots(u: Umbrella, t: Target, date: datetime, name: str, title: str):
    hrs = [8, 10, 12, 14, 16, 18]
    fig, axs = plt.subplots(1, len(hrs), figsize=(2.3 * len(hrs), 2.8))
    for ax, hh in zip(axs, hrs):
        tt = datetime(date.year, date.month, date.day, hh, tzinfo=TZ)
        sp = sun_position(tt, LAT, LON)
        if sp.elevation_deg < 5:
            ax.set_title(f"{hh}:00 sole basso", fontsize=9); ax.axis("off"); continue
        sol = solve_pose(u, sp.vector_enu, t)
        ev = top_view(ax, u, sol.pose, sp.vector_enu, t,
                      f"{hh}:00  sole {sp.elevation_deg:.0f}°\ncopertura {100*ev_cov(sol):.0f}%")
    fig.suptitle(title + "  (grigio = ombra, cerchio = zona richiesta, freccia = sole)", fontsize=9)
    fig.savefig(FIG / name)
    plt.close(fig)


def ev_cov(sol):
    return sol.eval.coverage


def fig_side_view(u: Umbrella, t: Target, name: str):
    """Vista laterale nel piano verticale del sole per tre elevazioni."""
    fig, axs = plt.subplots(1, 3, figsize=(11, 3.6))
    for ax, e in zip(axs, (65, 45, 30)):
        s = sun_vector_enu(e, 180.0)
        sol = solve_pose(u, s, t)
        fk = sol.eval.fk
        # proiezione sul piano (y=Sud positivo a destra -> uso -y), z
        ax.plot([0, 0], [0, u.H], color=INK, lw=4)
        ax.plot([0, -fk["E"][1]], [u.H, fk["E"][2]], color=INK, lw=3)
        rim = canopy_rim(fk["C"], fk["n"], u.R, 72)
        ax.plot(-rim[:, 1], rim[:, 2], color=C1, lw=1.5)
        # raggi solari dai bordi del tettuccio al suolo
        for k in range(0, 72, 9):
            P0 = rim[k]
            lam = P0[2] / s[2]
            G = P0 - s * lam
            ax.plot([-P0[1], -G[1]], [P0[2], 0], color=C4, lw=0.6, alpha=0.7)
        ax.plot([-t.y - t.r, -t.y + t.r], [0.02, 0.02], color=C6 if sol.full_coverage else C2, lw=5, solid_capstyle="butt")
        ax.axhline(u.h_min, color=INK2, ls=":", lw=0.8)
        ax.set_aspect("equal"); ax.set_xlim(-2.5, 4.5); ax.set_ylim(0, 4)
        ax.set_title(f"sole a {e}° (Sud)  theta={sol.pose.theta_deg:.0f}°  beta={sol.pose.beta_deg:.0f}°\n"
                     f"copertura {100*sol.eval.coverage:.0f}%", fontsize=9)
        ax.set_xlabel("← Nord      metri      Sud →")
    axs[0].set_ylabel("quota [m]")
    fig.savefig(FIG / name)
    plt.close(fig)


def fig_limits(u: Umbrella, t: Target, fast: bool):
    """Elevazione minima per copertura totale in funzione di L (o sbalzo) e theta_max."""
    Ls = np.array([1.2, 1.6, 2.0, 2.4]) if fast else np.array([1.2, 1.4, 1.6, 1.8, 2.0, 2.2, 2.4])
    ths = np.array([50, 60, 70, 80]) if fast else np.array([50, 55, 60, 65, 70, 75, 80, 85])
    grid = np.arange(89, 14, -3.0) if fast else np.arange(89, 14, -2.0)
    Z = np.full((len(Ls), len(ths)), np.nan)
    for i, L in enumerate(Ls):
        for j, th in enumerate(ths):
            e = min_elevation_for_full_coverage(u.with_(L=float(L), theta_max_deg=float(th)), t, 180.0, grid)
            Z[i, j] = e if e is not None else np.nan
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    im = ax.imshow(Z, origin="lower", cmap="Blues_r", aspect="auto",
                   extent=[ths[0] - 2.5, ths[-1] + 2.5, Ls[0] - 0.1, Ls[-1] + 0.1])
    for i, L in enumerate(Ls):
        for j, th in enumerate(ths):
            if not np.isnan(Z[i, j]):
                ax.text(th, L, f"{Z[i,j]:.0f}°", ha="center", va="center", fontsize=8,
                        color=INK if Z[i, j] > 35 else "white")
    ax.set(xlabel="inclinazione massima braccio theta_max [°]", ylabel="lunghezza braccio L [m]",
           title=f"Elevazione minima del sole per copertura totale\n(H={u.H} m, R={u.R} m, zona r={t.r} m centrata sul palo)")
    ax.grid(False)
    fig.colorbar(im, label="elevazione minima [°]  (più basso = meglio)")
    fig.savefig(FIG / "05_limiti_L_theta.png")
    plt.close(fig)
    return {"L": Ls.tolist(), "theta_max": ths.tolist(), "min_elev": Z.tolist()}


def fig_variants(fast: bool):
    base = Umbrella()
    variants = [
        ("Base: H2.0 L1.6 R1.5\nθmax 70°, zona centrata", base, Target(0, 0, 1.0)),
        ("+ sbalzo tettuccio 0.6 m", base.with_(canopy_offset=0.6), Target(0, 0, 1.0)),
        ("+ braccio telescopico\n1.2–2.4 m", base.with_(L_min=1.2, L_max=2.4), Target(0, 0, 1.0)),
        ("+ tettuccio R 1.8 m", base.with_(R=1.8), Target(0, 0, 1.0)),
        ("+ palo più basso H 1.6", base.with_(H=1.6), Target(0, 0, 1.0)),
        ("palo a SUD della zona\n(zona 1.2 m a Nord del palo)", base, Target(0, 1.2, 1.0)),
        ("palo a Sud della zona\n+ sbalzo 0.6", base.with_(canopy_offset=0.6), Target(0, 1.2, 1.0)),
        ("palo a Sud della zona + sbalzo 0.6\n+ telescopico 1.2–2.4", base.with_(canopy_offset=0.6, L_min=1.2, L_max=2.4), Target(0, 1.2, 1.0)),
        ("palo a NORD della zona\n(zona 1.2 m a Sud del palo)", base, Target(0, -1.2, 1.0)),
    ]
    grid = np.arange(89, 9, -3.0) if fast else np.arange(89, 9, -1.0)
    rows = []
    for name, u, t in variants:
        res = {}
        for az in (180, 120, 90):
            res[az] = min_elevation_for_full_coverage(u, t, az, grid)
        rows.append((name, res[180], res[120], res[90]))
    # ore di copertura totale il 15 luglio (a Sud) in base all'elevazione minima
    path = sun_path(datetime(2026, 7, 15), LAT, LON, 5, TZ)
    def hours_above(e):
        if e is None:
            return 0.0, None, None
        ts = [t for t, sp in path if sp.elevation_deg >= e]
        return len(ts) * 5 / 60, (ts[0] if ts else None), (ts[-1] if ts else None)
    out = []
    fig, ax = plt.subplots(figsize=(8.5, 4.6))
    names = [r[0] for r in rows]
    vals = [r[1] if r[1] is not None else 90 for r in rows]
    bars = ax.barh(range(len(rows)), vals, color=[C1 if i == 0 else C3 for i in range(len(rows))], height=0.6)
    for i, r in enumerate(rows):
        hrs, t0, t1 = hours_above(r[1])
        ax.text(vals[i] + 0.8, i, f"{vals[i]:.0f}°  →  {hrs:.1f} h/giorno ({fmt(t0)}–{fmt(t1)})", va="center", fontsize=8, color=INK)
        out.append({"variante": r[0].replace("\n", " "), "min_elev_S": r[1], "min_elev_SE": r[2], "min_elev_E": r[3],
                    "ore_copertura_totale_15lug": hrs, "da": fmt(t0), "a": fmt(t1)})
    ax.set_yticks(range(len(rows))); ax.set_yticklabels(names, fontsize=8)
    ax.invert_yaxis(); ax.set_xlim(0, 75)
    ax.set_xlabel("elevazione minima del sole per copertura TOTALE della zona (r = 1 m) [°]")
    ax.set_title("Quanto si guadagna con le varianti di progetto (15 luglio, Rimini)", fontsize=10)
    fig.savefig(FIG / "06_varianti.png")
    plt.close(fig)
    return out


def fig_mechanics(u: Umbrella):
    mm = MassModel()
    work = Pose(180, 70, 39, 180)       # posa di massimo sbraccio
    park = Pose(180, 0, 0, 180)
    vs = np.arange(2, 16.1, 1.0)
    rows = {k: [] for k in ("tilt_w", "az_w", "head_w", "base_w", "base_p", "tilt_p")}
    for v in vs:
        lw, lp = worst_case_loads(u, work, mm, v), worst_case_loads(u, park, mm, v)
        rows["tilt_w"].append(lw.tilt_torque_Nm); rows["az_w"].append(lw.azimuth_torque_Nm)
        rows["head_w"].append(lw.head_torque_Nm); rows["base_w"].append(lw.base_moment_Nm)
        rows["base_p"].append(lp.base_moment_Nm); rows["tilt_p"].append(lp.tilt_torque_Nm)
    fig, ax = plt.subplots(1, 2, figsize=(10, 3.8))
    ax[0].plot(vs * 3.6, rows["tilt_w"], color=C1, lw=2, label="inclinazione braccio (lavoro)")
    ax[0].plot(vs * 3.6, rows["az_w"], color=C2, lw=2, label="rotazione azimut (lavoro)")
    ax[0].plot(vs * 3.6, rows["head_w"], color=C3, lw=2, label="cerniera tettuccio (lavoro)")
    ax[0].plot(vs * 3.6, rows["tilt_p"], color=C1, lw=1.5, ls="--", label="inclinazione (parcheggio)")
    ax[0].axvline(WIND_WORK * 3.6, color=INK2, ls=":", lw=1)
    ax[0].text(WIND_WORK * 3.6 + 0.5, max(rows["tilt_w"]) * 0.9, "limite esercizio\n→ parcheggio", fontsize=8, color=INK2)
    ax[0].set(xlabel="vento [km/h]", ylabel="coppia al giunto [N·m]", title="Coppie ai giunti (caso peggiore di direzione)")
    ax[0].legend(frameon=False, fontsize=8)
    ax[1].plot(vs * 3.6, rows["base_w"], color=C1, lw=2, label="posa di lavoro (θ=70°)")
    ax[1].plot(vs * 3.6, rows["base_p"], color=C1, lw=1.5, ls="--", label="parcheggio (braccio verticale)")
    ax[1].set(xlabel="vento [km/h]", ylabel="momento ribaltante alla base [N·m]", title="Ribaltamento")
    ax[1].legend(frameon=False, fontsize=8)
    fig.savefig(FIG / "07_coppie_vento.png")
    plt.close(fig)

    lw = worst_case_loads(u, work, mm, WIND_WORK)
    lp = worst_case_loads(u, park, mm, WIND_PARK)
    res = {
        "masse_kg": {"tettuccio": mm.canopy_mass(u), "braccio": mm.arm_mass(u), "palo": mm.pole_mass(u),
                     "snodo": mm.joint_kg, "elettronica": mm.electronics_kg},
        "carichi_lavoro_8ms": {"coppia_inclinazione_Nm": lw.tilt_torque_Nm, "coppia_azimut_Nm": lw.azimuth_torque_Nm,
                               "coppia_tettuccio_Nm": lw.head_torque_Nm, "momento_base_Nm": lw.base_moment_Nm,
                               "forza_vento_tettuccio_N": lw.canopy_force_N},
        "carichi_parcheggio_15ms": {"coppia_inclinazione_Nm": lp.tilt_torque_Nm, "momento_base_Nm": lp.base_moment_Nm},
        "zavorra_kg": {f"base_r{r}_lavoro_8ms": required_base_mass(u, work, mm, WIND_WORK, r) for r in (0.4, 0.5, 0.6)},
        "zavorra_parcheggio_15ms_r0.5": required_base_mass(u, park, mm, WIND_PARK, 0.5),
        "motori": {
            "azimut_stepper_vite_senza_fine": size_motor("azimut", lw.azimuth_torque_Nm, 180, 60, 60, 0.45).__dict__,
            "inclinazione_attuatore_lineare": size_linear_actuator("inclinazione", lw.tilt_torque_Nm, 0.15, 70, 40),
            "tettuccio_attuatore_lineare": size_linear_actuator("tettuccio", lw.head_torque_Nm, 0.08, 70, 30),
        },
    }
    return res


def fig_materials(u: Umbrella):
    mm = MassModel()
    p = Pose(180, 70, 39, 180)
    cands = {
        "Al 6061-T6": [Tube(d, 0.003) for d in (0.04, 0.05, 0.06, 0.07, 0.08)],
        "Acciaio S235": [Tube(d, 0.002) for d in (0.04, 0.05, 0.06, 0.07, 0.08)],
        "CFRP": [Tube(d, 0.002) for d in (0.04, 0.05, 0.06, 0.07, 0.08)],
        "GFRP": [Tube(d, 0.003) for d in (0.04, 0.05, 0.06, 0.07, 0.08)],
    }
    res = material_sweep(u, p, mm, WIND_WORK, cands)
    cols = {"Al 6061-T6": C1, "Acciaio S235": C2, "CFRP": C3, "GFRP": C4}
    fig, ax = plt.subplots(1, 2, figsize=(10, 3.8))
    for mat in cands:
        rr = [r for r in res if r.material == mat]
        D = [r.tube.D * 1000 for r in rr]
        ax[0].plot(D, [r.tip_deflection_mm for r in rr], "o-", color=cols[mat], lw=2, ms=5, label=mat)
        ax[1].plot(D, [r.mass_kg for r in rr], "o-", color=cols[mat], lw=2, ms=5, label=mat)
    ax[0].axhline(20, color=INK2, ls=":", lw=1); ax[0].text(41, 21.5, "freccia accettabile ≈ 20 mm", fontsize=8, color=INK2)
    ax[0].set(xlabel="diametro esterno tubo [mm]", ylabel="freccia in punta [mm]", yscale="log",
              title=f"Rigidezza del braccio (L={u.L} m, vento {WIND_WORK*3.6:.0f} km/h, θ=70°)")
    ax[1].set(xlabel="diametro esterno tubo [mm]", ylabel="massa braccio [kg]", title="Massa del braccio")
    ax[0].legend(frameon=False, fontsize=8)
    fig.savefig(FIG / "08_materiali.png")
    plt.close(fig)
    table = [{"materiale": r.material, "D_mm": r.tube.D * 1000, "t_mm": r.tube.t * 1000, "massa_kg": r.mass_kg,
              "freccia_mm": r.tip_deflection_mm, "tensione_MPa": r.stress_MPa, "coeff_sicurezza": r.safety_factor}
             for r in res]
    return table


def fig_fem(u: Umbrella):
    mm = MassModel()
    p = Pose(180, 70, 39, 180)
    fr = frame_fem(u, p, mm, WIND_WORK)
    fig, ax = plt.subplots(figsize=(5.5, 4.2))
    scale = 25
    for (i, j), st in zip(fr.elements, fr.max_stress_MPa):
        ax.plot(fr.nodes[[i, j], 0], fr.nodes[[i, j], 1], color=GRID, lw=5)
    nd = fr.nodes + scale * fr.disp[:, :2]
    sc = ax.scatter(nd[:, 0], nd[:, 1], c=np.r_[fr.max_stress_MPa, fr.max_stress_MPa[-1]], cmap="YlOrRd", s=25, zorder=3)
    ax.plot(nd[:, 0], nd[:, 1], color=INK, lw=1.5, zorder=2)
    ax.set_aspect("equal")
    ax.set(xlabel="sbraccio [m]", ylabel="quota [m]",
           title=f"FEM telaio palo+braccio, vento {WIND_WORK*3.6:.0f} km/h\n"
                 f"spostamenti ×{scale}; freccia reale in punta {fr.tip_deflection_mm:.1f} mm, "
                 f"σ max {fr.max_stress_MPa.max():.0f} MPa")
    fig.colorbar(sc, label="tensione massima per elemento [MPa]")
    fig.savefig(FIG / "09_fem.png")
    plt.close(fig)
    return {"freccia_punta_mm": fr.tip_deflection_mm, "sigma_max_MPa": float(fr.max_stress_MPa.max()),
            "sigma_amm_Al_MPa": MATERIALS["Al 6061-T6"].sigma_y / 1e6}


# ----------------------------------------------------------------------------
def write_markdown(res: dict, path: Path):
    L = []
    L.append("# Risultati della simulazione\n")
    L.append(f"Generato il {res['generato']} con `python -m ombrellone.simulate`. Località: Rimini "
             f"({LAT}N, {LON}E), fuso CEST.\n")
    L.append("## Progetto base\n")
    u = res["progetto_base"]
    L.append("| parametro | valore |\n|---|---|")
    for k, v in u.items():
        L.append(f"| {k} | {v} |")
    L.append("\n## Giornata tipo (15 luglio), zona r = 1 m centrata sul palo\n")
    d = res["giornata_15_luglio"]
    L.append("| metrica | valore |\n|---|---|")
    for k, v in d.items():
        L.append(f"| {k} | {v} |")
    L.append("\n![giornata](figure/02_giornata_15lug.png)\n")
    L.append("![istantanee](figure/03_istantanee_15lug.png)\n")
    L.append("![vista laterale](figure/04_vista_laterale.png)\n")
    L.append("\n## Giornata di confronto (21 settembre)\n")
    d = res["giornata_21_settembre"]
    L.append("| metrica | valore |\n|---|---|")
    for k, v in d.items():
        L.append(f"| {k} | {v} |")
    L.append("\n## Limiti geometrici\n")
    L.append("![limiti](figure/05_limiti_L_theta.png)\n")
    L.append("### Varianti di progetto\n")
    L.append("| variante | elev. min. sole a Sud | a Sud-Est | a Est | ore copertura totale 15 lug (sole a Sud) | finestra |\n|---|---|---|---|---|---|")
    for r in res["varianti"]:
        L.append(f"| {r['variante']} | {r['min_elev_S']}° | {r['min_elev_SE']}° | {r['min_elev_E']}° | {r['ore_copertura_totale_15lug']:.1f} h | {r['da']}–{r['a']} |")
    L.append("\n![varianti](figure/06_varianti.png)\n")
    L.append("\n## Meccanica\n")
    m = res["meccanica"]
    L.append("| massa | kg |\n|---|---|")
    for k, v in m["masse_kg"].items():
        L.append(f"| {k} | {v:.1f} |")
    L.append("\n| carico (vento 8 m/s = 29 km/h, posa di massimo sbraccio) | valore |\n|---|---|")
    for k, v in m["carichi_lavoro_8ms"].items():
        L.append(f"| {k} | {v:.0f} |")
    L.append("\n| carico (vento 15 m/s = 54 km/h, parcheggio) | valore |\n|---|---|")
    for k, v in m["carichi_parcheggio_15ms"].items():
        L.append(f"| {k} | {v:.0f} |")
    L.append("\n| zavorra richiesta (coeff. sicurezza 1.5) | kg |\n|---|---|")
    for k, v in m["zavorra_kg"].items():
        L.append(f"| {k} | {v:.0f} |")
    L.append(f"| parcheggio 15 m/s, base r=0.5 | {m['zavorra_parcheggio_15ms_r0.5']:.0f} |")
    L.append("\n### Attuatori\n")
    L.append("```json\n" + json.dumps(m["motori"], indent=2, ensure_ascii=False) + "\n```\n")
    L.append("![coppie](figure/07_coppie_vento.png)\n")
    L.append("\n## Materiali del braccio\n")
    L.append("| materiale | D [mm] | t [mm] | massa [kg] | freccia [mm] | σ [MPa] | coeff. sicurezza |\n|---|---|---|---|---|---|---|")
    for r in res["materiali"]:
        L.append(f"| {r['materiale']} | {r['D_mm']:.0f} | {r['t_mm']:.0f} | {r['massa_kg']:.2f} | {r['freccia_mm']:.1f} | {r['tensione_MPa']:.0f} | {r['coeff_sicurezza']:.0f} |")
    L.append("\n![materiali](figure/08_materiali.png)\n")
    L.append("\n## FEM telaio\n")
    L.append("```json\n" + json.dumps(res["fem"], indent=2) + "\n```\n")
    L.append("![fem](figure/09_fem.png)\n")
    L.append("\n## Leggi di scala per il mini (1:10)\n")
    L.append("```json\n" + json.dumps(res["scala_mini"], indent=2, ensure_ascii=False) + "\n```\n")
    path.write_text("\n".join(L), encoding="utf-8")


def day_summary(plan: DayPlan) -> dict:
    s = plan.summary()
    w = s["finestra_copertura_totale"]
    return {
        "ore_di_sole_(elev>5°)": round(s["ore_sole"], 1),
        "finestra_copertura_totale": f"{fmt(w[0])}–{fmt(w[1])}" if w else "mai",
        "ore_copertura_totale": round(s["ore_copertura_totale_ideale"], 1),
        "buchi_(copertura_parziale)": ", ".join(f"{fmt(a)}–{fmt(b)}" for a, b in s["buchi"]) or "nessuno",
        "copertura_media_tenuta_%": round(100 * s["copertura_media_tenuta"], 1),
        "copertura_minima_tenuta_%": round(100 * s["copertura_minima_tenuta"], 1),
        "movimenti_al_giorno": s["movimenti"],
        "corsa_totale_giunti_gradi": round(s["corsa_totale_gradi"]),
    }


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--fast", action="store_true", help="griglie più rade (circa 5 minuti invece di 20)")
    args = ap.parse_args(argv)
    FIG.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    u = Umbrella()
    t = Target(0, 0, 1.0)
    res = {"generato": datetime.now().strftime("%Y-%m-%d %H:%M"), "progetto_base": u.__dict__ | {"zona": t.__dict__}}

    print("sole..."); fig_sun_paths()
    step = 10 if args.fast else 5
    print("giornata 15 luglio...")
    plan = plan_day(u, t, datetime(2026, 7, 15), LAT, LON, TZ, step_minutes=step)
    fig_day(plan, "02_giornata_15lug.png", "15 luglio, Rimini — progetto base, zona r=1 m centrata sul palo")
    res["giornata_15_luglio"] = day_summary(plan)
    print(res["giornata_15_luglio"])
    print("giornata 21 settembre...")
    plan2 = plan_day(u, t, datetime(2026, 9, 21), LAT, LON, TZ, step_minutes=step)
    fig_day(plan2, "02b_giornata_21set.png", "21 settembre, Rimini — progetto base")
    res["giornata_21_settembre"] = day_summary(plan2)
    print("istantanee..."); fig_snapshots(u, t, datetime(2026, 7, 15), "03_istantanee_15lug.png", "15 luglio, vista dall'alto")
    print("vista laterale..."); fig_side_view(u, t, "04_vista_laterale.png")
    print("limiti L/theta..."); res["limiti_L_theta"] = fig_limits(u, t, args.fast)
    print("varianti..."); res["varianti"] = fig_variants(args.fast)
    print("meccanica..."); res["meccanica"] = fig_mechanics(u)
    print("materiali..."); res["materiali"] = fig_materials(u)
    print("fem..."); res["fem"] = fig_fem(u)
    res["scala_mini"] = scale_report(u, 0.1)
    (ROOT / "docs" / "risultati.json").write_text(json.dumps(res, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    write_markdown(res, ROOT / "docs" / "risultati.md")
    print(f"fatto in {time.time()-t0:.0f} s -> docs/risultati.md")


if __name__ == "__main__":
    main()
