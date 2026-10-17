# Mercato, concorrenza e valutazione come startup

Ricerca fatta il 17 ottobre 2026 con ricerche web (fonti in fondo). Dove non
ho trovato conferme recenti lo dico esplicitamente.

## 1. Cosa esiste già

| prodotto / progetto | cosa fa | cosa NON fa | stato |
|---|---|---|---|
| **Shadecraft Sunflower** (Los Angeles, CES 2017) | ombrellone robotico da giardino: insegue il sole con dati astronomici, pannelli solari, speaker, luci, telecamera, chiusura automatica col vento; tilt 45°, rotazione 360°, 3 motori | non tiene ferma un'ombra scelta dall'utente: punta il tettuccio al sole e l'ombra "sta sotto"; prezzo di listino annunciato ≈ 8.000 $, presale 5.220 $ | 2 M$ di seed nel 2017; nessuna fonte recente sullo stato attuale dell'azienda (da verificare) |
| **SOLEX (Ombrellificio Magnani)** | ombrellone professionale da stabilimento: apertura/chiusura motorizzata via telecomando o app, pannello fotovoltaico integrato | nessun inseguimento del sole | prodotto in catalogo, data non chiara |
| **Ombrelloni fotovoltaici di Jesolo** (2016) | apertura/chiusura dallo smartphone, ≈ 80 € per ombrellone | nessun inseguimento | sperimentazione, stato attuale ignoto |
| **Cumulus Parasol** (Studio Toer, 2014) | si apre da solo quando c'è sole diretto | nessun inseguimento | concept di design |
| **Brevetti** | US 7 631 653 "Apparatus for automated movement of an umbrella" (ombrellone che segue il sole); domanda cinese CN122140061A (giroscopio + sensori di luce + telecamera per riconoscere l'ombra) | | esistono: serve una ricerca di anteriorità seria prima di brevettare |
| **Progetti universitari** (Manitoba, Illinois 2025, UCF) | prototipi con fotoresistenze/fotodiodi che inseguono il sole | | tesi e senior design |

Conclusione sulla concorrenza: **l'inseguimento del sole esiste** (Sunflower,
brevetti, tesi). Quello che non ho trovato è il nostro angolo: **l'utente
sceglie la zona** (il lettino), il sistema calcola la posa per tenerla in
ombra, **predice fino a che ora ce la fa** e avvisa prima. È una differenza
sottile per il marketing ma grossa per l'esperienza: Sunflower "sta al sole",
noi "proteggiamo una persona".

## 2. Mercati adiacenti dove la stessa idea è già un business

* **Agrivoltaico dinamico**: Ombrea (Francia, acquisita da TotalEnergies nel
  2023) e Sun'Agri muovono pannelli solari sopra le colture con algoritmi che
  decidono quanto ombreggiare in base al microclima e allo stadio della pianta.
  Stesso problema matematico (dove deve stare il pannello perché l'ombra cada
  sulla pianta), scala e budget enormi. È la prova che "ombra calcolata" vale
  soldi.
* **Pergole bioclimatiche** (lamelle orientabili motorizzate per ristoranti e
  terrazze): oggi le lamelle seguono sensori di pioggia/vento/luce; il nostro
  algoritmo le farebbe inclinare per tenere in ombra i tavoli, non per
  "chiudere al sole". È un **software venduto ai produttori di pergole**, senza
  costruire hardware.
* **Stabilimenti balneari e hotel**: file di ombrelloni che si aprono, si
  orientano e si chiudono da soli, con l'app che dice al bagnino quali
  spostare. Qui il cliente è B2B e paga la manodopera risparmiata.
* Altri: ombra per culle e passeggini (prodotto piccolo, mercato emotivo),
  pannelli ombreggianti per bestiame, tende da sole per vetrine.

## 3. È una buona idea per una startup? Valutazione onesta

**A favore**
* Il dolore è reale e quotidiano: chiunque sia stato in spiaggia ha spostato il
  lettino tre volte. La demo si capisce in 10 secondi.
* L'intelligenza è software (già scritto e validato in questo repo): il
  vantaggio competitivo è nell'algoritmo + app + dati, non nella meccanica.
* Ci sono tre mercati con tre prezzi diversi: consumer (giardino/spiaggia),
  B2B stabilimenti/hotel, licenza software a chi fa pergole e ombrelloni.
* Il mercato tropicale (Canarie, Caraibi, Medio Oriente, Sud-Est asiatico) è
  "tutto l'anno": è il mercato giusto per l'hardware premium.

**Contro**
* **Hardware stagionale e all'aperto**: vento, sabbia, salsedine,
  certificazioni (Direttiva Macchine), zavorra di 80–100 kg. Sunflower a 8.000 $
  non è diventato un prodotto di massa, e questo è un dato.
* **La fisica limita la promessa**: ombra totale solo con sole sopra 30–45°.
  Al mattino presto e nel tardo pomeriggio nessun ombrellone a palo copre un
  lettino. Chi vende "ombra sempre" mente; chi vende "ti dico fino a quando" è
  credibile ma meno sexy.
* **Costo del prodotto vero**: attuatori, ralla, elettronica, batteria,
  pannello: 600–900 € di distinta base per un Ø3 m, quindi 2.000–3.000 € di
  prezzo al pubblico. È un prodotto da ville e hotel, non da bagno popolare.
* Brevetti esistenti sull'inseguimento: il brevetto nostro deve essere
  sull'inversione (zona scelta → posa) e sulla previsione oraria.

**La mia raccomandazione: parti dal software, non dal ferro.**

1. **MVP a costo zero di hardware: l'app "ombra predittiva"** per ombrelloni
   normali. L'utente fissa dove sono palo e lettino, l'app (stesso solver,
   tettuccio fisso) dice "l'ombra lascia il lettino alle 15:40, spostalo
   60 cm a Nord" e manda la notifica. Si testa in un'estate su 1.000 utenti con
   un budget da hobby, e si capisce se la gente paga 3 € per non scottarsi.
   Tutto il codice c'è già: `ombrellone/planner.py` con theta fisso.
2. **Retrofit kit per stabilimenti**: motorizzare l'azimut e l'inclinazione
   degli ombrelloni esistenti (attuatore lineare + ralla + ESP32, 150–250 € a
   pezzo), venduto al bagno con l'app del bagnino. Il bagno paga per la
   manodopera risparmiata e per la "ombra garantita" come servizio premium
   (lettino "smart" a +5 €/giorno).
3. **Licenza dell'algoritmo** ai produttori di pergole bioclimatiche e di
   ombrelloni a braccio (Magnani, Scolaro, Caravita, Umbrosa, Glatz…): loro
   hanno i canali e la meccanica, a noi manca tutto questo.
4. Solo dopo, se i numeri del punto 2 reggono, l'ombrellone proprietario
   "Magico 300" per hotel e resort tropicali.

Cosa serve per decidere in 3 mesi: il mini 1:10 per la demo (in questo repo),
un'estate di test dell'app predittiva in uno stabilimento amico, due
conversazioni con produttori di ombrelloni, una ricerca di anteriorità
brevettuale su Espacenet con le parole chiave "umbrella shadow target
tracking".

## Fonti

* Sunflower: [SCMP](https://amp.scmp.com/tech/innovation/article/2127587/meet-sunflower-us8000-robotic-umbrella-moves-sun), [designboom](https://www.designboom.com/technology/shadecraft-sunflower-08-26-2017/), [Sound & Vision](https://www.soundandvision.com/content/shadecraft%E2%80%99s-beautiful-intelligent-robotic-sunflower), [socaltech (seed 2 M$)](https://socaltech.com/report_shadecraft_raises__m_for_solar_tracking_sunshade/s-0069640.html), [Reuters video](https://reuters.screenocean.com/record/908634)
* SOLEX Magnani: [mondobalneare](https://www.mondobalneare.com/?p=170586); Jesolo: [Focus](https://www.focus.it/ambiente/ecologia/a-jesolo-arrivano-in-spiaggia-gli-ombrelloni-a-energia-solare), [greenMe](https://www.greenme.it/?p=534256); Cumulus: [greenMe](https://www.greenme.it/?p=504260)
* Brevetti: [US7631653B2](https://patents.google.com/patent/US7631653), [CN122140061A](https://eureka.patsnap.com/patent-CN122140061A)
* Prototipi universitari: [Manitoba](https://mspace.lib.umanitoba.ca/xmlui/handle/1993/35644), [Illinois ECE445](https://courses.physics.illinois.edu/ece445/getfile.asp?id=25269), [UCF](https://ece.ucf.edu/seniordesign/su2015fa2015/g09/Proposal.docx)
* Agrivoltaico: [Ombrea vs Sun'Agri (CB Insights)](https://www.cbinsights.com/compare/ombrea-vs-sunagri), [Ombrea (Dealroom)](https://dealroom.co/companies/ombrea/), [Sun'Agri (AgriExpo)](https://www.agriexpo.online/prod/sun-agri/product-4601580-190132.html), [INRAE, pannelli mobili e colture](https://hal.inrae.fr/hal-02629148)
