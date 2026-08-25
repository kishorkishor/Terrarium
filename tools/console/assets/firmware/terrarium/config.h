/* ============================================================================
 * TERRARIUM CONFIG — everything you should ever need to edit lives here.
 * Pin map matches the build guide §04 and the Wokwi diagram exactly.
 * ========================================================================== */
#pragma once

/* ---- Wi-Fi -------------------------------------------------------------- */
#define WIFI_SSID        "YOUR_WIFI_NAME"      // <-- EDIT
#define WIFI_PASS        "YOUR_WIFI_PASSWORD"  // <-- EDIT
#define WIFI_TIMEOUT_S   15        // give up after this and start own hotspot
#define AP_SSID          "Terrarium"           // fallback hotspot name
#define AP_PASS          "terrarium123"        // min 8 chars
#define MDNS_NAME        "terrarium"           // http://terrarium.local

/* Bangladesh = UTC+6, no DST */
#define TZ_OFFSET_SEC    (6 * 3600)
#define NTP_SERVER       "pool.ntp.org"

/* ---- which hardware is actually connected ------------------------------- *
 * 1 = present, 0 = not fitted. Anything set to 0 is skipped entirely and
 * its pin stays reserved for later.                                         */
#define ENABLE_BME280    1   // air temp + humidity (I2C 0x76)
#define ENABLE_BH1750    1   // lux sensor        (I2C 0x23)
#define ENABLE_SOIL2     1   // second soil probe on GPIO35
#define ENABLE_FLOAT     1   // reservoir float switch on GPIO27 (see note)
#define ENABLE_LEAK      1   // drip-tray leak sensor on GPIO32
#define ENABLE_FAN_EXH   1   // exhaust fan on GPIO17
#define ENABLE_FAN_CIRC  0   // circulation fan on GPIO18
#define ENABLE_BUZZER    1   // alarm buzzer on GPIO26

/* Buzzer type. A PASSIVE buzzer has no oscillator inside — a steady HIGH just
 * clicks once, so it must be driven with a square wave. An ACTIVE buzzer makes
 * its own tone and only needs a level. If yours clicks once and goes quiet,
 * it is passive: leave this at 1.                                            */
#define BUZZER_PASSIVE   1
#define BUZZER_TONE_HZ   2700   // most passive buzzers are loudest near 2-3 kHz

/* Set to 1 for real operation. At 0 the buzzer only responds to the app's
 * manual button, so bench testing stays quiet.                               */
#define BUZZER_AUTO_ALARM 0
/* NOTE on ENABLE_FLOAT: with no switch wired, the pin reads "tank OK" and
 * never blocks anything — so leaving this at 1 is harmless before the switch
 * arrives. Cheap mist discs BURN OUT when run dry; buy the ৳299 switch.    */

/* Optocoupler MOSFET boards: their input LED needs more current than a 3.3V
 * GPIO can push, so the ESP32 sinks the opto instead of sourcing it —
 * board IN pin sits on permanent 5V, board GND pin goes to the GPIO.
 * That inverts the logic: pin LOW = channel ON.
 * Set to 0 if you ever wire a board that triggers on a HIGH level.        */
#define MOSFET_ACTIVE_LOW 1

/* ---- pins (build guide §04 — do not change casually) -------------------- */
#define PIN_SDA          21
#define PIN_SCL          22
#define PIN_SOIL_1       34    // ADC1, input-only
#define PIN_SOIL_2       35    // ADC1, input-only
#define PIN_LEAK         32    // ADC1
#define PIN_FLOAT        27    // INPUT_PULLUP
#define PIN_DS18B20       4    // reserved (not used by this firmware yet)
#define PIN_MIST_WATER   16    // mist module used for WATERING  (was: pump)
#define PIN_MIST_HUM     25    // mist module used for HUMIDITY
#define PIN_FAN_EXH      17
#define PIN_FAN_CIRC     18
#define PIN_LIGHT        19    // grow light, PWM-dimmable
#define PIN_SPARE        23
#define PIN_BUZZER       26

/* Float switch: which reading means "tank EMPTY"?
 * LOW  = switch closes to GND when empty (most common mounting)
 * Flip to HIGH if yours reads inverted — test with the multimeter first.  */
#define FLOAT_EMPTY_STATE  LOW

/* ---- soil calibration (per sensor!) -------------------------------------
 * Record these at bench bring-up step 6: raw ADC in dry air, then fully
 * submerged in water. Capacitive sensors read HIGH when dry, LOW when wet. */
#define SOIL1_ADC_DRY    2450
#define SOIL1_ADC_WET    1070
#define SOIL2_ADC_DRY    2485
#define SOIL2_ADC_WET    1070

/* Leak sensor: dry board reads near 0, water bridging the traces pulls it
 * up. Anything above this counts as "wet". Tune from the live reading.  */
#define LEAK_WET_ADC     1500

/* ---- default thresholds (all editable live from the app, saved to flash) */
#define DEF_SOIL_DRY_PCT   35   // water when average soil % falls below this
#define DEF_HUM_LOW        75   // start humidity mist below this %RH
#define DEF_HUM_HIGH       90   // stop at this %RH
#define DEF_LUX_ON        800   // grow light on below this lux (in window)
#define DEF_LUX_OFF      2000   // grow light off above this lux
#define DEF_LIGHT_START     7   // photoperiod start hour (24h clock)
#define DEF_LIGHT_END      19   // photoperiod end hour
#define DEF_LIGHT_BRIGHT  220   // grow light PWM 0..255

/* ---- timings & safety limits -------------------------------------------- */
#define SENSOR_PERIOD_MS   2000UL   // sample everything every 2 s
#define WATER_RUN_S          90     // one watering mist burst
#define WATER_SOAK_MIN       20     // wait this long before re-judging soil
#define WATER_MAX_S_DAY    1800     // hard cap: 30 min watering mist per day
#define HUM_MIST_MAX_S      300     // one humidity burst never exceeds 5 min
#define HUM_MIST_COOLDOWN_S 180     // rest between humidity bursts
#define MANUAL_OUT_MAX_S    600     // manual mist auto-off after 10 min
#define TEMP_VENT_ON       32.0     // exhaust fan on above this °C (if fitted)
#define TEMP_VENT_OFF      29.0
