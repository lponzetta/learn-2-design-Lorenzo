/*
 * Ombrellone intelligente - firmware ESP32 (mini-prototipo e base per il reale)
 * ----------------------------------------------------------------------------
 * Funzioni:
 *  - ora via NTP (WiFi) con fallback RTC DS3231 (opzionale)
 *  - posizione del sole (stesso algoritmo NOAA del pacchetto Python)
 *  - soluzione cinematica: centro ombra sul bersaglio, tettuccio verso il sole,
 *    saturazione ai limiti + raffinamento numerico del margine di copertura
 *  - 4 servo: azimut braccio (alpha), inclinazione braccio (theta),
 *    inclinazione tettuccio (beta), azimut tettuccio (gamma)
 *  - web app minimale (http://ombrellone.local o IP): scegli la zona d'ombra
 *    toccando la pianta, vedi stato e limiti ("copertura totale fino alle ...")
 *  - isteresi: si muove solo quando il margine scende sotto soglia
 *  - calibrazione del Nord: dai l'orario e punta il braccio verso il sole,
 *    oppure usa il magnetometro (opzionale)
 *
 * Librerie (Library Manager): ESP32Servo, (opz.) RTClib, TinyGPSPlus, QMC5883LCompass
 * Scheda: ESP32 Dev Module.  Alimentazione servo SEPARATA (5-6 V, >= 3 A).
 */
#include <WiFi.h>
#include <WebServer.h>
#include <ESPmDNS.h>
#include <ESP32Servo.h>
#include <Preferences.h>
#include <time.h>
#include <math.h>

#include "config.h"
#include "webpage.h"

// ---------------------------------------------------------------- stato
struct Target { float x = 0, y = 0, r = TARGET_R_DEFAULT; };   // metri (scala del modello)
struct Pose   { float alpha = 180, theta = 0, beta = 0, gamma = 180; };
struct SunPos { float elev, az; bool up; };

Target target;
Pose   held;            // posa attualmente tenuta
Pose   ideal;           // posa ottima istantanea
float  heldMargin = 0, heldCoverage = 0, idealMargin = 0, idealCoverage = 0;
bool   fullCoverage = false, parked = true;
unsigned long lastMoveMs = 0;
Preferences prefs;
WebServer server(80);
Servo sAlpha, sTheta, sBeta, sGamma;
#if DEMO_RIG
Servo sTable, sLamp;
#endif
// modalita' demo: tempo accelerato (giornata in pochi minuti) e sole artificiale
struct Demo { bool on = false; float speed = DEMO_SPEED_DEFAULT; time_t t0 = 0; unsigned long ms0 = 0; } demo;
static time_t currentEpoch() {
  if (demo.on) return demo.t0 + (time_t)((millis() - demo.ms0) / 1000.0f * demo.speed);
  return time(nullptr);
}

// ---------------------------------------------------------------- utilita'
static const float DEG = 3.14159265358979f / 180.0f;
static inline float clampf(float v, float lo, float hi) { return v < lo ? lo : (v > hi ? hi : v); }
static inline float wrap360(float a) { a = fmodf(a, 360.0f); return a < 0 ? a + 360.0f : a; }

// ---------------------------------------------------------------- sole (NOAA)
SunPos sunPosition(time_t utc, float lat, float lon) {
  struct tm tmv; gmtime_r(&utc, &tmv);
  int y = tmv.tm_year + 1900, m = tmv.tm_mon + 1;
  double d = tmv.tm_mday + (tmv.tm_hour + (tmv.tm_min + tmv.tm_sec / 60.0) / 60.0) / 24.0;
  if (m <= 2) { y -= 1; m += 12; }
  int a = y / 100, b = 2 - a + a / 4;
  double jd = floor(365.25 * (y + 4716)) + floor(30.6001 * (m + 1)) + d + b - 1524.5;
  double jc = (jd - 2451545.0) / 36525.0;
  double gml = fmod(280.46646 + jc * (36000.76983 + jc * 0.0003032), 360.0);
  double gma = 357.52911 + jc * (35999.05029 - 0.0001537 * jc);
  double ecc = 0.016708634 - jc * (0.000042037 + 0.0000001267 * jc);
  double gmar = gma * DEG;
  double ceq = sin(gmar) * (1.914602 - jc * (0.004817 + 0.000014 * jc)) + sin(2 * gmar) * (0.019993 - 0.000101 * jc) + sin(3 * gmar) * 0.000289;
  double tl = gml + ceq;
  double omega = 125.04 - 1934.136 * jc;
  double al = tl - 0.00569 - 0.00478 * sin(omega * DEG);
  double mo = 23.0 + (26.0 + (21.448 - jc * (46.815 + jc * (0.00059 - jc * 0.001813))) / 60.0) / 60.0;
  double ob = mo + 0.00256 * cos(omega * DEG);
  double decl = asin(sin(ob * DEG) * sin(al * DEG));
  double yy = tan(ob * DEG / 2); yy *= yy;
  double eot = 4.0 / DEG * (yy * sin(2 * gml * DEG) - 2 * ecc * sin(gmar) + 4 * ecc * yy * sin(gmar) * cos(2 * gml * DEG) - 0.5 * yy * yy * sin(4 * gml * DEG) - 1.25 * ecc * ecc * sin(2 * gmar));
  double minutes = tmv.tm_hour * 60.0 + tmv.tm_min + tmv.tm_sec / 60.0;
  double tsm = fmod(minutes + eot + 4.0 * lon + 1440.0, 1440.0);
  double ha = tsm / 4.0 - 180.0;
  double latr = lat * DEG, har = ha * DEG;
  double cz = sin(latr) * sin(decl) + cos(latr) * cos(decl) * cos(har);
  cz = clampf(cz, -1, 1);
  double zen = acos(cz);
  double elev = 90.0 - zen / DEG;
  // rifrazione
  if (elev < 85) {
    double te = tan(elev * DEG), r;
    if (elev > 5) r = 58.1 / te - 0.07 / (te * te * te) + 0.000086 / pow(te, 5);
    else if (elev > -0.575) r = 1735.0 + elev * (-518.2 + elev * (103.4 + elev * (-12.79 + elev * 0.711)));
    else r = -20.774 / te;
    elev += r / 3600.0;
  }
  double sz = sin(zen), az;
  if (sz < 1e-9) az = 180;
  else {
    double caz = clampf((sin(latr) * cz - sin(decl)) / (cos(latr) * sz), -1, 1);
    az = acos(caz) / DEG;
    az = (ha > 0) ? fmod(az + 180.0, 360.0) : fmod(540.0 - az, 360.0);
  }
  SunPos sp; sp.elev = elev; sp.az = az; sp.up = elev > 0; return sp;
}

// ---------------------------------------------------------------- geometria
struct Vec3 { float x, y, z; };
static Vec3 dirv(float azDeg, float tiltDeg) {
  float a = azDeg * DEG, t = tiltDeg * DEG;
  return { sinf(t) * sinf(a), sinf(t) * cosf(a), cosf(t) };
}
static Vec3 sunVec(const SunPos& s) { return dirv(s.az, 90.0f - s.elev); }

// Ombra del disco (centro C, normale n, raggio R) lungo il versore s su z=0.
// Ritorna centro G e matrice M (colonne = proiezioni di R*u1, R*u2).
static void shadowEllipse(Vec3 C, Vec3 n, float R, Vec3 s, float G[2], float M[4]) {
  // base ortonormale del disco
  Vec3 ref = fabsf(n.z) < 0.9f ? Vec3{0, 0, 1} : Vec3{1, 0, 0};
  Vec3 u1 = { n.y * ref.z - n.z * ref.y, n.z * ref.x - n.x * ref.z, n.x * ref.y - n.y * ref.x };
  float l = sqrtf(u1.x * u1.x + u1.y * u1.y + u1.z * u1.z); u1 = { u1.x / l, u1.y / l, u1.z / l };
  Vec3 u2 = { n.y * u1.z - n.z * u1.y, n.z * u1.x - n.x * u1.z, n.x * u1.y - n.y * u1.x };
  auto proj = [&](Vec3 p, float out[2]) { float k = p.z / s.z; out[0] = p.x - s.x * k; out[1] = p.y - s.y * k; };
  proj(C, G);
  float p1[2], p2[2];
  proj({C.x + R * u1.x, C.y + R * u1.y, C.z + R * u1.z}, p1);
  proj({C.x + R * u2.x, C.y + R * u2.y, C.z + R * u2.z}, p2);
  M[0] = p1[0] - G[0]; M[2] = p2[0] - G[0];
  M[1] = p1[1] - G[1]; M[3] = p2[1] - G[1];
}

// Valuta una posa: margine (1 - max rho sul bordo), copertura (frazione punti interni), quota minima.
struct Eval { float margin, coverage, zlow; bool feasible; };
static Eval evaluatePose(const Pose& p, Vec3 s) {
  Vec3 ad = dirv(p.alpha, p.theta);
  Vec3 C = { ARM_L * ad.x + CANOPY_OFFSET * sinf(p.alpha * DEG), ARM_L * ad.y + CANOPY_OFFSET * cosf(p.alpha * DEG), POLE_H + ARM_L * ad.z };
  Vec3 n = dirv(p.gamma, p.beta);
  float G[2], M[4];
  shadowEllipse(C, n, CANOPY_R, s, G, M);
  float det = M[0] * M[3] - M[2] * M[1];
  Eval e; e.zlow = C.z - CANOPY_R * sqrtf(fmaxf(0, 1 - n.z * n.z));
  e.feasible = (p.theta >= -0.01f && p.theta <= THETA_MAX + 0.01f && p.beta >= -0.01f && p.beta <= BETA_MAX + 0.01f && e.zlow >= H_MIN - 0.005f);
  if (fabsf(det) < 1e-9f) { e.margin = -10; e.coverage = 0; return e; }
  float inv[4] = { M[3] / det, -M[1] / det, -M[2] / det, M[0] / det };
  float maxRho = 0; int inside = 0; const int NB = 36, ND = 60;
  for (int i = 0; i < NB; i++) {
    float ph = 2 * 3.14159265f * i / NB;
    float qx = target.x + target.r * cosf(ph) - G[0], qy = target.y + target.r * sinf(ph) - G[1];
    float a = inv[0] * qx + inv[2] * qy, b = inv[1] * qx + inv[3] * qy;
    float rho = sqrtf(a * a + b * b); if (rho > maxRho) maxRho = rho;
  }
  for (int i = 0; i < ND; i++) {   // campionamento a girasole del disco
    float rr = target.r * sqrtf((i + 0.5f) / ND), ph = (i + 0.5f) * 2.39996f;
    float qx = target.x + rr * cosf(ph) - G[0], qy = target.y + rr * sinf(ph) - G[1];
    float a = inv[0] * qx + inv[2] * qy, b = inv[1] * qx + inv[3] * qy;
    if (a * a + b * b <= 1) inside++;
  }
  e.margin = 1 - maxRho; e.coverage = (float)inside / ND;
  return e;
}

// Soluzione analitica: C = T + lam*s con |E-P| = L.  Ritorna false se irraggiungibile.
static bool analyticPose(Vec3 s, const SunPos& sp, Pose& out) {
  float ox = 0, oy = 0, alpha = 180;
  for (int it = 0; it < (CANOPY_OFFSET > 0 ? 4 : 1); it++) {
    float dx = target.x - ox, dy = target.y - oy, dz = -POLE_H;
    float b = 2 * (dx * s.x + dy * s.y + dz * s.z), c = dx * dx + dy * dy + dz * dz - ARM_L * ARM_L;
    float disc = b * b - 4 * c; if (disc < 0) return false;
    float lam = (-b + sqrtf(disc)) / 2; if (lam <= 0) return false;
    float ex = dx + lam * s.x, ey = dy + lam * s.y, ez = dz + lam * s.z;
    alpha = wrap360(atan2f(ex, ey) / DEG);
    out.theta = acosf(clampf(ez / ARM_L, -1, 1)) / DEG;
    ox = CANOPY_OFFSET * sinf(alpha * DEG); oy = CANOPY_OFFSET * cosf(alpha * DEG);
  }
  out.alpha = alpha; out.beta = 90 - sp.elev; out.gamma = sp.az;
  return true;
}

static float score(const Eval& e) {   // da massimizzare
  float s = e.coverage + (e.margin > 0 ? 0.2f * fminf(e.margin, 0.5f) : 2.0f * e.margin);
  if (!e.feasible) s -= 5;
  return s;
}

// Posa ottima: analitica -> saturazione -> discesa a coordinate sui 4 giunti.
static Pose solvePoseVec(Vec3 s, const SunPos& sp, Eval& bestEval);
static Pose solvePose(const SunPos& sp, Eval& bestEval) { return solvePoseVec(sunVec(sp), sp, bestEval); }
static Pose solvePoseVec(Vec3 s, const SunPos& sp, Eval& bestEval) {
  Pose p;
  if (!analyticPose(s, sp, p)) { p.alpha = sp.az; p.theta = THETA_MAX; p.beta = fminf(90 - sp.elev, BETA_MAX); p.gamma = sp.az; }
  p.theta = clampf(p.theta, 0, THETA_MAX);
  p.beta  = clampf(p.beta, 0, BETA_MAX);
  // abbassa beta finche' il bordo rispetta la quota minima
  Eval e = evaluatePose(p, s);
  while (e.zlow < H_MIN && p.beta > 0.5f) { p.beta -= 1.0f; e = evaluatePose(p, s); }
  if (e.feasible && e.margin >= 0) { bestEval = e; return p; }
  // discesa a coordinate (pattern search) sul punteggio
  float step[4] = { 8, 8, 8, 8 };
  float best = score(e);
  for (int iter = 0; iter < 60; iter++) {
    bool improved = false;
    for (int j = 0; j < 4; j++) {
      for (int sgn = -1; sgn <= 1; sgn += 2) {
        Pose q = p;
        if (j == 0) q.alpha = wrap360(q.alpha + sgn * step[0]);
        if (j == 1) q.theta = clampf(q.theta + sgn * step[1], 0, THETA_MAX);
        if (j == 2) q.beta  = clampf(q.beta + sgn * step[2], 0, BETA_MAX);
        if (j == 3) q.gamma = wrap360(q.gamma + sgn * step[3]);
        Eval eq = evaluatePose(q, s);
        float sc = score(eq);
        if (sc > best + 1e-5f) { best = sc; p = q; e = eq; improved = true; }
      }
    }
    if (!improved) { for (int j = 0; j < 4; j++) step[j] *= 0.5f; if (step[0] < 0.25f) break; }
  }
  bestEval = e; return p;
}

// ---------------------------------------------------------------- servo
static void writeServos(const Pose& p) {
  // alpha: il servo copre ALPHA_SERVO_RANGE gradi centrato su ALPHA_CENTER (direzione "Sud" del modello)
  float aRel = fmodf(p.alpha - NORTH_OFFSET - ALPHA_CENTER + 540.0f, 360.0f) - 180.0f;
  float gRel = fmodf(p.gamma - NORTH_OFFSET - p.alpha + 540.0f, 360.0f) - 180.0f;  // testa relativa al braccio
  sAlpha.write(constrain(90 + aRel * (180.0f / ALPHA_SERVO_RANGE) * ALPHA_SIGN + ALPHA_TRIM, 0, 180));
  sTheta.write(constrain(THETA_SERVO_ZERO + p.theta * THETA_SIGN, 0, 180));
#if HEAD_ON_ARM
  sBeta.write(constrain(BETA_SERVO_ZERO + (p.beta - p.theta) * BETA_SIGN, 0, 180));  // zero = normale lungo il braccio
#else
  sBeta.write(constrain(BETA_SERVO_ZERO + p.beta * BETA_SIGN, 0, 180));
#endif
#if HEAD_PAN_SERVO
  sGamma.write(constrain(90 + gRel * GAMMA_SIGN + GAMMA_TRIM, 0, 180));
#else
  (void)gRel;
#endif
}

#if DEMO_RIG
// Posizione della lampada nel riferimento del modello per il sole (elev, az):
// la piattaforma ruota il modello di -(az - TABLE_AZ_CENTER), quindi nel
// riferimento del modello la lampada sta all'azimut az.  Il braccio (lunghezza
// LAMP_ARM_L) ruota attorno a un perno a distanza LAMP_PIVOT_OFF e quota
// LAMP_PIVOT_H: si cerca l'angolo phi del braccio che da' l'elevazione voluta.
static float lampPhiForElev(float elevDeg) {
  float lo = -10, hi = 95;                          // bisezione su phi (gradi)
  for (int i = 0; i < 30; i++) {
    float phi = 0.5f * (lo + hi);
    float r = LAMP_PIVOT_OFF + LAMP_ARM_L * cosf(phi * DEG), z = LAMP_PIVOT_H + LAMP_ARM_L * sinf(phi * DEG);
    float e = atan2f(z, r) / DEG;
    if (e < elevDeg) lo = phi; else hi = phi;
  }
  return 0.5f * (lo + hi);
}
static Vec3 lampPosition(const SunPos& sp, float& phiOut) {
  float phi = lampPhiForElev(sp.elev); phiOut = phi;
  float r = LAMP_PIVOT_OFF + LAMP_ARM_L * cosf(phi * DEG), z = LAMP_PIVOT_H + LAMP_ARM_L * sinf(phi * DEG);
  return { r * sinf(sp.az * DEG), r * cosf(sp.az * DEG), z };
}
static void writeRig(const SunPos& sp, float phi) {
  float aRel = fmodf(sp.az - TABLE_AZ_CENTER + 540.0f, 360.0f) - 180.0f;
  sTable.write(constrain(90 + aRel * (180.0f / TABLE_SERVO_RANGE) * TABLE_SIGN + TABLE_TRIM, 0, 180));
  sLamp.write(constrain(LAMP_SERVO_ZERO + phi * LAMP_SIGN, 0, 180));
}
// La lampada e' una sorgente puntiforme a 0.6-0.8 m, non il sole all'infinito:
// il "vettore sole" corretto va dal centro del tettuccio alla lampada.  Si
// itera 2 volte (posa -> centro tettuccio -> vettore -> posa).
static Pose solveForLamp(const SunPos& sp, Eval& e) {
  float phi; Vec3 Lp = lampPosition(sp, phi);
  Vec3 s = sunVec(sp); Pose p = solvePoseVec(s, sp, e);
  for (int it = 0; it < 2; it++) {
    Vec3 ad = dirv(p.alpha, p.theta);
    Vec3 C = { ARM_L * ad.x + CANOPY_OFFSET * sinf(p.alpha * DEG), ARM_L * ad.y + CANOPY_OFFSET * cosf(p.alpha * DEG), POLE_H + ARM_L * ad.z };
    Vec3 d = { Lp.x - C.x, Lp.y - C.y, Lp.z - C.z }; float n = sqrtf(d.x*d.x + d.y*d.y + d.z*d.z);
    s = { d.x / n, d.y / n, d.z / n };
    SunPos spEff; spEff.elev = asinf(s.z) / DEG; spEff.az = fmodf(atan2f(s.x, s.y) / DEG + 360.0f, 360.0f); spEff.up = true;
    p = solvePoseVec(s, spEff, e);
  }
  writeRig(sp, phi);
  return p;
}
#endif

static void park() { held = Pose{180, 0, 0, 180}; writeServos(held); parked = true; }

// ---------------------------------------------------------------- controllo
static void controlStep() {
  time_t now = currentEpoch();
  if (now < 1600000000) return;              // ora non ancora sincronizzata
  SunPos sp = sunPosition(now, LATITUDE, LONGITUDE);
  if (sp.elev < MIN_SUN_ELEV) { if (!parked) park(); fullCoverage = false; return; }
  Eval ei;
#if DEMO_RIG
  if (demo.on) ideal = solveForLamp(sp, ei); else ideal = solvePose(sp, ei);
#else
  ideal = solvePose(sp, ei);
#endif
  idealMargin = ei.margin; idealCoverage = ei.coverage; fullCoverage = ei.feasible && ei.margin >= 0;
  Eval eh = evaluatePose(held, sunVec(sp));
  heldMargin = eh.margin; heldCoverage = eh.coverage;
  bool need = parked || eh.margin < MARGIN_MOVE || !eh.feasible;
  bool urgent = eh.coverage < 0.97f;
  bool better = ei.coverage > eh.coverage + 0.02f || ei.margin > eh.margin + 0.02f;
  bool waited = millis() - lastMoveMs > MIN_HOLD_MS;
  if (demo.on) waited = (millis() - lastMoveMs) > (unsigned long)(MIN_HOLD_MS / demo.speed);  // isteresi scalata col tempo accelerato
  if (need && (better || parked) && (waited || urgent)) {
    held = ideal; writeServos(held); lastMoveMs = millis(); parked = false;
  }
}

// Prossimo orario (oggi) in cui la copertura totale smette di essere possibile.
static String coverageWindowToday() {
  time_t now = currentEpoch(); struct tm lt; localtime_r(&now, &lt);
  lt.tm_hour = 0; lt.tm_min = 0; lt.tm_sec = 0; time_t t0 = mktime(&lt);
  int first = -1, last = -1;
  Target saved = target;
  for (int m = 0; m < 1440; m += 10) {
    SunPos sp = sunPosition(t0 + m * 60, LATITUDE, LONGITUDE);
    if (sp.elev < MIN_SUN_ELEV) continue;
    Eval e; solvePose(sp, e);
    if (e.feasible && e.margin >= 0) { if (first < 0) first = m; last = m; }
  }
  target = saved;
  if (first < 0) return "mai (zona troppo grande o lontana)";
  char buf[48]; snprintf(buf, sizeof buf, "%02d:%02d - %02d:%02d", first / 60, first % 60, last / 60, last % 60);
  return String(buf);
}

// ---------------------------------------------------------------- web API
static void handleRoot() { server.send_P(200, "text/html", WEBPAGE); }

static void handleStatus() {
  time_t now = currentEpoch(); SunPos sp = sunPosition(now, LATITUDE, LONGITUDE);
  String j = "{";
  j += "\"sun\":{\"elev\":" + String(sp.elev, 1) + ",\"az\":" + String(sp.az, 1) + "},";
  j += "\"target\":{\"x\":" + String(target.x, 3) + ",\"y\":" + String(target.y, 3) + ",\"r\":" + String(target.r, 3) + "},";
  j += "\"held\":{\"alpha\":" + String(held.alpha, 1) + ",\"theta\":" + String(held.theta, 1) + ",\"beta\":" + String(held.beta, 1) + ",\"gamma\":" + String(held.gamma, 1) + "},";
  j += "\"margin\":" + String(heldMargin, 3) + ",\"coverage\":" + String(heldCoverage, 3) + ",";
  j += "\"idealCoverage\":" + String(idealCoverage, 3) + ",\"full\":" + String(fullCoverage ? "true" : "false") + ",";
  j += "\"parked\":" + String(parked ? "true" : "false") + ",\"demo\":" + String(demo.on ? "true" : "false") + ",\"speed\":" + String(demo.speed, 0) + ",";
  j += "\"geom\":{\"H\":" + String(POLE_H, 3) + ",\"L\":" + String(ARM_L, 3) + ",\"R\":" + String(CANOPY_R, 3) + ",\"thetaMax\":" + String(THETA_MAX, 0) + "},";
  j += "\"time\":" + String((long)now) + "}";
  server.send(200, "application/json", j);
}

static void handleSet() {
  if (server.hasArg("x")) target.x = server.arg("x").toFloat();
  if (server.hasArg("y")) target.y = server.arg("y").toFloat();
  if (server.hasArg("r")) target.r = clampf(server.arg("r").toFloat(), 0.02f, 5.0f);
  prefs.putFloat("tx", target.x); prefs.putFloat("ty", target.y); prefs.putFloat("tr", target.r);
  lastMoveMs = 0; parked = true;   // forza il riposizionamento
  controlStep();
  server.send(200, "application/json", "{\"ok\":true,\"window\":\"" + coverageWindowToday() + "\"}");
}

// /demo?on=1&speed=240&date=2026-07-15&hour=6  -> giornata accelerata dalle 6 del giorno indicato
// /demo?on=0 -> torna all'ora reale
static void handleDemo() {
  if (server.hasArg("on") && server.arg("on").toInt() == 0) { demo.on = false; parked = true; lastMoveMs = 0; server.send(200, "application/json", "{\"demo\":false}"); return; }
  demo.speed = server.hasArg("speed") ? server.arg("speed").toFloat() : DEMO_SPEED_DEFAULT;
  struct tm lt; time_t base = time(nullptr); localtime_r(&base, &lt);
  if (server.hasArg("date")) { String d = server.arg("date"); lt.tm_year = d.substring(0, 4).toInt() - 1900; lt.tm_mon = d.substring(5, 7).toInt() - 1; lt.tm_mday = d.substring(8, 10).toInt(); }
  lt.tm_hour = server.hasArg("hour") ? server.arg("hour").toInt() : 6; lt.tm_min = 0; lt.tm_sec = 0;
  demo.t0 = mktime(&lt); demo.ms0 = millis(); demo.on = true; parked = true; lastMoveMs = 0;
  controlStep();
  server.send(200, "application/json", "{\"demo\":true,\"speed\":" + String(demo.speed, 0) + "}");
}

static void handleWindow() { server.send(200, "application/json", "{\"window\":\"" + coverageWindowToday() + "\"}"); }

static void handlePark() { park(); server.send(200, "application/json", "{\"ok\":true}"); }

// Calibrazione del Nord: l'utente ruota il braccio con "a=<gradi servo>" finche' l'ombra del
// braccio e' allineata al sole, poi chiama /calib: l'offset viene calcolato dall'azimut solare.
static void handleCalib() {
  if (server.hasArg("servo")) { sAlpha.write(server.arg("servo").toInt()); server.send(200, "text/plain", "ok"); return; }
  time_t now = time(nullptr); SunPos sp = sunPosition(now, LATITUDE, LONGITUDE);
  float servoDeg = sAlpha.read();
  float aRel = (servoDeg - 90 - ALPHA_TRIM) / ((180.0f / ALPHA_SERVO_RANGE) * ALPHA_SIGN);
  NORTH_OFFSET = wrap360(sp.az - ALPHA_CENTER - aRel);
  prefs.putFloat("north", NORTH_OFFSET);
  server.send(200, "application/json", "{\"north_offset\":" + String(NORTH_OFFSET, 1) + "}");
}

// ---------------------------------------------------------------- setup/loop
void setup() {
  Serial.begin(115200);
  prefs.begin("ombrellone", false);
  target.x = prefs.getFloat("tx", 0); target.y = prefs.getFloat("ty", 0); target.r = prefs.getFloat("tr", TARGET_R_DEFAULT);
  NORTH_OFFSET = prefs.getFloat("north", NORTH_OFFSET);

  ESP32PWM::allocateTimer(0); ESP32PWM::allocateTimer(1); ESP32PWM::allocateTimer(2); ESP32PWM::allocateTimer(3);
  sAlpha.setPeriodHertz(50); sTheta.setPeriodHertz(50); sBeta.setPeriodHertz(50); sGamma.setPeriodHertz(50);
  sAlpha.attach(PIN_SERVO_ALPHA, 500, 2500); sTheta.attach(PIN_SERVO_THETA, 500, 2500);
  sBeta.attach(PIN_SERVO_BETA, 500, 2500);
#if HEAD_PAN_SERVO
  sGamma.attach(PIN_SERVO_GAMMA, 500, 2500);
#endif
#if DEMO_RIG
  sTable.setPeriodHertz(50); sLamp.setPeriodHertz(50);
  sTable.attach(PIN_SERVO_TABLE, 500, 2500); sLamp.attach(PIN_SERVO_LAMP, 500, 2500);
#endif
  park();

  WiFi.mode(WIFI_STA); WiFi.begin(WIFI_SSID, WIFI_PASS);
  Serial.print("WiFi");
  for (int i = 0; i < 40 && WiFi.status() != WL_CONNECTED; i++) { delay(500); Serial.print("."); }
  if (WiFi.status() != WL_CONNECTED) {            // fallback: access point proprio
    WiFi.mode(WIFI_AP); WiFi.softAP("ombrellone", "ombrellone");
    Serial.println("\nAP: 192.168.4.1 (senza NTP: imposta l'ora da /time?epoch=...)");
  } else {
    Serial.println(String("\nIP: ") + WiFi.localIP().toString());
    configTzTime(TIMEZONE, "pool.ntp.org", "time.google.com");
    MDNS.begin("ombrellone");
  }
  server.on("/", handleRoot);
  server.on("/status", handleStatus);
  server.on("/set", handleSet);
  server.on("/window", handleWindow);
  server.on("/park", handlePark);
  server.on("/calib", handleCalib);
  server.on("/demo", handleDemo);
  server.on("/time", []() {           // impostazione manuale dell'ora (modalita' AP)
    if (server.hasArg("epoch")) { struct timeval tv = { (time_t)server.arg("epoch").toInt(), 0 }; settimeofday(&tv, nullptr); }
    server.send(200, "text/plain", String((long)time(nullptr)));
  });
  server.begin();
}

void loop() {
  server.handleClient();
  static unsigned long lastCtrl = 0;
  if (millis() - lastCtrl > CONTROL_PERIOD_MS) { lastCtrl = millis(); controlStep(); }
}
