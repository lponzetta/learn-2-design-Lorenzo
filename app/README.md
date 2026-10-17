# App mobile — prototipo di interfaccia

`design/` contiene le 7 schermate del prototipo cliccabile pubblicato sul canvas
di design (claude.ai): Benvenuto, Posizione, Fissa l'ombrellone, Zona d'ombra
(interattiva, con il solver vero), Oggi (con scorrimento della giornata),
Avviso sul blocco schermo, Esplora.

I parametri dell'ombrellone ("Magico 300": tettuccio Ø 3 m, braccio 1,6 m,
θmax 70°, sbalzo mobile 0–80 cm) sono del costruttore e non modificabili
dall'utente. L'app chiede solo: dove sei, dov'è il palo, cosa vuoi in ombra; poi
mostra fino a che ora l'ombra è totale e avvisa 15 minuti prima che scappi.

Le schermate sono file `.dc.html` (un HTML autonomo per schermata con la logica
in una classe JavaScript): si aprono anche da sole nel browser, senza il canvas,
tranne i collegamenti fra schermate.
