"""Studio meccanico-robotico: masse, carichi da vento, coppie ai giunti,
ribaltamento, dimensionamento motori, verifica strutturale del braccio e
un piccolo solutore a elementi finiti (telaio piano, travi di Eulero-Bernoulli)
per palo + braccio.

Tutte le formule sono di primo dimensionamento (fase di concept): servono a
scegliere sezioni, motori e zavorra prima di passare a un CAD/FEM completo.
Unita' SI (m, kg, N, Pa) salvo dove indicato.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from .geometry import Umbrella, Pose, forward_kinematics, horiz_unit

G = 9.81
RHO_AIR = 1.225


# ----------------------------------------------------------------------------
# materiali
# ----------------------------------------------------------------------------
@dataclass(frozen=True)
class Material:
    name: str
    E: float          # modulo elastico [Pa]
    sigma_y: float    # tensione ammissibile / snervamento [Pa]
    rho: float        # densita' [kg/m^3]
    cost_eur_kg: float
    note: str = ""


MATERIALS: dict[str, Material] = {
    "Al 6061-T6": Material("Alluminio 6061-T6", 69e9, 240e6, 2700, 8.0,
                           "tubo anodizzato: standard per ombrelloni, saldabile, leggero"),
    "Acciaio S235": Material("Acciaio S235 zincato", 210e9, 235e6, 7850, 2.5,
                             "rigido ed economico, ma pesante: alza coppie e zavorra"),
    "Inox 304": Material("Acciaio inox AISI 304", 193e9, 215e6, 8000, 7.0,
                         "resistenza salsedine, ottimo per perni e viteria"),
    "CFRP": Material("Tubo carbonio pultruso", 110e9, 500e6, 1600, 60.0,
                     "leggerissimo e rigido, caro, va protetto dai raggi UV e dagli urti"),
    "GFRP": Material("Vetroresina pultrusa", 35e9, 300e6, 1900, 12.0,
                     "economico, flessibile: ok per stecche, meno per il braccio"),
    "PETG (stampa 3D)": Material("PETG stampato", 2.0e9, 45e6, 1270, 25.0,
                                 "per il mini-prototipo: giunti, supporti, mozzo"),
    "Carbonio 8 mm (mini)": Material("Tubo carbonio 8x6 mm", 100e9, 500e6, 1600, 60.0,
                                     "braccio del mini-prototipo (aste da aquilone/drone)"),
}


# ----------------------------------------------------------------------------
# sezioni tubolari
# ----------------------------------------------------------------------------
@dataclass(frozen=True)
class Tube:
    D: float   # diametro esterno [m]
    t: float   # spessore [m]

    @property
    def d(self) -> float:
        return self.D - 2 * self.t

    @property
    def area(self) -> float:
        return math.pi / 4 * (self.D**2 - self.d**2)

    @property
    def I(self) -> float:
        return math.pi / 64 * (self.D**4 - self.d**4)

    @property
    def W(self) -> float:  # modulo di resistenza
        return self.I / (self.D / 2)

    def mass_per_m(self, m: Material) -> float:
        return self.area * m.rho


# ----------------------------------------------------------------------------
# masse del sistema
# ----------------------------------------------------------------------------
@dataclass
class MassModel:
    canopy_fabric_kg_m2: float = 0.30      # acrilico 300 g/m2
    n_ribs: int = 8
    rib_kg_m: float = 0.09                 # stecca Al 12x1 mm
    head_kg: float = 1.5                   # mozzo + motori testa tettuccio
    arm_tube: Tube = field(default_factory=lambda: Tube(0.060, 0.003))
    arm_material: str = "Al 6061-T6"
    joint_kg: float = 3.0                  # snodo cima palo con motoriduttori
    pole_tube: Tube = field(default_factory=lambda: Tube(0.080, 0.004))
    pole_material: str = "Al 6061-T6"
    electronics_kg: float = 1.0

    def canopy_mass(self, u: Umbrella) -> float:
        area = math.pi * u.R**2
        return area * self.canopy_fabric_kg_m2 + self.n_ribs * u.R * self.rib_kg_m + self.head_kg

    def arm_mass(self, u: Umbrella, L: float | None = None) -> float:
        L = L if L is not None else u.L
        return self.arm_tube.mass_per_m(MATERIALS[self.arm_material]) * L

    def pole_mass(self, u: Umbrella) -> float:
        return self.pole_tube.mass_per_m(MATERIALS[self.pole_material]) * u.H


# ----------------------------------------------------------------------------
# vento
# ----------------------------------------------------------------------------
def wind_force_on_disk(R: float, n: np.ndarray, wind_dir_az_deg: float, v: float) -> np.ndarray:
    """Forza aerodinamica (vettore, N) su un disco di normale ``n`` e raggio ``R``.

    Modello a lastra piana: forza normale al disco, coefficiente
    C_N = max(1.17*|sin a|, 0.35) dove a e' l'angolo d'attacco fra vento e disco.
    Il minimo 0.35 rappresenta la portanza del tettuccio bombato con vento radente
    (e' il caso che "strappa" gli ombrelloni veri).
    """
    w = horiz_unit(wind_dir_az_deg)      # direzione da cui soffia -> verso cui spinge
    n = n / np.linalg.norm(n)
    sin_a = abs(float(w @ n))            # angolo d'attacco: 90 deg se vento perpendicolare
    cn = max(1.17 * sin_a, 0.35)
    q = 0.5 * RHO_AIR * v**2
    A = math.pi * R**2
    sign = 1.0 if float(w @ n) >= 0 else -1.0
    return sign * q * cn * A * n


def wind_force_on_tube(L: float, D: float, v: float) -> float:
    """Resistenza su un cilindro trasversale al vento (Cd~1.2)."""
    return 0.5 * RHO_AIR * v**2 * 1.2 * D * L


# ----------------------------------------------------------------------------
# coppie ai giunti e ribaltamento
# ----------------------------------------------------------------------------
@dataclass
class Loads:
    wind_speed: float
    wind_dir_deg: float
    tilt_torque_Nm: float      # coppia sul giunto di inclinazione braccio
    azimuth_torque_Nm: float   # coppia sul giunto di rotazione (asse verticale)
    head_torque_Nm: float      # coppia sul giunto del tettuccio
    base_moment_Nm: float      # momento ribaltante alla base
    canopy_force_N: float
    arm_tip_force_N: np.ndarray


def joint_loads(u: Umbrella, p: Pose, mm: MassModel, v_wind: float, wind_dir_deg: float) -> Loads:
    fk = forward_kinematics(u, p)
    P, E, C, n = fk["P"], fk["E"], fk["C"], fk["n"]
    L = fk["L"]
    m_c = mm.canopy_mass(u)
    m_a = mm.arm_mass(u, L)

    Fw_c = wind_force_on_disk(u.R, n, wind_dir_deg, v_wind)
    Fw_a = wind_force_on_tube(L, mm.arm_tube.D, v_wind) * horiz_unit(wind_dir_deg)
    Fg_c = np.array([0, 0, -m_c * G])
    Fg_a = np.array([0, 0, -m_a * G])
    arm_mid = (P + E) / 2

    def moment(point, forces_points):
        M = np.zeros(3)
        for F, X in forces_points:
            M += np.cross(X - point, F)
        return M

    M_joint = moment(P, [(Fw_c + Fg_c, C), (Fw_a + Fg_a, arm_mid)])
    # asse di inclinazione: orizzontale, perpendicolare al piano verticale del braccio
    tilt_axis = np.cross(np.array([0, 0, 1.0]), horiz_unit(p.alpha_deg))
    tilt_torque = abs(float(M_joint @ tilt_axis))
    az_torque = abs(float(M_joint[2]))
    # giunto testa: peso + vento attorno a E.  Il centro di pressione di una
    # lastra inclinata non e' al centro: si sposta verso il bordo sopravvento di
    # e_cp = 0.5*R*(1 - sin a) (a = angolo d'attacco), quindi anche con sbalzo
    # nullo il vento genera una coppia sulla cerniera del tettuccio.
    w = horiz_unit(wind_dir_deg)
    sin_a = abs(float(w @ (n / np.linalg.norm(n))))
    e_cp = 0.5 * u.R * (1.0 - sin_a)
    M_head = moment(E, [(Fw_c + Fg_c, C)])
    head_torque = float(np.linalg.norm(M_head)) + float(np.linalg.norm(Fw_c)) * e_cp
    # ribaltamento: momento orizzontale rispetto alla base (origine)
    Fw_p = wind_force_on_tube(u.H, mm.pole_tube.D, v_wind) * horiz_unit(wind_dir_deg)
    M_base = moment(np.zeros(3), [(Fw_c + Fg_c, C), (Fw_a + Fg_a, arm_mid),
                                  (Fw_p, np.array([0, 0, u.H / 2]))])
    base_moment = float(np.hypot(M_base[0], M_base[1]))
    return Loads(v_wind, wind_dir_deg, tilt_torque, az_torque, head_torque, base_moment,
                 float(np.linalg.norm(Fw_c)), Fw_c + Fg_c)


def worst_case_loads(u: Umbrella, p: Pose, mm: MassModel, v_wind: float) -> Loads:
    """Vento da tutte le direzioni (passo 15 gradi): inviluppo dei carichi.

    Ogni coppia/momento e' il massimo sulla propria direzione peggiore (sono
    grandezze di dimensionamento di componenti diversi); la forza in punta e'
    quella della direzione che massimizza la flessione del braccio.
    """
    fk = forward_kinematics(u, p)
    arm_dir = fk["arm_dir"]
    cases = [joint_loads(u, p, mm, v_wind, az) for az in range(0, 360, 15)]

    def perp(F):
        return float(np.linalg.norm(F - arm_dir * float(F @ arm_dir)))

    bend = max(cases, key=lambda l: perp(l.arm_tip_force_N))
    base = max(cases, key=lambda l: l.base_moment_Nm)
    return Loads(v_wind, base.wind_dir_deg,
                 max(l.tilt_torque_Nm for l in cases),
                 max(l.azimuth_torque_Nm for l in cases),
                 max(l.head_torque_Nm for l in cases),
                 base.base_moment_Nm,
                 max(l.canopy_force_N for l in cases),
                 bend.arm_tip_force_N)


def required_base_mass(u: Umbrella, p: Pose, mm: MassModel, v_wind: float, base_radius: float,
                       safety: float = 1.5) -> float:
    """Zavorra necessaria perche' non si ribalti (base circolare di raggio ``base_radius``).

    Momento stabilizzante: tutte le masse x g x (r_base - sbraccio orizzontale).
    """
    l = worst_case_loads(u, p, mm, v_wind)
    fk = forward_kinematics(u, p)
    m_c = mm.canopy_mass(u)
    m_a = mm.arm_mass(u, fk["L"])
    m_p = mm.pole_mass(u) + mm.joint_kg + mm.electronics_kg
    x_c = math.hypot(*fk["C"][:2])
    x_a = math.hypot(*((fk["P"] + fk["E"]) / 2)[:2])
    stabilizing = G * (m_c * (base_radius - x_c) + m_a * (base_radius - x_a) + m_p * base_radius)
    need = safety * l.base_moment_Nm - stabilizing
    return max(0.0, need / (G * base_radius))


# ----------------------------------------------------------------------------
# motori
# ----------------------------------------------------------------------------
@dataclass
class MotorSpec:
    joint: str
    holding_torque_Nm: float
    design_torque_Nm: float    # con fattore di sicurezza
    output_speed_rpm: float
    gear_ratio: float
    motor_torque_Nm: float     # coppia richiesta al motore prima del riduttore
    power_W: float
    suggestion: str


def size_motor(joint: str, torque_Nm: float, travel_deg: float, time_s: float,
               gear_ratio: float, efficiency: float, safety: float = 2.0) -> MotorSpec:
    design = torque_Nm * safety
    rpm_out = (travel_deg / 360.0) / (time_s / 60.0)
    motor_torque = design / (gear_ratio * efficiency)
    power = design * (rpm_out * 2 * math.pi / 60.0) / efficiency
    if motor_torque < 0.4:
        sugg = "NEMA17 stepper (0.4-0.5 Nm) o DC 12V 30-50 W con riduttore"
    elif motor_torque < 1.5:
        sugg = "NEMA23 stepper (1.2-1.9 Nm) o DC 24V 60-100 W"
    else:
        sugg = "motoriduttore DC 24V >100 W, oppure riduttore piu' spinto"
    return MotorSpec(joint, torque_Nm, design, rpm_out, gear_ratio, motor_torque, power, sugg)


def size_linear_actuator(joint: str, torque_Nm: float, lever_arm_m: float, travel_deg: float,
                         time_s: float, safety: float = 2.0) -> dict:
    """Attuatore lineare (vite + motore DC, autobloccante) che agisce su una leva.

    E' la scelta pratica per inclinazione braccio e tettuccio: coppie di
    centinaia di Nm con attuatori economici da 1000-3000 N.
    """
    force = torque_Nm * safety / lever_arm_m
    stroke = 2 * lever_arm_m * math.sin(math.radians(travel_deg) / 2)
    speed = stroke / time_s
    return {"giunto": joint, "forza_N": force, "corsa_mm": stroke * 1000,
            "velocita_mm_s": speed * 1000, "braccio_leva_m": lever_arm_m,
            "suggerimento": ("attuatore 12/24 V classe 1500 N" if force < 1500 else
                             "attuatore 12/24 V classe 3000-6000 N" if force < 6000 else
                             "aumentare il braccio di leva o usare due attuatori")}


# ----------------------------------------------------------------------------
# verifica a trave del braccio (cantilever)
# ----------------------------------------------------------------------------
@dataclass
class BeamCheck:
    material: str
    tube: Tube
    mass_kg: float
    tip_force_N: float
    max_moment_Nm: float
    stress_MPa: float
    safety_factor: float
    tip_deflection_mm: float


def arm_beam_check(u: Umbrella, p: Pose, mm: MassModel, tube: Tube, material: str,
                   v_wind: float) -> BeamCheck:
    """Braccio come mensola incastrata nello snodo, carico in punta = tettuccio (peso+vento)."""
    mat = MATERIALS[material]
    mm2 = MassModel(**{**mm.__dict__, "arm_tube": tube, "arm_material": material})
    loads = worst_case_loads(u, p, mm2, v_wind)
    fk = forward_kinematics(u, p)
    L = fk["L"]
    arm_dir = fk["arm_dir"]
    F = loads.arm_tip_force_N
    # componente della forza perpendicolare al braccio -> flessione
    F_perp = F - arm_dir * float(F @ arm_dir)
    Fp = float(np.linalg.norm(F_perp))
    q = tube.mass_per_m(mat) * G * math.sin(math.radians(p.theta_deg))  # peso proprio trasversale
    # sbalzo del tettuccio: aggiunge momento concentrato
    M_off = mm2.canopy_mass(u) * G * u.canopy_offset
    M_max = Fp * L + q * L**2 / 2 + M_off
    sigma = M_max / tube.W
    delta = Fp * L**3 / (3 * mat.E * tube.I) + q * L**4 / (8 * mat.E * tube.I) + M_off * L**2 / (2 * mat.E * tube.I)
    return BeamCheck(material, tube, tube.mass_per_m(mat) * L, Fp, M_max, sigma / 1e6,
                     mat.sigma_y / sigma if sigma > 0 else float("inf"), delta * 1000)


def material_sweep(u: Umbrella, p: Pose, mm: MassModel, v_wind: float,
                   candidates: dict[str, list[Tube]]) -> list[BeamCheck]:
    out = []
    for mat, tubes in candidates.items():
        for tb in tubes:
            out.append(arm_beam_check(u, p, mm, tb, mat, v_wind))
    return out


# ----------------------------------------------------------------------------
# FEM: telaio piano con travi di Eulero-Bernoulli (3 gdl/nodo: u, v, rot)
# ----------------------------------------------------------------------------
@dataclass
class FrameResult:
    nodes: np.ndarray            # (n,2) coordinate nel piano verticale del braccio (r, z)
    disp: np.ndarray             # (n,3) spostamenti u, v, rot
    deformed: np.ndarray         # (n,2) coordinate deformate (scala 1)
    tip_deflection_mm: float
    max_stress_MPa: np.ndarray   # per elemento
    elements: list[tuple[int, int]]


def _beam_k(E: float, A: float, I: float, L: float, c: float, s: float) -> np.ndarray:
    k = np.array([
        [E * A / L, 0, 0, -E * A / L, 0, 0],
        [0, 12 * E * I / L**3, 6 * E * I / L**2, 0, -12 * E * I / L**3, 6 * E * I / L**2],
        [0, 6 * E * I / L**2, 4 * E * I / L, 0, -6 * E * I / L**2, 2 * E * I / L],
        [-E * A / L, 0, 0, E * A / L, 0, 0],
        [0, -12 * E * I / L**3, -6 * E * I / L**2, 0, 12 * E * I / L**3, -6 * E * I / L**2],
        [0, 6 * E * I / L**2, 2 * E * I / L, 0, -6 * E * I / L**2, 4 * E * I / L],
    ])
    T = np.zeros((6, 6))
    r = np.array([[c, s, 0], [-s, c, 0], [0, 0, 1]])
    T[:3, :3] = r
    T[3:, 3:] = r
    return T.T @ k @ T


def frame_fem(u: Umbrella, p: Pose, mm: MassModel, v_wind: float, wind_dir_deg: float | None = None,
              n_el: int = 8) -> FrameResult:
    """Palo + braccio come telaio piano nel piano verticale del braccio.

    Il palo e' incastrato alla base; il giunto in cima e' considerato bloccato
    (motore con freno/vite senza fine).  Il carico del tettuccio (peso + vento,
    componente nel piano) e' applicato in punta; il peso proprio e' distribuito.
    Ritorna spostamenti e tensioni massime per elemento.
    """
    fk = forward_kinematics(u, p)
    L = fk["L"]
    th = math.radians(p.theta_deg)
    e_r = horiz_unit(p.alpha_deg)                 # direzione orizzontale del braccio
    mat_p, mat_a = MATERIALS[mm.pole_material], MATERIALS[mm.arm_material]
    tp, ta = mm.pole_tube, mm.arm_tube

    # nodi: palo da (0,0) a (0,H), braccio da (0,H) a (L sin th, H + L cos th)
    pole_nodes = [(0.0, u.H * i / n_el) for i in range(n_el + 1)]
    arm_nodes = [(L * math.sin(th) * i / n_el, u.H + L * math.cos(th) * i / n_el) for i in range(1, n_el + 1)]
    nodes = np.array(pole_nodes + arm_nodes)
    elements = [(i, i + 1) for i in range(n_el)] + [(n_el, n_el + 1)] + \
               [(n_el + i, n_el + i + 1) for i in range(1, n_el)]
    props = [(mat_p, tp)] * n_el + [(mat_a, ta)] * n_el
    ndof = 3 * len(nodes)
    K = np.zeros((ndof, ndof))
    F = np.zeros(ndof)

    for (i, j), (mat, tb) in zip(elements, props):
        dx, dz = nodes[j] - nodes[i]
        Le = math.hypot(dx, dz)
        c, s = dx / Le, dz / Le
        k = _beam_k(mat.E, tb.area, tb.I, Le, c, s)
        idx = [3 * i, 3 * i + 1, 3 * i + 2, 3 * j, 3 * j + 1, 3 * j + 2]
        K[np.ix_(idx, idx)] += k
        # peso proprio come carichi nodali equivalenti (meta' per nodo)
        w = tb.mass_per_m(mat) * G * Le
        F[3 * i + 1] -= w / 2
        F[3 * j + 1] -= w / 2

    # carico in punta: peso tettuccio + vento (worst case nel piano se non specificato)
    if wind_dir_deg is None:
        loads = worst_case_loads(u, p, mm, v_wind)
    else:
        loads = joint_loads(u, p, mm, v_wind, wind_dir_deg)
    Ftip = loads.arm_tip_force_N
    tip = len(nodes) - 1
    F[3 * tip] += float(Ftip[:2] @ e_r[:2])        # componente radiale (nel piano)
    F[3 * tip + 1] += float(Ftip[2])
    F[3 * tip + 2] += mm.canopy_mass(u) * G * (-u.canopy_offset)  # momento dello sbalzo

    fixed = [0, 1, 2]
    free = [d for d in range(ndof) if d not in fixed]
    d = np.zeros(ndof)
    d[free] = np.linalg.solve(K[np.ix_(free, free)], F[free])
    disp = d.reshape(-1, 3)

    # tensioni: sigma = N/A + M*(D/2)/I ai nodi di estremita' di ogni elemento
    stresses = []
    for (i, j), (mat, tb) in zip(elements, props):
        dx, dz = nodes[j] - nodes[i]
        Le = math.hypot(dx, dz)
        c, s = dx / Le, dz / Le
        k_loc = _beam_k(mat.E, tb.area, tb.I, Le, 1.0, 0.0)
        r = np.array([[c, s, 0], [-s, c, 0], [0, 0, 1]])
        T = np.zeros((6, 6)); T[:3, :3] = r; T[3:, 3:] = r
        de = T @ np.concatenate([disp[i], disp[j]])
        f = k_loc @ de                      # forze di estremita' in coordinate locali
        N = abs(f[0]); M = max(abs(f[2]), abs(f[5]))
        stresses.append((N / tb.area + M / tb.W) / 1e6)
    deformed = nodes + disp[:, :2]
    tip_defl = float(np.linalg.norm(disp[tip, :2]) * 1000)
    return FrameResult(nodes, disp, deformed, tip_defl, np.array(stresses), elements)


# ----------------------------------------------------------------------------
# leggi di scala per il mini-prototipo
# ----------------------------------------------------------------------------
def scale_report(u_full: Umbrella, scale: float) -> dict:
    """Come cambiano le grandezze passando dal modello reale al mini (stessa velocita' del vento)."""
    return {
        "scala_lunghezze": scale,
        "H_m": u_full.H * scale,
        "L_m": u_full.L * scale,
        "R_m": u_full.R * scale,
        "fattore_aree_e_forze_vento": scale**2,
        "fattore_masse": scale**3,
        "fattore_momenti_gravita": scale**4,
        "fattore_momenti_vento": scale**3,
        "nota": "a parita' di vento il mini e' relativamente PIU' robusto: valida software e cinematica, non la struttura",
    }
