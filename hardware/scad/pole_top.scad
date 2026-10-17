// Cima del palo: tappo per il tubo + tasca per il micro servo di INCLINAZIONE
// (MG90S), con l'albero orizzontale.  L'asse dell'albero e' la cerniera theta.
include <params.scad>

module pole_top() {
    difference() {
        union() {
            cylinder(d=pole_tube_d+2*wall+2, h=30);                 // manicotto sul tubo
            translate([-sv_mic_w/2-wall, -sv_mic_l/2-6, 28]) cube([sv_mic_w+2*wall, sv_mic_l+12, sv_mic_h+wall]);
        }
        translate([0,0,-1]) cylinder(d=pole_tube_d+fit*2, h=26);    // tubo palo
        // servo con albero lungo X (orizzontale): ruoto la tasca
        translate([0, 0, 28+sv_mic_h/2+wall]) rotate([0,90,0]) translate([0,0,sv_mic_w/2+wall+0.01]) rotate([0,0,90]) servo_mic_pocket(extra=10);
        translate([-sv_mic_w/2-wall-1, -3, 10]) cube([sv_mic_w+2*wall+2, 6, 20]); // passaggio cavo
    }
}
pole_top();
