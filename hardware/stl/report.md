# Parti stampabili — report di generazione

Generato da `python hardware/build_parts.py`. Ogni STL e' gia' orientato per la stampa (z=0 sul piatto).

| file | descrizione | ingombro x·y·z [mm] | volume [cm³] | PETG ≈ g (30 % riempimento) | chiusa | sporgenze > 45° [cm²] |
|---|---|---|---|---|---|---|
| `01_base.stl` | base del modello: servo azimut MG996R 270°, 4 viti M4 alla piattaforma | 110 · 90 · 44 | 387.3 | 246 | sì | 5.3 |
| `02_pole_hub.stl` | mozzo del palo sulla squadretta rotonda; incollare il tubo Ø10 | 40 · 40 · 30 | 15.1 | 10 | sì | 0.1 |
| `03_pole_top.stl` | cima del palo: tasca MG90S (inclinazione), albero orizzontale | 34 · 42 · 68 | 28.5 | 18 | sì | 7.9 |
| `04_arm_root.stl` | radice del braccio sulla squadretta MG90S; incollare il tubo Ø8 | 56 · 24 · 14 | 6.1 | 4 | sì | 6.1 |
| `05_arm_tip.stl` | punta del braccio: tasca MG90S (testa), albero perpendicolare al braccio | 33 · 42 · 69 | 27.6 | 18 | sì | 7.5 |
| `06_hub_centrato.stl` | mozzo tettuccio centrato: piastra 40x40 4xM3 + 8 stecche Ø2 | 40 · 40 · 37 | 18.0 | 11 | sì | 3.0 |
| `06b_hub_sbalzo50.stl` | mozzo tettuccio con sbalzo 50 mm (variante) | 40 · 82 · 37 | 21.5 | 14 | sì | 3.3 |
| `07_turntable_hub.stl` | banco demo: mozzo piattaforma sulla squadretta MG996R, 6 viti M4 | 70 · 70 · 8 | 29.4 | 19 | sì | 0.0 |
| `08_turntable_servo_mount.stl` | banco demo: supporto del servo piattaforma, 4 viti M4 al tavolo | 80 · 60 · 44 | 167.5 | 106 | sì | 3.5 |
| `09_lamp_pivot.stl` | banco demo: colonna del braccio lampada, tasca MG996R orizzontale | 82 · 105 · 73 | 192.2 | 122 | sì | 19.1 |
| `10_lamp_arm_root.stl` | banco demo: attacco braccio lampada (tubo Ø10) sulla squadretta | 69 · 30 · 17 | 9.7 | 6 | sì | 9.9 |
| `11_lamp_holder.stl` | banco demo: porta-LED Ø28 in punta al tubo Ø10 | 34 · 34 · 52 | 11.4 | 7 | sì | 0.6 |

## Regole usate

```
wall: 3.0
fit_tube: 0.35
fit_servo: 0.4
fit_horn: 0.5
hole_m2_tap: 1.8
hole_m3_tap: 2.6
hole_m3_clear: 3.4
hole_m4_clear: 4.4
max_overhang_deg: 45
bed: (220, 220, 250)
```

Servo: MG996R (corpo 40.5×20×38, flange a 27.5 mm dal fondo, fori 49.5×10 → M3 autofilettanti 2.6 mm), MG90S (corpo 22.8×12.2×22.5, flange a 16 mm dal fondo, fori a 28 mm → M2 autofilettanti 1.8 mm). Tubi carbonio Ø10 (palo, braccio lampada) e Ø8 (braccio), gioco 0.35 mm, incollare con epossidica.
