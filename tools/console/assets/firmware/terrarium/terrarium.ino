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
  /* timings, editable from the UI: seconds unless the name says minutes */
  int waterRun, waterSoak, waterCap, humMax, humCool, manMax;
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
String staSsid;                 // network we try to join (NVS beats config.h)
String staPass;
bool apMode = false;            // true when serving from our own hotspot
unsigned long rebootAt = 0;     // /api/wifi answers first, restarts here

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
      if (st.soilAvg < cfg.soilDry && st.tankOk &&
          waterSecToday < (unsigned long)cfg.waterCap * 60UL) {
        wPhase = W_RUN; wPhaseStart = millis();
        out.water = true;
        Serial.printf("[water] soil %d%% < %d%% -> burst %ds\n",
                      st.soilAvg, cfg.soilDry, cfg.waterRun);
      }
      break;
    case W_RUN:
      if (!st.tankOk || secsSince(wPhaseStart) >= (unsigned long)cfg.waterRun) {
        waterSecToday += secsSince(wPhaseStart);
        out.water = false;
        wPhase = W_SOAK; wPhaseStart = millis();
        Serial.println("[water] soak");
      }
      break;
    case W_SOAK:
      if (secsSince(wPhaseStart) >= (unsigned long)cfg.waterSoak * 60UL) wPhase = W_IDLE;
      break;
  }

  /* -- humidity mist: hysteresis + max runtime + cooldown ----------------- */
  if (!isnan(st.hum)) {
    humBadReads = 0;
    if (!out.hum) {
      /* signed diff, not >, so a 49-day millis() wrap cannot freeze misting */
      if (st.hum < cfg.humLo && st.tankOk &&
          (long)(millis() - humCooldownUntil) >= 0) {
        out.hum = true; humStart = millis();
        Serial.printf("[hum] %.0f%% < %d%% -> mist on\n", st.hum, cfg.humLo);
      }
    } else {
      if (st.hum >= cfg.humHi || !st.tankOk || secsSince(humStart) >= (unsigned long)cfg.humMax) {
        out.hum = false;
        humCooldownUntil = millis() + (unsigned long)cfg.humCool * 1000UL;
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
  unsigned long cap = (unsigned long)cfg.manMax * 60UL;
  if (out.water && secsSince(manWaterStart) > cap) out.water = false;
  if (out.hum   && secsSince(manHumStart)   > cap) out.hum   = false;
}

/* ========================================================================= */
/*  web API                                                                  */
/* ========================================================================= */
void buildStatus(char* buf, size_t bufn) {
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

  /* SSID goes into JSON - neutralise the two characters that would break it */
  char ss[40];
  snprintf(ss, sizeof(ss), "%s", staSsid.c_str());
  for (char* c = ss; *c; ++c) if (*c == '"' || *c == '\\') *c = '\'';

  snprintf(buf, bufn,
    "{\"ssid\":\"%s\",\"ap\":%s,"
    "\"temp\":%s,\"hum\":%s,\"lux\":%s,"
    "\"soil\":%d,\"soil1\":%d,\"soil2\":%s,\"raw1\":%d,\"raw2\":%d,"
    "\"leak\":%d,\"leakWet\":%s,"
    "\"tankOk\":%s,\"mode\":\"%s\",\"ip\":\"%s\",\"up\":\"%s\",\"waterToday\":%lu,"
    "\"out\":{\"water\":%d,\"hum\":%d,\"light\":%d,\"buzz\":%d,\"fan\":%d},"
    "\"cfg\":{\"soilDry\":%d,\"humLo\":%d,\"humHi\":%d,\"luxOn\":%d,"
    "\"luxOff\":%d,\"lightStart\":%d,\"lightEnd\":%d,\"bright\":%d,"
    "\"waterRun\":%d,\"waterSoak\":%d,\"waterCap\":%d,"
    "\"humMax\":%d,\"humCool\":%d,\"manMax\":%d}}",
    ss, apMode ? "true" : "false",
    t, h, l,
    st.soilAvg, st.soil1, s2, st.raw1, st.raw2,
    st.leakRaw, st.leakWet ? "true" : "false",
    st.tankOk ? "true" : "false",
    manualMode ? "manual" : "auto",
    ip, up, waterSecToday,
    (int)out.water, (int)out.hum, (int)out.light, (int)out.buzzer,
    (int)out.fanExh,
    cfg.soilDry, cfg.humLo, cfg.humHi, cfg.luxOn,
    cfg.luxOff, cfg.lightStart, cfg.lightEnd, cfg.bright,
    cfg.waterRun, cfg.waterSoak, cfg.waterCap,
    cfg.humMax, cfg.humCool, cfg.manMax);
}

void sendStatus() {
  char buf[1240];
  buildStatus(buf, sizeof(buf));
  server.send(200, "application/json", buf);
}

void savePrefs() {
  prefs.putInt("soilDry", cfg.soilDry);   prefs.putInt("humLo",  cfg.humLo);
  prefs.putInt("humHi",   cfg.humHi);     prefs.putInt("luxOn",  cfg.luxOn);
  prefs.putInt("luxOff",  cfg.luxOff);    prefs.putInt("lightSt", cfg.lightStart);
  prefs.putInt("lightEn", cfg.lightEnd);  prefs.putInt("bright", cfg.bright);
  prefs.putInt("wRun",  cfg.waterRun);    prefs.putInt("wSoak", cfg.waterSoak);
  prefs.putInt("wCap",  cfg.waterCap);    prefs.putInt("hMax",  cfg.humMax);
  prefs.putInt("hCool", cfg.humCool);     prefs.putInt("mMax",  cfg.manMax);
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
  cfg.waterRun   = prefs.getInt("wRun",  WATER_RUN_S);
  cfg.waterSoak  = prefs.getInt("wSoak", WATER_SOAK_MIN);
  cfg.waterCap   = prefs.getInt("wCap",  WATER_MAX_S_DAY / 60);
  cfg.humMax     = prefs.getInt("hMax",  HUM_MIST_MAX_S);
  cfg.humCool    = prefs.getInt("hCool", HUM_MIST_COOLDOWN_S);
  cfg.manMax     = prefs.getInt("mMax",  MANUAL_OUT_MAX_S / 60);
}

/* ---- shared command layer: the web API and the USB-serial commands call
        exactly these, so wired and wireless control can never drift apart -- */
void setModeCmd(bool manual) {
  manualMode = manual;
  if (!manualMode) {              // returning to auto: let logic re-decide
    out.water = false; out.hum = false;
    wPhase = W_IDLE;
  }
}

/* returns an error string, or NULL on success */
const char* applyOutCmd(const char* n, bool s1) {
  if (!manualMode) {
    manualMode = true;            // any output press takes manual control
    wPhase = W_IDLE;
    Serial.println("[mode] manual (taken by an output command)");
  }
  if      (!strcmp(n, "water")) { out.water = s1; manWaterStart = millis(); }
  else if (!strcmp(n, "hum"))   { out.hum   = s1; manHumStart   = millis(); }
  else if (!strcmp(n, "light")) { out.light = s1; }
  else if (!strcmp(n, "buzz"))  { out.buzzer = s1; }
  else if (!strcmp(n, "fan"))   { out.fanExh = s1; }
  else return "unknown output";
  if (s1 && !st.tankOk && (!strcmp(n, "water") || !strcmp(n, "hum"))) {
    out.water = false; out.hum = false;
    return "tank empty - mist blocked";
  }
  applyOutputs();
  return NULL;
}

bool setCfgKV(const char* k, long v) {
  if      (!strcmp(k, "soilDry"))    cfg.soilDry    = constrain((int)v, 5, 80);
  else if (!strcmp(k, "humLo"))      cfg.humLo      = constrain((int)v, 30, 95);
  else if (!strcmp(k, "humHi"))      cfg.humHi      = constrain((int)v, 40, 99);
  else if (!strcmp(k, "luxOn"))      cfg.luxOn      = constrain((int)v, 0, 20000);
  else if (!strcmp(k, "luxOff"))     cfg.luxOff     = constrain((int)v, 0, 30000);
  else if (!strcmp(k, "lightStart")) cfg.lightStart = constrain((int)v, 0, 23);
  else if (!strcmp(k, "lightEnd"))   cfg.lightEnd   = constrain((int)v, 1, 24);
  else if (!strcmp(k, "bright"))     cfg.bright     = constrain((int)v, 0, 255);
  else if (!strcmp(k, "waterRun"))   cfg.waterRun   = constrain((int)v, 10, 600);
  else if (!strcmp(k, "waterSoak"))  cfg.waterSoak  = constrain((int)v, 1, 180);
  else if (!strcmp(k, "waterCap"))   cfg.waterCap   = constrain((int)v, 1, 240);
  else if (!strcmp(k, "humMax"))     cfg.humMax     = constrain((int)v, 30, 1800);
  else if (!strcmp(k, "humCool"))    cfg.humCool    = constrain((int)v, 0, 3600);
  else if (!strcmp(k, "manMax"))     cfg.manMax     = constrain((int)v, 1, 120);
  else return false;
  return true;
}
static const char* CFG_KEYS[] = {
  "soilDry","humLo","humHi","luxOn","luxOff","lightStart","lightEnd","bright",
  "waterRun","waterSoak","waterCap","humMax","humCool","manMax" };

void finishCfg() {
  if (cfg.humHi <= cfg.humLo) cfg.humHi = cfg.humLo + 5;
  savePrefs();
}

void saveWifiCreds(const String& ssid, const String& pass) {
  prefs.putString("wssid", ssid);
  prefs.putString("wpass", pass);
  Serial.printf("[wifi] new network \"%s\" saved - restarting\n", ssid.c_str());
  rebootAt = millis() + 800;      // let the reply out first
}

void clearWifiCreds() {
  prefs.remove("wssid"); prefs.remove("wpass");
  Serial.println("[wifi] saved network cleared - restarting on config.h Wi-Fi");
  rebootAt = millis() + 800;
}

/* ---- USB-serial control: the same commands, no Wi-Fi needed --------------
     CMD STATUS                -> #R {status json}
     CMD OUT <name> <0|1>      -> #R {status json} | #R {"err":...}
     CMD MODE <auto|manual>    -> #R {status json}
     CMD SET k=v k=v ...       -> #R {status json}
     CMD WIFI <ssid>\t<pass>   -> #R {"ok":true}   (tab-separated!)
     CMD WIFI-CLEAR            -> #R {"ok":true}
     CMD PING                  -> #R {"pong":true}
   Anything not starting with "CMD " is ignored, so a human typing in a
   serial monitor does no harm.                                             */
void respondStatus() {
  char buf[1240];
  buildStatus(buf, sizeof(buf));
  Serial.print("#R "); Serial.println(buf);
}

void handleCommand(char* line) {
  if (strncmp(line, "CMD ", 4)) return;
  line += 4;
  if (!strcmp(line, "STATUS")) { respondStatus(); }
  else if (!strcmp(line, "PING")) { Serial.println("#R {\"pong\":true}"); }
  else if (!strncmp(line, "OUT ", 4)) {
    char n[12]; int v;
    if (sscanf(line + 4, "%11s %d", n, &v) == 2) {
      const char* err = applyOutCmd(n, v != 0);
      if (err) { Serial.printf("#R {\"err\":\"%s\"}\n", err); }
      else respondStatus();
    } else Serial.println("#R {\"err\":\"usage: CMD OUT name 0|1\"}");
  }
  else if (!strncmp(line, "MODE ", 5)) {
    setModeCmd(!strcmp(line + 5, "manual"));
    respondStatus();
  }
  else if (!strncmp(line, "SET ", 4)) {
    char* tok = strtok(line + 4, " ");
    while (tok) {
      char* eq = strchr(tok, '=');
      if (eq) { *eq = 0; setCfgKV(tok, atol(eq + 1)); }
      tok = strtok(NULL, " ");
    }
    finishCfg();
    respondStatus();
  }
  else if (!strcmp(line, "WIFI-CLEAR")) {
    Serial.println("#R {\"ok\":true,\"msg\":\"cleared - restarting\"}");
    clearWifiCreds();
  }
  else if (!strncmp(line, "WIFI ", 5)) {
    char* tab = strchr(line + 5, '\t');
    if (tab && tab != line + 5) {
      *tab = 0;
      Serial.println("#R {\"ok\":true,\"msg\":\"saved - restarting\"}");
      saveWifiCreds(String(line + 5), String(tab + 1));
    } else Serial.println("#R {\"err\":\"usage: CMD WIFI ssid<TAB>pass\"}");
  }
  else Serial.println("#R {\"err\":\"unknown command\"}");
}

void handleSerialInput() {
  static char buf[200];
  static size_t n = 0;
  while (Serial.available()) {
    char c = (char)Serial.read();
    if (c == '\n' || c == '\r') {
      if (n) { buf[n] = 0; handleCommand(buf); n = 0; }
    } else if (n < sizeof(buf) - 1) buf[n++] = c;
    else n = 0;                       // oversize line: drop it whole
  }
}

void setupServer() {
  server.on("/", []() { server.send_P(200, "text/html", INDEX_HTML); });

  server.on("/api/status", sendStatus);

  server.on("/api/mode", []() {
    setModeCmd(server.arg("m") == "manual");
    sendStatus();
  });

  server.on("/api/out", []() {
    const char* err = applyOutCmd(server.arg("name").c_str(),
                                  server.arg("state") == "1");
    if (err) {
      char e[80]; snprintf(e, sizeof(e), "{\"err\":\"%s\"}", err);
      server.send(200, "application/json", e);
      return;
    }
    sendStatus();
  });

  server.on("/api/set", []() {
    for (auto k : CFG_KEYS)
      if (server.hasArg(k)) setCfgKV(k, server.arg(k).toInt());
    finishCfg();
    sendStatus();
  });

  /* Save a new Wi-Fi network to NVS and restart on it. Reachable from the
     hotspot too: join "Terrarium" / terrarium123, open http://192.168.4.1,
     type the venue's Wi-Fi (a phone hotspot works) - no laptop, no reflash.
     If the new network cannot be joined the hotspot simply comes back. */
  server.on("/api/wifi", []() {
    if (server.hasArg("clear")) {
      server.send(200, "application/json",
                  "{\"ok\":true,\"msg\":\"cleared - restarting\"}");
      clearWifiCreds();
    } else {
      String ss = server.arg("ssid");
      if (!ss.length()) {
        server.send(200, "application/json", "{\"err\":\"ssid empty\"}");
        return;
      }
      server.send(200, "application/json", "{\"ok\":true}");
      saveWifiCreds(ss, server.arg("pass"));
    }
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

  /* Wi-Fi: join home network, else raise own hotspot.
     Credentials saved from the dashboard (NVS) win; config.h is only the
     default. So a demo needs no reflash: power up anywhere, join the
     hotspot, set the venue's Wi-Fi from the web app. */
  staSsid = prefs.getString("wssid", WIFI_SSID);
  staPass = prefs.getString("wpass", WIFI_PASS);
  bool haveCreds = staSsid.length() && staSsid != "YOUR_WIFI_NAME";
  WiFi.persistent(false);          // NVS "terra" is the single source of truth
  WiFi.setAutoReconnect(true);     // rejoin by itself after a router reboot
  if (haveCreds) {
    WiFi.mode(WIFI_STA);
    WiFi.begin(staSsid.c_str(), staPass.c_str());
    Serial.printf("Wi-Fi: joining %s", staSsid.c_str());
    unsigned long t0 = millis();
    while (WiFi.status() != WL_CONNECTED && secsSince(t0) < WIFI_TIMEOUT_S) {
      delay(250); Serial.print(".");
    }
  } else {
    Serial.println("Wi-Fi: no network saved yet - starting hotspot straight away");
  }
  if (WiFi.status() == WL_CONNECTED) {
    Serial.printf("\nWi-Fi ok: http://%s\n", WiFi.localIP().toString().c_str());
    configTime(TZ_OFFSET_SEC, 0, NTP_SERVER);
    struct tm t;
    st.timeOk = getLocalTime(&t, 3000);
    Serial.printf("NTP: %s\n", st.timeOk ? "synced" : "no (schedule falls back to lux-only)");
  } else {
    apMode = true;
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

/* Background Wi-Fi care, called from loop():
   - hotspot up but a real network saved -> keep retrying it (AP stays alive;
     the ESP32 runs AP+STA together, so nobody is kicked off the hotspot)
   - joined but NTP never synced -> keep retrying NTP                        */
void wifiTick() {
  static unsigned long lastTry = 0, lastNtp = 0;
  static bool staAnnounced = false;
  bool haveCreds = staSsid.length() && staSsid != "YOUR_WIFI_NAME";

  if (apMode && haveCreds && WiFi.status() != WL_CONNECTED &&
      millis() - lastTry > 90000UL) {
    lastTry = millis();
    WiFi.mode(WIFI_AP_STA);
    WiFi.begin(staSsid.c_str(), staPass.c_str());
    Serial.printf("[wifi] retrying \"%s\" in the background\n", staSsid.c_str());
  }
  if (WiFi.status() == WL_CONNECTED && !staAnnounced) {
    staAnnounced = true;
    Serial.printf("[wifi] joined \"%s\": http://%s\n",
                  staSsid.c_str(), WiFi.localIP().toString().c_str());
  }
  if (WiFi.status() != WL_CONNECTED) staAnnounced = false;

  if (!st.timeOk && WiFi.status() == WL_CONNECTED &&
      millis() - lastNtp > 300000UL) {
    lastNtp = millis();
    configTime(TZ_OFFSET_SEC, 0, NTP_SERVER);
    struct tm t;
    st.timeOk = getLocalTime(&t, 2000);
    if (st.timeOk) Serial.println("[ntp] synced");
  }
}

void loop() {
  server.handleClient();
  handleSerialInput();             // USB-serial control - works with no Wi-Fi

  if (rebootAt && millis() > rebootAt) ESP.restart();   // set by wifi save

  wifiTick();

  /* the daily watering budget must reset even with no clock: fall back to
     "every 24h of uptime" until NTP provides real midnights */
  static unsigned long capEpoch = 0;
  if (!st.timeOk && millis() - capEpoch >= 86400000UL) {
    capEpoch = millis();
    waterSecToday = 0;
  }

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
