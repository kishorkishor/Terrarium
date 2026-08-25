/* ============================================================================
 * BENCH MONITOR — every input in the terrarium, one screen, once per 2s.
 *
 * Flash this while wiring up. It reports whatever is currently connected and
 * says nothing useful about whatever is not — so you can add one part at a
 * time and watch it appear.
 *
 *   soil 1   D34      capacitive probe   dry ~2500  wet ~1300
 *   soil 2   D35      capacitive probe
 *   leak     D32      drip tray sensor   dry = high
 *   float    D27      tank switch        INPUT_PULLUP
 *   I2C      D21/D22  BME280 + BH1750    line health + address scan
 *
 * Board: ESP32 Dev Module · Serial Monitor 115200
 * ========================================================================== */
#include <Wire.h>

#define PIN_SOIL_1 34
#define PIN_SOIL_2 35
#define PIN_LEAK   32
#define PIN_FLOAT  27
#define PIN_SDA    21
#define PIN_SCL    22

int readAvg(int pin) {
  long acc = 0;
  for (int i = 0; i < 16; i++) { acc += analogRead(pin); delay(2); }
  return acc / 16;
}

/* an analog pin with nothing on it drifts and jitters; a real sensor is steady */
bool looksFloating(int pin) {
  int lo = 4095, hi = 0;
  for (int i = 0; i < 24; i++) {
    int v = analogRead(pin);
    if (v < lo) lo = v;
    if (v > hi) hi = v;
    delay(2);
  }
  return (lo < 400 && (hi - lo) > 80);
}

int sampleHigh(int pin) {
  pinMode(pin, INPUT);
  int hi = 0;
  for (int i = 0; i < 30; i++) { if (digitalRead(pin)) hi++; delay(2); }
  return hi;
}

int scanBus(int sdaPin, int sclPin, const char* label) {
  Wire.end();
  Wire.begin(sdaPin, sclPin);
  Wire.setClock(100000);
  int found = 0;
  for (byte a = 1; a < 127; a++) {
    Wire.beginTransmission(a);
    if (Wire.endTransmission() == 0) {
      Serial.printf("I2C  [%s] device at 0x%02X", label, a);
      if (a == 0x76 || a == 0x77) Serial.print(F("  <- BME280"));
      if (a == 0x23)              Serial.print(F("  <- BH1750"));
      if (a == 0x5C)              Serial.print(F("  <- BH1750, tie ADDR to GND"));
      Serial.println();
      found++;
    }
  }
  Serial.printf("I2C  [%s] %d device(s)\n", label, found);
  return found;
}

void setup() {
  Serial.begin(115200);
  delay(600);
  analogSetAttenuation(ADC_11db);
  pinMode(PIN_FLOAT, INPUT_PULLUP);
  Serial.println();
  Serial.println(F("== BENCH MONITOR =="));
}

void loop() {
  int s1 = readAvg(PIN_SOIL_1);
  int s2 = readAvg(PIN_SOIL_2);
  int lk = readAvg(PIN_LEAK);
  bool f1 = looksFloating(PIN_SOIL_1);
  bool f2 = looksFloating(PIN_SOIL_2);

  pinMode(PIN_FLOAT, INPUT_PULLUP);
  int fl = digitalRead(PIN_FLOAT);

  Serial.println(F("\n------------------------------------------"));
  Serial.printf("SOIL1 D34  %4d  %s\n", s1, f1 ? "(floating - not connected)" : "(steady - connected)");
  Serial.printf("SOIL2 D35  %4d  %s\n", s2, f2 ? "(floating - not connected)" : "(steady - connected)");
  Serial.printf("LEAK  D32  %4d\n", lk);
  Serial.printf("FLOAT D27  %s\n", fl ? "HIGH (open / tank OK)" : "LOW (closed / tank empty)");

  int sda = sampleHigh(PIN_SDA);
  int scl = sampleHigh(PIN_SCL);
  Serial.printf("I2C lines  SDA %2d/30  SCL %2d/30  %s\n", sda, scl,
                (sda > 27 && scl > 27) ? "both HIGH - module powered"
                                       : "LOW - no powered module on the bus");

  int found = scanBus(PIN_SDA, PIN_SCL, "normal  SDA=D21 SCL=D22");

  /* If nothing answered, try the bus with the two wires interpreted the other
     way round. A hit here proves the physical wires are swapped — no need to
     pull anything apart to find out. */
  int swapped = 0;
  if (found == 0) swapped = scanBus(PIN_SCL, PIN_SDA, "SWAPPED SDA=D22 SCL=D21");

  if (found == 0 && swapped > 0) {
    Serial.println(F("I2C  >>> YOUR SDA AND SCL WIRES ARE SWAPPED. Exchange them."));
  } else if (found == 0 && swapped == 0) {
    Serial.println(F("I2C  no reply either way round."));
    Serial.println(F("I2C  BME280: jumper CSB->3V3 (forces I2C) and SDO->GND (0x76)."));
  }

  delay(1200);
}
