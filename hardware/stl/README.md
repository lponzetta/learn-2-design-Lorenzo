# STL pronti da stampare — mini-prototipo 1:10 e banco demo

Generati da `hardware/build_parts.py` (trimesh + manifold3d). Ogni file è già
nell'orientamento di stampa: appoggialo com'è sul piatto, senza ruotarlo.
`report.md` ha ingombri, volumi, massa stimata e area delle sporgenze.
`assieme_modello.stl/.png` è l'assieme di controllo (non si stampa).

## Impostazioni di stampa

| | |
|---|---|
| materiale | PETG (o ASA per il banco demo se la lampada scalda) |
| ugello / layer | 0,4 mm / 0,2 mm |
| perimetri / strati pieni | 3 / 4 |
| riempimento | 30 % gyroid (base e supporti servo: 40 %) |
| supporti | **nessuno** se stampi nell'orientamento dato: le tasche sono aperte verso l'alto o di lato, le transizioni sono a 45°. Dentro le tasche ci sono ponti di 12–20 mm: stampabili |
| adesione | brim 3 mm per `02_pole_hub`, `03_pole_top`, `05_arm_tip`, `11_lamp_holder` (base d'appoggio piccola) |

## Tolleranze incorporate

| accoppiamento | gioco | se non entra / balla |
|---|---|---|
| tubi carbonio Ø10 e Ø8 (incollati) | +0,35 mm sul diametro | alesa con punta da 10,2 / 8,2; se balla, epossidica riempie |
| tasche servo MG996R / MG90S | +0,4 mm | lima leggera; il servo deve entrare a mano senza forzare |
| sedi squadrette rotonde | +0,5 mm | |
| viti flange servo | M3 2,6 mm (MG996R), M2 1,8 mm (MG90S): autofilettanti | |
| viti squadrette | 2,2 mm (M2 sulla squadretta MG996R), 1,8 mm (micro squadretta) | |
| viti piattaforma / tavolo | M4 passanti 4,4 mm | |

Il gioco giusto dipende dalla stampante: stampa prima `04_arm_root` (6 cm³,
15 minuti) e prova il tubo Ø8 e una squadretta MG90S. Se serve, cambia `fit_tube`
e `fit_servo` in `PRINT` dentro `build_parts.py` e rigenera tutto.

## Parti e viteria

| file | pezzi | viti |
|---|---|---|
| `01_base` | 1 | 4× M3×8 (flange servo), 4× M4×16 + dadi (alla piattaforma) |
| `02_pole_hub` | 1 | 4× M2×6 (squadretta rotonda MG996R), vite centrale della squadretta |
| `03_pole_top` | 1 | 2× M2×8 (flange MG90S) |
| `04_arm_root` | 1 | 4× M1,6/M2×5 (squadretta MG90S), vite centrale |
| `05_arm_tip` | 1 | 2× M2×8 |
| `06_hub_centrato` (o `06b_hub_sbalzo50`) | 1 | 4× M2×5 (squadretta), 4× M3×10 + dadi (disco tettuccio) |
| `07_turntable_hub` | 1 | 4× M2×6 (squadretta), 6× M4×12 (disco piattaforma) |
| `08_turntable_servo_mount` | 1 | 4× M3×8 (flange), 4× M4×20 (al tavolo) |
| `09_lamp_pivot` | 1 | 4× M3×8 (flange), 4× M4×20 (al tavolo) |
| `10_lamp_arm_root` | 1 | 4× M2×6 (squadretta) |
| `11_lamp_holder` | 1 | il modulo LED Ø28 entra a pressione; una goccia di colla |

Tempo di stampa totale ≈ 9 h, ≈ 460 g di PETG (compreso il banco demo).

## Cosa NON è nel file e devi fare tu

* Tagliare i tubi: palo Ø10 × 250 mm, braccio Ø8 × 200 mm, braccio lampada Ø10 × 600 mm.
* Disco tettuccio Ø300 in forex 5 mm con 4 fori M3 a ±14 mm dal centro (dima: la piastra del mozzo).
* Disco piattaforma Ø300 in compensato 5 mm con 6 fori M4 a 28 mm dal centro e il foro centrale Ø9 per la vite della squadretta.
* Griglia di carta da incollare sulla piattaforma (10 cm = 1 m).
