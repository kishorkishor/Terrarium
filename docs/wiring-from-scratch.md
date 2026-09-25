# Wiring from scratch (bench build)

Date: 2026-09-25. Pins match `firmware/terrarium/config.h`. Previous bench record: `wiring-as-built.html` (2026-08-26).

Rules that never change:
- Sensors run on **3V3 only**. Never 5 V or VIN to a sensor.
- **Power off** (adapter unplugged, USB unplugged) while wiring. Plug in only at the check steps.
- On the ESP32 DevKit V1, **D21 and D22 are not next to each other**. The row reads: D19, D21, RX0, TX0, D22, D23.
- Every module must be **soldered** (header or wire). Wires pushed into bare holes fail.
- The MOSFET board's opto inputs are wired **active-low**: the "PWM n" terminal sits on 5 V and the "GND n" terminal is the ESP32 signal pin. Firmware has `MOSFET_ACTIVE_LOW 1`. No 10 k pulldowns.

## Step 0: rails
| Wire | From | To |
|---|---|---|
| A1 | ESP32 3V3 | red rail (sensor supply) |
| A2 | ESP32 GND | blue rail |

## Step 1: float switch (tank-empty interlock, 2 wires, no polarity)
| Wire | From | To |
|---|---|---|
| S1 | float wire A | **D27** |
| S2 | float wire B | blue rail (GND) |

Firmware reads D27 with an internal pull-up. Closed to GND = "tank empty" (`FLOAT_EMPTY_STATE LOW`). If the app shows the reverse of reality, flip that one line in config.h, don't rewire.

## Step 2: BME280 (GY-BME/PM 280, 6 pin)
| Wire | From | To |
|---|---|---|
| B1 | VCC | red rail (3V3) |
| B2 | GND | blue rail |
| B3 | SDA | **D21** |
| B4 | SCL | **D22** |
| B5 | CSB | leave empty (or red rail; both give I2C mode) |
| B6 | SDO | leave empty (or blue rail; both give address 0x76) |

**Optional second BME280 (room / reference air, added 2026-09-25).** Same as above except **SDO → red rail (3V3)**, which moves it to address 0x77. Firmware `ENABLE_BME280_2 1` reads it as "room" (temp2/hum2 in the status, "Room (2nd sensor)" card in the app). It never drives the mist; only the 0x76 sensor does. Both verified 2026-09-25 on the new board: 0x76 + 0x77 answer, chip id 0x60 each, readings agree within 0.1 °C.

## Step 3: BH1750 light sensor
| Wire | From | To |
|---|---|---|
| C1 | VCC | red rail |
| C2 | GND | blue rail |
| C3 | SDA | D21 (same wire/row as BME280) |
| C4 | SCL | D22 |
| C5 | ADDR | blue rail (address 0x23) |

**Check A (sensors):** plug USB in, say "check". Expected: 0x76 answers with chip id 0x60, 0x23 answers.

## Step 4: soil probes, leak sensor, buzzer
| Wire | From | To |
|---|---|---|
| D1–D3 | Soil 1 VCC / GND / AOUT | red / blue / **D34** |
| D4–D6 | Soil 2 VCC / GND / AOUT | red / blue / **D35** |
| E1–E3 | Leak VCC / GND / S | red / blue / **D32** |
| F1–F3 | Buzzer VCC / GND / I/O | red / blue / **D26** |

Soil probe wires must be firm. A loose probe 1 reads 0–4095 and the firmware waters.

## Step 5: power and MOSFET board A (5 V side)
| Wire | From | To |
|---|---|---|
| P1 | 12 V adapter plug | buck converter barrel IN |
| P2 | buck 5 V OUT | Board A DC+ |
| P3 | buck GND OUT | Board A DC− |
| P4 | Board A DC− | blue rail (common ground with the ESP32; required) |
| G1 | ESP32 **VIN** (5 V) | Board A **PWM2** terminal |
| G2 | ESP32 **D16** (silk RX2) | Board A **GND2** terminal |
| G3 | Board A PWM2 | Board A **PWM1** (short jumper, carries 5 V on) |
| G4 | ESP32 **D25** | Board A **GND1** terminal |

Measure the buck output before P2: it must read 5.0–5.2 V.

## Step 6: mist makers (disc under water before power, always)
| Wire | From | To | Firmware |
|---|---|---|---|
| H1, H2 | Board A OUT2+ / OUT2− | mist maker 1 + / − | `PIN_MIST_WATER` 16, watering |
| H3, H4 | Board A OUT1+ / OUT1− | mist maker 2 + / − | `PIN_MIST_HUM` 25, humidity |

**Check B (actuators):** flash terrarium firmware, open TerrariumTester, toggle each mist manually, watch the float reading with the switch held up and down.

## Later (Board B, 12 V side, not bought yet)
Grow light → D19, exhaust fan → D17, circulation fan → D18, each through a second MOSFET board fed from 12 V, with a 1N5819 flyback diode across each fan. Chain: adapter → 3 A fuse → rocker switch → 12 V bus. DS18B20 reserved on D4 with 4.7 k pull-up.

## Free pins after this build
D17, D18, D19 (reserved above), D4, D23, D13, D12, D14, D15, D5, D33, VN, VP.
