#pragma once
// ============================================================================
// Configurazione del mini-prototipo (scala ~1:10).  Lunghezze in METRI.
// Cambia questi valori per il modello reale: la logica e' identica.
// ============================================================================

// --- rete e ora ------------------------------------------------------------
#define WIFI_SSID   "IL_TUO_WIFI"
#define WIFI_PASS   "LA_TUA_PASSWORD"
#define TIMEZONE    "CET-1CEST,M3.5.0,M10.5.0/3"   // Italia (ora legale automatica)

// --- posizione (GPS opzionale: con TinyGPSPlus sovrascrivi queste a runtime) --
static float LATITUDE  = 44.06f;    // Rimini
static float LONGITUDE = 12.57f;

// --- geometria del modello ---------------------------------------------------
static const float POLE_H        = 0.20f;   // altezza palo fisso
static const float ARM_L         = 0.16f;   // lunghezza braccio
static const float CANOPY_R      = 0.15f;   // raggio tettuccio
static const float CANOPY_OFFSET = 0.05f;   // sbalzo del tettuccio lungo il braccio
static const float THETA_MAX     = 70.0f;   // inclinazione massima braccio (gradi)
static const float BETA_MAX      = 70.0f;   // inclinazione massima tettuccio (gradi)
static const float H_MIN         = 0.12f;   // quota minima bordo tettuccio
static const float TARGET_R_DEFAULT = 0.10f;

// --- controllo ----------------------------------------------------------------
static const float MIN_SUN_ELEV   = 5.0f;    // sotto: parcheggio
static const float MARGIN_MOVE    = 0.05f;   // si muove quando il margine < 5% del raggio zona
static const unsigned long MIN_HOLD_MS    = 10UL * 60UL * 1000UL;  // silenzio minimo fra movimenti
static const unsigned long CONTROL_PERIOD_MS = 15000UL;            // periodo del controllo

// --- servo (pin ESP32 e calibrazioni meccaniche) -----------------------------
#define PIN_SERVO_ALPHA 13
#define PIN_SERVO_THETA 12
#define PIN_SERVO_BETA  14
#define PIN_SERVO_GAMMA 27
static float NORTH_OFFSET = 0.0f;           // gradi: azimut reale verso cui punta lo "zero" del modello (da /calib)
static const float ALPHA_CENTER = 180.0f;   // azimut (del modello) con servo alpha a 90 gradi
static const float ALPHA_SERVO_RANGE = 270.0f; // escursione meccanica del servo alpha (270 per servo "270 gradi")
static const float ALPHA_SIGN = 1.0f, ALPHA_TRIM = 0.0f;
static const float THETA_SERVO_ZERO = 10.0f, THETA_SIGN = 1.0f;   // servo a 10 gradi = braccio verticale
static const float BETA_SERVO_ZERO  = 90.0f, BETA_SIGN  = 1.0f;   // servo a 90 gradi = tettuccio orizzontale
static const float GAMMA_SIGN = 1.0f, GAMMA_TRIM = 0.0f;
#define HEAD_ON_ARM 1        // 1: servo beta montato in punta al braccio (zero = tettuccio perpendicolare al braccio)
#define HEAD_PAN_SERVO 0     // 1: quarto servo (gamma) presente; 0: gamma = alpha meccanicamente (3 servo)

// --- banco demo "sole artificiale" (vedi docs/PROTOTIPO_1_10.md) -------------
#define DEMO_RIG 1           // 1: piattaforma girevole + braccio lampada collegati all'ESP32
#define PIN_SERVO_TABLE 26   // servo MG996R 270 gradi sotto la piattaforma
#define PIN_SERVO_LAMP  25   // servo MG996R di elevazione del braccio lampada
static const float TABLE_AZ_CENTER = 180.0f;   // azimut (del modello) verso la lampada con servo a 90 gradi
static const float TABLE_SERVO_RANGE = 270.0f, TABLE_SIGN = 1.0f, TABLE_TRIM = 0.0f;
static const float LAMP_ARM_L = 0.60f;         // lunghezza braccio lampada [m]
static const float LAMP_PIVOT_OFF = 0.17f;     // distanza orizzontale perno-centro piattaforma [m]
static const float LAMP_PIVOT_H = 0.06f;       // quota del perno sopra la piattaforma [m]
static const float LAMP_SERVO_ZERO = 0.0f, LAMP_SIGN = 1.0f;  // servo a 0 gradi = braccio orizzontale
static const float DEMO_SPEED_DEFAULT = 240.0f;               // 240x: una giornata di sole in ~3.5 minuti
