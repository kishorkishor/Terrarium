/* ============================================================================
 * TERRARIUM — WIRING VERIFICATION SKETCH
 * EEE4103 capstone · pin map from build guide §04
 *
 * This is NOT the control firmware. Its only job is to prove that every wire
 * goes where you think it goes. Run it twice:
 *
 *   1. In Wokwi, against diagram.json — confirms the pin map and your logic.
 *   2. On the real board at step 9 of the bench bring-up order (§10),
 *      BEFORE the pump, fogger or grow light are ever connected.
 *
 * Outputs are driven ONE AT A TIME so that if two are swapped, you see it.
 * On real hardware, leave the MOSFET outputs loaded with a plain LED or a
 * resistor for this test. Never the pump.
 *
 * Libraries: OneWire + DallasTemperature (Library Manager).
 * Everything else is built in — no sensor libraries needed, because an I2C
 * scan proves presence and address more reliably than any driver does.
 * ========================================================================== */

#include <Wire.h>
#include <OneWire.h>
#include <DallasTemperature.h>

/* ---- pin map — identical to the real build ------------------------------ */
#define PIN_SDA        21   // BME280 + BH1750 + OLED
#define PIN_SCL        22
#define PIN_SOIL_1     34   // ADC1 — input-only, no pull-up
#define PIN_SOIL_2     35   // ADC1
#define PIN_LEAK       32   // ADC1
#define PIN_DS18B20     4   // 1-Wire, needs external 4.7k to 3V3
#define PIN_FLOAT      27   // INPUT_PULLUP — cannot be 34..39

#define PIN_PUMP       16   // D4184 #1
#define PIN_MIST       25   // D4184 #2 (24 V rail)
#define PIN_FAN_EXH    17   // 4-ch board CH1
#define PIN_FAN_CIRC   18   // 4-ch board CH2
#define PIN_LIGHT      19   // 4-ch board CH3
#define PIN_SPARE      23   // 4-ch board CH4
#define PIN_BUZZER     26

/* ---- simulation-only stand-in -------------------------------------------
 * Wokwi has no BH1750 part, so in the simulator a potentiometer on GPIO33
 * plays the light sensor. In the real build this pin is UNUSED — light
 * comes from the BH1750 on the I2C bus above. The BMP180 in the diagram
 * likewise stands in for the BME280 (same bus, address 0x77 vs 0x76).
 * ---------------------------------------------------------------------- */
#define PIN_SIM_LIGHT  33

/* ---- expected I2C addresses -------------------------------------------- */
#define ADDR_BH1750  0x23
#define ADDR_OLED    0x3C
#define ADDR_BME280  0x76   // some modules ship as 0x77
#define ADDR_BMP180  0x77   // what Wokwi presents in place of the BME280

OneWire oneWire(PIN_DS18B20);
DallasTemperature dsBus(&oneWire);

struct Output { const char *name; uint8_t pin; };

const Output OUTPUTS[] = {
  { "Irrigation pump", PIN_PUMP     },
  { "Mist maker",      PIN_MIST     },
  { "Exhaust fan",     PIN_FAN_EXH  },
  { "Circulation fan", PIN_FAN_CIRC },
  { "Grow light",      PIN_LIGHT    },
  { "Spare channel",   PIN_SPARE    },
  { "Buzzer",          PIN_BUZZER   },
};
const uint8_t N_OUTPUTS = sizeof(OUTPUTS) / sizeof(OUTPUTS[0]);

/* ========================================================================= */

void allOutputsOff() {
  for (uint8_t i = 0; i < N_OUTPUTS; i++) {
    digitalWrite(OUTPUTS[i].pin, LOW);   // latch low first
    pinMode(OUTPUTS[i].pin, OUTPUT);     // then enable the driver
    digitalWrite(OUTPUTS[i].pin, LOW);
  }
}

void scanI2C() {
  Serial.println(F("\n-- I2C bus scan --"));
  uint8_t found = 0;
  for (uint8_t addr = 1; addr < 127; addr++) {
    Wire.beginTransmission(addr);
    if (Wire.endTransmission() == 0) {
      found++;
      Serial.printf("   0x%02X  ", addr);
      switch (addr) {
        case ADDR_BH1750: Serial.println(F("BH1750 light sensor      OK")); break;
        case ADDR_OLED:   Serial.println(F("SSD1306 OLED             OK")); break;
        case ADDR_BME280: Serial.println(F("BME280 air sensor        OK")); break;
        case ADDR_BMP180: Serial.println(F("BMP180 / BME280 alt addr OK")); break;
        default:          Serial.println(F("unexpected device"));           break;
      }
    }
  }
  if (found == 0) {
    Serial.println(F("   NOTHING FOUND."));
    Serial.println(F("   Check: SDA=21 SCL=22, sensors on 3V3 not 5V, GND common."));
  } else {
    Serial.printf("   %u device(s) on the bus.\n", found);
  }
}

void setup() {
  allOutputsOff();                       // before anything else can glitch

  pinMode(PIN_FLOAT, INPUT_PULLUP);      // 34..39 have no internal pull-up

  Serial.begin(115200);
  delay(400);
  Serial.println(F("\n================================================"));
  Serial.println(F(" TERRARIUM — WIRING VERIFICATION"));
  Serial.println(F("================================================"));

  Wire.begin(PIN_SDA, PIN_SCL);
  scanI2C();

  dsBus.begin();
  Serial.printf("\n-- 1-Wire --\n   DS18B20 devices found: %d", dsBus.getDeviceCount());
  Serial.println(dsBus.getDeviceCount() ? F("   OK")
                                        : F("   NONE — check the 4.7k pull-up to 3V3"));

  Serial.println(F("\nOutputs pulse one at a time. Watch which load lights."));
  Serial.println(F("If two are swapped, you will see it here — not in the tank.\n"));
}

void readInputs() {
  int soil1 = analogRead(PIN_SOIL_1);
  int soil2 = analogRead(PIN_SOIL_2);
  int leak  = analogRead(PIN_LEAK);
  int lux   = analogRead(PIN_SIM_LIGHT);
  bool floatOk = digitalRead(PIN_FLOAT);   // HIGH = pulled up = contact open

  dsBus.requestTemperatures();
  float soilTemp = dsBus.getTempCByIndex(0);

  Serial.println(F("-- inputs -------------------------------------"));
  Serial.printf("   Soil 1     GPIO34   %4d\n", soil1);
  Serial.printf("   Soil 2     GPIO35   %4d\n", soil2);
  Serial.printf("   Leak       GPIO32   %4d   %s\n", leak,
                leak > 1500 ? "** WATER DETECTED **" : "dry");
  Serial.printf("   Light      GPIO33   %4d   (sim pot standing in for BH1750)\n", lux);
  Serial.printf("   Float      GPIO27   %s\n",
                floatOk ? "open   (reservoir OK)" : "closed (RESERVOIR EMPTY)");

  if (soilTemp == DEVICE_DISCONNECTED_C) {
    Serial.println(F("   DS18B20    GPIO4    DISCONNECTED"));
  } else {
    Serial.printf("   DS18B20    GPIO4    %.2f C\n", soilTemp);
  }

  /* Sanity checks that catch the two most expensive wiring mistakes. */
  if (soil1 > 4090 || soil2 > 4090 || leak > 4090) {
    Serial.println(F("   !! An analog input is pinned at full scale."));
    Serial.println(F("   !! Sensor is probably on 5V. Move it to 3V3 — see check 03/04."));
  }
  Serial.println();
}

void pulseOutputs() {
  Serial.println(F("-- outputs ------------------------------------"));
  for (uint8_t i = 0; i < N_OUTPUTS; i++) {
    Serial.printf("   ON  -> %s (GPIO%u)\n", OUTPUTS[i].name, OUTPUTS[i].pin);
    digitalWrite(OUTPUTS[i].pin, HIGH);
    delay(800);
    digitalWrite(OUTPUTS[i].pin, LOW);
    delay(400);
  }
  Serial.println(F("   all outputs LOW\n"));
}

void loop() {
  readInputs();
  pulseOutputs();
  delay(1500);
}
