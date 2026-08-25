/* ============================================================================
 * I2C BUS SCANNER — terrarium bench tool
 *
 * Flash this when a sensor reports NOT FOUND. It asks every possible address
 * on the bus whether anybody is home, then prints what answered.
 *
 * Board: ESP32 Dev Module · Serial Monitor 115200
 *
 * WHAT THE RESULT MEANS
 *   0x76 or 0x77 found ....... BME280 is alive and wired correctly
 *   0x23 (or 0x5C) found ..... BH1750 is alive (0x5C = ADDR pin left floating
 *                              or tied high — pull ADDR to GND for 0x23)
 *   nothing found ............ power or the two bus wires. The sensors are
 *                              almost certainly fine; the wiring is not.
 *                              See the checklist printed after each sweep.
 * ========================================================================== */
#include <Wire.h>

#define PIN_SDA 21
#define PIN_SCL 22

void setup() {
  Serial.begin(115200);
  delay(600);
  Serial.println();
  Serial.println(F("=================================================="));
  Serial.println(F(" I2C SCANNER"));
  Serial.print  (F(" SDA = GPIO")); Serial.print(PIN_SDA);
  Serial.print  (F("   SCL = GPIO")); Serial.println(PIN_SCL);
  Serial.println(F("=================================================="));
  Wire.begin(PIN_SDA, PIN_SCL);
  Wire.setClock(100000);          // slow and forgiving for long jumper wires
}

void loop() {
  byte found = 0;

  Serial.println(F("\nscanning 0x01 .. 0x7E ..."));
  for (byte addr = 1; addr < 127; addr++) {
    Wire.beginTransmission(addr);
    if (Wire.endTransmission() == 0) {
      found++;
      Serial.print(F("  DEVICE at 0x"));
      if (addr < 16) Serial.print('0');
      Serial.print(addr, HEX);
      if (addr == 0x76 || addr == 0x77) Serial.print(F("   <- BME280"));
      if (addr == 0x23)                 Serial.print(F("   <- BH1750"));
      if (addr == 0x5C)                 Serial.print(F("   <- BH1750 (ADDR is high"
                                                      " — tie ADDR to GND for 0x23)"));
      if (addr == 0x3C || addr == 0x3D) Serial.print(F("   <- OLED display"));
      Serial.println();
    }
  }

  if (found == 0) {
    Serial.println(F("  nothing answered."));
    Serial.println(F("\n  Check, in this order:"));
    Serial.println(F("   1. SDA and SCL swapped? SDA=D21, SCL=D22."));
    Serial.println(F("      On this board D21 and D22 are NOT next to each other —"));
    Serial.println(F("      RX0 and TX0 sit between them. Read the silk labels."));
    Serial.println(F("   2. Sensor power on the 3V3 rail (never the ESP32 VIN pin)."));
    Serial.println(F("   3. Breadboard power rails often split in the middle —"));
    Serial.println(F("      bridge the gap, or wire a sensor straight to the pins."));
    Serial.println(F("   4. Module pushed fully into the breadboard."));
  } else {
    Serial.print(F("\n  ")); Serial.print(found);
    Serial.println(F(" device(s) on the bus."));
  }

  delay(4000);
}
