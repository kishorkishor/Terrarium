/* ============================================================================
 * SOIL SENSOR CALIBRATION — reads the raw ADC so you can fill in config.h
 *
 * Wiring (no soldering needed — these sensors ship with connectors):
 *   SOIL 1   VCC -> 3V3      GND -> GND      AOUT -> D34
 *   SOIL 2   VCC -> 3V3      GND -> GND      AOUT -> D35
 *
 * NEVER power these from VIN (5V). 3V3 only.
 *
 * HOW TO CALIBRATE
 *   1. Hold the sensor in open air, completely dry -> note the DRY number
 *   2. Stand it in a glass of water up to (not past) the white line
 *      -> note the WET number
 *   3. Put those two numbers into config.h as SOILn_ADC_DRY / SOILn_ADC_WET
 *
 * Capacitive sensors read HIGH when dry and LOW when wet — if yours goes the
 * other way it is a resistive sensor and the wrong type for this build.
 *
 * Board: ESP32 Dev Module · Serial Monitor 115200
 * ========================================================================== */

#define PIN_SOIL_1 34
#define PIN_SOIL_2 35

int readAvg(int pin) {
  long acc = 0;
  for (int i = 0; i < 16; i++) { acc += analogRead(pin); delay(2); }
  return acc / 16;
}

/* same maths the firmware uses, so the % you see here is the % it will use */
int soilPercent(int raw, int dry, int wet) {
  long pct = 100L * (dry - raw) / (dry - wet);
  return constrain((int)pct, 0, 100);
}

void setup() {
  Serial.begin(115200);
  delay(600);
  analogSetAttenuation(ADC_11db);        // full 0-3.3V range, as in firmware
  Serial.println();
  Serial.println(F("=================================================="));
  Serial.println(F(" SOIL CALIBRATION   D34 = soil 1   D35 = soil 2"));
  Serial.println(F(" dry in air -> note the number. in water -> note it."));
  Serial.println(F("=================================================="));
}

void loop() {
  int r1 = readAvg(PIN_SOIL_1);
  int r2 = readAvg(PIN_SOIL_2);

  /* percentages against the current config.h defaults, for reference only */
  int p1 = soilPercent(r1, 3200, 1200);
  int p2 = soilPercent(r2, 3200, 1200);

  Serial.printf("SOIL1 raw %4d  (%3d%% with default cal)   |   "
                "SOIL2 raw %4d  (%3d%%)\n", r1, p1, r2, p2);

  if (r1 > 4090 && r2 > 4090)
    Serial.println(F("   both pegged at max -> nothing connected to D34/D35 yet"));
  if (r1 < 30 && r2 < 30)
    Serial.println(F("   both near zero -> check VCC on 3V3 and GND"));

  delay(1000);
}
