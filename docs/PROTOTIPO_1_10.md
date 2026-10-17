# Prototipo 1:10 da tavolo — guida di costruzione e demo per investitori

Obiettivo: un modello da scrivania, alto 40 cm, che **fa vedere in 3 minuti**
quello che il prodotto fa in una giornata: la lampada-sole percorre il suo arco,
l'ombrellone si muove da solo e l'ombra resta sul lettino. Poi, dal telefono,
sposti il cerchio dell'ombra e l'ombrellone si riassesta.

Tutto quello che serve è in questo repository:

| cosa | dove |
|---|---|
| parti stampabili in 3D (parametriche, OpenSCAD) | `hardware/scad/*.scad` |
| firmware ESP32 con web app e **modalità demo** (giornata accelerata, sole artificiale) | `firmware/ombrellone_esp32/` |
| simulatore per la presentazione (stagionalità, mappamondo) | `docs/simulatore.html` |
| numeri per il pitch | `docs/risultati.md`, `docs/stagionalita.md` |

Budget: **≈ 150–200 €** (modello + banco demo), **3 fine settimana**.

---

## 1. Che cosa costruisci

```
                 lampada LED (il "sole")  ●
                                        /   braccio lampada 60 cm, servo di elevazione
                                       /
            tettuccio Ø30 cm  ========●=====          perno della lampada
                     braccio 16 cm  /                 (colonna fissa, fuori dalla piattaforma)
                    servo testa  ●/
                                 |  palo 20 cm
        servo inclinazione  ●----|
                                 |
        servo azimut (nella base)|
   ╔═════════════════════════════╧═════════════════════════╗
   ║   piattaforma girevole Ø30 cm (il "mondo che ruota")  ║  servo + lazy susan
   ╚═══════════════════════════════════════════════════════╝
```

Due oggetti:

1. **Il modello dell'ombrellone** (scala 1:10 del progetto base): palo 20 cm,
   braccio 16 cm, tettuccio Ø30 cm con sbalzo 5 cm, **3 servo** (azimut,
   inclinazione braccio, inclinazione tettuccio). Un quarto servo (rotazione
   della testa) è opzionale: con la zona centrata il firmware non ne ha bisogno.
2. **Il banco demo "sole artificiale"**: una piattaforma girevole su cui sta il
   modello (ruota di −azimut: è il mondo che gira sotto il sole) e una lampada
   LED su un braccio con servo di elevazione. L'ESP32 comanda tutto: il
   firmware sa dov'è la lampada e corregge il fatto che è a 60 cm e non
   all'infinito (`solveForLamp` nel firmware).

Scelta di progetto importante: nel mini il servo di azimut sta **nella base** e
fa ruotare l'intero palo. È geometricamente identico allo snodo in cima al palo
del prodotto vero (il palo è un asse verticale) ma è molto più facile da
costruire e tiene il peso in basso.

---

## 2. Lista della spesa

### Modello (≈ 70 €)
| pezzo | q.tà | prezzo | note |
|---|---|---|---|
| ESP32 DevKit V1 (o ESP32-S3) | 1 | 8–12 € | |
| servo MG996R **270°** (azimut) | 1 | 10–15 € | cerca "MG996R 270 degree"; il 180° limita la giornata |
| micro servo MG90S (inclinazione braccio, testa) | 2 | 4–5 € | metallici, non SG90 di plastica |
| tubo carbonio Ø10 × 250 mm (palo) e Ø8 × 200 mm (braccio) | 1 + 1 | 8 € | aste da aquilone/drone; va bene anche alluminio |
| aste carbonio Ø2 × 150 mm (stecche) | 8 | 4 € | oppure disco rigido, vedi sotto |
| disco forex/cartone alveolare 5 mm Ø30 cm (tettuccio demo) | 1 | 3 € | ombra nitida: per la demo è meglio della tela |
| tela poliestere 180 g/m² 40×40 cm (tettuccio "vero") | 1 | 5 € | per la versione fotogenica |
| filamento PETG (o ASA) | 150 g | 4 € | |
| viti M2×8, M3×10, M4×16 con dadi; squadrette servo (in dotazione) | – | 5 € | |
| colla cianoacrilica + epossidica 5 min | – | 6 € | per i tubi nei manicotti |
| cavi Dupont, breadboard piccola o PCB millefori | – | 5 € | |

### Alimentazione ed elettronica (≈ 25 €)
| pezzo | q.tà | prezzo | note |
|---|---|---|---|
| alimentatore 6 V 5 A (o UBEC 5 A) | 1 | 10–12 € | i servo **non** vanno alimentati dall'ESP32 |
| condensatore elettrolitico 1000 µF 10 V | 1 | 1 € | sul bus dei servo |
| modulo RTC DS3231 | 1 | 3 € | ora corretta anche senza WiFi |
| (opz.) driver servo PCA9685 16 canali | 1 | 5 € | cablaggio più pulito, un solo bus 6 V |

### Banco demo (≈ 60 €)
| pezzo | q.tà | prezzo | note |
|---|---|---|---|
| servo MG996R 270° (piattaforma) | 1 | 10–15 € | |
| servo MG996R (elevazione lampada) | 1 | 10 € | 180° bastano |
| lazy susan (cuscinetto girevole) Ø200 mm | 1 | 6 € | porta il peso del modello |
| disco compensato/forex 5 mm Ø300 mm | 1 | 5 € | piattaforma; ci stampi sopra la griglia e il lettino |
| tubo carbonio Ø10 × 600 mm (braccio lampada) | 1 | 6 € | |
| LED COB 3 W bianco freddo con lente 30° + driver 5 V (o torcia LED con zoom) | 1 | 8 € | sorgente piccola = ombra nitida |
| tavola di base 60 × 40 cm (MDF) | 1 | 8 € | tutto avvitato sopra: trasportabile |

Totale ≈ 155 €. Se hai già stampante 3D e un ESP32, ≈ 110 €.

---

## 3. Stampa 3D

**STL definitivi in `hardware/stl/`**, generati da `hardware/build_parts.py`
(modellazione solida parametrica in Python: tasche servo con le quote reali
MG996R/MG90S, giochi per i tubi, fori per le viti, transizioni a 45° per
stampare senza supporti, ogni file già orientato per il piatto). Le istruzioni
di stampa, le tolleranze e la viteria sono in `hardware/stl/README.md`;
`report.md` riporta per ogni pezzo ingombro, volume, massa e sporgenze;
`assieme_modello.png` è l'assieme di controllo.

| file | parte |
|---|---|
| `01_base` | base del modello con tasca MG996R 270° (azimut) e 4 fori M4 |
| `02_pole_hub` | mozzo del palo sulla squadretta, alloggio tubo Ø10 |
| `03_pole_top` | cima del palo: tasca MG90S ad albero orizzontale (inclinazione) |
| `04_arm_root` | radice del braccio sulla squadretta MG90S, alloggio tubo Ø8 |
| `05_arm_tip` | punta del braccio: tasca MG90S (testa), albero perpendicolare al piano del braccio |
| `06_hub_centrato` / `06b_hub_sbalzo50` | mozzo del tettuccio: piastra 40×40 (disco forex) + 8 stecche Ø2 |
| `07`–`11` | banco demo: mozzo e supporto servo della piattaforma, colonna, attacco e porta-LED del braccio lampada |

I sorgenti OpenSCAD in `hardware/scad/` restano come riferimento modificabile,
ma gli STL ufficiali sono quelli generati dallo script (con `python
hardware/build_parts.py` li rigeneri dopo aver cambiato un gioco o una quota).

Convenzione: i tubi in carbonio si **incollano** nei manicotti (epossidica), i
servo si avvitano nelle tasche con viti autofilettanti, le squadrette rotonde si
fissano nelle sedi predisposte.

## 4. Montaggio (ordine consigliato)

1. **Base**: inserisci l'MG996R nella tasca (albero in alto), vite di fissaggio,
   cavo nel passaggio laterale. Avvita la base alla piattaforma (4 viti M4) con
   l'albero esattamente al centro del disco.
2. **Palo**: incolla il tubo Ø10 nel mozzo (`pole_hub`), infila il mozzo sulla
   squadretta rotonda del servo con il servo a **90°** (centro corsa) e il cavo
   del servo di inclinazione dentro la fessura. Incolla `pole_top` in cima:
   l'albero del micro servo deve essere orizzontale.
3. **Braccio**: incolla il tubo Ø8 nella radice (`arm_root`) e nel terminale
   (`arm_tip`); monta il micro servo di inclinazione nella tasca di `pole_top`
   e innesta la radice del braccio sulla sua squadretta con servo a **10°** =
   braccio verticale (poi si regola via software, `THETA_SERVO_ZERO`).
4. **Testa**: micro servo nella tasca di `arm_tip` (albero perpendicolare al
   piano del braccio); squadretta a croce → `hub`. Con servo a 90° il tettuccio
   è perpendicolare al braccio (`BETA_SERVO_ZERO`).
5. **Tettuccio**: per la demo, disco di forex Ø30 cm avvitato al mozzo con 4
   viti M3 (centro del disco a 50 mm dal perno della testa: è lo sbalzo). Per la
   versione bella: 8 stecche Ø2 incollate nel mozzo e tela cucita a 8 spicchi.
6. **Banco**: lazy susan avvitata al tavolo, piattaforma sopra; `turntable_hub`
   al centro sotto la piattaforma, sulla squadretta del servo piattaforma fissato
   al tavolo con `turntable_servo_mount` (attenzione: il servo deve essere
   concentrico alla lazy susan entro 1 mm, altrimenti forza). Colonna lampada
   (`lamp_pivot`) a 17 cm dal bordo della piattaforma con l'albero del servo
   orizzontale e **alla stessa quota** del piano della piattaforma + 6 cm.
   Braccio lampada: tubo Ø10 × 60 cm, LED in punta puntato verso il centro
   della piattaforma.
7. **Cablaggio** (tutte le masse in comune):

```
 alimentatore 6 V ──┬── + servo azimut (MG996R)        segnale → GPIO13
                    ├── + servo inclinazione (MG90S)   segnale → GPIO12
                    ├── + servo testa (MG90S)          segnale → GPIO14
                    ├── + servo piattaforma (MG996R)   segnale → GPIO26
                    ├── + servo lampada (MG996R)       segnale → GPIO25
                    ├── + LED COB (tramite il suo driver 5 V)
                    └── 1000 µF ── GND ─── GND ESP32
 ESP32 alimentato da USB (o dal 6 V tramite il pin VIN se ≤ 6 V: verifica la scheda)
 DS3231: SDA → GPIO21, SCL → GPIO22, VCC 3.3 V
```

8. **Griglia sulla piattaforma**: stampa su carta un foglio con la griglia da
   10 cm (= 1 m in scala), il cerchio della zona (r = 10 cm) e la sagoma di un
   lettino 20 × 8 cm; incollalo sulla piattaforma con il palo al centro. È la
   cosa che l'investitore guarda: l'ombra deve restare dentro il cerchio.

---

## 5. Firmware e calibrazione (30 minuti)

1. Arduino IDE → scheda "ESP32 Dev Module", libreria **ESP32Servo**. Apri
   `firmware/ombrellone_esp32/ombrellone_esp32.ino`.
2. In `config.h`: WiFi, `LATITUDE/LONGITUDE` della spiaggia che vuoi
   raccontare (Rimini di default), `DEMO_RIG 1`, `HEAD_PAN_SERVO 0`.
3. Carica. Apri `http://ombrellone.local` (o l'IP stampato sul monitor seriale;
   senza WiFi crea la rete "ombrellone", password "ombrellone", pagina
   `192.168.4.1`).
4. **Zeri dei servo**: premi "Parcheggia". Il palo deve essere verticale, il
   braccio verticale, il tettuccio orizzontale: correggi `THETA_SERVO_ZERO`,
   `BETA_SERVO_ZERO`, `ALPHA_TRIM` (±gradi) e ricarica. Per il banco:
   `TABLE_TRIM` finché, con `/demo?hour=12`, la lampada sta davanti al "Sud"
   della griglia; `LAMP_SERVO_ZERO` finché il braccio lampada è orizzontale con
   servo a 0.
5. **Prova al sole vero** (facoltativa ma convincente): porta il modello fuori,
   `/calib` come descritto in `PROGETTO.md` §9.2, e fotografa l'ombra ogni
   15 minuti. Le foto affiancate alla timeline del simulatore sono una slide
   fortissima.

---

## 6. Copione della demo (3 minuti)

| tempo | cosa succede | cosa dici |
|---|---|---|
| 0:00 | Modello in parcheggio. Apri la web app sul telefono, mostra la pianta con il cerchio. | "Questa è la zona che voglio in ombra: il lettino. Non lo sposto io, lo sposta il sole." |
| 0:20 | Premi **Demo giornata** (`/demo?on=1&speed=240&hour=6`). La lampada parte bassa a Est, la piattaforma ruota lentamente. | "Una giornata del 15 luglio in tre minuti. L'ombrellone sa dove si trova, che giorno è, e dove sarà il sole tra dieci minuti." |
| 0:50 | Verso le 10:00 simulate l'ombra entra nel cerchio e ci resta. Il braccio si abbassa verso il sole, il tettuccio si inclina. | "Da qui in poi l'ombra non si muove più. L'ombrellone si corregge ogni dieci minuti: movimenti piccoli, silenziosi." |
| 1:40 | Mezzogiorno: il braccio è quasi verticale. Trascina il cerchio sull'app di 10 cm di lato e premi Applica: il modello si riassesta in due secondi. | "Il cliente cambia posto? Sposta il cerchio. Sapere dov'è l'ombra è un problema di geometria, non di sensori." |
| 2:20 | Verso le 16:30 simulate l'ombra comincia a scappare; l'app mostra in rosso "il sole è troppo basso". | "Qui siamo onesti: con un braccio di 1.6 m il sole sotto i 44° non si copre. L'app lo dice al cliente in anticipo: 'ombra garantita fino alle 16:30'. Con lo sbalzo mobile che vi mostro nel simulatore si arriva alle 18." |
| 2:50 | Tramonto: parcheggio automatico. Passa al simulatore (`docs/simulatore.html`): calendario annuale, mappamondo, confronto Rimini/Tenerife. | "Nella stagione balneare italiana funziona tutti i giorni, 7–9 ore al giorno. Dal 35° parallelo in giù, tutto l'anno." |

Consigli pratici: stanza in penombra (il LED deve dominare), lampada con lente
stretta (ombra netta), piattaforma bianca opaca, telefono già connesso, un
secondo modello di tettuccio in tela da passare in mano. Tieni il simulatore
aperto sul portatile come piano B se la rete fa i capricci.

---

## 7. Numeri da mettere nel pitch (tutti dal repository)

* Copertura totale di un lettino (r = 1 m) a Rimini, 15 luglio: **6.7 h/giorno**
  con l'ombrellone base, **8.3 h** con lo sbalzo mobile, **9.3 h** con braccio
  telescopico + sbalzo mobile (`risultati.md`, simulatore).
* Stagione balneare (15 mag – 15 set): **123 giorni utili su 123** con lo sbalzo
  mobile; da marzo a ottobre con il palo a Sud della zona (`stagionalita.md`).
* Ore/anno di copertura totale: 966 (base) → 1547 (sbalzo mobile) → 1849
  (+ palo a Sud). A Tenerife ≈ 1500 h/anno anche con la geometria base.
* Meccanica del prodotto vero: vento di esercizio 29 km/h, coppia 240 N·m sul
  giunto principale, zavorra 80–100 kg, attuatori lineari autobloccanti da
  60–90 €, consumo 40 Wh/giorno coperto da un pannello da 30 W sul tettuccio.
* Il software è il prodotto: stesso algoritmo in Python (simulazione), C++
  (ESP32) e JavaScript (app), validato contro `pvlib` con errore < 0.05°.

Cosa chiedere e cosa promettere (in ordine): prototipo 1:2 da giardino con
attuatori veri e anemometro (budget 700 €, 2 mesi) → prototipo 1:1 con prove di
vento e app nativa (3–6 mesi) → pre-serie per 2–3 stabilimenti pilota.

---

## 8. Rischi e limiti da dichiarare (gli investitori li chiederanno)

* **Geometria**: sole sotto ~44° (base) o ~30° (sbalzo mobile) non si copre.
  Mattina presto e tardo pomeriggio restano fuori. Il mini lo mostra
  onestamente; l'app lo comunica in anticipo.
* **Vento**: il prodotto vero vive di zavorra e di parcheggio automatico sopra
  29 km/h; sopra 43 km/h va chiuso. Serve un anemometro (10 €) e una
  certificazione (Direttiva Macchine per le parti motorizzate).
* **Il mini non valida la struttura**: a parità di vento le forze scalano con
  il quadrato della scala (1/100) e i momenti con il cubo. Lo dice anche la
  tabella "leggi di scala" in `risultati.md`. Per la struttura ci sono i
  calcoli (`mechanics.py`, FEM) e il prototipo 1:2.
* **Concorrenza**: esistono ombrelloni che inseguono il sole (es. Shadecraft);
  nessuno tiene ferma un'ombra scelta dall'utente con previsione dell'orario di
  copertura. Il vantaggio è il software + l'app, non il meccanismo.
* **Calibrazione del Nord** nel prodotto vero: magnetometro o procedura
  "punta il braccio al sole" (già nel firmware) + fotoresistenze per la
  correzione fine (2 €).

---

## 9. Dopo la demo: dal mini al prototipo 1:2

Stessa architettura, stessa elettronica (ESP32), attuatori diversi:

| giunto | mini (1:10) | 1:2 da giardino | 1:1 prodotto |
|---|---|---|---|
| azimut | MG996R 270° nella base | motoriduttore DC 12 V + vite senza fine, encoder AS5600 | ralla a vite senza fine (slew drive) |
| inclinazione braccio | MG90S | attuatore lineare 12 V 150 mm / 750 N | attuatore lineare 12/24 V 300 mm / 3000 N |
| tettuccio | MG90S | attuatore lineare 12 V 100 mm / 500 N | attuatore lineare 1500 N |
| sbalzo mobile | fisso 5 cm | carrello con cinghia + stepper NEMA17 | carrello con cinghia o vite, stepper NEMA23 |
| sicurezza | – | anemometro, finecorsa, limitazione di corrente | + chiusura motorizzata, certificazione |

Il firmware resta lo stesso: cambiano solo `config.h` (geometria, pin) e la
funzione `writeServos` (da PWM servo a driver motore con encoder).
