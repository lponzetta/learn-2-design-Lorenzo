// Banco demo "sole artificiale": piattaforma girevole (servo MG996R 270 gradi al
// centro + lazy susan che porta il peso) e braccio della lampada con servo di
// elevazione.  L'ESP32 muove la piattaforma di -(azimut) e la lampada di
// (elevazione): visto dal modello, la lampada percorre l'arco del sole.
include <params.scad>

lamp_arm_l = 600;        // lunghezza braccio lampada (tubo carbonio 10 mm)
pivot_off  = 170;        // distanza del perno dal centro della piattaforma
pivot_h    = 60;         // quota del perno

// mozzo centrale: squadretta servo sotto, disco (forex 5 mm) sopra
module turntable_hub() {
    difference() {
        cylinder(d=70, h=8);
        translate([0,0,-1]) cylinder(d=horn_std_d+fit*2, h=3.5);
        for (a=[0:90:270]) rotate(a) translate([7,0,-1]) cylinder(d=2.2, h=10);
        for (a=[0:60:300]) rotate(a) translate([28,0,-1]) cylinder(d=4.2, h=10);   // viti M4 al disco
    }
}
// supporto del servo piattaforma, da avvitare al tavolo
module turntable_servo_mount() {
    difference() {
        translate([-40, -30, 0]) cube([80, 60, sv_std_h + 4]);
        translate([0,0,sv_std_h+4]) servo_std_pocket(extra=5);
        for (x=[-1,1], y=[-1,1]) translate([x*32, y*22, -1]) cylinder(d=4.2, h=50);
    }
}
// colonna del braccio lampada: tasca servo standard con albero orizzontale
module lamp_pivot() {
    difference() {
        union() {
            translate([-25, -30, 0]) cube([50, 60, pivot_h + 10]);
            translate([-40, -40, 0]) cube([80, 80, 5]);           // piede
        }
        translate([0, 0, pivot_h]) rotate([0, 90, 0]) translate([0, 0, 0]) rotate([0,0,90]) servo_std_pocket(extra=30);
        for (x=[-1,1], y=[-1,1]) translate([x*33, y*33, -1]) cylinder(d=4.2, h=8);
    }
}
// attacco del braccio lampada sulla squadretta rotonda + manicotto tubo 10 mm
module lamp_arm_root() {
    difference() {
        union() { cylinder(d=30, h=5); translate([0,0,5]) rotate([0,90,0]) cylinder(d=16, h=40); }
        translate([0,0,-1]) cylinder(d=horn_std_d+fit*2, h=3.5);
        for (a=[0:90:270]) rotate(a) translate([7,0,-1]) cylinder(d=2.2, h=7);
        translate([5,0,5]) rotate([0,90,0]) cylinder(d=10+fit*2, h=40);
    }
}
// porta-lampada in punta: manicotto tubo + anello per LED COB con lente (d 20-30 mm)
module lamp_holder() {
    difference() {
        union() { rotate([0,90,0]) cylinder(d=16, h=30); translate([30, 0, 0]) rotate([0,90,0]) cylinder(d=34, h=12); }
        translate([-1,0,0]) rotate([0,90,0]) cylinder(d=10+fit*2, h=28);
        translate([29,0,0]) rotate([0,90,0]) cylinder(d=28+fit*2, h=14);
    }
}
turntable_hub();
translate([0, 90, 0]) turntable_servo_mount();
translate([130, 0, 0]) lamp_pivot();
translate([130, 100, 0]) lamp_arm_root();
translate([130, 160, 10]) lamp_holder();
