# Ombrellone magico — ombra ferma mentre il sole si muove

Progetto di un ombrellone robotico che tiene in ombra una zona scelta dall'app
(di default centrata sul palo) spostando tettuccio e braccio in base alla
posizione del sole calcolata da coordinate GPS e orario.

Contenuto del repository:

| cartella | cosa c'è |
|---|---|
| `ombrellone/` | pacchetto Python: posizione del sole (`solar.py`), cinematica e ombra (`geometry.py`), algoritmo di controllo e pianificazione giornaliera con limiti (`planner.py`), studio meccanico, materiali e FEM (`mechanics.py`), script di simulazione (`simulate.py`) |
| `tests/` | test automatici (pytest), inclusa validazione del sole contro pvlib |
| `firmware/ombrellone_esp32/` | firmware Arduino per ESP32 del mini-prototipo (4 servo, web app, NTP, stesso algoritmo) |
| `docs/PROGETTO.md` | documento di progetto: concetto, algoritmo, limiti, meccanica, materiali, elettronica, prototipo mini, lista della spesa, idee |
| `docs/risultati.md` | risultati numerici e figure generate dalla simulazione |
| `docs/simulatore.html` | simulatore interattivo nel browser (stesso algoritmo in JavaScript) |

## Avvio rapido

```bash
pip install -r requirements.txt
python -m pytest -q                 # test
python -m ombrellone.simulate --fast  # figure e risultati in docs/ (circa 5 minuti)
```

Esempio d'uso del pacchetto:

```python
from datetime import datetime, timezone
from ombrellone.geometry import Umbrella, Target
from ombrellone.planner import solve_pose
from ombrellone.solar import sun_position

u = Umbrella(H=2.0, L=1.6, R=1.5, theta_max_deg=70)
sp = sun_position(datetime(2026, 7, 15, 13, 0, tzinfo=timezone.utc), 44.06, 12.57)
sol = solve_pose(u, sp.vector_enu, Target(0, 0, 1.0))
print(sol.pose, sol.eval.coverage, sol.full_coverage)
```
