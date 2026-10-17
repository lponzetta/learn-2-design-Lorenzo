// Braccio: (1) attacco alla squadretta del servo di inclinazione + sede tubo;
// (2) terminale del braccio con la tasca del micro servo della TESTA (beta),
// con l'albero perpendicolare al piano del braccio.
include <params.scad>

module arm_root() {
    difference() {
        union() {
            cylinder(d=26, h=5);                                    // disco sulla squadretta a croce/rotonda SG90
            translate([0, 0, 0]) rotate([0, 0, 0]) translate([-6, -6, 0]) cube([12, 12, 14]);
            translate([0, 0, 14]) rotate([0, 90, 0]) cylinder(d=arm_tube_d+2*wall, h=30);  // manicotto tubo lungo +X
        }
        translate([0,0,-1]) cylinder(d=7.2, h=3);                   // mozzo squadretta
        for (a=[0:90:270]) rotate(a) translate([7.5,0,-1]) cylinder(d=1.8, h=7);  // viti squadretta
        translate([3, 0, 14]) rotate([0, 90, 0]) cylinder(d=arm_tube_d+fit*2, h=40);  // tubo braccio (incollare)
    }
}
module arm_tip() {
    difference() {
        union() {
            rotate([0, 90, 0]) cylinder(d=arm_tube_d+2*wall, h=30);               // manicotto
            translate([26, -sv_mic_l/2-wall, -sv_mic_w/2-wall]) cube([sv_mic_h+wall, sv_mic_l+2*wall, sv_mic_w+2*wall]);
        }
        translate([-1, 0, 0]) rotate([0, 90, 0]) cylinder(d=arm_tube_d+fit*2, h=28);
        // servo testa: albero lungo Y (perpendicolare al piano verticale del braccio, che e' XZ)
        translate([26+sv_mic_h+wall-0.01, 0, 0]) rotate([0, 0, 0]) rotate([-90, 0, 0]) rotate([0, 0, 90]) translate([0,0,sv_mic_w/2+wall]) servo_mic_pocket(extra=10);
    }
}
arm_root();
translate([0, 40, 0]) arm_tip();
