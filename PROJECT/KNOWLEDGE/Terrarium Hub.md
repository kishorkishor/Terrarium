---
tags: [terrarium, hub]
updated: 2026-08-06
---

# 🌿 Terrarium Hub

**IoT-Based Automated Tropical Terrarium** — AIUB EEE4103 capstone, Summer 2025-26.
ESP32 senses air temp/RH, soil moisture ×2, lux, tank level; drives 2 mist makers
(watering + humidity), grow light, 2 fans — controlled from an Android phone via the
board's own web app. All automation runs locally; Wi-Fi loss changes nothing.

## Notes

- [[Parts & Cart]] — the final verified RoboticsBD cart + what to still add
- [[Pin Map]] — every GPIO, and the pins that must never be used
- [[Wiring & Power]] — rails, the two switch boards, all component values
- [[Build Stages & Meter Tests]] — the 6-stage build order with multimeter checks
- [[Firmware & App]] — what the code does, how to flash, how the phone app works
- [[Simulation & Testing]] — Wokwi projects + the offline dashboard preview
- [[Design Decisions]] — why every major choice went the way it did
- [[Safety & Care]] — the 5 hardware rules + plant/water gotchas
- [[Suppliers & Links]] — shops, carts, contacts

## Files in `Desktop/TERRARIUM/`

| File | What it is |
|---|---|
| `master-build-guide.html` | **THE build document** — interactive diagram (63 clickable wires, clickable shop links), 6 stages, checklist |
| `terrarium-build-guide.html` | Full research guide — parts, prices, compatibility checks, tutorials |
| `wiring-diagram.html` | Earlier simplified-build wiring page (superseded by master) |
| `terrarium-component-list.pdf` | Shop-ready purchase PDF, exact specs, no prices |
| `firmware/terrarium/` | The real firmware: `terrarium.ino`, `config.h`, `webui.h`, `README.md` |
| `firmware/dashboard-preview.html` | Phone app + simulated tank, runs anywhere, speed slider |
| `wokwi/` | Wiring-verification sketch + diagram for wokwi.com |
| `wokwi/logic-sim/` | Zero-library control-logic sim on emulated ESP32 |
| `ffffff…(1)(2).docx` | The original course proposal (survey, lit review, Gantt) |

## Status

- [x] Research, BOM, compatibility audit
- [x] Firmware written (app, hysteresis, interlock)
- [x] Simulations ready (Wokwi + dashboard preview)
- [x] Cart verified (৳9,299) — pending: +1 F5305S, 1N5819, M-F jumpers, breadboard; −WaveShare
- [ ] Parts ordered / received
- [ ] Stage 0–1: flash + sensors on breadboard
- [ ] Stage 2–3: control + power
- [ ] Stage 4–6: loads, veroboard, 48h soak
- [ ] Enclosure, substrate, plants
- [ ] Report: calibration table, irrigation volume, MAE vs reference meter

## Tools
- **`TerrariumConsole.exe`** — one-file setup/flash/diagnose tool for any laptop → [[Firmware & App]]
- `tools/arduino-cli.exe` + `arduino-cli.yaml` — headless compile/upload, reuses the IDE's core
- `3d/*.scad` — every printable part; OpenSCAD CLI exports STLs → [[Wiring & Power]]
