---
tags: [terrarium, hardware]
updated: 2026-08-06
---

# Wiring & Power

Full interactive version: `TERRARIUM/master-build-guide.html` — 63 clickable wires, each
with its own colour; click any wire (or checklist row) to trace it. This note is the summary.

## Architecture

```
mains → 12V 5A adapter → barrel jack → FUSE 3A → rocker switch → 12V BUS
   12V BUS ─→ Board B DC+ (F5305S #2)  → grow light · exhaust fan · circ fan
   12V BUS ─→ BUCK LM2596S → 5.0V ─→ ESP32 VIN
                              5.0V ─→ Board A DC+ (F5305S #1) → mist 1 · mist 2
   ESP32 3V3 → sensor rail → BME280 · BH1750 · soil ×2 · float · (leak)
   ONE COMMON GROUND: adapter− · buck− · both boards · ESP32 · sensor rail (C19 bond)
```

> [!warning] The boards look identical
> Tape-label them **A-5V** and **B-12V** the moment they arrive. Swapping them puts 12V
> into the mist drivers. Meter check in stage 3 catches it: Board A DC+ must read **5V**.

## Wire groups (checklist IDs in the master guide)

- **A1–A19** — sensors, all on the 3.3V rail. BH1750 ADDR → GND (locks 0x23).
- **B1–B8** — control: 16→A·IN1, 25→A·IN2, 19→B·IN1, 17→B·IN2, 18→B·IN3, signal
  grounds chained, **10k pulldown at every IN (×5)**.
- **C1–C19** — power chain in order; **C8 = measure 5.00V before the ESP32 is connected**.
  C18 = rocker pin 3 → GND (lights its lamp). C19 = sensor rail → GND bus bond.
- **D1–D12** — loads. Fans get **1N5819 flyback diodes, stripe to the + wire**.
- **E1–E6** — optional leak sensor + buzzer.

## Values

| What | Value | Recognise |
|---|---|---|
| Pulldowns ×5 | 10kΩ ¼W | brown-black-orange-gold |
| DS18B20 pullup (future) | 4.7kΩ | yellow-violet-red-gold |
| C1 C2 C3 | 1000µF 25V | stripe = − leg → faces GND |
| Fan diodes | 1N5819 | silver band = cathode → + wire |
| Fuse | 3A fast, 5×20mm | first thing after barrel jack |
| Buck out | 5.0V ±0.1 | measured unloaded (C8) |
| Wire | 18AWG power · 22AWG signal | |

## Recheck fixes (2026-08-06)

1. Adapter→barrel had no link drawn — added ("plugs in").
2. Rocker pin 3 was floating — added C18 so the lamp works.
3. Sensor GND rail now bonds directly to GND bus (C19) instead of only through the ESP32's plane.

See [[Pin Map]] · [[Build Stages & Meter Tests]] · [[Safety & Care]]
