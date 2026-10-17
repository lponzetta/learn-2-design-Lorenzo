"""Genera gli STL definitivi del mini-prototipo 1:10 e del banco demo.

Uso:  python hardware/build_parts.py        -> hardware/stl/*.stl + hardware/stl/report.md + anteprime PNG

Modellazione solida con trimesh + manifold3d (booleane esatte).  Tutte le quote
in millimetri.  Le regole costruttive sono raccolte in PRINT e SERVO: cambia li'
se la tua stampante o i tuoi servo sono diversi.

Convenzione per ogni parte: il file e' gia' nell'orientamento di stampa
(z = verso l'alto sul piatto, z=0 = piatto).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import trimesh
from trimesh.transformations import rotation_matrix, translation_matrix

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "stl"
OUT.mkdir(exist_ok=True)

# ----------------------------------------------------------------------------
# regole costruttive (stampa FDM, ugello 0.4, layer 0.2, PETG)
# ----------------------------------------------------------------------------
PRINT = {
    "wall": 3.0,            # pareti portanti (3 perimetri = 1.2 mm minimo, qui abbondante)
    "fit_tube": 0.35,       # gioco diametrale per i tubi incollati (carbonio da aquilone)
    "fit_servo": 0.4,       # gioco per le tasche dei servo
    "fit_horn": 0.5,        # gioco per le sedi delle squadrette
    "hole_m2_tap": 1.8,     # vite M2 autofilettante nel PETG
    "hole_m3_tap": 2.6,     # vite M3 autofilettante
    "hole_m3_clear": 3.4,   # passaggio M3
    "hole_m4_clear": 4.4,   # passaggio M4
    "max_overhang_deg": 45, # oltre servono supporti
    "bed": (220, 220, 250), # piatto minimo richiesto
}
FIT_T, FIT_S, FIT_H = PRINT["fit_tube"], PRINT["fit_servo"], PRINT["fit_horn"]
W = PRINT["wall"]

# tubi in carbonio (aste da aquilone): diametro esterno nominale
POLE_TUBE = 10.0
ARM_TUBE = 8.0
LAMP_TUBE = 10.0


@dataclass(frozen=True)
class Servo:
    """Quote di un servo con l'albero in origine, asse +Z, faccia superiore del corpo a z=0."""
    name: str
    x0: float; x1: float        # corpo lungo X (l'albero e' decentrato: x0 < 0 < x1)
    half_w: float               # meta' larghezza (Y)
    body_h: float               # altezza del corpo sotto la faccia superiore
    tab_x0: float; tab_x1: float  # estensione delle flange lungo X
    tab_z0: float; tab_z1: float  # quota delle flange (sotto z=0), tab_z0 < tab_z1 < 0
    hole_dx: float              # semidistanza fori flange lungo X (dal centro corpo)
    hole_dy: float              # semidistanza fori lungo Y (0 = un foro per lato)
    hole_d: float               # foro nel pezzo stampato (autofilettante)
    shaft_above: float          # quanto sporge l'albero/la squadretta sopra z=0 (per le sedi)
    horn_d: float               # diametro squadretta rotonda
    horn_t: float               # spessore squadretta
    horn_hole_r: float          # raggio del cerchio dei fori della squadretta
    horn_hole_d: float          # foro nel pezzo per le viti della squadretta

    @property
    def xc(self) -> float:
        return (self.x0 + self.x1) / 2


# MG996R / DS3218: corpo 40.5 x 20 x 38, flange a 27.5 mm dal fondo, fori 49.5 x 10
MG996R = Servo("MG996R", -10.1, 30.4, 10.0, 38.0, -17.2, 37.5, -11.5, -9.0, 24.75, 5.0,
               PRINT["hole_m3_tap"], 5.0, 21.0, 3.0, 7.0, 2.2)
# MG90S / SG90: corpo 22.8 x 12.2 x 22.5, flange a 16 mm dal fondo, fori a 28 mm
MG90S = Servo("MG90S", -6.3, 16.5, 6.1, 22.5, -11.2, 21.4, -6.6, -4.2, 14.0, 0.0,
              PRINT["hole_m2_tap"], 4.0, 20.0, 1.6, 7.0, 1.8)


# ----------------------------------------------------------------------------
# primitive e booleane
# ----------------------------------------------------------------------------
def box(sx, sy, sz, at=(0, 0, 0)):
    return trimesh.creation.box((sx, sy, sz), transform=translation_matrix(at))


def box_from_to(x0, x1, y0, y1, z0, z1):
    return box(x1 - x0, y1 - y0, z1 - z0, ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))


def cyl(d, h, at=(0, 0, 0), axis="z", sections=96):
    m = trimesh.creation.cylinder(radius=d / 2, height=h, sections=sections)
    if axis == "x":
        m.apply_transform(rotation_matrix(math.pi / 2, (0, 1, 0)))
    elif axis == "y":
        m.apply_transform(rotation_matrix(math.pi / 2, (1, 0, 0)))
    m.apply_transform(translation_matrix(at))
    return m


def cone(d0, d1, h, at=(0, 0, 0)):
    """Tronco di cono lungo +Z da z=0 (d0) a z=h (d1)."""
    n = 96
    a = np.linspace(0, 2 * np.pi, n, endpoint=False)
    bottom = np.column_stack([d0 / 2 * np.cos(a), d0 / 2 * np.sin(a), np.zeros(n)])
    top = np.column_stack([d1 / 2 * np.cos(a), d1 / 2 * np.sin(a), np.full(n, h)])
    m = trimesh.convex.convex_hull(np.vstack([bottom, top]))
    m.apply_transform(translation_matrix(at))
    return m


def hull(*meshes):
    return trimesh.convex.convex_hull(np.vstack([m.vertices for m in meshes]))


def union(*ms):
    ms = [m for m in ms if m is not None]
    return trimesh.boolean.union(ms, engine="manifold") if len(ms) > 1 else ms[0]


def diff(a, *cutters):
    return trimesh.boolean.difference([a, union(*cutters)], engine="manifold")


def R(m, angle_deg, axis):
    m = m.copy(); m.apply_transform(rotation_matrix(math.radians(angle_deg), axis)); return m


def T(m, dx=0, dy=0, dz=0):
    m = m.copy(); m.apply_transform(translation_matrix((dx, dy, dz))); return m


# ----------------------------------------------------------------------------
# tasche servo (cutter nel riferimento del servo: albero in origine, asse +Z)
# ----------------------------------------------------------------------------
def servo_cutter(s: Servo, slot_up=60.0, screw_depth=10.0, body_extra_down=0.6):
    """Volume da sottrarre: corpo (con gioco), slot delle flange aperto verso +Z
    (il servo entra dall'alto e si appoggia con le flange), fori per le viti."""
    body = box_from_to(s.x0 - FIT_S, s.x1 + FIT_S, -s.half_w - FIT_S, s.half_w + FIT_S,
                       -s.body_h - body_extra_down, 0.01)
    slot = box_from_to(s.tab_x0 - FIT_S, s.tab_x1 + FIT_S, -s.half_w - FIT_S, s.half_w + FIT_S,
                       s.tab_z0 - 0.1, slot_up)
    holes = []
    ys = [-s.hole_dy, s.hole_dy] if s.hole_dy > 0 else [0.0]
    for dx in (-s.hole_dx, s.hole_dx):
        for y in ys:
            holes.append(cyl(s.hole_d, screw_depth + 0.1, (s.xc + dx, y, s.tab_z0 - screw_depth / 2 + 0.05)))
    return union(body, slot, *holes)


def horn_cutter(s: Servo, depth=None, center_d=9.0, through=20.0):
    """Sede della squadretta rotonda su una faccia a z=0 (la sede scende in -Z)."""
    depth = depth if depth is not None else s.horn_t
    seat = cyl(s.horn_d + FIT_H, depth + 0.1, (0, 0, -depth / 2 + 0.05))
    center = cyl(center_d, through, (0, 0, 0))            # passaggio della vite centrale / testa
    screws = [cyl(s.horn_hole_d, through, (s.horn_hole_r * math.cos(a), s.horn_hole_r * math.sin(a), 0))
              for a in np.arange(0, 2 * np.pi, np.pi / 2)]
    return union(seat, center, *screws)


def place_servo_x(cutter):
    """Riorienta un cutter (asse albero +Z, lunghezza lungo X) in: albero lungo +X,
    lunghezza del servo lungo +Y, larghezza lungo Z."""
    return R(R(cutter, 90, (0, 0, 1)), 90, (0, 1, 0))


# ----------------------------------------------------------------------------
# PARTI DEL MODELLO
# ----------------------------------------------------------------------------
def part_base():
    """Base: tasca MG996R (albero in alto al centro), canale cavo, 4 fori M4,
    sede anulare per la gonna del mozzo del palo."""
    L, Wd, H = 110.0, 90.0, 44.0
    body = box(L, Wd, H, (0, 0, H / 2))
    # smusso estetico/robustezza: niente (booleane piane), ma arrotondiamo gli spigoli verticali
    corners = [cyl(16, H, (sx * (L / 2 - 8), sy * (Wd / 2 - 8), H / 2)) for sx in (-1, 1) for sy in (-1, 1)]
    body = hull(*corners)
    cut = T(servo_cutter(MG996R), 0, 0, H)                       # faccia superiore del servo a filo
    cable = box_from_to(-L / 2 - 1, MG996R.x0 + 2, -6, 6, 8, 20)
    feet = [cyl(PRINT["hole_m4_clear"], H + 2, (sx * (L / 2 - 8), sy * (Wd / 2 - 8), H / 2)) for sx in (-1, 1) for sy in (-1, 1)]
    return diff(body, cut, cable, *feet)


def part_pole_hub():
    """Mozzo del palo: sta sulla squadretta del servo di azimut, porta il tubo del palo.
    Stampato con il disco sul piatto (la sede squadretta e' sulla faccia inferiore)."""
    disc = cyl(40, 4, (0, 0, 2))                                   # z 0..4 (fondo = faccia sulla squadretta)
    boss = cone(32, 24, 8, (0, 0, 4))                               # raccordo a 45 gradi
    boss2 = cyl(24, 18, (0, 0, 12 + 9))                             # z 12..30
    m = union(disc, boss, boss2)
    m = diff(m, horn_cutter(MG996R, depth=3.0, center_d=9.0),       # sede squadretta sulla faccia z=0 (verso -z)
             cyl(POLE_TUBE + FIT_T, 22, (0, 0, 30 - 10)),           # alloggio tubo: z 9..30 (cieco)
             box_from_to(-1.5, 1.5, 6, 30, 3.5, 31))                # fessura per il cavo del servo di inclinazione
    return m


def sleeve_with_servo_block(tube_d, sleeve_od, servo: Servo, sleeve_len=30.0, z_shaft=None):
    """Manicotto verticale per un tubo + blocco in cima con una tasca MG90S ad albero
    orizzontale (+X).  Usato per la cima del palo e per la punta del braccio."""
    body_w = 2 * (servo.half_w + FIT_S)                 # ingombro del servo lungo Z nel blocco
    depth = servo.body_h + FIT_S + 3.0                  # spessore blocco lungo -X (corpo + parete)
    blk_x0, blk_x1 = -depth, 0.0
    blk_y0, blk_y1 = servo.tab_x0 - 4.5, servo.tab_x1 + 4.5
    r = sleeve_od / 2
    # transizione a 45 gradi dal manicotto al blocco: altezza = massimo sbalzo laterale
    rise = max(depth - r, blk_y1 - r, -blk_y0 - r) + 1.0
    blk_z0 = sleeve_len + rise
    z_shaft = blk_z0 + W + body_w / 2
    blk_z1 = z_shaft + body_w / 2 + W
    block = box_from_to(blk_x0, blk_x1, blk_y0, blk_y1, blk_z0, blk_z1)
    sleeve = cyl(sleeve_od, sleeve_len + 1, (0, 0, (sleeve_len + 1) / 2))
    gusset = hull(box_from_to(-r, r, -r, r, sleeve_len - 0.5, sleeve_len + 0.5),
                  box_from_to(blk_x0, blk_x1, blk_y0, blk_y1, blk_z0 - 0.5, blk_z0 + 0.5))
    m = union(sleeve, block, gusset)
    cutter = T(place_servo_x(servo_cutter(servo, slot_up=40, screw_depth=8)), 0, 0, z_shaft)
    tube = cyl(tube_d + FIT_T, sleeve_len - 4 + 1, (0, 0, (sleeve_len - 4 - 1) / 2))   # cieco, dal basso
    cable = box_from_to(-sleeve_od / 2 - 1, -sleeve_od / 2 + 2.5, -3, 3, 6, sleeve_len + 1)  # scanalatura cavo sul manicotto
    return diff(m, cutter, tube, cable)


def part_pole_top():
    return sleeve_with_servo_block(POLE_TUBE, POLE_TUBE + 2 * W, MG90S)


def part_arm_tip():
    return sleeve_with_servo_block(ARM_TUBE, ARM_TUBE + 2 * W, MG90S)


def horn_disc_x(servo: Servo, d=24.0, t=3.0):
    """Disco con sede squadretta sulla faccia x=0 (verso -X), spessore t lungo +X."""
    disc = cyl(d, t, (t / 2, 0, 0), axis="x")
    cutter = R(horn_cutter(servo, depth=servo.horn_t, center_d=6.0, through=2 * t + 2), -90, (0, 1, 0))
    # horn_cutter scava verso -Z; ruotato di -90 attorno a Y, -Z -> +X: la sede entra nella faccia x=0
    return diff(disc, cutter)


def part_arm_root():
    """Radice del braccio: disco sulla squadretta del servo di inclinazione + manicotto per il tubo.
    Stampato con la faccia della squadretta (x=0) sul piatto: ruotato di -90 attorno a Y."""
    disc = horn_disc_x(MG90S)
    od = ARM_TUBE + 2 * W
    sleeve = cyl(od, 36, (od / 2, 0, 8 + 18))                       # lungo +Z, x da 0 a od
    bridge = box_from_to(0, od, -7, 7, 0, 12)
    m = union(disc, sleeve, bridge)
    m = diff(m, cyl(ARM_TUBE + FIT_T, 32, (od / 2, 0, 12 + 16)))    # alloggio tubo cieco (z 12..44)
    return R(m, -90, (0, 1, 0))   # faccia x=0 -> piatto (z=0), il manicotto sdraiato


def part_hub(offset=0.0):
    """Mozzo del tettuccio: disco sulla squadretta del servo di testa + staffa + piastra 40x40
    con 4 fori M3 (disco di forex) e 8 fori radiali per le stecche (tela).
    offset: sbalzo del centro tettuccio lungo +Y (versione 'sbalzo 50').
    Stampato con la piastra sul piatto."""
    disc = horn_disc_x(MG90S)                                      # faccia squadretta a x=0
    zp = 14.0                                                      # quota della piastra sopra l'asse del servo
    plate = box_from_to(-20, 20, offset - 20, offset + 20, zp, zp + 3)
    post = box_from_to(0, 3, -7, 7, 0, zp + 1)                     # montante dal disco alla piastra
    beam = box_from_to(-3, 3, -7, offset + 7, zp - 4, zp + 11)     # nervatura dal disco al mozzo: nella stampa poggia sul piatto
    boss = box_from_to(-20, 20, offset - 20, offset + 20, zp + 3, zp + 11)   # mozzo stecche a tutta piastra
    m = union(disc, post, beam, plate, boss)
    cut = [cyl(PRINT["hole_m3_clear"], 20, (sx * 14, offset + sy * 14, zp)) for sx in (-1, 1) for sy in (-1, 1)]
    for a in np.arange(0, 2 * np.pi, np.pi / 4):                   # stecche radiali d2
        cut.append(cyl(2.0 + 0.3, 24, (0 + 12 * math.cos(a), offset + 12 * math.sin(a), zp + 7),
                       axis="z"))
    spokes = []
    for a in np.arange(0, 2 * np.pi, np.pi / 4):
        c = cyl(2.3, 30, (0, 0, 0), axis="x")
        c = R(c, math.degrees(a), (0, 0, 1)); c = T(c, 20 * math.cos(a), offset + 20 * math.sin(a), zp + 7)
        spokes.append(c)
    m = diff(m, *cut[:4], *spokes)
    # orientamento di stampa: piastra sul piatto -> ribalto (z -> -z) e traslo
    m = R(m, 180, (1, 0, 0)); m = T(m, 0, 0, zp + 11)
    return m


# ----------------------------------------------------------------------------
# BANCO DEMO
# ----------------------------------------------------------------------------
def part_turntable_hub():
    disc = cyl(70, 8, (0, 0, 4))
    cut = [horn_cutter(MG996R, depth=3.0, center_d=9.0)]
    cut += [cyl(PRINT["hole_m4_clear"], 10, (28 * math.cos(a), 28 * math.sin(a), 4)) for a in np.arange(0, 2 * np.pi, np.pi / 3)]
    return diff(disc, *cut)


def part_turntable_servo_mount():
    L, Wd, H = 80.0, 60.0, 44.0
    body = box(L, Wd, H, (0, 0, H / 2))
    cut = T(servo_cutter(MG996R), 0, 0, H)
    cable = box_from_to(-L / 2 - 1, MG996R.x0 + 2, -6, 6, 8, 20)
    feet = [cyl(PRINT["hole_m4_clear"], H + 2, (sx * (L / 2 - 7), sy * (Wd / 2 - 7), H / 2)) for sx in (-1, 1) for sy in (-1, 1)]
    return diff(body, cut, cable, *feet)


def part_lamp_pivot():
    """Colonna con tasca MG996R ad albero orizzontale (+X) a quota 60 mm + piede 90x90."""
    z_shaft = 60.0
    body_w = 2 * (MG996R.half_w + FIT_S)
    depth = MG996R.body_h + FIT_S + 4.0
    blk = box_from_to(-depth, 0, MG996R.tab_x0 - 5, MG996R.tab_x1 + 5, 5, z_shaft + body_w / 2 + W)
    foot = box_from_to(-depth - 20, 20, MG996R.tab_x0 - 25, MG996R.tab_x1 + 25, 0, 5)
    m = union(blk, foot)
    cutter = T(place_servo_x(servo_cutter(MG996R, slot_up=60, screw_depth=10)), 0, 0, z_shaft)
    feet = [cyl(PRINT["hole_m4_clear"], 8, (x, y, 2.5)) for x in (-depth - 12, 12) for y in (MG996R.tab_x0 - 17, MG996R.tab_x1 + 17)]
    cable = box_from_to(-depth - 1, -depth + 6, MG996R.xc - 6, MG996R.xc + 6, 20, 40)
    return diff(m, cutter, cable, *feet)


def part_lamp_arm_root():
    disc = cyl(30, 4, (2, 0, 0), axis="x")
    disc = diff(disc, R(horn_cutter(MG996R, depth=3.0, center_d=9.0, through=12), -90, (0, 1, 0)))
    od = LAMP_TUBE + 2 * W
    sleeve = cyl(od, 44, (od / 2 + 1, 0, 10 + 22))
    bridge = box_from_to(0, od + 1, -8, 8, 0, 14)
    m = union(disc, sleeve, bridge)
    m = diff(m, cyl(LAMP_TUBE + FIT_T, 40, (od / 2 + 1, 0, 14 + 20)))
    return R(m, -90, (0, 1, 0))


def part_lamp_holder(led_d=28.0):
    od = LAMP_TUBE + 2 * W
    sleeve = cyl(od, 30, (0, 0, 15))
    trans = cone(od, led_d + 2 * W, 10, (0, 0, 30))
    ring = cyl(led_d + 2 * W, 12, (0, 0, 40 + 6))
    m = union(sleeve, trans, ring)
    return diff(m, cyl(LAMP_TUBE + FIT_T, 29, (0, 0, 14)), cyl(led_d + FIT_H, 14, (0, 0, 40 + 6.5)),
                cyl(6, 14, (0, 0, 33)))   # passaggio cavo LED


# ----------------------------------------------------------------------------
# verifica e output
# ----------------------------------------------------------------------------
PARTS = {
    "01_base": (part_base, "base del modello: servo azimut MG996R 270°, 4 viti M4 alla piattaforma"),
    "02_pole_hub": (part_pole_hub, "mozzo del palo sulla squadretta rotonda; incollare il tubo Ø10"),
    "03_pole_top": (part_pole_top, "cima del palo: tasca MG90S (inclinazione), albero orizzontale"),
    "04_arm_root": (part_arm_root, "radice del braccio sulla squadretta MG90S; incollare il tubo Ø8"),
    "05_arm_tip": (part_arm_tip, "punta del braccio: tasca MG90S (testa), albero perpendicolare al braccio"),
    "06_hub_centrato": (lambda: part_hub(0.0), "mozzo tettuccio centrato: piastra 40x40 4xM3 + 8 stecche Ø2"),
    "06b_hub_sbalzo50": (lambda: part_hub(50.0), "mozzo tettuccio con sbalzo 50 mm (variante)"),
    "07_turntable_hub": (part_turntable_hub, "banco demo: mozzo piattaforma sulla squadretta MG996R, 6 viti M4"),
    "08_turntable_servo_mount": (part_turntable_servo_mount, "banco demo: supporto del servo piattaforma, 4 viti M4 al tavolo"),
    "09_lamp_pivot": (part_lamp_pivot, "banco demo: colonna del braccio lampada, tasca MG996R orizzontale"),
    "10_lamp_arm_root": (part_lamp_arm_root, "banco demo: attacco braccio lampada (tubo Ø10) sulla squadretta"),
    "11_lamp_holder": (part_lamp_holder, "banco demo: porta-LED Ø28 in punta al tubo Ø10"),
}


def overhang_area(m: trimesh.Trimesh, max_deg: float) -> float:
    """Area delle facce rivolte verso il basso piu' ripide del limite, escluso il piatto (z=0)."""
    n = m.face_normals
    down = n[:, 2] < -math.cos(math.radians(90 - max_deg)) - 1e-6   # normale verso il basso oltre 45 gradi
    zc = m.triangles_center[:, 2]
    bad = down & (zc > 0.3)
    return float(m.area_faces[bad].sum())


def render(m: trimesh.Trimesh, path: Path, title: str):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    fig = plt.figure(figsize=(5, 4.2), dpi=110)
    ax = fig.add_subplot(111, projection="3d")
    tri = m.vertices[m.faces]
    shade = 0.55 + 0.45 * np.clip(m.face_normals @ np.array([0.3, 0.4, 0.86]), 0, 1)
    cols = np.column_stack([shade * 0.55, shade * 0.72, shade * 0.85, np.ones_like(shade)])
    pc = Poly3DCollection(tri, facecolors=cols, edgecolors="none")
    ax.add_collection3d(pc)
    lo, hi = m.bounds
    c = (lo + hi) / 2; r = (hi - lo).max() / 2
    ax.set_xlim(c[0] - r, c[0] + r); ax.set_ylim(c[1] - r, c[1] + r); ax.set_zlim(0, 2 * r)
    ax.set_box_aspect((1, 1, 1)); ax.view_init(28, -50)
    ax.set_title(title, fontsize=9); ax.set_xlabel("x"); ax.set_ylabel("y")
    fig.savefig(path, bbox_inches="tight"); plt.close(fig)


def assembly(theta_deg=40.0, beta_rel_deg=-15.0):
    """Assieme del modello (senza banco demo) per controllare la cinematica e gli ingombri.
    theta: inclinazione del braccio; beta_rel: rotazione della testa rispetto al braccio."""
    parts = []
    base = part_base(); parts.append(base)
    H_BASE = 44.0
    hub = part_pole_hub(); parts.append(T(hub, 0, 0, H_BASE + 2.0))              # sulla squadretta (2 mm sopra il corpo)
    z_tube0 = H_BASE + 2.0 + 9.0
    POLE_LEN = 250.0
    parts.append(cyl(POLE_TUBE, POLE_LEN, (0, 0, z_tube0 + POLE_LEN / 2)))
    top = part_pole_top()
    z_top0 = z_tube0 + POLE_LEN - 26.0
    parts.append(T(top, 0, 0, z_top0))
    # asse di inclinazione: albero del MG90S a (x=0, y=0, z_top0 + z_shaft_top)
    tb = top.bounds; z_shaft = z_top0 + (tb[1][2] - (MG90S.half_w + FIT_S) - W)
    # radice del braccio: disco sulla squadretta (x = +4), braccio lungo +Z ruotato di theta attorno a X
    root = R(part_arm_root(), 90, (0, 1, 0))                      # riporta la faccia squadretta su x=0
    arm = union(root, cyl(ARM_TUBE, 200, (ARM_TUBE / 2 + W, 0, 12 + 100)))
    tip = part_arm_tip()
    arm = union(arm, T(R(tip, 0, (0, 0, 1)), ARM_TUBE / 2 + W, 0, 12 + 200 - 26))
    tipb = T(tip, ARM_TUBE / 2 + W, 0, 12 + 200 - 26).bounds
    z_head = tipb[1][2] - (MG90S.half_w + FIT_S) - W
    head = R(part_hub(0.0), 180, (1, 0, 0)); head = T(head, 0, 0, -(head.bounds[1][2]))   # ripristina orientamento: piastra in alto
    hb = head.bounds; head = T(head, 0, 0, -hb[0][2])
    # il disco squadretta della testa sta a x=0.. ; centro sull'asse testa
    canopy = cyl(300, 3, (0, 0, 25 + 1.5))
    head = union(head, canopy)
    head = R(head, beta_rel_deg, (1, 0, 0))
    head = T(head, ARM_TUBE / 2 + W + 4, 0, z_head)
    arm = union(arm, head)
    arm = R(arm, theta_deg, (1, 0, 0)); arm = T(arm, 4.0, 0, z_shaft)
    parts.append(arm)
    return trimesh.util.concatenate(parts)


def main():
    rows = ["# Parti stampabili — report di generazione\n",
            "Generato da `python hardware/build_parts.py`. Ogni STL e' gia' orientato per la stampa (z=0 sul piatto).\n",
            "| file | descrizione | ingombro x·y·z [mm] | volume [cm³] | PETG ≈ g (30 % riempimento) | chiusa | sporgenze > 45° [cm²] |",
            "|---|---|---|---|---|---|---|"]
    ok_all = True
    for name, (fn, desc) in PARTS.items():
        m = fn()
        lo, hi = m.bounds
        m.apply_translation([0, 0, -lo[2]])                 # piatto a z=0
        lo, hi = m.bounds
        ext = hi - lo
        wt = bool(m.is_watertight)
        oh = overhang_area(m, PRINT["max_overhang_deg"]) / 100.0
        vol = float(abs(m.volume)) / 1000.0
        grams = vol * 1.27 * 0.5
        fits = all(e <= b for e, b in zip(ext, PRINT["bed"]))
        ok_all &= wt and fits
        m.export(OUT / f"{name}.stl")
        render(m, OUT / f"{name}.png", f"{name}  {ext[0]:.0f}×{ext[1]:.0f}×{ext[2]:.0f} mm")
        rows.append(f"| `{name}.stl` | {desc} | {ext[0]:.0f} · {ext[1]:.0f} · {ext[2]:.0f} | {vol:.1f} | {grams:.0f} | {'sì' if wt else 'NO'} | {oh:.1f} |")
        print(f"{name:28s} {ext[0]:6.1f} {ext[1]:6.1f} {ext[2]:6.1f}  vol {vol:6.1f} cm3  watertight={wt}  overhang={oh:.1f} cm2")
    rows.append("\n## Regole usate\n")
    rows.append("```\n" + "\n".join(f"{k}: {v}" for k, v in PRINT.items()) + "\n```\n")
    rows.append("Servo: MG996R (corpo 40.5×20×38, flange a 27.5 mm dal fondo, fori 49.5×10 → M3 autofilettanti 2.6 mm), "
                "MG90S (corpo 22.8×12.2×22.5, flange a 16 mm dal fondo, fori a 28 mm → M2 autofilettanti 1.8 mm). "
                "Tubi carbonio Ø10 (palo, braccio lampada) e Ø8 (braccio), gioco 0.35 mm, incollare con epossidica.\n")
    (OUT / "report.md").write_text("\n".join(rows), encoding="utf-8")
    asm = assembly()
    asm.export(OUT / "assieme_modello.stl")
    render(asm, OUT / "assieme_modello.png", "assieme del modello (braccio a 40°, tettuccio Ø300)")
    print("tutte chiuse e nel piatto:", ok_all)


if __name__ == "__main__":
    main()
