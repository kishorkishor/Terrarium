/* ============================================================================
 * I2C BUS HEALTH — is a powered sensor actually on the wires?
 *
 * Every BME280/BH1750 breakout carries its own pull-up resistors to its VCC.
 * So if a module is connected AND powered, both SDA and SCL sit HIGH even with
 * the ESP32's internal pull-ups switched off. If nothing is connected, or the
 * module has no power, the lines float and read LOW / unstable.
 *
 * This separates "wiring is wrong" from "sensor has no power" without a meter.
 *
 * Board: ESP32 Dev Module · Serial Monitor 115200
 * ========================================================================== */
#include <Wire.h>

#define PIN_SDA 21
#define PIN_SCL 22

int sampleHigh(int pin) {
  pinMode(pin, INPUT);              // no internal pull-up — external only
  int hi = 0;
  for (int i = 0; i < 40; i++) { if (digitalRead(pin)) hi++; delay(2); }
  return hi;                        // out of 40
}

void setup() {
  Serial.begin(115200);
  delay(600);
  Serial.println();
  Serial.println(F("=================================================="));
  Serial.println(F(" I2C BUS HEALTH"));
  Serial.println(F("=================================================="));
}

void loop() {
  int sda = sampleHigh(PIN_SDA);
  int scl = sampleHigh(PIN_SCL);

  Serial.printf("\nSDA (GPIO21) high %2d/40   SCL (GPIO22) high %2d/40\n", sda, scl);

  if (sda > 36 && scl > 36) {
    Serial.println(F("  BOTH LINES HIGH -> a powered module IS on the bus."));
    Serial.println(F("  Wiring and power are good. The fault is addressing"));
    Serial.println(F("  or a damaged sensor. Re-run the scanner."));
  } else if (sda < 4 && scl < 4) {
    Serial.println(F("  BOTH LINES LOW -> no pull-ups seen."));
    Serial.println(F("  Either nothing is connected to D21/D22, or the module"));
    Serial.println(F("  has no power (check VIN->3V3 and GND), or its header"));
    Serial.println(F("  pins are NOT SOLDERED to the module."));
  } else if (sda > 36 || scl > 36) {
    Serial.println(F("  ONE line high, one not -> exactly one wire is landing."));
    Serial.println(F("  The other is on the wrong pin. Remember: D21 and D22 are"));
    Serial.println(F("  NOT adjacent (D19 D21 RX0 TX0 D22 D23)."));
  } else {
    Serial.println(F("  Lines floating/unstable -> nothing driving them."));
    Serial.println(F("  Same causes as BOTH LOW above."));
  }

  /* now let the real I2C driver try, so both results appear together */
  Wire.begin(PIN_SDA, PIN_SCL);
  Wire.setClock(100000);
  byte found = 0;
  for (byte a = 1; a < 127; a++) {
    Wire.beginTransmission(a);
    if (Wire.endTransmission() == 0) {
      Serial.printf("  device at 0x%02X\n", a);
      found++;
    }
  }
  Serial.printf("  scan: %d device(s)\n", found);

  delay(3000);
}
