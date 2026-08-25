---
tags: [terrarium, hardware]
updated: 2026-08-06
---

# Pin Map — ESP32 DevKit V1 (WROOM-32)

Matches `firmware/terrarium/config.h` exactly. Find pins by **printed label** — board
variants shuffle positions. GPIO16 is printed **RX2** on 30-pin boards, **16** on 38-pin.

| GPIO | Silk | Connects to | Mode | Notes |
|---|---|---|---|---|
| 21 | D21 | BME280 + BH1750 SDA | I2C | shared bus |
| 22 | D22 | BME280 + BH1750 SCL | I2C | shared bus |
| 34 | D34 | Soil 1 AOUT | analog in | ADC1, input-only |
| 35 | D35 | Soil 2 AOUT | analog in | ADC1, input-only |
| 32 | D32 | Leak sensor AOUT | analog in | ADC1 · optional |
| 27 | D27 | Float switch (other leg → GND) | INPUT_PULLUP | can't be 34–39 (no pullup there) |
| 16 | **RX2** | Board A IN1 — watering mist | out | WROOM only (WROVER uses 16/17!) |
| 25 | D25 | Board A IN2 — humidity mist | out | |
| 19 | D19 | Board B IN1 — grow light | PWM out | dimmable |
| 17 | TX2 | Board B IN2 — exhaust fan | out | |
| 18 | D18 | Board B IN3 — circulation fan | out | |
| 26 | D26 | Buzzer S | out | optional |
| 4 | D4 | *(reserved: DS18B20 + 4.7k pullup)* | 1-Wire | future |
| 23 | D23 | *(spare)* | — | |
| VIN | VIN | Buck 5V out | power | + 1000µF cap |
| 3V3 | 3V3 | Sensor rail | power | all sensors, ~45mA total |

## Hard rules

> [!danger] Never use
> **GPIO 6–11** (SPI flash — board won't boot) · **0, 2, 5, 12, 15** (boot straps) ·
> **1, 3** (USB serial)

- **ADC2 dies when Wi-Fi is on** — every analog input here is deliberately ADC1 (32/34/35). Silent wrong-numbers bug otherwise.
- GPIO34–39: input-only, no internal pull-up → float switch lives on 27 instead.
- All five MOSFET INs get a **10kΩ pulldown to GND** — stops boot-glitch pulses (pump firing during reset).

Wiring detail: [[Wiring & Power]] · code: [[Firmware & App]]
