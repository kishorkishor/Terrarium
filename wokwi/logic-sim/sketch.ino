/* ============================================================================
 * TERRARIUM — CONTROL LOGIC SIMULATION
 * EEE4103 capstone · runs on emulated ESP32 hardware at wokwi.com
 *
 * WHY THIS EXISTS
 *   Proves the control logic in terrarium.ino actually runs on real ESP32
 *   silicon before you spend a taka. Same state machines, same thresholds,
 *   same safety interlock — only the sensor reads differ, because Wokwi has
 *   no BME280 or BH1750 part.
 *
 * ZERO EXTERNAL LIBRARIES. Nothing to install, nothing that can fail to
 * compile. Only analogRead / digitalRead / digitalWrite and Serial.
 *
 * HOW TO DRIVE IT
 *   SOIL 1 / SOIL 2  turn DOWN  -> soil reads dry  -> watering mist fires
 *   HUMIDITY         turn DOWN  -> RH falls        -> humidity mist fires
 *   LIGHT            turn DOWN  -> dark            -> grow light comes on
 *   FLOAT switch     slide LEFT -> tank empty      -> BOTH mists forced off
 *
 * Time runs SIM_SPEED times faster than real, so soak delays and the
 * photoperiod are watchable. Serial Monitor at 115200.
 * ========================================================================== */

/* ---- pins — identical to config.h ---------------------------------------- */
#define PIN_SOIL_1      34   // ADC1  (exact match to real build)
#define PIN_SOIL_2      35   // ADC1  (exact match)
#define PIN_SIM_HUM     32   // sim stand-in: real build reads RH from BME280 on I2C
#define PIN_SIM_LUX     33   // sim stand-in: real build reads lux from BH1750 on I2C
#define PIN_FLOAT       27   // exact match, INPUT_PULLUP

#define PIN_MIST_WATER  16   // exact match
#define PIN_MIST_HUM    25   // exact match
#define PIN_FAN_EXH     17   // exact match
#define PIN_FAN_CIRC    18   // exact match
#define PIN_LIGHT       19   // exact match
#define PIN_SPARE       23   // exact match
#define PIN_BUZZER      26   // exact match

/* ---- soil calibration — same constants as config.h ----------------------- */
#define SOIL1_ADC_DRY 3200
#define SOIL1_ADC_WET 1200
#define SOIL2_ADC_DRY 3200
#define SOIL2_ADC_WET 1200

/* ---- thresholds — same defaults as config.h ------------------------------ */
int cfgSoilDry    = 35;     // water below this soil %
int cfgHumLo      = 75;     // mist below this RH %
int cfgHumHi      = 90;     // stop misting at this RH %
int cfgLuxOn      = 800;    // light on below this lux
int cfgLuxOff     = 2000;   // light off above this lux
int cfgLightStart = 7;      // photoperiod start hour
int cfgLightEnd   = 19;     // photoperiod end hour

/* ---- timings — same as config.h ------------------------------------------ */
#define WATER_RUN_S        90UL     // one watering burst
#define WATER_SOAK_S    (20UL*60)   // soak before re-judging
#define HUM_MIST_MAX_S    300UL     // cap on one humidity burst
#define HUM_COOLDOWN_S    180UL     // rest between humidity bursts
#define TEMP_VENT_ON      32.0f
#define TEMP_VENT_OFF     29.0f

/* ---- simulation clock ---------------------------------------------------- */
#define SIM_SPEED    120UL          // simulated seconds per real second
#define START_HOUR     6UL          // simulation begins at 06:00

/* ---- state --------------------------------------------------------------- */
struct { bool water=false, hum=false, light=false, fanExh=false, fanCirc=false; } out;

enum WPhase { W_IDLE, W_RUN, W_SOAK };
WPhase       wPhase      = W_IDLE;
unsigned long wPhaseAt   = 0;
unsigned long humAt      = 0;
unsigned long humCoolUntil = 0;
unsigned long lastPrint  = 0;
bool          tankOk     = true;
float         temp       = 25.0f;

/* simulated seconds since boot — 64-bit maths avoids the overflow you get
 * from millis()*SIM_SPEED after ~35 s of real time. */
unsigned long simSeconds() {
  return (unsigned long)(((unsigned long long)millis() * SIM_SPEED) / 1000ULL);
}
unsigned long dayClock() { return (START_HOUR * 3600UL + simSeconds()) % 86400UL; }

/* ---- helpers — soilPercent is character-for-character the firmware's ----- */
int soilPercent(int raw, int dryAdc, int wetAdc) {
  long pct = 100L * (dryAdc - raw) / (dryAdc - wetAdc);
  return constrain((int)pct, 0, 100);
}
int readAvg(int pin) {
  long acc = 0;
  for (int i = 0; i < 8; i++) acc += analogRead(pin);
  return acc / 8;
}

void applyOutputs() {
  /* SAFETY INTERLOCK — identical to applyOutputs() in terrarium.ino.
     An empty tank kills both mist channels. No manual override exists. */
  bool water = out.water && tankOk;
  bool humid = out.hum   && tankOk;
  digitalWrite(PIN_MIST_WATER, water ? HIGH : LOW);
  digitalWrite(PIN_MIST_HUM,   humid ? HIGH : LOW);
  digitalWrite(PIN_LIGHT,      out.light   ? HIGH : LOW);
  digitalWrite(PIN_FAN_EXH,    out.fanExh  ? HIGH : LOW);
  digitalWrite(PIN_FAN_CIRC,   out.fanCirc ? HIGH : LOW);
  digitalWrite(PIN_BUZZER,     tankOk ? LOW : HIGH);
  digitalWrite(PIN_SPARE,      LOW);
}

const char* phaseName() {
  return wPhase == W_IDLE ? "idle" : (wPhase == W_RUN ? "WATERING" : "soaking");
}

/* ========================================================================== */
void setup() {
  const int outs[] = { PIN_MIST_WATER, PIN_MIST_HUM, PIN_FAN_EXH,
                       PIN_FAN_CIRC, PIN_LIGHT, PIN_SPARE, PIN_BUZZER };
  for (unsigned i = 0; i < sizeof(outs)/sizeof(outs[0]); i++) {
    digitalWrite(outs[i], LOW);      // latch low BEFORE enabling the driver
    pinMode(outs[i], OUTPUT);
    digitalWrite(outs[i], LOW);
  }
  pinMode(PIN_FLOAT, INPUT_PULLUP);
  analogSetAttenuation(ADC_11db);    // full 0–3.3 V ADC range, as in firmware

  Serial.begin(115200);
  delay(400);
  Serial.println();
  Serial.println(F("=================================================="));
  Serial.println(F(" TERRARIUM CONTROL LOGIC — SIMULATION"));
  Serial.println(F("=================================================="));
  Serial.println(F(" Turn SOIL 1/2 down  -> watering mist fires"));
  Serial.println(F(" Turn HUMIDITY down  -> humidity mist fires"));
  Serial.println(F(" Turn LIGHT down     -> grow light comes on"));
  Serial.println(F(" Slide FLOAT left    -> tank empty, mists blocked"));
  Serial.print  (F(" Clock runs ")); Serial.print(SIM_SPEED);
  Serial.println(F("x real time."));
  Serial.println();
}

void loop() {
  unsigned long now  = simSeconds();
  unsigned long dsec = dayClock();
  int  hour = dsec / 3600;

  /* ---- read the "sensors" ---------------------------------------------- */
  int soil1 = soilPercent(readAvg(PIN_SOIL_1), SOIL1_ADC_DRY, SOIL1_ADC_WET);
  int soil2 = soilPercent(readAvg(PIN_SOIL_2), SOIL2_ADC_DRY, SOIL2_ADC_WET);
  int soil  = (soil1 + soil2) / 2;
  int hum   = map(readAvg(PIN_SIM_HUM), 0, 4095, 0, 100);
  int lux   = map(readAvg(PIN_SIM_LUX), 0, 4095, 0, 5000);
  tankOk    = (digitalRead(PIN_FLOAT) == HIGH);   // LOW (switch closed) = empty

  /* air temperature follows a simple day curve, plus grow-light heating */
  float dayCurve = sin((hour - 6) / 12.0 * PI);
  if (dayCurve < 0) dayCurve = 0;
  temp = 24.0f + dayCurve * 6.0f + (out.light ? 1.2f : 0.0f);

  /* ---- WATERING: burst -> soak -> re-judge ------------------------------ */
  switch (wPhase) {
    case W_IDLE:
      if (soil < cfgSoilDry && tankOk) {
        wPhase = W_RUN; wPhaseAt = now; out.water = true;
        Serial.print(F(">> soil ")); Serial.print(soil);
        Serial.print(F("% < ")); Serial.print(cfgSoilDry);
        Serial.println(F("% -> WATERING MIST ON"));
      }
      break;
    case W_RUN:
      if (!tankOk || now - wPhaseAt >= WATER_RUN_S) {
        out.water = false; wPhase = W_SOAK; wPhaseAt = now;
        Serial.println(F(">> watering done -> soaking 20 min before re-check"));
      }
      break;
    case W_SOAK:
      if (now - wPhaseAt >= WATER_SOAK_S) {
        wPhase = W_IDLE;
        Serial.println(F(">> soak complete -> re-judging soil"));
      }
      break;
  }

  /* ---- HUMIDITY: hysteresis + max runtime + cooldown -------------------- */
  if (!out.hum) {
    if (hum < cfgHumLo && tankOk && now >= humCoolUntil) {
      out.hum = true; humAt = now;
      Serial.print(F(">> RH ")); Serial.print(hum);
      Serial.print(F("% < ")); Serial.print(cfgHumLo);
      Serial.println(F("% -> HUMIDITY MIST ON"));
    }
  } else {
    if (hum >= cfgHumHi || !tankOk || now - humAt >= HUM_MIST_MAX_S) {
      out.hum = false; humCoolUntil = now + HUM_COOLDOWN_S;
      Serial.print(F(">> humidity mist OFF (RH ")); Serial.print(hum);
      Serial.println(F("%), 3 min cooldown"));
    }
  }

  /* ---- GROW LIGHT: photoperiod window gated by measured lux ------------- */
  bool inWindow = (hour >= cfgLightStart && hour < cfgLightEnd);
  bool wasLight = out.light;
  if (!inWindow)            out.light = false;
  else if (lux < cfgLuxOn)  out.light = true;
  else if (lux > cfgLuxOff) out.light = false;
  if (wasLight != out.light) {
    Serial.print(F(">> grow light "));
    Serial.println(out.light ? F("ON") : F("OFF"));
  }

  /* ---- VENTILATION ------------------------------------------------------ */
  bool wasFan = out.fanExh;
  if (temp > TEMP_VENT_ON)  out.fanExh = true;
  if (temp < TEMP_VENT_OFF) out.fanExh = false;
  if (wasFan != out.fanExh) {
    Serial.print(F(">> exhaust fan "));
    Serial.println(out.fanExh ? F("ON") : F("OFF"));
  }
  out.fanCirc = out.light;          // circulate whenever the light is running

  /* ---- interlock + drive the pins --------------------------------------- */
  static bool wasTankOk = true;
  if (wasTankOk && !tankOk)
    Serial.println(F("!! TANK EMPTY — both mist channels forced OFF, buzzer on"));
  if (!wasTankOk && tankOk)
    Serial.println(F(">> tank refilled"));
  wasTankOk = tankOk;

  applyOutputs();

  /* ---- status block once per real second -------------------------------- */
  if (millis() - lastPrint >= 1000) {
    lastPrint = millis();
    char buf[200];
    snprintf(buf, sizeof(buf),
      "[%02d:%02d] soil %3d%% (%d/%d)  RH %3d%%  lux %4d  %4.1fC  tank:%s  %s\n"
      "         water:%s  mist:%s  light:%s  exh:%s  circ:%s\n",
      hour, (int)((dsec / 60) % 60), soil, soil1, soil2, hum, lux, temp,
      tankOk ? "OK" : "EMPTY", phaseName(),
      out.water && tankOk ? "ON " : "off",
      out.hum   && tankOk ? "ON " : "off",
      out.light            ? "ON " : "off",
      out.fanExh           ? "ON " : "off",
      out.fanCirc          ? "ON " : "off");
    Serial.print(buf);
  }

  delay(20);
}
