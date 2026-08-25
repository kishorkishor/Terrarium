---
tags: [terrarium, build]
updated: 2026-08-06
---

# Build Stages & Meter Tests

Six stages; each ends with a test. **Never move on with a failing test** — a stage-2 fault
costs minutes, the same fault in stage 6 costs hardware. Full detail in `master-build-guide.html`.

> [!info] Meter modes
> **Continuity ♪** — beeps on a connected path. Power OFF + USB unplugged ONLY.
> **DC Volts ⎓ 20V** — black probe on GND, red on the test point. Safe on live circuits.

## Stage 0 — flash the bare board
Arduino IDE per `firmware/terrarium/README.md`. Wi-Fi creds into `config.h`. Upload, open
the printed IP on the phone — the app runs with zero wiring.
**🔎** 3V3 pin ↔ GND on USB = **3.25–3.35V**. Lower = bad board, use the spare.

## Stage 1 — sensors on breadboard (group A, USB only)
**🔎 before power (continuity):** 3V3↔rail *beep* · GND↔rail *beep* · **3V3↔GND NO beep**
(beep = short — fix first).
**🔎 powered:** sensor VCC↔GND = 3.3V · soil AOUT = **2.2–3.0V dry → 1.0–1.5V in water** ·
float switch beeps in one position only — **write down which**.
App shows temp/RH/lux/soil live. **Calibrate here:** record each soil sensor's dry & wet raw
ADC into `config.h` (per sensor — same batch differs).

## Stage 2 — control signals (group B, USB only)
Label boards A-5V / B-12V first. Wire the five INs + grounds + 10k pulldowns.
**🔎** app MANUAL, toggle each: board IN↔GND = **3.3V ON / 0.0V OFF**.
Stuck 0V = wrong GPIO wire · floats 1–2V when off = missing pulldown.

## Stage 3 — power (group C)
Chain: barrel → fuse → rocker → 12V bus → buck.
**🔎 before wall plug (continuity):** 12Vbus↔GNDbus NO beep · 5Vrail↔GND NO beep.
**🔎 powered walk:** barrel+ 12V → fuse-out 12V (0V = blown) → rocker-out 12V + lamp →
buck IN 12V → **C8: buck OUT = 4.9–5.1V UNLOADED** → then wire C9+ → ESP VIN 5V ·
3V3 3.3V · **Board A DC+ 5V · Board B DC+ 12V** (A at 12V = boards swapped, STOP).
Then unplug USB — board must run from the wall alone.

## Stage 4 — loads (group D, water in cups FIRST)
**🔎 across each load's own terminals:** OFF ≈ 0V · ON = full supply (mist 5V, light/fans 12V).
Half-voltage/weak = wrong board or missing ground. Fan twitches = diode backwards.
**Interlock demo:** lift float from water → both mists die instantly, even in MANUAL. ⭐

## Stage 5 — veroboard (permanent)
ESP32 on 2×19 female headers (removable), copper strips as rails, screw terminals for all
cables, heat-shrink + hot-glue strain relief. Add C19 bond.
**🔎 after every soldering session:** stage-1 trio again + continuity between **every pair of
neighbouring copper strips** near new joints — a beep = solder bridge. Re-run the stage-3 walk.

## Stage 6 — 48-hour soak, then plants
Empty tank, AUTO mode, two days. Watch: stray condensation, tubing creep, RH stuck at 100%
(move BME280 higher, out of mist plume — [[Safety & Care]]). Trigger tank-empty daily; it must
always win. Then substrate, plants, final light position, tune thresholds from the app.

[[Wiring & Power]] · [[Firmware & App]] · [[Pin Map]]
