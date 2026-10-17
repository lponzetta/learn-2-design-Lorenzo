# Risultati della simulazione

Generato il 2026-10-17 14:03 con `python -m ombrellone.simulate`. Località: Rimini (44.06N, 12.57E), fuso CEST.

## Progetto base

| parametro | valore |
|---|---|
| H | 2.0 |
| L | 1.6 |
| R | 1.5 |
| theta_max_deg | 70.0 |
| beta_max_deg | 70.0 |
| h_min | 1.6 |
| canopy_offset | 0.0 |
| L_min | None |
| L_max | None |
| pole_radius | 0.04 |
| alpha_min_deg | -1000000000.0 |
| alpha_max_deg | 1000000000.0 |
| zona | {'x': 0, 'y': 0, 'r': 1.0} |

## Giornata tipo (15 luglio), zona r = 1 m centrata sul palo

| metrica | valore |
|---|---|
| ore_di_sole_(elev>5°) | 14.0 |
| finestra_copertura_totale | 10:00–16:30 |
| ore_copertura_totale | 6.7 |
| buchi_(copertura_parziale) | 06:20–10:00, 16:40–20:10 |
| copertura_media_tenuta_% | 60.9 |
| copertura_minima_tenuta_% | 0.0 |
| movimenti_al_giorno | 31 |
| corsa_totale_giunti_gradi | 645 |

![giornata](figure/02_giornata_15lug.png)

![istantanee](figure/03_istantanee_15lug.png)

![vista laterale](figure/04_vista_laterale.png)


## Giornata di confronto (21 settembre)

| metrica | valore |
|---|---|
| ore_di_sole_(elev>5°) | 11.2 |
| finestra_copertura_totale | 12:00–14:10 |
| ore_copertura_totale | 2.3 |
| buchi_(copertura_parziale) | 07:30–12:00, 14:20–18:30 |
| copertura_media_tenuta_% | 48.3 |
| copertura_minima_tenuta_% | 0.0 |
| movimenti_al_giorno | 41 |
| corsa_totale_giunti_gradi | 447 |

## Limiti geometrici

![limiti](figure/05_limiti_L_theta.png)

### Varianti di progetto

| variante | ore copertura totale 15 lug | finestra | buchi | elev. min. sole a Sud | a Sud-Est | a Est |
|---|---|---|---|---|---|---|
| Base: H2.0 L1.6 R1.5 θmax 70°, zona centrata | 6.8 h | 10:00–16:30 | - | 44.0° | 44.0° | 44.0° |
| + sbalzo tettuccio 0.6 m | 8.2 h | 09:15–17:15 | - | 38.0° | 38.0° | 38.0° |
| + braccio telescopico 1.2–2.4 m | 7.8 h | 09:30–17:00 | - | 38.0° | 38.0° | 38.0° |
| + tettuccio R 1.8 m | 7.8 h | 09:30–17:00 | - | 41.0° | 41.0° | 41.0° |
| + palo più basso H 1.6 | 7.2 h | 09:45–16:45 | - | 41.0° | 41.0° | 41.0° |
| palo a SUD della zona (zona 1.2 m a Nord del palo) | 6.2 h | 10:15–16:15 | - | 32.0° | 41.0° | 56.0° |
| palo a Sud della zona + sbalzo 0.6 | 7.8 h | 09:30–17:00 | - | 26.0° | 32.0° | 41.0° |
| palo a Sud della zona + sbalzo 0.6 + telescopico 1.2–2.4 | 8.5 h | 09:00–17:30 | 13:15–13:30 | 26.0° | 29.0° | 35.0° |
| palo a NORD della zona (zona 1.2 m a Sud del palo) | 0.0 h | -–- | - | 71.0° | 65.0° | 56.0° |

![varianti](figure/06_varianti.png)


## Meccanica

| massa | kg |
|---|---|
| tettuccio | 4.7 |
| braccio | 2.3 |
| palo | 5.2 |
| snodo | 3.0 |
| elettronica | 1.0 |

| carico (vento 8 m/s = 29 km/h, posa di massimo sbraccio) | valore |
|---|---|
| coppia_inclinazione_Nm | 238 |
| coppia_azimut_Nm | 93 |
| coppia_tettuccio_Nm | 76 |
| momento_base_Nm | 263 |
| forza_vento_tettuccio_N | 223 |

| carico (vento 15 m/s = 54 km/h, parcheggio) | valore |
|---|---|
| coppia_inclinazione_Nm | 169 |
| momento_base_Nm | 422 |

| zavorra richiesta (coeff. sicurezza 1.5) | kg |
|---|---|
| base_r0.4_lavoro_8ms | 107 |
| base_r0.5_lavoro_8ms | 82 |
| base_r0.6_lavoro_8ms | 66 |
| parcheggio 15 m/s, base r=0.5 | 113 |

### Attuatori

```json
{
  "azimut_stepper_vite_senza_fine": {
    "joint": "azimut",
    "holding_torque_Nm": 92.66103578488902,
    "design_torque_Nm": 185.32207156977805,
    "output_speed_rpm": 0.5,
    "gear_ratio": 400,
    "motor_torque_Nm": 1.1582629473111128,
    "power_W": 24.258602441319024,
    "suggestion": "NEMA23 stepper (1.2-1.9 Nm) o DC 24V 60-100 W"
  },
  "inclinazione_attuatore_lineare": {
    "giunto": "inclinazione",
    "forza_N": 1905.3846181936763,
    "corsa_mm": 286.788218175523,
    "velocita_mm_s": 7.169705454388076,
    "braccio_leva_m": 0.25,
    "suggerimento": "attuatore 12/24 V classe 3000-6000 N"
  },
  "tettuccio_attuatore_lineare": {
    "giunto": "tettuccio",
    "forza_N": 1260.7715784701409,
    "corsa_mm": 137.65834472425104,
    "velocita_mm_s": 4.588611490808368,
    "braccio_leva_m": 0.12,
    "suggerimento": "attuatore 12/24 V classe 1500 N"
  }
}
```

![coppie](figure/07_coppie_vento.png)


## Materiali del braccio

| materiale | D [mm] | t [mm] | massa [kg] | freccia [mm] | σ [MPa] | coeff. sicurezza |
|---|---|---|---|---|---|---|
| Al 6061-T6 | 40 | 3 | 1.51 | 47.5 | 78 | 3 |
| Al 6061-T6 | 50 | 3 | 1.91 | 23.5 | 48 | 5 |
| Al 6061-T6 | 60 | 3 | 2.32 | 13.3 | 33 | 7 |
| Al 6061-T6 | 70 | 3 | 2.73 | 8.3 | 24 | 10 |
| Al 6061-T6 | 80 | 3 | 3.14 | 5.5 | 18 | 13 |
| Acciaio S235 | 40 | 2 | 3.00 | 22.5 | 113 | 2 |
| Acciaio S235 | 50 | 2 | 3.79 | 11.4 | 72 | 3 |
| Acciaio S235 | 60 | 2 | 4.58 | 6.6 | 50 | 5 |
| Acciaio S235 | 70 | 2 | 5.37 | 4.1 | 37 | 6 |
| Acciaio S235 | 80 | 2 | 6.16 | 2.8 | 29 | 8 |
| CFRP | 40 | 2 | 0.61 | 40.5 | 105 | 5 |
| CFRP | 50 | 2 | 0.77 | 20.2 | 66 | 8 |
| CFRP | 60 | 2 | 0.93 | 11.5 | 45 | 11 |
| CFRP | 70 | 2 | 1.09 | 7.2 | 33 | 15 |
| CFRP | 80 | 2 | 1.25 | 4.8 | 25 | 20 |
| GFRP | 40 | 3 | 1.06 | 92.6 | 77 | 4 |
| GFRP | 50 | 3 | 1.35 | 45.6 | 47 | 6 |
| GFRP | 60 | 3 | 1.63 | 25.8 | 32 | 9 |
| GFRP | 70 | 3 | 1.92 | 16.0 | 23 | 13 |
| GFRP | 80 | 3 | 2.21 | 10.6 | 18 | 17 |

![materiali](figure/08_materiali.png)


## FEM telaio

```json
{
  "freccia_punta_mm": 19.37653302643836,
  "sigma_max_MPa": 33.24567814713745,
  "sigma_amm_Al_MPa": 240.0
}
```

![fem](figure/09_fem.png)


## Leggi di scala per il mini (1:10)

```json
{
  "scala_lunghezze": 0.1,
  "H_m": 0.2,
  "L_m": 0.16000000000000003,
  "R_m": 0.15000000000000002,
  "fattore_aree_e_forze_vento": 0.010000000000000002,
  "fattore_masse": 0.0010000000000000002,
  "fattore_momenti_gravita": 0.00010000000000000002,
  "fattore_momenti_vento": 0.0010000000000000002,
  "nota": "a parita' di vento il mini e' relativamente PIU' robusto: valida software e cinematica, non la struttura"
}
```
