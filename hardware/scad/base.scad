// Base dell'ombrellone: contiene il servo di AZIMUT (MG996R 270 gradi) che fa
// ruotare tutto il palo attorno al proprio asse (geometricamente identico allo
// snodo in cima al palo, ma molto piu' semplice: baricentro basso, un solo cavo
// che sale).  Sopra: la ralla stampata e il mozzo del palo (pole_hub).
include <params.scad>

base_w = 90; base_l = 110; base_h = sv_std_h + 6;

module base() {
    difference() {
        hull() { for (x=[-1,1], y=[-1,1]) translate([x*(base_l/2-8), y*(base_w/2-8), 0]) cylinder(r=8, h=base_h); }
        translate([0,0,base_h]) servo_std_pocket(extra=5);           // tasca servo, albero in alto al centro
        translate([-base_l/2-1, -8, 6]) cube([20, 16, 10]);         // passaggio cavo servo
        for (x=[-1,1], y=[-1,1]) translate([x*(base_l/2-8), y*(base_w/2-8), -1]) cylinder(d=4.2, h=base_h+2); // viti M4 al tavolo / piattaforma
        // sede dell'anello di scorrimento del mozzo (ralla stampata)
        translate([0,0,base_h-1.5]) difference() { cylinder(d=60+fit*2, h=2); cylinder(d=46, h=2); }
    }
}
// mozzo del palo: si innesta sulla squadretta rotonda del servo e tiene il tubo del palo
module pole_hub() {
    difference() {
        union() {
            cylinder(d=58, h=4);                                    // anello che scorre sulla sede della base
            cylinder(d=24, h=22);
        }
        translate([0,0,-1]) cylinder(d=horn_std_d+fit*2, h=3.5);    // sede squadretta rotonda
        for (a=[0:90:270]) rotate(a) translate([7,0,-1]) cylinder(d=2.2, h=5);  // viti squadretta
        translate([0,0,6]) cylinder(d=pole_tube_d+fit*2, h=20);     // tubo palo (incollare)
        translate([-1.5, 8, 6]) cube([3, 10, 20]);                  // fessura per il cavo del servo di inclinazione
    }
}
base();
translate([0, base_w/2 + 45, 0]) pole_hub();
