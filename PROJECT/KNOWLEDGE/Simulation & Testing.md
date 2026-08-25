---
tags: [terrarium, simulation]
updated: 2026-08-06
---

# Simulation & Testing

Three sims, each proving a different thing. None replaces the multimeter steps in
[[Build Stages & Meter Tests]] — Wokwi simulates logic, **not electricity** (it will happily
"survive" 12V into a 3.3V pin).

## 1 · Control-logic sim — `wokwi/logic-sim/`
Runs the REAL control logic on emulated ESP32 silicon at [wokwi.com](https://wokwi.com/projects/new/esp32)
(ESP32 → Arduino → paste both files). **Zero libraries — cannot fail to compile.**
- Knobs: SOIL1/SOIL2 down = dry → watering fires · HUMIDITY down → mist fires ·
  LIGHT down → grow light on · FLOAT slide LEFT = tank empty → mists blocked
- Clock runs **120×** → a full day in ~12 min · Serial 115200 shows every decision
- Same burst/soak/hysteresis/interlock code as the firmware

## 2 · Wiring-verification sketch — `wokwi/sketch.ino`
Not control firmware — proves wires go where you think. I2C scan names each address,
inputs print with GPIO numbers, **outputs pulse one at a time** so a swapped pair is obvious.
**Run it twice: once in Wokwi, again on the real board at stage 2** before any load power.

## 3 · Phone-app preview — `firmware/dashboard-preview.html`
Double-click, runs anywhere (laptop/phone), no hardware. The exact dashboard UI with a
simulated tank behind it: speed slider to 300× = watch a whole day (soil dries → burst →
soak → light follows photoperiod). Buttons: *Empty the tank* (interlock demo), *Dry the soil*,
*Make it dark*. **Presentation material** — examiner sees a day of automation in a minute.

## Free-tier limits worth knowing
- Wokwi free = `Wokwi-GUEST` Wi-Fi, **outgoing only** — you cannot open the ESP32's web app
  from your browser (needs paid Private Gateway → `localhost:9080`). That's exactly why the
  dashboard-preview file exists.
- Wokwi has no BME280/BH1750 parts — pots stand in on the sim's GPIO32/33; the real build
  reads them over I2C instead.
- Electrical "will this burn" questions → [Falstad CircuitJS](https://www.falstad.com/circuit/), or
  just follow the meter steps.

[[Firmware & App]] · [[Wiring & Power]]
