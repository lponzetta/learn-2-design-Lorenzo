// ============================================================================
// Ombrellone magico - mini prototipo 1:10 - parametri condivisi (mm)
// Apri i singoli file con OpenSCAD (https://openscad.org), F6 e esporta STL.
// ============================================================================
$fn = 64;

// --- geometria del modello (scala 1:10 del progetto base) ------------------
pole_h      = 200;    // altezza palo fisso (dalla base alla cerniera di inclinazione)
arm_l       = 160;    // lunghezza braccio (dalla cerniera al centro testa)
canopy_r    = 150;    // raggio tettuccio
canopy_off  = 50;     // sbalzo del tettuccio lungo il braccio (fisso nel mini)

// --- tubi in carbonio (aste da aquilone) -----------------------------------
pole_tube_d = 10;     // diametro esterno tubo palo
arm_tube_d  = 8;      // diametro esterno tubo braccio
spoke_d     = 2;      // stecche tettuccio
fit         = 0.25;   // gioco per gli accoppiamenti stampati (0.2-0.35 a seconda della stampante)

// --- servo ------------------------------------------------------------------
// MG996R / DS3218 (standard): corpo 40.5 x 20 x 38 mm, flangia 54.5 mm, fori a 49 mm
sv_std_l = 40.7; sv_std_w = 20.2; sv_std_h = 38; sv_std_tab = 54.7; sv_std_hole = 49; sv_std_tab_t = 2.6;
// SG90 / MG90S (micro): corpo 22.8 x 12.2 x 22.5 mm, flangia 32.5 mm, fori a 28 mm
sv_mic_l = 23.0; sv_mic_w = 12.4; sv_mic_h = 22.7; sv_mic_tab = 32.7; sv_mic_hole = 28; sv_mic_tab_t = 2.4;
horn_std_d = 21;      // squadretta rotonda MG996R
horn_mic_d = 20;      // squadretta rotonda SG90 (a croce: 20 mm)

// --- cuscinetto ralla (lazy susan) ------------------------------------------
turntable_d = 300;    // disco piattaforma demo (compensato/forex 5 mm, tagliato a mano)
bearing_d   = 200;    // lazy susan 200 mm

wall = 3;

// tasca per servo standard (asse Z verso l'alto, albero in origine)
module servo_std_pocket(extra=10) {
    translate([-sv_std_l/2 + 10 - 1, -sv_std_w/2, -sv_std_h]) cube([sv_std_l + fit*2, sv_std_w + fit*2, sv_std_h + extra]);
    // flange
    translate([-sv_std_tab/2 + 10 - 1, -sv_std_w/2, -sv_std_h + 27]) cube([sv_std_tab, sv_std_w + fit*2, sv_std_tab_t + 0.5]);
    for (x = [-sv_std_hole/2, sv_std_hole/2]) translate([x + 10 - 1, 0, -sv_std_h]) cylinder(d = 3.2, h = sv_std_h + extra);
}
// tasca per micro servo (asse Z verso l'alto, albero in origine: l'albero e' a 6 mm da un'estremita')
module servo_mic_pocket(extra=10) {
    translate([-sv_mic_l/2 + 5.5, -sv_mic_w/2, -sv_mic_h]) cube([sv_mic_l + fit*2, sv_mic_w + fit*2, sv_mic_h + extra]);
    translate([-sv_mic_tab/2 + 5.5, -sv_mic_w/2, -sv_mic_h + 16]) cube([sv_mic_tab, sv_mic_w + fit*2, sv_mic_tab_t + 0.5]);
    for (x = [-sv_mic_hole/2, sv_mic_hole/2]) translate([x + 5.5, 0, -sv_mic_h]) cylinder(d = 2.2, h = sv_mic_h + extra);
}
