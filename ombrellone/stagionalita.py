"""Stagionalità: quante ore al giorno l'ombrellone tiene la zona in ombra
totale, lungo tutto l'anno e a diverse latitudini.

Idea chiave: la fattibilità della copertura totale dipende SOLO dalla direzione
del sole (elevazione, azimut) e dalla geometria, non dalla data o dal luogo.
Quindi si calcola una volta una **mappa di fattibilità** su una griglia
(elevazione × azimut) e poi la si applica a qualunque giorno e località con
puro calcolo astronomico (istantaneo).

Uso:  python -m ombrellone.stagionalita [--fast]
Produce docs/figure/10..12 e docs/stagionalita.md
"""
from __future__ import annotations

import argparse
import json
import math
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm

from .geometry import Umbrella, Target
from .planner import solve_pose
from .solar import sun_position, sun_vector_enu

ROOT = Path(__file__).resolve().parent.parent
FIG = ROOT / "docs" / "figure"
C1, C2, C3, C4, C5, C6 = "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e6e4df"
plt.rcParams.update({"font.size": 10, "axes.edgecolor": INK2, "axes.labelcolor": INK2,
                     "xtick.color": INK2, "ytick.color": INK2, "axes.grid": True,
                     "grid.color": GRID, "grid.linewidth": 0.6, "axes.spines.top": False,
                     "axes.spines.right": False, "figure.dpi": 130, "savefig.bbox": "tight"})

MESI = ["gen", "feb", "mar", "apr", "mag", "giu", "lug", "ago", "set", "ott", "nov", "dic"]
STAGIONE_BALNEARE = (datetime(2026, 5, 15), datetime(2026, 9, 15))


# ----------------------------------------------------------------------------
# mappa di fattibilita'
# ----------------------------------------------------------------------------
@dataclass
class FeasibilityMap:
    elev: np.ndarray          # griglia elevazioni [gradi]
    az: np.ndarray            # griglia azimut [gradi], oppure [180] se simmetrica
    full: np.ndarray          # (n_elev, n_az) bool: copertura totale possibile
    coverage: np.ndarray      # (n_elev, n_az) frazione coperta (ottimo)
    symmetric: bool           # True: indipendente dall'azimut (zona centrata)

    def lookup(self, elev_deg: float, az_deg: float) -> tuple[bool, float]:
        i = int(np.clip(np.searchsorted(self.elev, elev_deg) - 0, 0, len(self.elev) - 1))
        # prende il nodo di elevazione immediatamente inferiore (conservativo)
        i = max(0, min(len(self.elev) - 1, int(np.floor((elev_deg - self.elev[0]) / (self.elev[1] - self.elev[0])))))
        if self.symmetric:
            j = 0
        else:
            a = az_deg if az_deg <= 180 else 360 - az_deg       # simmetria Est/Ovest
            j = int(round((a - self.az[0]) / (self.az[1] - self.az[0])))
            j = max(0, min(len(self.az) - 1, j))
        return bool(self.full[i, j]), float(self.coverage[i, j])


def feasibility_map(u: Umbrella, t: Target, elev_step: float = 2.0, az_step: float = 15.0,
                    elev_min: float = 5.0, verbose: bool = True) -> FeasibilityMap:
    symmetric = (abs(t.x) < 1e-9 and abs(t.y) < 1e-9)
    elev = np.arange(elev_min, 90.0 + 1e-9, elev_step)
    # zona sull'asse Nord-Sud: simmetria Est/Ovest -> basta 0..180
    az = np.array([180.0]) if symmetric else np.arange(0.0, 180.0 + 1e-9, az_step)
    full = np.zeros((len(elev), len(az)), dtype=bool)
    cov = np.zeros((len(elev), len(az)))
    t0 = time.time()
    for j, a in enumerate(az):
        for i, e in enumerate(elev):
            sol = solve_pose(u, sun_vector_enu(float(e), float(a)), t, n_starts=4)
            full[i, j] = sol.full_coverage
            cov[i, j] = sol.eval.coverage
        if verbose:
            print(f"    azimut {a:5.0f}: elev. minima {elev[full[:, j]].min() if full[:, j].any() else None}  "
                  f"({time.time() - t0:.0f} s)", flush=True)
    return FeasibilityMap(elev, az, full, cov, symmetric)


# ----------------------------------------------------------------------------
# profilo annuale
# ----------------------------------------------------------------------------
@dataclass
class DayStat:
    date: datetime
    sun_hours: float
    full_hours: float
    partial_hours: float      # copertura >= 80% ma non totale
    first: float | None       # ora locale (decimale) inizio copertura totale
    last: float | None
    states: np.ndarray        # per ogni passo: 0 notte/sole basso, 1 scoperto, 2 parziale, 3 totale


def day_profile(fmap: FeasibilityMap, date: datetime, lat: float, lon: float, tz,
                step_min: int = 10, min_elev: float = 5.0) -> DayStat:
    start = datetime(date.year, date.month, date.day, tzinfo=tz)
    n = 24 * 60 // step_min
    states = np.zeros(n, dtype=np.int8)
    first = last = None
    for k in range(n):
        tt = start + timedelta(minutes=k * step_min)
        sp = sun_position(tt, lat, lon)
        if sp.elevation_deg < min_elev:
            continue
        ok, cov = fmap.lookup(sp.elevation_deg, sp.azimuth_deg)
        states[k] = 3 if ok else (2 if cov >= 0.8 else 1)
        if ok:
            h = tt.hour + tt.minute / 60
            first = h if first is None else first
            last = h
    hrs = step_min / 60
    return DayStat(start, float((states > 0).sum() * hrs), float((states == 3).sum() * hrs),
                   float((states == 2).sum() * hrs), first, last, states)


def year_profile(fmap: FeasibilityMap, lat: float, lon: float, tz, every_days: int = 3,
                 year: int = 2026, step_min: int = 10) -> list[DayStat]:
    out = []
    d = datetime(year, 1, 1)
    while d.year == year:
        out.append(day_profile(fmap, d, lat, lon, tz, step_min))
        d += timedelta(days=every_days)
    return out


def monthly_table(prof: list[DayStat]) -> list[dict]:
    rows = []
    for m in range(1, 13):
        ds = [p for p in prof if p.date.month == m]
        if not ds:
            continue
        rows.append({"mese": MESI[m - 1],
                     "ore_sole": np.mean([p.sun_hours for p in ds]),
                     "ore_copertura_totale": np.mean([p.full_hours for p in ds]),
                     "ore_parziale": np.mean([p.partial_hours for p in ds]),
                     "giorni_utili_4h": 100 * np.mean([p.full_hours >= 4 for p in ds]),
                     "finestra_tipica": (f"{_hhmm(np.median([p.first for p in ds if p.first is not None]))}–"
                                         f"{_hhmm(np.median([p.last for p in ds if p.last is not None]))}"
                                         if any(p.first is not None for p in ds) else "–")})
    return rows


def _hhmm(h: float) -> str:
    return f"{int(h):02d}:{int(round((h - int(h)) * 60)):02d}"


def doy(d: datetime) -> int:
    return d.timetuple().tm_yday


# ----------------------------------------------------------------------------
# figure
# ----------------------------------------------------------------------------
def fig_calendar(profiles: dict[str, list[DayStat]], step_min: int, name: str, title: str):
    cmap = ListedColormap([GRID, "#e34948", "#eda100", "#1baf7a"])
    norm = BoundaryNorm([-0.5, 0.5, 1.5, 2.5, 3.5], 4)
    n = len(profiles)
    fig, axs = plt.subplots(1, n, figsize=(5.2 * n, 4.6), sharey=True)
    axs = np.atleast_1d(axs)
    for ax, (lab, prof) in zip(axs, profiles.items()):
        M = np.stack([p.states for p in prof], axis=1)           # (ore, giorni)
        x = [doy(p.date) for p in prof]
        ax.imshow(M, aspect="auto", cmap=cmap, norm=norm, origin="lower", interpolation="nearest",
                  extent=[x[0] - 1.5, x[-1] + 1.5, 0, 24])
        ax.set_ylim(4, 22)
        ax.set_xticks([doy(datetime(2026, m, 15)) for m in range(1, 13)])
        ax.set_xticklabels(MESI)
        ax.set_yticks(range(4, 23, 2)); ax.set_yticklabels([f"{h}:00" for h in range(4, 23, 2)])
        for d in STAGIONE_BALNEARE:
            ax.axvline(doy(d), color=INK, ls="--", lw=0.8)
        tot = sum(p.full_hours for p in prof) * (365 / len(prof))
        ax.set_title(f"{lab}\n{tot:.0f} h/anno di copertura totale", fontsize=9)
        ax.grid(False)
    axs[0].set_ylabel("ora locale")
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in ["#1baf7a", "#eda100", "#e34948", GRID]]
    fig.legend(handles, ["copertura totale", "parziale (≥ 80 %)", "scoperta", "notte / sole < 5°"],
               loc="lower center", ncol=4, frameon=False, fontsize=8, bbox_to_anchor=(0.5, -0.04))
    fig.suptitle(title + "  (tratteggio: stagione balneare 15 mag – 15 set)", fontsize=10, y=1.02)
    fig.savefig(FIG / name)
    plt.close(fig)


def fig_hours_year(profiles: dict[str, list[DayStat]], name: str, title: str, colors=None):
    colors = colors or [C1, C3, C2, C5, C4, C6]
    fig, ax = plt.subplots(figsize=(10, 4.4))
    first = next(iter(profiles.values()))
    x = [doy(p.date) for p in first]
    ax.plot(x, [p.sun_hours for p in first], color=INK2, ls="--", lw=1.2, label="ore di sole (> 5°)")
    for (lab, prof), c in zip(profiles.items(), colors):
        ax.plot(x, [p.full_hours for p in prof], color=c, lw=2.2, label=lab)
    ax.axvspan(doy(STAGIONE_BALNEARE[0]), doy(STAGIONE_BALNEARE[1]), color=C6, alpha=0.06, lw=0)
    ax.axhline(4, color=INK2, ls=":", lw=0.8); ax.text(3, 4.2, "soglia 'giornata utile' = 4 h", fontsize=8, color=INK2)
    ax.set_xticks([doy(datetime(2026, m, 15)) for m in range(1, 13)]); ax.set_xticklabels(MESI)
    ax.set_ylim(0, 16); ax.set_ylabel("ore al giorno di copertura totale")
    ax.set_title(title, fontsize=10)
    ax.legend(frameon=False, fontsize=8, ncol=2)
    fig.savefig(FIG / name)
    plt.close(fig)


# ----------------------------------------------------------------------------
def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--fast", action="store_true")
    args = ap.parse_args(argv)
    FIG.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    estep, astep, every = (3.0, 30.0, 6) if args.fast else (2.0, 15.0, 3)
    step_min = 10

    base = Umbrella()
    configs = {
        "A · base (tutto fisso)": (base, Target(0, 0, 1.0)),
        "B · sbalzo mobile 0–0.8 m": (base.with_(offset_min=0.0, offset_max=0.8), Target(0, 0, 1.0)),
        "C · B + palo a Sud della zona": (base.with_(offset_min=0.0, offset_max=0.8), Target(0, 1.2, 1.0)),
        "D · braccio telescopico 1.6–2.4 + sbalzo mobile": (base.with_(L_min=1.6, L_max=2.4, offset_min=0.0, offset_max=0.8), Target(0, 0, 1.0)),
    }
    maps = {}
    for lab, (u, t) in configs.items():
        print(f"mappa di fattibilità: {lab}", flush=True)
        maps[lab] = feasibility_map(u, t, estep, astep)

    rome = ZoneInfo("Europe/Rome")
    LAT, LON = 44.06, 12.57
    print("profili annuali Rimini...", flush=True)
    prof = {lab: year_profile(m, LAT, LON, rome, every, step_min=step_min) for lab, m in maps.items()}

    fig_calendar({k: prof[k] for k in list(prof)[:1] + list(prof)[2:3]}, step_min,
                 "10_stagionalita_calendario.png", "Rimini: quando la zona (r = 1 m) è in ombra totale")
    fig_hours_year(prof, "11_stagionalita_ore.png", "Rimini: ore al giorno di copertura totale lungo l'anno")

    # latitudini: configurazione C
    places = {"Milano (45.5°N)": (45.46, 9.19, rome), "Rimini (44.1°N)": (LAT, LON, rome),
              "Roma (41.9°N)": (41.90, 12.50, rome), "Palermo (38.1°N)": (38.12, 13.36, rome),
              "Tenerife (28.5°N)": (28.46, -16.25, ZoneInfo("Atlantic/Canary"))}
    labC = list(configs)[2]
    print("latitudini...", flush=True)
    prof_lat = {p: year_profile(maps[labC], la, lo, tz, every, step_min=step_min) for p, (la, lo, tz) in places.items()}
    fig_hours_year(prof_lat, "12_stagionalita_latitudini.png",
                   f"Configurazione {labC.split(' · ')[0]} ({labC.split(' · ')[1]}): ore di copertura totale per latitudine",
                   colors=[C1, C3, C2, C5, C4])

    # tabella mensile e riepilogo
    res = {"generato": datetime.now().strftime("%Y-%m-%d %H:%M"), "passo_min": step_min,
           "griglia": {"elev_step": estep, "az_step": astep, "ogni_giorni": every},
           "rimini": {lab: monthly_table(p) for lab, p in prof.items()},
           "latitudini": {p: monthly_table(pr) for p, pr in prof_lat.items()},
           "mappe": {lab: {"elev_min_per_az": {f"{a:.0f}": (float(m.elev[m.full[:, j]].min()) if m.full[:, j].any() else None)
                                               for j, a in enumerate(m.az)}} for lab, m in maps.items()}}
    (ROOT / "docs" / "stagionalita.json").write_text(json.dumps(res, indent=2, ensure_ascii=False, default=float), encoding="utf-8")
    write_markdown(res, prof, prof_lat, ROOT / "docs" / "stagionalita.md")
    print(f"fatto in {time.time() - t0:.0f} s -> docs/stagionalita.md")


def write_markdown(res, prof, prof_lat, path: Path):
    L = ["# Stagionalità: quando l'ombrellone è utilizzabile (e vendibile)\n",
         f"Generato il {res['generato']} con `python -m ombrellone.stagionalita`. Zona da coprire: cerchio r = 1 m. "
         "\"Copertura totale\" = tutta la zona in ombra; \"giornata utile\" = almeno 4 h di copertura totale.\n",
         "La fattibilità dipende solo dalla direzione del sole: è stata calcolata una volta su una griglia "
         f"(elevazione ogni {res['griglia']['elev_step']}°, azimut ogni {res['griglia']['az_step']}°) e applicata "
         f"a tutto l'anno (un giorno ogni {res['griglia']['ogni_giorni']}, passo {res['passo_min']} min).\n",
         "## Configurazioni\n",
         "| sigla | configurazione |\n|---|---|",
         "| A | progetto base: H 2.0, L 1.6, R 1.5, θmax 70°, zona centrata sul palo |",
         "| B | A + sbalzo mobile 0–0.8 m (carrello sotto il tettuccio) |",
         "| C | B + palo a Sud della zona (zona 1.2 m a Nord del palo) |",
         "| D | A + braccio telescopico 1.6–2.4 m + sbalzo mobile 0–0.8 m |\n",
         "## Rimini: calendario\n", "![calendario](figure/10_stagionalita_calendario.png)\n",
         "![ore](figure/11_stagionalita_ore.png)\n",
         "## Rimini: tabella mensile (ore medie al giorno di copertura totale)\n"]
    labs = list(prof)
    L.append("| mese | ore sole | " + " | ".join(l.split(" · ")[0] for l in labs) + " | giorni utili (≥4 h) C |")
    L.append("|---|---|" + "---|" * len(labs) + "---|")
    for i in range(12):
        rows = [res["rimini"][l][i] for l in labs]
        L.append(f"| {MESI[i]} | {rows[0]['ore_sole']:.1f} | " + " | ".join(f"{r['ore_copertura_totale']:.1f}" for r in rows)
                 + f" | {rows[2]['giorni_utili_4h']:.0f} % |")
    tot = {l: sum(p.full_hours for p in prof[l]) * (365 / len(prof[l])) for l in labs}
    L.append("\n| configurazione | ore/anno di copertura totale | giorni utili/anno (≥4 h) | giorni utili nella stagione balneare (15 mag–15 set, 123 gg) |\n|---|---|---|---|")
    for l in labs:
        util = sum(1 for p in prof[l] if p.full_hours >= 4) * (365 / len(prof[l]))
        util_s = sum(1 for p in prof[l] if p.full_hours >= 4 and STAGIONE_BALNEARE[0] <= p.date.replace(tzinfo=None) <= STAGIONE_BALNEARE[1]) * (365 / len(prof[l]))
        L.append(f"| {l} | {tot[l]:.0f} | {util:.0f} | {min(123, util_s):.0f} |")
    L += ["\n## Latitudini (configurazione C)\n", "![latitudini](figure/12_stagionalita_latitudini.png)\n",
          "| località | ore/anno copertura totale | giorni utili/anno | mesi con ≥ 4 h/giorno in media |\n|---|---|---|---|"]
    for p, pr in prof_lat.items():
        tot_p = sum(x.full_hours for x in pr) * (365 / len(pr))
        util = sum(1 for x in pr if x.full_hours >= 4) * (365 / len(pr))
        mesi = [r["mese"] for r in res["latitudini"][p] if r["ore_copertura_totale"] >= 4]
        L.append(f"| {p} | {tot_p:.0f} | {util:.0f} | {', '.join(mesi) if mesi else '–'} |")
    L += ["\n## Elevazione minima del sole per azimut (dalle mappe)\n", "```json",
          json.dumps(res["mappe"], indent=1, ensure_ascii=False), "```"]
    path.write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    main()
