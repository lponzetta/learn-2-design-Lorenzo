"""Posto e giorno migliori: ore al giorno di copertura totale in funzione di
latitudine e giorno dell'anno, dalle soglie di elevazione (per azimut) gia'
calcolate in docs/stagionalita.json.  Uso: python -m ombrellone.posto_migliore
"""
from __future__ import annotations
import json, math
from datetime import datetime, timedelta, timezone
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from .solar import sun_position

ROOT = Path(__file__).resolve().parent.parent
FIG = ROOT / "docs" / "figure"
MESI = ["gen", "feb", "mar", "apr", "mag", "giu", "lug", "ago", "set", "ott", "nov", "dic"]
INK2 = "#52514e"
plt.rcParams.update({"font.size": 10, "axes.edgecolor": INK2, "axes.labelcolor": INK2, "xtick.color": INK2,
                     "ytick.color": INK2, "figure.dpi": 130, "savefig.bbox": "tight"})


def thresholds():
    maps = json.loads((ROOT / "docs" / "stagionalita.json").read_text())["mappe"]
    out = {}
    for lab, m in maps.items():
        d = {float(k): (v if v is not None else 99.0) for k, v in m["elev_min_per_az"].items()}
        az = np.array(sorted(d)); e = np.array([d[a] for a in az])
        out[lab] = (az, e)
    return out


def emin_at(az_grid, e_grid, az_deg, south_hemisphere=False):
    if len(az_grid) == 1:
        return e_grid[0]
    a = az_deg if az_deg <= 180 else 360 - az_deg          # simmetria Est/Ovest
    if south_hemisphere:                                    # palo a Sud della zona -> nell'emisfero Sud palo a Nord: specchio
        a = 180 - a
    return float(np.interp(a, az_grid, e_grid))


def hours_day(az_grid, e_grid, lat, doy, step_min=10):
    """Ore di copertura totale nel giorno doy alla latitudine lat (lon 0, UTC: conta solo l'elevazione)."""
    t0 = datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(days=doy - 1)
    n = 0
    for k in range(0, 24 * 60, step_min):
        sp = sun_position(t0 + timedelta(minutes=k), lat, 0.0)
        if sp.elevation_deg >= 5 and sp.elevation_deg >= emin_at(az_grid, e_grid, sp.azimuth_deg, lat < 0):
            n += 1
    return n * step_min / 60


def main():
    th = thresholds()
    lats = np.arange(-60, 61, 3.0)
    doys = np.arange(3, 366, 6)
    results = {}
    fig, axs = plt.subplots(1, 2, figsize=(11, 4.4), sharey=True)
    for ax, lab in zip(axs, [list(th)[0], list(th)[2]]):
        az_grid, e_grid = th[lab]
        H = np.array([[hours_day(az_grid, e_grid, la, int(d)) for d in doys] for la in lats])
        i, j = np.unravel_index(np.argmax(H), H.shape)
        best_day = datetime(2026, 1, 1) + timedelta(days=int(doys[j]) - 1)
        annual = H.sum(axis=1) * (365 / len(doys))
        ia = int(np.argmax(annual))
        results[lab] = {"max_ore_giorno": float(H[i, j]), "lat": float(lats[i]), "giorno": best_day.strftime("%d %b"),
                        "max_ore_anno": float(annual[ia]), "lat_anno": float(lats[ia]),
                        "ore_anno_per_lat": {f"{la:.0f}": float(a) for la, a in zip(lats, annual)}}
        im = ax.imshow(H, origin="lower", aspect="auto", cmap="YlGn", vmin=0, vmax=12,
                       extent=[doys[0] - 3, doys[-1] + 3, lats[0] - 1.5, lats[-1] + 1.5])
        cs = ax.contour(doys, lats, H, levels=[4, 6, 8, 10], colors="#0b0b0b", linewidths=0.6)
        ax.clabel(cs, fmt="%.0f h", fontsize=7)
        ax.plot(doys[j], lats[i], "o", color="#e34948", ms=8, mec="white")
        ax.annotate(f"max {H[i,j]:.1f} h/giorno\n{best_day.strftime('%d %b')}, lat {lats[i]:.0f}°",
                    (doys[j], lats[i]), xytext=(10, -40), textcoords="offset points", fontsize=8,
                    arrowprops=dict(arrowstyle="-", color="#0b0b0b", lw=0.6))
        ax.axhline(44.06, color="#2a78d6", ls="--", lw=0.9); ax.text(5, 45.5, "Rimini", color="#2a78d6", fontsize=8)
        ax.set_xticks([(datetime(2026, m, 15) - datetime(2026, 1, 1)).days + 1 for m in range(1, 13)]); ax.set_xticklabels(MESI)
        ax.set_title(f"{lab}\nmiglior latitudine sull'anno: {lats[ia]:.0f}° ({annual[ia]:.0f} h/anno)", fontsize=9)
        ax.set_xlabel("giorno dell'anno")
    axs[0].set_ylabel("latitudine [°] (negativa = emisfero Sud)")
    fig.colorbar(im, ax=axs, label="ore/giorno di copertura totale", fraction=0.03)
    fig.suptitle("Dove e quando l'ombrellone rende di più (zona r = 1 m)", fontsize=11, y=1.02)
    fig.savefig(FIG / "13_posto_e_giorno.png"); plt.close(fig)
    (ROOT / "docs" / "posto_migliore.json").write_text(json.dumps(results, indent=1, ensure_ascii=False), encoding="utf-8")
    for lab, r in results.items():
        print(f"{lab}: max {r['max_ore_giorno']:.1f} h/giorno a lat {r['lat']:.0f}° il {r['giorno']}; "
              f"max annuo {r['max_ore_anno']:.0f} h a lat {r['lat_anno']:.0f}°")
        for la in ("0", "12", "24", "36", "45", "-24", "-36"):
            print(f"    lat {la:>3}: {r['ore_anno_per_lat'][la]:.0f} h/anno")


if __name__ == "__main__":
    main()
