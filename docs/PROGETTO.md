# Ombrellone magico — documento di progetto

Un ombrellone che tiene **ferma l'ombra** mentre il sole si muove: scegli dall'app
la zona da proteggere (di default centrata sul palo), lui conosce posizione GPS e
orario, calcola dove sarà il sole e sposta braccio e tettuccio da solo.

Questo documento raccoglie: il concetto, l'algoritmo (con i limiti geometrici e
la risposta a "fino a che ora ce la fa"), lo studio meccanico-robotico, i
materiali, l'elettronica, come costruire un **mini-prototipo** e cosa comprare,
più idee e suggerimenti. I numeri citati vengono dalla simulazione del
pacchetto `ombrellone/` (vedi `risultati.md`, rigenerabile con
`python -m ombrellone.simulate`).

---

## 1. Idea e requisiti

| requisito | scelta di progetto |
|---|---|
| forma del tettuccio | **disco circolare** di raggio R (3 m di diametro nel progetto base) |
| struttura | **palo fisso** verticale (H) + **braccio** rigido (L) con snodo a 2 gradi di libertà in cima al palo (rotazione in azimut α, inclinazione θ) + **testa** del tettuccio a 2 gradi di libertà (inclinazione β, direzione γ) |
| zona da coprire | cerchio di raggio r_t (1 m nel progetto base: un lettino da 2 × 0.8 m ci sta) centrato dove vuoi, di default sul palo |
| limiti meccanici | θ ≤ θ_max (70°), β ≤ β_max (70°), quota del bordo più basso del tettuccio ≥ h_min (1.6 m), nessuna collisione col palo |
| intelligenza | GPS + orologio (NTP/RTC) → posizione del sole → posa dei giunti → attuatori. Nessuna telecamera, nessun sensore di luce obbligatorio |
| app | pianta vista dall'alto: trascini il cerchio dell'ombra; l'ombrellone ti dice subito "copertura totale fino alle 16:30" |
| comfort | si muove solo quando serve (isteresi), al massimo ogni 10 minuti salvo emergenza |

**Che cosa è fisicamente possibile.** L'ombra di un disco illuminato da raggi
paralleli è un'**ellisse** a terra. Con il tettuccio orizzontale l'ombra è un
cerchio uguale al tettuccio (raggio R) spostato di `z/tan(h)` verso il lato
opposto al sole (z = quota del tettuccio, h = elevazione del sole). Con il
tettuccio rivolto verso il sole l'ombra si allunga nella direzione del sole fino
a `R/sin(h)`. Per tenere l'ombra ferma quindi il **centro del tettuccio deve
stare sulla retta che va dal centro della zona verso il sole**: più il sole è
basso, più il tettuccio deve essere lontano in orizzontale e/o basso. È da qui
che nascono i limiti.

---

## 2. Architettura del sistema

```
 GPS (lat, lon) ─┐
 ora (NTP/RTC) ──┼─► posizione del sole (elev, azimut) ─► solver cinematico ─► posa (α, θ, β, γ)
 zona scelta ────┘        (algoritmo NOAA, err. < 0.05°)      (analitico + numerico,         │
   dall'app                                                     con limiti e margine)        ▼
                                                                                  attuatori + encoder/finecorsa
 anemometro ──► se vento > soglia: parcheggio (braccio verticale, tettuccio orizzontale)
 IMU/magnetometro (opz.) ──► calibrazione del Nord e della verticale
```

Tutto il calcolo gira comodamente su un ESP32: la soluzione analitica costa
poche centinaia di operazioni, il raffinamento numerico qualche decina di
migliaia. Il firmware in `firmware/ombrellone_esp32/` implementa esattamente lo
stesso algoritmo del pacchetto Python (stessi nomi, stessi risultati).

---

## 3. Algoritmo (il "software proprietario")

### 3.1 Posizione del sole
Algoritmo NOAA (Meeus semplificato): giorno giuliano → longitudine media,
anomalia, equazione del centro, obliquità → declinazione ed equazione del tempo →
angolo orario → zenit e azimut, con correzione per rifrazione. Validato contro
`pvlib` con errore < 0.05° (`tests/test_solar.py`). Il disco solare è largo
0.53°, quindi è più che sufficiente.

### 3.2 Cinematica diretta (terna ENU: x=Est, y=Nord, z=Su)
```
P = (0, 0, H)                                 cima del palo
E = P + L · d(α, θ)                           estremità del braccio
C = E + e · û(α)                              centro del tettuccio (e = sbalzo opzionale)
n = d(γ, β)                                   normale del tettuccio
d(a, t) = (sin t sin a, sin t cos a, cos t)
```

### 3.3 Ombra e copertura
Proiezione del disco (C, n, R) lungo il versore solare s su z = 0:
`G = C − s·C_z/s_z` è il centro dell'ombra, `M = [proj(R u₁) − G, proj(R u₂) − G]`
una matrice 2×2 tale che il bordo è `G + M·(cos φ, sin φ)`. Un punto Q è in
ombra se `ρ(Q) = ‖M⁻¹(Q − G)‖ ≤ 1`.

Due metriche per la zona (cerchio di raggio r_t):
* **margine** `= 1 − max ρ` sui 72 punti del bordo della zona: ≥ 0 significa
  **copertura totale** (l'ellisse è convessa, basta il bordo); `margine · r_t` è
  in metri. Il progetto base ha 0.5 m di margine con sole alto.
* **copertura** = frazione dei 400 punti del disco zona in ombra (quando la
  copertura totale è impossibile, è quello che si massimizza).

### 3.4 Soluzione analitica (quella che gira sul microcontrollore)
Il centro del tettuccio deve stare in `C = T + λ·s` (T = centro zona, a terra) e
contemporaneamente a distanza L dalla cima del palo:
`|T + λ s − P|² = L²` → equazione di 2° grado in λ; si prende la radice più
alta. Da C si ricavano α e θ; il tettuccio si orienta verso il sole
(β = 90° − h, γ = azimut del sole), poi β viene ridotto finché il bordo basso
rispetta h_min. Con lo sbalzo e ≠ 0 si itera 3-4 volte (converge subito).

### 3.5 Quando i limiti mordono
Se θ > θ_max (o la quota minima non è rispettata) la soluzione esatta non
esiste. Allora un **ottimizzatore** (Nelder-Mead multi-start in Python,
pattern search sul microcontrollore) cerca nei 4 giunti la posa che massimizza
`copertura + margine` con penalità sui vincoli. In pratica: braccio a fine corsa
verso il sole, tettuccio inclinato per allungare l'ellisse verso la zona.
Il risultato è "l'ombra più vicina possibile a quella richiesta".

### 3.6 Isteresi (per chi dorme)
Ogni 15 s il controllo valuta la posa **tenuta**: si muove solo se il margine
è sceso sotto `margin_move` (5 % del raggio zona = 5 cm) e sono passati almeno
10 minuti dall'ultimo movimento (salvo copertura < 97 %). Nella giornata tipo
risultano circa **30 movimenti** per 650° di corsa totale dei giunti: con
attuatori a vite senza fine sono impercettibili.

### 3.7 "Dopo una certa ora non ce la fa più"
La condizione esatta per l'ombra centrata sotto il palo (zona centrata, tettuccio
orizzontale) è `tan h = (H + L cos θ)/(L sin θ)`. Con H = 2, L = 1.6, θ = 70°
serve h ≥ 59°; il margine R − r_t e l'inclinazione del tettuccio la abbassano a
**44°**. Il firmware calcola ogni mattina la finestra oraria e la mostra
nell'app ("copertura totale possibile oggi: 10:00–16:30").

---

## 4. Risultati chiave della simulazione (progetto base, Rimini)

Progetto base: H = 2.0 m, L = 1.6 m, R = 1.5 m, θ_max = 70°, β_max = 70°,
h_min = 1.6 m, zona r = 1 m centrata sul palo.

| grandezza | 15 luglio | 21 settembre |
|---|---|---|
| elevazione minima del sole per copertura totale | 44° | 44° |
| finestra di copertura totale | **10:00 – 16:30** (6.7 h) | **12:00 – 14:10** (2.3 h: a settembre il sole a mezzogiorno arriva a 46°) |
| copertura media della zona nelle ore di sole | 61 % | 48 % |
| movimenti al giorno (con isteresi) | 31 | 41 |

Figure: `figure/02_giornata_15lug.png` (giornata), `03_istantanee_15lug.png`
(pianta ora per ora), `04_vista_laterale.png` (sezione), `05_limiti_L_theta.png`
(mappa L × θ_max), `06_varianti.png` (quanto rende ogni variante).

**Lettura onesta del risultato:** un ombrellone "classico" di 3 m con braccio da
1.6 m tiene in ombra totale un lettino solo con sole sopra ~44°, cioè in piena
estate dalle 10 alle 16:30. Fuori da quella finestra copre parzialmente e
l'ombra "scappa" verso il lato opposto al sole. Non è un difetto del software:
è geometria. La sezione 5 dice cosa cambia davvero le carte in tavola.

---

## 5. Cosa aiuta davvero (classifica delle leve)

Dallo sweep sulle varianti (`figure/06_varianti.png` e `risultati.md`):

1. **Posizione del palo: mettilo sul lato del sole (a Sud della zona).**
   Zona 1.2 m a Nord del palo: elevazione minima **31°** a mezzogiorno invece di
   44°. È la leva gratis. Attenzione: di mattina/sera (sole a Est/Ovest) il
   vantaggio si riduce, per questo l'app suggerisce l'orientamento.
   Mettere il palo a Nord della zona è invece la scelta peggiore (71°).
2. **Sbalzo orizzontale del tettuccio** (il centro del tettuccio è spostato di
   0.6 m lungo il braccio, come negli ombrelloni "a braccio"): da 44° a 36°.
   È più efficiente dell'allungare il braccio perché **non alza il tettuccio**.
   Controindicazione: uno sbalzo fisso crea una **zona morta** vicino al palo
   quando il sole è alto (il centro del tettuccio non può avvicinarsi al palo
   meno dello sbalzo). Soluzione: sbalzo **telescopico** (terzo grado di libertà
   lineare) oppure sbalzo ≤ R − r_t così il margine lo assorbe.
3. **Braccio telescopico 1.2–2.4 m**: da 44° a 38°. Buono ma pesa e costa.
4. **Tettuccio più grande (R 1.8)**: 39°. Semplice, ma vento e coppie salgono
   col quadrato del raggio.
5. **θ_max 85°** (braccio quasi orizzontale): 39°. Serve un braccio molto
   rigido e un attuatore più forte.
6. **Palo più basso (H 1.6)**: 41°. La quota conta poco perché il tettuccio
   deve comunque stare sopra le teste.
7. **Abbassare h_min** non serve a niente: il limite è lo sbraccio, non la quota.

**Gradi di libertà "mobili" (nel simulatore: casella "telescopico"/"mobile").**
Invece di fissare L e sbalzo, si dà un intervallo e il solver sceglie il valore
migliore istante per istante (piccolo con sole alto, massimo con sole basso):
così non c'è zona morta. Sul 15 luglio a Rimini, zona centrata:

| gradi di libertà | finestra di copertura totale |
|---|---|
| progetto base (tutto fisso) | 10:00–16:40 (6.7 h) |
| + braccio telescopico 1.6–2.4 m | 09:30–17:20 (7.8 h) |
| + sbalzo mobile 0–0.8 m (carrello sotto il tettuccio) | **08:40–18:00 (9.3 h)** |
| + palo telescopico 2.0–2.6 m | nessun guadagno (l'altezza non aiuta) |

Oltre si va solo con un meccanismo diverso (sezione 10: carrello a terra o rotaia).

---

## 6. Studio meccanico-robotico

### 6.1 Masse (progetto base)
| componente | kg | note |
|---|---|---|
| tettuccio (tela acrilica 300 g/m², 8 stecche Al 12×1, mozzo con motori) | ≈ 4.7 | 7 m² di tela |
| braccio tubo Al 6061 Ø60×3, 1.6 m | ≈ 2.3 | |
| palo tubo Al Ø80×4, 2.0 m | ≈ 5.2 | |
| snodo in cima al palo (2 attuatori + cuscinetto) | ≈ 3 | |
| elettronica + batteria | ≈ 1–3 | |

### 6.2 Vento: il vero dimensionante
Forza su un disco: `F = ½ ρ v² C_N A`, C_N ≈ 1.17 perpendicolare, minimo
0.35 radente (portanza della tela bombata), più una resistenza tangenziale
C_T ≈ 0.1 (bordo, stecche, tela che sventola). Con R = 1.5 m e 8 m/s (29 km/h,
Beaufort 5) la forza sul tettuccio arriva a **≈ 220 N**; a 12 m/s (43 km/h) a
500 N. Posa di massimo sbraccio (θ = 70°, tettuccio inclinato 39°), direzione
del vento peggiore per ogni grandezza (`figure/07_coppie_vento.png`):

| vento | coppia giunto inclinazione | coppia azimut | momento alla base | zavorra base Ø1 m (coeff. 1.5) |
|---|---|---|---|---|
| 5 m/s (18 km/h) | 146 N·m | 36 N·m | 156 N·m | 49 kg |
| **8 m/s (29 km/h)** | **238 N·m** | **93 N·m** | **263 N·m** | **82 kg** |
| 12 m/s (43 km/h) | 428 N·m | 208 N·m | 485 N·m | 150 kg |
| 8 m/s in parcheggio (braccio verticale, tettuccio orizzontale) | 48 N·m | – | 120 N·m | 20 kg |
| 15 m/s (54 km/h) in parcheggio | 169 N·m | – | 422 N·m | 113 kg |

Conseguenze di progetto:
* **Limite operativo 8 m/s** e **parcheggio automatico** sopra (anemometro a
  coppette da 10 €, o stima dalla corrente degli attuatori). In parcheggio le
  coppie crollano di un ordine di grandezza: è la stessa regola degli ombrelloni
  da bar, solo automatica.
* **Zavorra 80–100 kg** con base Ø1 m per lavorare fino a 8 m/s (base a croce
  con 4 piastre da 20–25 kg, oppure fissata a una pedana/interrata). È la cifra
  degli ombrelloni a braccio in commercio, non è un'anomalia del progetto.
  Per restare **aperto** a 15 m/s servirebbero 110+ kg: sopra 12 m/s conviene
  **chiudere** il tettuccio (manovella motorizzata), esattamente come si fa a mano.
* Gli attuatori devono essere **autobloccanti** (vite senza fine o vite a
  ricircolo): a motore spento il vento non deve muoverli.

### 6.3 Attuatori (dimensionamento in `risultati.md`, sezione "Attuatori")
| giunto | coppia di progetto (×2) | soluzione consigliata |
|---|---|---|
| inclinazione braccio θ | 480 N·m | **attuatore lineare 12/24 V** su leva da 25 cm → ≈ 1900 N, corsa ≈ 29 cm, 7 mm/s. Classe "3000 N", autobloccante, 60–90 € |
| rotazione azimut α | ≈ 185 N·m (vento laterale, centro di pressione eccentrico) | **ralla a vite senza fine** ("slew drive" da 3", autobloccante, 100–150 €) con motoriduttore DC 24 V, oppure vite senza fine 1:100 + cinghia 1:4 su stepper NEMA23; 0.5 giri/min bastano (il sole fa 15°/h) |
| inclinazione tettuccio β | ≈ 150 N·m | attuatore lineare classe 1500 N su leva da 12 cm, corsa 14 cm (30–40 €) |
| direzione tettuccio γ | piccola | motoriduttore + vite senza fine; **opzionale**: con zona centrata γ ≈ α e si può bloccare meccanicamente γ = α (3 motori invece di 4) |

Velocità: tutto molto lento (giri/min frazionari). La potenza di picco è
≈ 40–60 W per attuatore (3–5 A a 12 V), per qualche decina di secondi.

### 6.4 Energia
≈ 30 movimenti/giorno × 30 s × 50 W ≈ 12 Wh + elettronica 24 h × 1 W ≈ 24 Wh →
**≈ 40 Wh/giorno**. Batteria LiFePO4 12 V 7 Ah (90 Wh) = 3 giorni; un
**pannello solare da 20–30 W** cucito sul tettuccio (sempre orientato al sole!)
la ricarica in 2 ore. Dettaglio elegante: il tettuccio che insegue il sole è un
inseguitore solare gratis.

### 6.5 Struttura (braccio e palo)
Verifica a mensola e **FEM a telaio piano** (travi di Eulero-Bernoulli, palo
incastrato + braccio, `mechanics.frame_fem`), vento 8 m/s, θ = 70°:

| braccio | massa | freccia in punta (mensola) | tensione | coeff. sicurezza |
|---|---|---|---|---|
| **Al 6061-T6 Ø60×3** | 2.3 kg | 13 mm (19 mm col FEM, che include la flessione del palo Ø80×4) | 33 MPa | 7 |
| Al 6061-T6 Ø70×3 | 2.7 kg | 8 mm | 24 MPa | 10 |
| Al 6061-T6 Ø40×3 | 1.5 kg | 47 mm | 78 MPa | 3 |
| acciaio S235 Ø50×2 | 3.8 kg | 11 mm | 72 MPa | 3 |
| carbonio Ø50×2 | 0.8 kg | 20 mm | 66 MPa | 8 |

Il braccio **non è critico a resistenza** (il vento dimensiona zavorra e
attuatori, non il tubo): si sceglie per rigidezza (freccia < 20 mm, altrimenti
l'ombra balla) e per il peso, che entra nelle coppie. Al Ø60×3 è il compromesso
giusto; il carbonio dimezza la massa ma costa 10× e teme urti/UV.
`figure/08_materiali.png` e `09_fem.png`.

### 6.6 Sicurezza
* Finecorsa meccanici su θ e β + encoder (o potenziometro) per sapere dove sei
  dopo un blackout; IMU sul braccio come conferma.
* Limitazione di corrente sugli attuatori (rilevazione di ostacolo: una persona
  che tocca il tettuccio).
* Vento: parcheggio sopra 8 m/s, chiusura (se il tettuccio è richiudibile)
  sopra 12 m/s, allarme in app.
* Normativa per un prodotto vero: Direttiva Macchine 2006/42/CE (parti in
  movimento motorizzate), EMC/RED per WiFi/BLE, EN 13561 come riferimento per le
  classi di vento delle tende da sole.

---

## 7. Materiali (scelte consigliate)

| parte | materiale | perché |
|---|---|---|
| palo e braccio | tubo alluminio 6061-T6 anodizzato | leggero, non arrugginisce, saldabile, standard degli ombrelloni |
| snodi, perni, viteria | inox AISI 304/316 | salsedine |
| tettuccio | tela acrilica tinta in massa 300 g/m² (o poliestere 180 g/m² per il mini) | UV, idrorepellente |
| stecche | alluminio 12×1 o vetroresina pultrusa | flessibili e leggere |
| carter degli attuatori | PA6-GF o ABS/ASA stampato (ASA resiste agli UV) | |
| base | ghisa/acciaio zincato con zavorra, oppure piastra da interrare | |
| mini-prototipo | PETG/ASA stampati 3D + aste in carbonio Ø8 | |

---

## 8. Elettronica e firmware

| funzione | componente |
|---|---|
| cervello + WiFi/BLE | **ESP32** (DevKit o ESP32-S3) |
| ora | NTP via WiFi + **RTC DS3231** per quando non c'è rete |
| posizione | **GPS u-blox NEO-M8N** (o NEO-6M); oppure la prendi dal telefono una volta sola e la salvi (un ombrellone non si sposta) |
| orientamento | **magnetometro QMC5883L** per il Nord (o calibrazione "punta il braccio al sole" con un tocco nell'app, implementata nel firmware) + **IMU MPU-6050** sul braccio per la verticale |
| vento | anemometro a coppette (uscita a impulsi) |
| attuatori | ponti H (BTS7960 per gli attuatori lineari, driver TMC2209/DRV8825 per gli stepper) |
| feedback | potenziometri interni agli attuatori lineari, encoder magnetico AS5600 sull'azimut |
| alimentazione | LiFePO4 12 V + regolatore buck 5 V + MPPT per il pannello |

Firmware (`firmware/ombrellone_esp32/`): posizione del sole, solver, isteresi,
parcheggio, web app (pianta con cerchio trascinabile, raggio, "copertura totale
possibile oggi"), calibrazione del Nord, salvataggio delle impostazioni in
flash, modalità Access Point se non c'è WiFi. Primo passo verso l'app: la pagina
web servita dall'ESP32 funziona già sul telefono; una vera app (Flutter/React
Native) parla alla stessa API JSON (`/status`, `/set`, `/window`, `/park`,
`/calib`).

---

## 9. Il mini-prototipo (scala 1:10)

**Obiettivo:** validare software, cinematica e app con un modello da tavolo;
le leggi di scala dicono che a parità di vento le forze scendono di 100× e le
coppie di 1000–10000×, quindi il mini **non** valida la struttura: per quella
servono i calcoli della sezione 6 e poi un prototipo in scala 1:2.

### 9.1 Geometria del mini
H = 20 cm, L = 16 cm, R = 15 cm (tettuccio Ø30 cm), sbalzo 5 cm, zona r = 10 cm.
Stessi angoli limite del reale (già nel `config.h`).

### 9.2 Passi
1. **Software a tavolino (fatto)**: `python -m pytest`, `python -m ombrellone.simulate`,
   `docs/simulatore.html` per giocare con i parametri.
2. **Stampa 3D** di: base con alloggio ESP32 e batteria; palo (o tubo Al Ø16);
   snodo a 2 assi in cima al palo (servo azimut con cuscinetto 6806 o ralla
   stampata + servo inclinazione); testa del tettuccio a 2 assi (2 micro servo);
   mozzo del tettuccio con 8 fori per le stecche.
3. **Tettuccio**: disco di foam/cartoncino rigido Ø30 cm per le prime prove
   (ombra netta, zero massa), poi tela di poliestere su stecche in carbonio Ø2.
4. **Elettronica**: ESP32 + 4 servo + RTC + (opz.) GPS/magnetometro su
   breadboard; alimentazione servo separata 5–6 V ≥ 3 A (powerbank "PD" o
   2×18650 con buck); GND in comune.
5. **Firmware**: imposta WiFi, lat/lon e i trim dei servo in `config.h`;
   carica con Arduino IDE (scheda "ESP32 Dev Module", librerie ESP32Servo).
6. **Calibrazione** (5 minuti, al sole):
   * metti il braccio verticale e il tettuccio orizzontale (`/park`), regola i
     trim finché sono davvero verticale/orizzontale (livella del telefono);
   * ruota il braccio con `/calib?servo=NN` finché la sua ombra è allineata
     all'ombra del palo, poi `/calib`: il firmware ricava l'offset del Nord
     dall'azimut del sole a quell'ora;
   * apri la pagina, trascina il cerchio e guarda l'ombra.
7. **Test di validazione**: fotografa l'ombra ogni 15 minuti per una giornata
   con un foglio quadrettato sotto: la zona cerchiata deve restare in ombra
   entro la finestra prevista dall'app, e l'app deve aver predetto giusto
   l'orario in cui comincia a scappare.
8. **Test al chiuso** (di sera): una lampada a 3–4 m simula il sole; non è a
   raggi paralleli, quindi l'ombra è più grande ma il centro è giusto. Utile
   per testare i movimenti senza aspettare il bel tempo (si imposta l'ora con
   `/time?epoch=...`).

### 9.3 Lista della spesa (mini) — circa 80–120 €
| pezzo | q.tà | prezzo indicativo | note |
|---|---|---|---|
| ESP32 DevKit (o ESP32-S3) | 1 | 8–12 € | |
| servo MG996R o DS3218 (azimut e inclinazione braccio) | 2 | 8–15 € l'uno | prendi la versione **270°** per l'azimut |
| micro servo SG90/MG90S (testa tettuccio) | 2 | 3–5 € l'uno | |
| modulo RTC DS3231 | 1 | 3 € | |
| GPS NEO-6M/M8N | 1 | 10–20 € | opzionale, puoi scrivere lat/lon a mano |
| magnetometro QMC5883L (GY-271) | 1 | 3 € | opzionale, c'è la calibrazione manuale |
| IMU MPU-6050 | 1 | 3 € | opzionale |
| buck 5 V 3 A (o UBEC) + 2×18650 con portabatterie, o powerbank | 1 | 10–15 € | i servo NON vanno alimentati dall'ESP32 |
| cuscinetto 6806 (30×42×7) per la ralla | 1 | 4 € | |
| aste carbonio Ø8 (palo/braccio) e Ø2 (stecche) | – | 10 € | aste da aquilone |
| filamento PETG/ASA | ~200 g | 5 € | |
| tela poliestere o foam Ø30 cm, viti M3, cavi Dupont, breadboard | – | 10 € | |
| fotoresistenze ×4 (per l'idea 10.2) | 4 | 2 € | opzionale |

Alternativa più "pulita": una scheda **ESP32 + driver servo PCA9685** (16 canali,
5 €) e un'unica alimentazione 6 V.

### 9.4 Dopo il mini: scala 1:2 da giardino (budget 400–700 €)
Tettuccio Ø1.5 m (un ombrellone da 1.5 m smontato), palo Al Ø50, braccio Al
Ø40, 2 attuatori lineari 12 V da 150 mm/750 N (25 € l'uno), motoriduttore con
vite senza fine per l'azimut, base con 25 kg di zavorra, ESP32 + BTS7960, batteria
12 V. A questa scala il vento comincia a farsi sentire: è il banco di prova per
anemometro e parcheggio automatico.

---

## 10. Idee e suggerimenti

1. **Palo "a Sud" come regola nell'app.** All'installazione l'app mostra la
   rosa dei venti e dice: "per questa zona, piazza il palo qui". Guadagni 13°
   di elevazione gratis.
2. **Controllo ibrido feed-forward + feedback.** Quattro fotoresistenze sul
   mozzo del tettuccio (sopra, lato sole) misurano se la normale punta davvero al
   sole e correggono gli errori di calibrazione del Nord e della verticale: il
   modello astronomico fa il 95 %, i sensori l'ultimo grado. Costa 2 €.
3. **Sbalzo telescopico invece del braccio telescopico**: un carrello lineare
   sotto il tettuccio (cinghia + stepper) sposta il tettuccio lungo il braccio.
   È il grado di libertà che vale di più per euro speso e risolve la zona morta.
4. **Sfruttare l'ellisse.** Un lettino è 2 × 0.8 m: nell'app la zona potrebbe
   essere un rettangolo orientato. Con il tettuccio inclinato l'ombra si allunga
   lungo la direzione del sole: se il lettino è messo con l'asse lungo
   Nord-Sud, la copertura dura di più. Il solver lo gestirebbe già (basta
   cambiare i punti di bordo).
5. **Modalità "seguimi"**: la zona è la posizione GPS del telefono (precisione
   2–3 m, troppo poca da sola) corretta con UWB/BLE o, più semplicemente,
   scegliendo tra 2–3 zone salvate ("lettino", "tavolo", "culla").
6. **Modalità "ombra a tempo"**: "voglio ombra fino alle 15, poi lasciami al
   sole" oppure "tienimi al sole il lato destro" (inversione del problema:
   massimizza la luce su una zona). Stesso solver, segno cambiato.
7. **Pannello solare sul tettuccio**: insegue il sole per costruzione; 30 W
   bastano a rendere il prodotto senza cavi.
8. **Chiusura automatica** di notte e con vento forte: il tettuccio deve essere
   richiudibile come un ombrellone normale (manovella motorizzata). È la
   funzione che vende di più ai bagni (stabilimenti balneari): file di ombrelloni
   che si aprono alle 8 e si chiudono alle 19 da soli.
9. **Multi-ombrellone**: in uno stabilimento ogni ombrellone conosce i vicini e
   coordina le inclinazioni per non toccarsi (il controllo collisioni col palo è
   già il mattone di base).
10. **Alternative meccaniche per andare sotto i 30° di sole**: (a) palo
    inclinabile alla base (un terzo asse grosso in basso, come le gru); (b)
    tettuccio su rotaia circolare a terra attorno alla zona (sbraccio illimitato
    ma ingombro); (c) due tettucci più piccoli. Vale la pena solo per usi
    specifici (culle, terrazze).
11. **Brevetto e concorrenza**: esistono ombrelloni "inseguitori di sole"
    (ad es. lo Shadecraft Sunflower, con pannelli e app) ma inseguono il sole
    con il tettuccio, **non tengono ferma l'ombra su una zona scelta**: la
    combinazione "zona scelta dall'app + solver geometrico con limiti + finestra
    oraria predetta" è il cuore da proteggere (ricerca preliminare su Espacenet
    con le parole chiave "umbrella sun tracking shadow target").
12. **Rumore**: attuatori lineari a vite e stepper con driver silenziosi
    (TMC2209) a velocità bassissime sono praticamente muti; evita i servo
    hobbistici nel prodotto finale (ronzano quando tengono la posizione).

---

## 11. Roadmap

| fase | cosa | durata indicativa |
|---|---|---|
| 0 | software + simulatore (questo repo) | fatto |
| 1 | mini 1:10 stampato in 3D, 4 servo, web app, test di una giornata | 2–3 fine settimana |
| 2 | scala 1:2 con attuatori lineari, anemometro, parcheggio, batteria + pannello | 1–2 mesi |
| 3 | prototipo 1:1 con tettuccio Ø3 m, base zavorrata, prove di vento, app nativa | 3–6 mesi |
| 4 | industrializzazione: carter, certificazioni (Macchine, EMC/RED), variante per stabilimenti | – |

---

## Appendice: formule rapide

* Spostamento dell'ombra di un tettuccio orizzontale a quota z con sole a
  elevazione h: `d = z / tan h` (z = 3 m, h = 30° → 5.2 m!).
* Allungamento dell'ombra con tettuccio inclinato di β verso il sole:
  semiasse lungo il sole = `R · sin(h + β) / sin h` (massimo per β = 90° − h).
* Condizione di ombra centrata sotto il palo (tettuccio orizzontale):
  `tan h = (H + L cos θ) / (L sin θ)`.
* Forza del vento: `F = 0.613 · v² · C_N · π R²` [N, v in m/s].
* Freccia di una mensola tubolare: `δ = F L³ / (3 E I)`, `I = π (D⁴ − d⁴) / 64`.
