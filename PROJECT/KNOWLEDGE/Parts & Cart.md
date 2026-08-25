---
tags: [terrarium, parts]
updated: 2026-08-06
---

# Parts & Cart

Verified shared cart **354660** — RoboticsBD — **৳9,299**. See [[Suppliers & Links]] for the cart URL.

## In the cart ✓

| Item | Qty | ৳ | Role |
|---|---|---|---|
| [ESP32 DevKit V1 CP2102](https://store.roboticsbd.com/development-boards/2267-esp32-dev-board-cp2102-robotics-bangladesh.html) | 2 | 1,300 | brain + spare — [[Pin Map]] |
| [GY-BME280 3.3V](https://store.roboticsbd.com/sensors/1946-gy-bme280-33v-temperature-and-humidity-sensor-robotics-bangladesh.html) | 2 | 840 | air temp + RH (I2C 0x76) + spare |
| [BH1750FVI](https://store.roboticsbd.com/sensors/429-bh1750fvi-digital-light-intensity-sensor-robotics-bangladesh.html) | 1 | 235 | lux (I2C 0x23, ADDR→GND) |
| [Capacitive soil sensor](https://store.roboticsbd.com/temperature-humidity/1042-capacitive-soil-moisture-sensor-robtoics-bangladesh.html) | 2 | 390 | GPIO34/35 — **3.3V only** |
| [52mm PP float switch](https://store.roboticsbd.com/sensors/1677-52mm-pp-liquid-water-level-sensor-horizontal-float-switch-down-robotics-bangladesh.html) | 1 | 299 | tank-empty interlock, GPIO27 |
| [Water level sensor ৳49](https://store.roboticsbd.com/sensors/1935-water-level-sensor-gold-coating-robotics-bangladesh.html) | 1 | 49 | leak alarm (optional, GPIO32) |
| [USB mist maker kit](https://store.roboticsbd.com/arduino-shield/2426-usb-mini-humidifier-mist-maker-and-driver-circuit-board-diy-kits-robotics-bangladesh.html) | 2 | 760 | watering (GPIO16) + humidity (GPIO25) |
| [MOSFET F5305S 4-ch](https://store.roboticsbd.com/electronics-module/2940-mosfet-f5305s-4-channel-pulse-trigger-switch-controller-robotics-bangladesh.html) | 1 | 550 | **need 2** — see below |
| [12V fan 40mm](https://store.roboticsbd.com/3d-printer/727-12v-mini-cooling-fan-40x40x10mm-robotics-bangladesh.html) | 2 | 300 | exhaust (17) + circulation (18) |
| [12V 5A adapter](https://store.roboticsbd.com/chargers-balancer/3020-12v-5a-power-supply-adapter-robotics-bangladesh.html) | 1 | 450 | main power |
| [LM2596S buck 12V→5V](https://store.roboticsbd.com/power-module-adapter/2222-lm2596s-dc-dc-24v12v-to-5v-5a-step-down-power-supply-buck-converter-charging-module-robotics-bangladesh.html) | **3** | 1,140 | only need 2 — drop one, −৳380 |
| [KCD1-1 illuminated rocker](https://store.roboticsbd.com/electronic-switches/4048-kcd1-1-bistable-illuminated-rocker-switch-red-1521mm-3pin-robotics-bangladesh.html) | 1 | 30 | 12V master switch |
| [BLX-A fuse holder](https://store.roboticsbd.com/components/2055-blx-a-cover-with-fuse-holder-robotics-bangladesh.html) | 2 | 60 | 3A fuse goes FIRST after barrel |
| [1000µF 25V caps](https://store.roboticsbd.com/capacitor/4225-1000uf-25v-capacitor-robotics-bangladesh.html) | 3 | 33 | C1 C2 C3 |
| [10k + 4.7k resistor packs](https://store.roboticsbd.com/components/245-34-resistor-robotics-bangladesh.html#/25-resistor_pack_of_5-10_k) | 20 | 100 | pulldowns (way over-bought, fine) |
| [Barrel jack female](https://store.roboticsbd.com/tools-accessories/1587-barrel-connector-female-robotics-bangladesh.html) | 2 | 76 | adapter connection |
| [Veroboard line](https://store.roboticsbd.com/robotics-parts/1363-veroboard-line-type-robotics-bangladesh.html) | 3 | 105 | permanent board |
| [Female headers](https://store.roboticsbd.com/connector/1122-female-pin-header-254mm-pitch-blue-robotics-bangladesh.html) | 4 | 80 | ESP32 socket (2×19) |
| [Screw terminals 2-pin](https://store.roboticsbd.com/tools-accessories/1184-2-pin-pitch-50mm-straight-pin-screw-pcb-terminal-block-connector-robotics-bangladesh.html) | 16 | 160 | every cable lands on one |
| [Jumper M-M 40pc](https://store.roboticsbd.com/robotics-parts/31-3-jumper-wire-40-pcs-set-20cm-robotics-bangladesh.html) | 1 | 100 | breadboard stage |
| [Heat shrink A/B/C](https://store.roboticsbd.com/assorted-kit/984-99--heat-shrink-tube-robotics-bangladesh.html) | 30 | 100 | every joint |
| [Active buzzer module](https://store.roboticsbd.com/audio-voice-piezo-buzzer-speech-module/2301-active-buzzer-module-robotics-bangladesh.html) | 1 | 52 | optional alarm (GPIO26) |
| [ESP32-CAM + MB shield](https://store.roboticsbd.com/development-boards/4493-esp32-cam-wifi-bluetooth-development-board-with-mb-programmer-shield-robotics-bangladesh.html) | 1 | 1,650 | optional camera — standalone Wi-Fi |

## ⚠ Fix before ordering

- **DELETE** WaveShare liquid level ৳440 — duplicate of the ৳49 sensor
- **REDUCE** buck 3 → 2 (−৳380)
- **ADD** [2nd F5305S](https://store.roboticsbd.com/electronics-module/2940-mosfet-f5305s-4-channel-pulse-trigger-switch-controller-robotics-bangladesh.html) ৳550 — Board A runs 5V (mist), Board B runs 12V (light+fans); one board cannot do both
- **ADD** [1N5819 ×10](https://store.roboticsbd.com/diode/3376-1n5819-schottky-diode-40v-1a-robotics-bangladesh.html) ৳30 — fan flyback diodes, mandatory
- **ADD** [M-F jumper wires](https://store.roboticsbd.com/connector/2104-male-to-female-jumper-wires-40-pin-30cm-robotics-bangladesh.html) ৳100 — sensors have male pins
- **ADD** [breadboard 830pt](https://store.roboticsbd.com/components/133-breadboard-full-size-bare-830-tie-points-robotics-bangladesh.html) ৳150 — stages 1–4 happen on it

## Not from RoboticsBD

- Glass fuses 3A 5×20mm + 18AWG wire (red/black 3m each) — **Katabon**
- Grow light: 12V 5050 strip, cool white, ~1m — **Daraz**, buy LAST after measuring tank
- [Multimeter UT33B+](https://store.roboticsbd.com/digital-multimeters-roboticsbd/910-ut33b-digital-multimeter-robotics-bangladesh.html) ৳620 if not owned — required for [[Build Stages & Meter Tests]]
- Micro-USB **data** cable

Related: [[Design Decisions]] for why each part beat its alternatives.
