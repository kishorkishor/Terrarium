/* ============================================================================
 * TERRARIUM LAB FIRMWARE  (paper experiments, bench build of 2026-09-25)
 *
 * Hardware it expects, and nothing else:
 *   BME280 "IN"   0x76  inside the box, the control sensor   (SDO -> GND or open)
 *   BME280 "OUT"  0x77  outside the box, room reference      (SDO -> 3V3)
 *   both on SDA = GPIO21, SCL = GPIO22, VCC = 3V3
 *   Mist A (main)   GPIO25 -> MOSFET board A GND1 terminal (OUT1)   active-low
 *   Mist B (backup) GPIO16 -> MOSFET board A GND2 terminal (OUT2)   active-low
 *   Float switch (optional) GPIO27 to GND. Not fitted = reads "tank OK".
 *
 * Every PERIOD it prints one data line, humidity to 0.01 %:
 *   D,ms,t_in,rh_in,p_in,t_out,rh_out,p_out,mistA,mistB,mode,in_ok,out_ok,tank_ok
 * Events print as  E,ms,text   (commands, faults, MARK lines).
 *
 * Commands over USB serial (115200, one per line, "CMD " prefix optional):
 *   STATUS | HEADER | RESCAN | DIAG (wire check: pull-ups on D21/D22 + bus scan)
 *   MODE OFF | MANUAL | RULES
 *   MIST A 1 | MIST A 0 | MIST B 1 | MIST B 0     (MANUAL mode only)
 *   SET lo=75 hi=90 max=300 cool=180 man=600 use=A|B|AB period=1
 *   MARK any text   -> logged as an event (fault start/stop, lid open, etc.)
 * Mode and settings are saved to flash, so a power blip resumes the experiment.
 *
 * A 15 s hardware watchdog reboots the chip if it ever freezes (bus lock-up);
 * settings and mode come back from flash, mist starts off.
 * If the inside sensor (0x76) is dead for 60 s and 0x77 is healthy, 0x77 becomes the
 * control sensor (event "CONTROL SENSOR FALLBACK"; rh_in then carries 0x77).
 * Safety, always on: mist off if the inside sensor is lost (RULES), if the
 * tank is empty, or when a burst hits its cap. Lost sensors are re-probed
 * every 5 s, so a sensor that drops off comes back without a reboot when it can.
 * ========================================================================== */
#include <Wire.h>
#include <Adafruit_BME280.h>
#include <Preferences.h>
#include <esp_task_wdt.h>

#define PIN_SDA        21
#define PIN_SCL        22
int sclPin = PIN_SCL;
#define PIN_MIST_A     25
#define PIN_MIST_B     16
#define PIN_FLOAT      27
#define ENABLE_FLOAT   1
#define ACTIVE_LOW     1          // opto MOSFET board: pin LOW = channel ON
#define ADDR_IN        0x76
#define ADDR_OUT       0x77
/* Optional: power each sensor from a GPIO so the firmware can power-cycle a
 * sensor latched by condensation. -1 = sensor VCC wired to 3V3 (default).   */
#define PIN_PWR_IN     -1
#define PIN_PWR_OUT    -1

Adafruit_BME280 bmeIn, bmeOut;
Preferences prefs;

enum Mode { M_OFF = 0, M_MANUAL = 1, M_RULES = 2 };
const char* MODE_NAME[] = {"OFF", "MANUAL", "RULES"};

struct Cfg {
  int mode = M_OFF;
  float lo = 75, hi = 90;         // RULES band, %RH
  int maxS = 300;                 // one burst never longer than this, s
  int coolS = 180;                // rest after a burst, s
  int manS = 600;                 // manual mist auto-off, s
  int use = 1;                    // 1 = A, 2 = B, 3 = both
  int periodS = 1;                // data line every N s
} cfg;

struct Reading { float t = NAN, rh = NAN, p = NAN; bool ok = false; int bad = 0; };
Reading rin, rout;
bool inFitted = false, outFitted = false;

bool mistA = false, mistB = false;
unsigned long mistOnAt = 0, mistOffAt = 0, manOnAtA = 0, manOnAtB = 0;
unsigned long lastSample = 0, lastProbe = 0;
bool tankOk = true;

/* ------------------------------------------------------------------ utils */
void event(const String& s) { Serial.printf("E,%lu,%s\n", millis(), s.c_str()); }

void drive(int pin, bool on) { digitalWrite(pin, (on ^ ACTIVE_LOW) ? HIGH : LOW); }

void setMist(bool a, bool b, const char* why) {
  if (a != mistA || b != mistB) {
    bool wasOn = mistA || mistB, nowOn = a || b;
    if (!wasOn && nowOn) mistOnAt = millis();
    if (wasOn && !nowOn) mistOffAt = millis();
    if (a && !mistA) manOnAtA = millis();
    if (b && !mistB) manOnAtB = millis();
    mistA = a; mistB = b;
    drive(PIN_MIST_A, a); drive(PIN_MIST_B, b);
    event(String("mist A=") + a + " B=" + b + " (" + why + ")");
  }
}

void saveCfg() {
  prefs.putInt("mode", cfg.mode); prefs.putFloat("lo", cfg.lo); prefs.putFloat("hi", cfg.hi);
  prefs.putInt("max", cfg.maxS); prefs.putInt("cool", cfg.coolS); prefs.putInt("man", cfg.manS);
  prefs.putInt("use", cfg.use); prefs.putInt("per", cfg.periodS);
}
void loadCfg() {
  cfg.mode = prefs.getInt("mode", M_OFF); cfg.lo = prefs.getFloat("lo", 75); cfg.hi = prefs.getFloat("hi", 90);
  cfg.maxS = prefs.getInt("max", 300); cfg.coolS = prefs.getInt("cool", 180); cfg.manS = prefs.getInt("man", 600);
  cfg.use = prefs.getInt("use", 1); cfg.periodS = prefs.getInt("per", 1);
  if (cfg.mode == M_MANUAL) cfg.mode = M_OFF;   // never resume a manual mist after a reset
}

void header() {
  Serial.println("H,ms,t_in,rh_in,p_in,t_out,rh_out,p_out,mistA,mistB,mode,in_ok,out_ok,tank_ok");
}

void status() {
  Serial.printf("S,mode=%s,lo=%.1f,hi=%.1f,max=%d,cool=%d,man=%d,use=%s,period=%d,in=%s,out=%s,tank=%s,mistA=%d,mistB=%d\n",
    MODE_NAME[cfg.mode], cfg.lo, cfg.hi, cfg.maxS, cfg.coolS, cfg.manS,
    cfg.use == 1 ? "A" : cfg.use == 2 ? "B" : "AB", cfg.periodS,
    inFitted ? (rin.ok ? "ok" : "bad") : "missing", outFitted ? (rout.ok ? "ok" : "bad") : "missing",
    tankOk ? "ok" : "EMPTY", mistA, mistB);
}

/* ---------------------------------------------------------------- sensors */
void powerCycle(int pin) {
  if (pin < 0) return;
  digitalWrite(pin, LOW); delay(500); digitalWrite(pin, HIGH); delay(50);
}

bool initSensor(Adafruit_BME280& b, uint8_t addr) {
  if (!b.begin(addr, &Wire)) return false;
  // forced mode, x1 oversampling, no filter: least self-heating at 1 Hz
  b.setSampling(Adafruit_BME280::MODE_FORCED,
                Adafruit_BME280::SAMPLING_X1, Adafruit_BME280::SAMPLING_X1, Adafruit_BME280::SAMPLING_X1,
                Adafruit_BME280::FILTER_OFF);
  return true;
}

/* No manual bus "unjam" here: tearing the I2C driver down and up (Wire.end/begin)
 * while the sensor objects still reference it crashed the chip (StoreProhibited,
 * seen 2026-09-26 23:40). The ESP32 driver clears a stuck bus itself on timeout,
 * and the 15 s watchdog covers anything worse.                                 */
void probe() {
  /* (auto-detect of SCL on D23 removed: it needed Wire.end()/begin(), which can crash the
     driver when the bus is hung. SCL is D22.) */
  if (!inFitted || !rin.ok) {
    if (inFitted && rin.bad >= 3) powerCycle(PIN_PWR_IN);
    bool ok = initSensor(bmeIn, ADDR_IN);
    if (ok && !inFitted) event("sensor IN found at 0x76");
    if (ok) { inFitted = true; rin.bad = 0; }
  }
  if (!outFitted || !rout.ok) {
    if (outFitted && rout.bad >= 3) powerCycle(PIN_PWR_OUT);
    bool ok = initSensor(bmeOut, ADDR_OUT);
    if (ok && !outFitted) event("sensor OUT found at 0x77");
    if (ok) { outFitted = true; rout.bad = 0; }
  }
}

bool swapped = false;             // true when the 0x77 sensor is being used as the control sensor
int inDeadS = 0;
void readSensor(Adafruit_BME280& b, Reading& r, bool fitted, const char* name) {
  if (!fitted) { r.ok = false; r.t = r.rh = r.p = NAN; return; }
  bool got = b.takeForcedMeasurement();
  float t = b.readTemperature(), h = b.readHumidity(), p = b.readPressure() / 100.0f;
  // a wet or latched BME280 returns nonsense (e.g. 179.4 C / 100 %) -> reject
  bool sane = got && !isnan(t) && !isnan(h) && t > 10 && t < 45 && h > 5 && h < 99.99 && p > 950 && p < 1060
              && (isnan(r.t) || fabs(t - r.t) < 2.0);   // a real sensor never jumps 2 C between 1 s samples
  if (sane) {
    if (!r.ok) event(String("sensor ") + name + " reading OK");
    r.t = t; r.rh = h; r.p = p; r.ok = true; r.bad = 0;
  } else {
    r.bad++;
    if (r.bad == 3 || r.bad % 30 == 0) event(String("sensor ") + name + " rejected reading: forced=" + got + " t=" + t + " rh=" + h + " p=" + p);
    if (r.bad >= 3) {
      if (r.ok) event(String("sensor ") + name + " LOST (bad readings)");
      r.ok = false; r.t = r.rh = r.p = NAN;
    }
  }
}

/* ---------------------------------------------------------------- control */
void control() {
  unsigned long now = millis();
  bool on = mistA || mistB;

  if (!tankOk && on) { setMist(false, false, "tank empty"); return; }

  if (cfg.mode == M_OFF) { if (on) setMist(false, false, "mode OFF"); return; }

  if (cfg.mode == M_MANUAL) {
    if (mistA && now - manOnAtA > (unsigned long)cfg.manS * 1000UL) setMist(false, mistB, "manual cap");
    if (mistB && now - manOnAtB > (unsigned long)cfg.manS * 1000UL) setMist(mistA, false, "manual cap");
    return;
  }

  // RULES: on/off hysteresis on the inside sensor, burst cap + cooldown
  if (!rin.ok) { if (on) setMist(false, false, "inside sensor lost"); return; }
  if (on) {
    if (rin.rh >= cfg.hi) setMist(false, false, "reached hi");
    else if (now - mistOnAt > (unsigned long)cfg.maxS * 1000UL) setMist(false, false, "burst cap");
  } else {
    bool rested = mistOffAt == 0 || now - mistOffAt > (unsigned long)cfg.coolS * 1000UL;
    if (rin.rh < cfg.lo && rested && tankOk) setMist(cfg.use & 1, cfg.use & 2, "below lo");
  }
}

/* DIAG: is a sensor's pull-up resistor reaching each I2C pin?  (wire check) */
bool pulledUp(int pin) {
  pinMode(pin, INPUT_PULLDOWN); delay(3);
  int h = 0; for (int k = 0; k < 20; k++) { h += digitalRead(pin); delayMicroseconds(200); }
  pinMode(pin, INPUT);
  return h >= 18;
}
void diag() {
  bool sda = pulledUp(PIN_SDA), scl = pulledUp(sclPin);
  // with the chip's own weak pull-up on: a free wire reads HIGH; LOW means something pulls the line to GND
  int sclUp = 20, sdaUp = 20;   // line tests disabled while the driver owns the pins (use firmware/i2c-health for that)
  Serial.printf("S,diag2,SDA with own pull-up high %d/20, SCL with own pull-up high %d/20 (%s)\n", sdaUp, sclUp,
                sclUp < 3 ? "SCL is being PULLED TO GND: short, wet sensor or unpowered chip" : sclUp > 17 ? "SCL free: wire not connected" : "SCL unstable");
  String found = "";
  for (uint8_t a = 1; a < 127; a++) { Wire.beginTransmission(a); if (Wire.endTransmission() == 0) found += String(" 0x") + String(a, HEX); }
  Serial.printf("S,diag,SDA(D21)=%s,SCL(D22)=%s,found:%s\n", sda ? "connected" : "NOT-CONNECTED", sclPin,
                scl ? "connected" : "NOT-CONNECTED", found.length() ? found.c_str() : " none");
}

/* --------------------------------------------------------------- commands */
void handle(String line) {
  line.trim();
  if (line.startsWith("CMD ")) line = line.substring(4);
  if (!line.length()) return;
  String up = line; up.toUpperCase();

  if (up == "STATUS") { status(); return; }
  if (up == "DIAG") { diag(); return; }
  if (up == "HEADER") { header(); return; }
  if (up == "RESCAN") { inFitted = outFitted = false; probe(); status(); return; }
  if (up.startsWith("MARK")) { event("MARK " + line.substring(4)); return; }

  if (up.startsWith("MODE ")) {
    String m = up.substring(5); m.trim();
    int nm = m == "OFF" ? M_OFF : m == "MANUAL" ? M_MANUAL : m == "RULES" ? M_RULES : -1;
    if (nm < 0) { event("ERR unknown mode " + m); return; }
    cfg.mode = nm; saveCfg();
    setMist(false, false, "mode change");
    event(String("mode ") + MODE_NAME[nm]); return;
  }

  if (up.startsWith("MIST ")) {
    char which = up.charAt(5); bool v = up.endsWith("1");
    if (v && cfg.mode != M_MANUAL) { event("ERR MIST on needs MODE MANUAL"); return; }   // off is always allowed
    if (v && !tankOk) { event("ERR tank empty"); return; }
    if (which == 'A') setMist(v, mistB, "manual");
    else if (which == 'B') setMist(mistA, v, "manual");
    else event("ERR MIST A|B 0|1");
    return;
  }

  if (up.startsWith("SET ")) {
    String rest = line.substring(4) + " ";
    int i = 0;
    while (i < (int)rest.length()) {
      int sp = rest.indexOf(' ', i); String kv = rest.substring(i, sp); i = sp + 1;
      int eq = kv.indexOf('='); if (eq < 0) continue;
      String k = kv.substring(0, eq), v = kv.substring(eq + 1); k.toLowerCase();
      if (k == "lo") cfg.lo = constrain(v.toFloat(), 30, 98);
      else if (k == "hi") cfg.hi = constrain(v.toFloat(), 35, 99);
      else if (k == "max") cfg.maxS = constrain(v.toInt(), 10, 900);
      else if (k == "cool") cfg.coolS = constrain(v.toInt(), 0, 3600);
      else if (k == "man") cfg.manS = constrain(v.toInt(), 10, 1800);
      else if (k == "period") cfg.periodS = constrain(v.toInt(), 1, 60);
      else if (k == "use") { v.toUpperCase(); cfg.use = v == "B" ? 2 : v == "AB" ? 3 : 1; }
      else event("ERR unknown setting " + k);
    }
    if (cfg.hi <= cfg.lo) cfg.hi = cfg.lo + 1;
    saveCfg(); status(); return;
  }
  event("ERR unknown command: " + line);
}

/* ------------------------------------------------------------------ main */
void setup() {
  pinMode(PIN_MIST_A, OUTPUT); drive(PIN_MIST_A, false);
  pinMode(PIN_MIST_B, OUTPUT); drive(PIN_MIST_B, false);
  if (PIN_PWR_IN >= 0)  { pinMode(PIN_PWR_IN, OUTPUT);  digitalWrite(PIN_PWR_IN, HIGH); }
  if (PIN_PWR_OUT >= 0) { pinMode(PIN_PWR_OUT, OUTPUT); digitalWrite(PIN_PWR_OUT, HIGH); }
  if (ENABLE_FLOAT) pinMode(PIN_FLOAT, INPUT_PULLUP);
  Serial.begin(115200);
  delay(300);
  Wire.begin(PIN_SDA, sclPin);
  Wire.setClock(50000);
  Wire.setTimeOut(20);
  prefs.begin("lab", false);
#if ESP_ARDUINO_VERSION_MAJOR >= 3
  esp_task_wdt_config_t wdt = { .timeout_ms = 15000, .idle_core_mask = 0, .trigger_panic = true };
  esp_task_wdt_reconfigure(&wdt);
#else
  esp_task_wdt_init(15, true);
#endif
  esp_task_wdt_add(NULL);
  loadCfg();
  Serial.println("\n== TERRARIUM LAB FIRMWARE ==");
  probe();
  if (!inFitted)  event("sensor IN (0x76) NOT FOUND - check wiring; retrying every 5 s");
  if (!outFitted) event("sensor OUT (0x77) NOT FOUND - check wiring; retrying every 5 s");
  status();
  header();
}

void loop() {
  static String buf;
  esp_task_wdt_reset();
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') { if (buf.length()) handle(buf); buf = ""; }
    else if (buf.length() < 200) buf += c;
  }

  unsigned long now = millis();
  if (now - lastProbe > 5000) {
    lastProbe = now;
    if (!inFitted || !rin.ok || !outFitted || !rout.ok) probe();
  }

  if (now - lastSample >= (unsigned long)cfg.periodS * 1000UL) {
    lastSample = now;
    tankOk = !ENABLE_FLOAT || digitalRead(PIN_FLOAT) == HIGH;
    if (swapped) { Reading tmp = rin; rin = rout; rout = tmp; }   // undo last cycle's swap so each object gets its own reading
    readSensor(bmeIn, rin, inFitted, "IN");
    readSensor(bmeOut, rout, outFitted, "OUT");
    // fallback: control sensor dead for 60 s while the second sensor is healthy -> use the second one
    if (!swapped) {
      inDeadS = rin.ok ? 0 : inDeadS + cfg.periodS;
      if (inDeadS >= 60 && rout.ok) { swapped = true; event("CONTROL SENSOR FALLBACK: 0x76 dead for 60 s, using 0x77 as the control sensor from now on"); }
    }
    if (swapped) { Reading tmp = rin; rin = rout; rout = tmp; }   // data line: columns t_in/rh_in now carry the 0x77 sensor
    control();
    Serial.printf("D,%lu,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%d,%d,%s,%d,%d,%d\n", now,
      rin.t, rin.rh, rin.p, rout.t, rout.rh, rout.p, mistA, mistB, MODE_NAME[cfg.mode], rin.ok, rout.ok, tankOk);
  } else {
    control();
  }
}
