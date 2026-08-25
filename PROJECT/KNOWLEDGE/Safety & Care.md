---
tags: [terrarium, safety]
updated: 2026-08-06
---

# Safety & Care

## The five hardware rules

> [!danger] Break one and something dies
> 1. **Sensors run on 3.3V, never 5V** — 5V into an ADC pin kills it
> 2. **One common ground** — every GND connects, no exceptions
> 3. **Measure 5.00V at the buck before it touches the ESP32** (stage-3 step C8)
> 4. **Capacitor stripe (−) faces GND** — backwards = pop
> 5. **Board A = 5V, Board B = 12V** — tape-label on arrival; swapped = dead mist drivers

Two habits: **unplug before rewiring, every time** · **never run a mist disc dry** (burns out
in minutes — water in the cup first).

## The interlock (the capstone's safety story)
Float switch says tank empty → **both mist channels forced OFF, even in MANUAL mode** —
no bypass exists in the firmware. Buzzer sounds if fitted. Demo: lift the float out of water
mid-misting; everything water-related dies instantly. Recovers on refill.

## Water & plant gotchas
- **Distilled water in the mist cups** — Dhaka tap water's minerals clog the ultrasonic disc in
  days, then blow white dust over the glass. Tap water is fine for plain irrigation only.
- **BME280 placement**: high in the airspace, away from glass, OUT of the mist plume —
  otherwise it reads 100% RH forever and misting never releases. Watch for this in the
  48-hour soak (stage 6).
- **Soil sensors**: conformal-coat / nail-polish the **upper electronics end** only — never the
  sensing paddle. Uncoated boards corrode at the soil line within weeks.
- **Silicone sealant**: aquarium-safe, 100% silicone, NO anti-mould/biocide additives —
  bathroom sealant leaches and kills moss/plants. Cure 48h with lid off before planting.
- Electronics box mounted **above the water line**, cables entering from below.
- Peristaltic/mist tubing = wear parts; keep spares.

## For the report's evaluation section
- Reference thermometer/hygrometer (HTC-2 ~৳350) → mean absolute error vs BME280
- 20mL syringe → mL per watering burst ×10 runs = repeatability figure
- Response time: command → actuator, phone stopwatch
- The interlock trigger test = the safety-response metric, run it on camera

[[Build Stages & Meter Tests]] · [[Design Decisions]]
