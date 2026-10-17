// Mozzo del tettuccio: si monta sulla squadretta del servo della testa, tiene
// 8 stecche in carbonio da 2 mm e porta lo SBALZO (canopy_off) verso l'esterno.
// Per la demo conviene un disco di forex/cartone alveolare da 3-5 mm
// (ombra nitida): si incolla sul mozzo con il centro a canopy_off dal perno.
include <params.scad>

module hub() {
    difference() {
        union() {
            cylinder(d=26, h=4);                                    // sulla squadretta
            hull() { cylinder(d=14, h=8); translate([canopy_off, 0, 0]) cylinder(d=34, h=8); }  // braccetto di sbalzo
            translate([canopy_off, 0, 0]) cylinder(d=34, h=10);
        }
        translate([0,0,-1]) cylinder(d=7.2, h=3);
        for (a=[0:90:270]) rotate(a) translate([7.5,0,-1]) cylinder(d=1.8, h=6);
        // 8 stecche radiali
        for (a=[0:45:315]) translate([canopy_off, 0, 7]) rotate([0, 0, a]) rotate([0, 90, 0]) cylinder(d=spoke_d+fit, h=20);
        // 4 fori M3 per fissare un disco rigido (opzione demo)
        for (a=[45:90:315]) translate([canopy_off, 0, 0]) rotate(a) translate([12, 0, -1]) cylinder(d=3.2, h=12);
    }
}
hub();
