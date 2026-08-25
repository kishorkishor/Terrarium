/* ============================================================================
 * TERRARIUM CONTROL FIRMWARE  ·  EEE4103 capstone
 * Board: ESP32 DevKit V1 (WROOM-32) — select "DOIT ESP32 DEVKIT V1" in the IDE
 *
 * What it does
 *   - Samples BME280 (temp/RH), BH1750 (lux), 2x capacitive soil, float switch
 *   - Waters via a mist module in timed bursts with a soak delay + daily cap
 *   - Raises humidity via a second mist module with hysteresis + cooldown
 *   - Runs the grow light on a photoperiod window gated by measured lux
 *   - Serves a phone dashboard (webui.h) with live values, manual mode,
 *     and editable thresholds persisted to flash (Preferences)
 *   - Safety: empty reservoir forces BOTH mist channels off, even in manual.
 *     All automation is local — Wi-Fi loss changes nothing.
 *
 * Libraries (Library Manager): "Adafruit BME280 Library" (accept the
 * dependency prompts) and "BH1750" by Christopher Laws. Nothing else.
 *
 * Wiring verification first! Run wokwi/sketch.ino on the bench (guide §11)
 * before trusting this firmware with water.
 * ========================================================================== */

#include <WiFi.h>
#include <WebServer.h>
#include <ESPmDNS.h>
#include <Preferences.h>
#include <Wire.h>
#include <time.h>
#include "config.h"
#include "webui.h"

#if ENABLE_BME280
  #include <Adafruit_BME280.h>
  Adafruit_BME280 bme;
#endif
#if ENABLE_BH1750
  #include <BH1750.h>
  BH1750 luxMeter(0x23);
#endif

WebServer server(80);
Preferences prefs;

/* ---- runtime settings (loaded from flash, edited from the app) ---------- */
struct Cfg {
  int soilDry, humLo, humHi, luxOn, luxOff, lightStart, lightEnd, bright;
} cfg;

/* ---- live state ---------------------------------------------------------- */
struct {
  float temp = NAN, hum = NAN, lux = NAN;
  int   soil1 = 0, soil2 = 0, soilAvg = 0;
  int   raw1  = 0, raw2  = 0;   // raw ADC, for calibration + report
  int   leakRaw = 0;
  bool  leakWet = false;
  bool  tankOk = true;
  bool  bmeOk = false, bhOk = false, timeOk = false;
} st;

struct {
  bool water = false, hum = false, light = false, fanExh = false;
  bool buzzer = false;          // manual buzzer test from the app
} out;

bool manualMode = false;

/* watering state machine */
enum WaterPhase { W_IDLE, W_RUN, W_SOAK };
WaterPhase wPhase = W_IDLE;
unsigned long wPhaseStart = 0;
unsigned long waterSecToday = 0;
int lastDay = -1;

/* humidity mist timers */
unsigned long humStart = 0, humCooldownUntil = 0;
int           humBadReads = 0;        // consecutive failed RH reads
/* manual auto-off timers */
unsigned long manWaterStart = 0, manHumStart = 0;
unsigned long lastSample = 0;

/* ========================================================================= */
/*  helpers                                                                  */
/* ========================================================================= */
static unsigned long secsSince(unsigned long t0) { return (millis() - t0) / 1000UL; }

/* Drive one MOSFET-board channel, honouring MOSFET_ACTIVE_LOW. */
static inline void writeOut(int pin, bool on) {
#if MOSFET_ACTIVE_LOW
  digitalWrite(pin, on ? LOW : HIGH);
#else
  digitalWrite(pin, on ? HIGH : LOW);
#endif
}

/* PWM channel (grow light). Active-low boards need the duty inverted. */
static inline void writePwmOut(int pin, int duty) {
#if MOSFET_ACTIVE_LOW
  analogWrite(pin, 255 - duty);
#else
  analogWrite(pin, duty);
#endif
}

void applyOutputs() {
  /* SAFETY INTERLOCK — empty tank kills both mist channels, no exceptions. */
  bool water = out.water && st.tankOk;
  bool humid = out.hum   && st.tankOk;
  writeOut(PIN_MIST_WATER, water);
  writeOut(PIN_MIST_HUM,   humid);
  writePwmOut(PIN_LIGHT, out.light ? cfg.bright : 0);
#if ENABLE_FAN_EXH
  writeOut(PIN_FAN_EXH, out.fanExh);
#endif
#if ENABLE_BUZZER
  /* Manual button always works; real alarms only when armed. */
  bool alarm = out.buzzer;
#if BUZZER_AUTO_ALARM
  alarm = alarm || (!st.tankOk) || st.leakWet;
#endif
  /* Only act on a CHANGE — restarting the tone every tick would stutter it. */
  static int lastAlarm = -1;
  if ((int)alarm != lastAlarm) {
    lastAlarm = alarm;
#if BUZZER_PASSIVE
    if (alarm) tone(PIN_BUZZER, BUZZER_TONE_HZ);
    else       noTone(PIN_BUZZER);
#else
    digitalWrite(PIN_BUZZER, alarm ? HIGH : LOW);
#endif
  }
#endif
}

void allOff() {
  out = {};
  applyOutputs();
}

int soilPercent(int raw, int dryAdc, int wetAdc) {
  long pct = 100L * (dryAdc - raw) / (dryAdc - wetAdc);
  return constrain((int)pct, 0, 100);
}

int readSoil(int pin) {          // average 8 reads to calm ADC noise
  long acc = 0;
  for (int i = 0; i < 8; i++) acc += analogRead(pin);
  return acc / 8;
}

/* ========================================================================= */
/*  sensors                                                                  */
/* ========================================================================= */
void sampleAll() {
#if ENABLE_BME280
  if (st.bmeOk) { st.temp = bme.readTemperature(); st.hum = bme.readHumidity(); }
#endif
#if ENABLE_BH1750
  if (st.bhOk) {
    float l = luxMeter.readLightLevel();
    st.lux = (l < 0) ? NAN : l;
  }
#endif
  st.raw1  = readSoil(PIN_SOIL_1);
  st.soil1 = soilPercent(st.raw1, SOIL1_ADC_DRY, SOIL1_ADC_WET);
#if ENABLE_SOIL2
  st.raw2  = readSoil(PIN_SOIL_2);
  st.soil2 = soilPercent(st.raw2, SOIL2_ADC_DRY, SOIL2_ADC_WET);
  st.soilAvg = (st.soil1 + st.soil2) / 2;
#else
  st.soilAvg = st.soil1;
#endif
#if ENABLE_LEAK
  st.leakRaw = readSoil(PIN_LEAK);          // same averaging helper
  st.leakWet = (st.leakRaw > LEAK_WET_ADC);
#endif
#if ENABLE_FLOAT
  st.tankOk = (digitalRead(PIN_FLOAT) != FLOAT_EMPTY_STATE);
#endif
}

/* ========================================================================= */
/*  control logic — runs every sample tick, auto mode only (safety always)   */
/* ========================================================================= */
bool inLightWindow() {
  if (!st.timeOk) return true;              // no clock yet -> lux gates alone
  struct tm t;
  if (!getLocalTime(&t, 0)) return true;
  if (t.tm_mday != lastDay) {               // midnight rollover: reset budget
    lastDay = t.tm_mday;
    waterSecToday = 0;
  }
  return (t.tm_hour >= cfg.lightStart) && (t.tm_hour < cfg.lightEnd);
}

void runAuto() {
  /* -- watering: burst -> soak -> re-judge ------------------------------- */
  switch (wPhase) {
    case W_IDLE:
      if (st.soilAvg < cfg.soilDry && st.tankOk && waterSecToday < WATER_MAX_S_DAY) {
        wPhase = W_RUN; wPhaseStart = millis();
        out.water = true;
        Serial.printf("[water] soil %d%% < %d%% -> burst %ds\n",
                      st.soilAvg, cfg.soilDry, WATER_RUN_S);
      }
      break;
    case W_RUN:
      if (!st.tankOk || secsSince(wPhaseStart) >= WATER_RUN_S) {
        waterSecToday += secsSince(wPhaseStart);
        out.water = false;
        wPhase = W_SOAK; wPhaseStart = millis();
        Serial.println("[water] soak");
      }
      break;
    case W_SOAK:
      if (secsSince(wPhaseStart) >= WATER_SOAK_MIN * 60UL) wPhase = W_IDLE;
      break;
  }

  /* -- humidity mist: hysteresis + max runtime + cooldown ----------------- */
  if (!isnan(st.hum)) {
    humBadReads = 0;
    if (!out.hum) {
      if (st.hum < cfg.humLo && st.tankOk && millis() > humCooldownUntil) {
        out.hum = true; humStart = millis();
        Serial.printf("[hum] %.0f%% < %d%% -> mist on\n", st.hum, cfg.humLo);
      }
    } else {
      if (st.hum >= cfg.humHi || !st.tankOk || secsSince(humStart) >= HUM_MIST_MAX_S) {
        out.hum = false;
        humCooldownUntil = millis() + HUM_MIST_COOLDOWN_S * 1000UL;
        Serial.println("[hum] mist off");
      }
    }
  } else {
    /* A dropped I2C read is not proof the air is dry. Require several in a
       row before acting, so one flaky sample cannot flap the mist channel. */
    if (++humBadReads >= 3) {
      if (out.hum) Serial.println("[hum] RH unreadable -> mist off (fail-safe)");
      out.hum = false;
    }
  }

  /* -- grow light: photoperiod window gated by measured lux --------------- */
  bool window = inLightWindow();
  if (!window)                 out.light = false;
  else if (isnan(st.lux))      out.light = true;              // schedule only
  else if (st.lux < cfg.luxOn)  out.light = true;
  else if (st.lux > cfg.luxOff) out.light = false;            // else: hold

  /* -- exhaust fan (only if fitted) --------------------------------------- */
#if ENABLE_FAN_EXH
  if (!isnan(st.temp)) {
    if (st.temp > TEMP_VENT_ON)  out.fanExh = true;
    if (st.temp < TEMP_VENT_OFF) out.fanExh = false;
  }
#endif
}

void runManualGuards() {
  /* forgot-it-running protection for manual mist */
  if (out.water && secsSince(manWaterStart) > MANUAL_OUT_MAX_S) out.water = false;
  if (out.hum   && secsSince(manHumStart)   > MANUAL_OUT_MAX_S) out.hum   = false;
}

/* ========================================================================= */
/*  web API                                                                  */
/* ========================================================================= */
void sendStatus() {
  char up[24];
  unsigned long s = millis() / 1000UL;
  snprintf(up, sizeof(up), "%luh %lum", s / 3600, (s / 60) % 60);

  /* Plain char buffers only. Arduino String temporaries inside a printf
     argument list are destroyed while printf is still reading them, and a
     format/argument mismatch here reads an int as a pointer — both give a
     LoadProhibited panic on every request. */
  char t[12], h[12], l[12], s2[8], ip[20];
  if (isnan(st.temp)) strcpy(t, "null"); else snprintf(t, sizeof(t), "%.1f", st.temp);
  if (isnan(st.hum))  strcpy(h, "null"); else snprintf(h, sizeof(h), "%.0f", st.hum);
  if (isnan(st.lux))  strcpy(l, "null"); else snprintf(l, sizeof(l), "%.0f", st.lux);
#if ENABLE_SOIL2
  snprintf(s2, sizeof(s2), "%d", st.soil2);
#else
  strcpy(s2, "null");
#endif
  snprintf(ip, sizeof(ip), "%s",
           (WiFi.getMode() & WIFI_MODE_AP) ? WiFi.softAPIP().toString().c_str()
                                           : WiFi.localIP().toString().c_str());

  char buf[860];
  snprintf(buf, sizeof(buf),
    "{\"temp\":%s,\"hum\":%s,\"lux\":%s,"
    "\"soil\":%d,\"soil1\":%d,\"soil2\":%s,\"raw1\":%d,\"raw2\":%d,"
    "\"leak\":%d,\"leakWet\":%s,"
    "\"tankOk\":%s,\"mode\":\"%s\",\"ip\":\"%s\",\"up\":\"%s\","
    "\"out\":{\"water\":%d,\"hum\":%d,\"light\":%d,\"buzz\":%d,\"fan\":%d},"
    "\"cfg\":{\"soilDry\":%d,\"humLo\":%d,\"humHi\":%d,\"luxOn\":%d,"
    "\"luxOff\":%d,\"lightStart\":%d,\"lightEnd\":%d,\"bright\":%d}}",
    t, h, l,
    st.soilAvg, st.soil1, s2, st.raw1, st.raw2,
    st.leakRaw, st.leakWet ? "true" : "false",
    st.tankOk ? "true" : "false",
    manualMode ? "manual" : "auto",
    ip, up,
    (int)out.water, (int)out.hum, (int)out.light, (int)out.buzzer,
    (int)out.fanExh,
    cfg.soilDry, cfg.humLo, cfg.humHi, cfg.luxOn,
    cfg.luxOff, cfg.lightStart, cfg.lightEnd, cfg.bright);
  server.send(200, "application/json", buf);
}

void savePrefs() {
  prefs.putInt("soilDry", cfg.soilDry);   prefs.putInt("humLo",  cfg.humLo);
  prefs.putInt("humHi",   cfg.humHi);     prefs.putInt("luxOn",  cfg.luxOn);
  prefs.putInt("luxOff",  cfg.luxOff);    prefs.putInt("lightSt", cfg.lightStart);
  prefs.putInt("lightEn", cfg.lightEnd);  prefs.putInt("bright", cfg.bright);
}

void loadPrefs() {
  cfg.soilDry    = prefs.getInt("soilDry", DEF_SOIL_DRY_PCT);
  cfg.humLo      = prefs.getInt("humLo",   DEF_HUM_LOW);
  cfg.humHi      = prefs.getInt("humHi",   DEF_HUM_HIGH);
  cfg.luxOn      = prefs.getInt("luxOn",   DEF_LUX_ON);
  cfg.luxOff     = prefs.getInt("luxOff",  DEF_LUX_OFF);
  cfg.lightStart = prefs.getInt("lightSt", DEF_LIGHT_START);
  cfg.lightEnd   = prefs.getInt("lightEn", DEF_LIGHT_END);
  cfg.bright     = prefs.getInt("bright",  DEF_LIGHT_BRIGHT);
}

void setupServer() {
  server.on("/", []() { server.send_P(200, "text/html", INDEX_HTML); });

  server.on("/api/status", sendStatus);

  server.on("/api/mode", []() {
    manualMode = (server.arg("m") == "manual");
    if (!manualMode) { /* returning to auto: let logic re-decide cleanly */
      out.water = false; out.hum = false;
      wPhase = W_IDLE;
    }
    sendStatus();
  });

  server.on("/api/out", []() {
    /* Pressing any output button takes manual control automatically — having
       to flip a mode switch first made the buttons look broken. */
    if (!manualMode) {
      manualMode = true;
      wPhase = W_IDLE;          // drop whatever the auto logic was mid-way through
      Serial.println("[mode] manual (taken by an output button)");
    }
    String n = server.arg("name");
    bool s = server.arg("state") == "1";
    if      (n == "water") { out.water = s; manWaterStart = millis(); }
    else if (n == "hum")   { out.hum   = s; manHumStart   = millis(); }
    else if (n == "light") { out.light = s; }
    else if (n == "buzz")  { out.buzzer = s; }
    else if (n == "fan")   { out.fanExh = s; }
    if (s && !st.tankOk && (n == "water" || n == "hum")) {
      out.water = false; out.hum = false;
      server.send(200, "application/json", "{\"err\":\"tank empty - mist blocked\"}");
      return;
    }
    applyOutputs();
    sendStatus();
  });

  server.on("/api/set", []() {
    auto grab = [&](const char* k, int lo, int hi, int cur) {
      return server.hasArg(k) ? constrain(server.arg(k).toInt(), lo, hi) : cur;
    };
    cfg.soilDry    = grab("soilDry",    5, 80,    cfg.soilDry);
    cfg.humLo      = grab("humLo",     30, 95,    cfg.humLo);
    cfg.humHi      = grab("humHi",     40, 99,    cfg.humHi);
    cfg.luxOn      = grab("luxOn",      0, 20000, cfg.luxOn);
    cfg.luxOff     = grab("luxOff",     0, 30000, cfg.luxOff);
    cfg.lightStart = grab("lightStart", 0, 23,    cfg.lightStart);
    cfg.lightEnd   = grab("lightEnd",   1, 24,    cfg.lightEnd);
    cfg.bright     = grab("bright",     0, 255,   cfg.bright);
    if (cfg.humHi <= cfg.humLo) cfg.humHi = cfg.humLo + 5;
    savePrefs();
    sendStatus();
  });

  server.begin();
}

/* ========================================================================= */
void setup() {
  /* outputs safe BEFORE anything else can stall */
  /* Latch OFF before enabling the driver, so nothing pulses at boot. */
  writeOut(PIN_MIST_WATER, false); pinMode(PIN_MIST_WATER, OUTPUT); writeOut(PIN_MIST_WATER, false);
  writeOut(PIN_MIST_HUM,   false); pinMode(PIN_MIST_HUM,   OUTPUT); writeOut(PIN_MIST_HUM,   false);
  pinMode(PIN_LIGHT, OUTPUT);      writePwmOut(PIN_LIGHT, 0);
#if ENABLE_FAN_EXH
  writeOut(PIN_FAN_EXH, false); pinMode(PIN_FAN_EXH, OUTPUT); writeOut(PIN_FAN_EXH, false);
#endif
#if ENABLE_BUZZER
  pinMode(PIN_BUZZER, OUTPUT); digitalWrite(PIN_BUZZER, LOW);
#endif
#if ENABLE_FLOAT
  pinMode(PIN_FLOAT, INPUT_PULLUP);
#endif

  Serial.begin(115200);
  delay(300);
  Serial.println("\n== Terrarium firmware ==");

  prefs.begin("terra", false);
  loadPrefs();

  analogSetAttenuation(ADC_11db);          // full 0-3.3V ADC range
  Wire.begin(PIN_SDA, PIN_SCL);
  Wire.setTimeOut(10);   // a loose wire must not stall the web server

#if ENABLE_BME280
  st.bmeOk = bme.begin(0x76, &Wire) || bme.begin(0x77, &Wire);
  Serial.printf("BME280: %s\n", st.bmeOk ? "ok" : "NOT FOUND (check 3V3 + address)");
#endif
#if ENABLE_BH1750
  st.bhOk = luxMeter.begin(BH1750::CONTINUOUS_HIGH_RES_MODE, 0x23, &Wire);
  Serial.printf("BH1750: %s\n", st.bhOk ? "ok" : "NOT FOUND");
#endif

  /* Wi-Fi: join home network, else raise own hotspot */
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  Serial.printf("Wi-Fi: joining %s", WIFI_SSID);
  unsigned long t0 = millis();
  while (WiFi.status() != WL_CONNECTED && secsSince(t0) < WIFI_TIMEOUT_S) {
    delay(250); Serial.print(".");
  }
  if (WiFi.status() == WL_CONNECTED) {
    Serial.printf("\nWi-Fi ok: http://%s\n", WiFi.localIP().toString().c_str());
    configTime(TZ_OFFSET_SEC, 0, NTP_SERVER);
    struct tm t;
    st.timeOk = getLocalTime(&t, 3000);
    Serial.printf("NTP: %s\n", st.timeOk ? "synced" : "no (schedule falls back to lux-only)");
  } else {
    WiFi.mode(WIFI_AP);
    WiFi.softAP(AP_SSID, AP_PASS);
    Serial.printf("\nNo Wi-Fi -> hotspot \"%s\" pw \"%s\" -> http://%s\n",
                  AP_SSID, AP_PASS, WiFi.softAPIP().toString().c_str());
  }
  if (MDNS.begin(MDNS_NAME)) Serial.printf("mDNS: http://%s.local\n", MDNS_NAME);

  setupServer();
  sampleAll();
  Serial.println("running.");
}

/* One status line every 10s. Wi-Fi can drop; the USB cable does not, so this
   is the channel to trust when something looks wrong — and it is the log you
   screenshot for the report. */
void printStatusLine() {
  /* No Arduino String here. A temporary String inside a printf argument list
     hands printf a pointer into an object that is already being destroyed —
     that is a LoadProhibited panic on ESP32. Fixed-size buffers instead. */
  char t[10], h[10], l[10];
  if (isnan(st.temp)) strcpy(t, "--"); else snprintf(t, sizeof(t), "%.1f", st.temp);
  if (isnan(st.hum))  strcpy(h, "--"); else snprintf(h, sizeof(h), "%.0f", st.hum);
  if (isnan(st.lux))  strcpy(l, "--"); else snprintf(l, sizeof(l), "%.0f", st.lux);

  /* Specifier order must match the argument order exactly. Getting this wrong
     hands an int to %s and panics the board — it has bitten this file twice. */
  Serial.printf("[%lus] temp %s  RH %s  lux %s  soil %d%% (raw %d/%d)  "
                "leak %d%s  tank:%s  %s  water:%d mist:%d light:%d  rssi %d\n",
    millis() / 1000UL, t, h, l,
    st.soilAvg, st.raw1, st.raw2,
    st.leakRaw, st.leakWet ? "(WET!)" : "",
    st.tankOk ? "OK" : "EMPTY",
    manualMode ? "manual" : "auto",
    (int)out.water, (int)out.hum, (int)out.light,
    WiFi.status() == WL_CONNECTED ? (int)WiFi.RSSI() : 0);
}

void loop() {
  server.handleClient();

  if (millis() - lastSample >= SENSOR_PERIOD_MS) {
    lastSample = millis();
    sampleAll();
    if (manualMode) runManualGuards();
    else            runAuto();
    applyOutputs();                        // interlock enforced every tick

    static unsigned long lastLine = 0;
    if (millis() - lastLine >= 10000UL) { lastLine = millis(); printStatusLine(); }
  }
}
