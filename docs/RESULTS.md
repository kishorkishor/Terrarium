# Terrarium brain: everything so far (as of 2026-09-27 03:10)

One file that holds the state of the project: what we are building, what has been measured on the real box, where every number lives, and what is left. Nothing in the results sections is simulated.

## 1. What we are building

A small "brain" for the terrarium that runs on the ESP32 and has three jobs:

1. **Learns the box.** Six weights, updated after every reading with recursive least squares, working in absolute humidity. Each weight means something physical: mister strength, how leaky the box is, fan effect, plant/room offset. Two learners: fast (about 40 min memory) and slow (about 7 h, the memory of the healthy box).
2. **Plans mist bursts** instead of reacting. Before a burst it simulates candidate lengths 10 min ahead and picks the shortest that reaches 88 %.
3. **Notices faults and repairs itself.** Sensor lost or stuck; part checks after each burst; a CUSUM watchdog on prediction error; "suspect loss" → 4 min quiet watch → mist test → verdict (lid open / leak, dead mister, or false alarm); backup mister switchover; learned misting rhythm when blind; snapshot and rollback of its own weights.

Code: `tools/brain/brain.py` (the brain), `tools/brain/sim_box.py` (simulator, constants now set from measured data), `tools/brain/run_demo.py` (logic test). Design notes: `docs/brain-design.md`. Baseline it is compared against: the firmware's on/off rule, mist below 75 %, off at 90 %, 5 min burst cap, 3 min cooldown.

**Research gap (three Consensus Deep Searches, 24 Sep, links in `docs/publication-plan.md`):** on-device learning exists for images/audio/solar/irrigation but not for humidity control; predictive humidity control exists in simulation, on PCs and PLCs, not on a cheap microcontroller driving an ultrasonic mister; nobody has measured a learning controller against the plain rule on the same hardware, or used one model for both control and fault diagnosis there.

## 2. The rig

- Acrylic box about 11 × 9 × 3 in, lid propped open (1 cm on 26 Sep, 4 cm on 27 Sep).
- ESP32 DevKit V1 on USB (COM3). Lab firmware `firmware/lab/lab.ino`: streams both sensors at 1 Hz with humidity to 0.01 %, accepts commands (MODE OFF/MANUAL/RULES, MIST A/B, SET, MARK), 15 s hardware watchdog, rejects nonsense readings, retries lost sensors every 5 s, falls back to the second sensor if the control sensor dies.
- BME280 "IN" (0x76) inside the box, high, shielded. BME280 "OUT" (0x77, SDO→3V3) on the table about 30 cm away. Both on SDA D21 / SCL D22 / 3V3.
- One ultrasonic mist maker in the box, channel A (GPIO25 → MOSFET board OUT1, active-low).
- Laptop tools: `tools/lab/logger.py` (records everything, runs protocols, live page at localhost:8765), `tools/lab/brain_runner.py` (runs the brain on the laptop: reads the inside sensor every 5 s, sends mist commands over USB), `tools/lab/analyze_step.py`, `tools/lab/analyze_session.py`.
- No plants inside during these sessions.

Wiring guide: `docs/wiring-from-scratch.md`. Test sheet: `docs/lab-tests.md`. Data index: `data/README.md`.

## 3. Measured results

### 3.1 Box characterisation, 25 Sep (`docs/lab-step-2026-09-25.md`)
Lid closed, one mister, three rounds of: 5 min quiet, mist until humidity stops rising, 20 min off. 4825 readings, 100 % good.

| Round | Start %RH | Peak %RH | Mist time | Mister strength (g/m³/s, dry-air) | Drop in 20 min |
|---|---|---|---|---|---|
| 1 | 83.0 | 89.0 | 110 s | 0.086 | 1.8 % |
| 2 | 86.9 | 89.5 | 97 s | 0.110 | 2.0 % |
| 3 | 87.1 | 89.9 | 104 s | 0.099 | 1.2 % |
| mean ± sd | | 89.5 ± 0.4 | 104 ± 7 s | 0.098 ± 0.012 | 1.7 ± 0.4 % |

Findings: the mister hits a hard ceiling near 89.5 %RH in under 2 min, repeatable to 0.4 %; longer bursts add droplets, not humidity (the rule's 5 min cap is wasteful; 2–3 min is enough). The closed box barely dries with the room at 75 %. Misting warms the air 0.2–0.4 °C while the disc runs, then it cools 0.5 °C as fog evaporates. Earlier the same day, with one end of the box open (`docs/box-experiment-2026-09-25.md`): 88 → 83 % in 11 min, mister strength 0.17, and the inside sensor fogged (179 °C / 100 %) twice → mount it high with a shield.

Figure: `docs/figures/lab-step-2026-09-25-1910.png`. Data: `data/lab-step-2026-09-25-1910.csv` (+ `.fit.json`).

### 3.2 Rule vs brain with injected faults, 26 Sep 22:22–23:24 (`docs/lab-session-2026-09-26.md`)
Lid 1 cm. Brain on the laptop, pre-seeded from 3.1, learning throughout.

| Block | Minutes | In 75–90 % | Mist min | Bursts |
|---|---|---|---|---|
| Old rule | 15.1 | 96.5 % | 5.0 | 1 |
| Brain, incl. lid-off fault | 37.1 | 95.4 % | 1.1 | 3 |
| Brain, wet-sensor test | 10.1 | 59.3 % | 1.5 | 1 |

| Injected fault | Brain's response |
|---|---|
| Lid fully off (23:02:11) | "suspect loss" after **1 s**; quiet watch; three 35 s test bursts; **"lid open / leak" after 400 s**; kept controlling with the fast model meanwhile |
| Lid back (23:10:47) | recovered; fault held until the box behaved normally for 10 min (by design) |
| Wet tissue on sensor (23:12:50) | sensor did not stick, but it **locked the I2C bus**; the watchdog rebooted the chip in 15 s and re-found both sensors in 1 s |
| Tissue removed (23:16:30) | reading fell 90 → 74 % in 40 s (sensor drying); brain raised "suspect loss", tested, and **cleared it as "false alarm, nothing wrong" at 23:23:03** |

Model: leak weight −0.036 (seed, closed box) → −0.131 after 25 min with the gap, before any fault: the slow learner re-fitted the leakier box on its own.

Figure: `docs/figures/session-2026-09-26.png`.

### 3.3 Rule vs brain, alternating blocks, 27 Sep 00:55–02:55 (`docs/lab-session-2026-09-27.md`)
Lid 4 cm, wiring redone, 100 % good readings in all four blocks.

| Block | Start | In 75–90 % | Below 75 % | Mist min | Bursts | RH range |
|---|---|---|---|---|---|---|
| Old rule | 00:55 | 98.9 % | 1.1 % | 10.2 | 3 | 72.4–87.1 |
| Brain | 01:25 | **100.0 %** | 0.0 % | **0.0** | 0 | 76.8–82.0 |
| Old rule | 01:55 | 99.9 % | 0.1 % | 4.4 | 1 | 75.0–88.0 |
| Brain | 02:25 | **100.0 %** | 0.0 % | **0.0** | 0 | 79.2–87.9 |
| **Rule, 60 min** | | 99.4 % | | **14.6** | 4 | |
| **Brain, 60 min** | | **100.0 %** | | **0.0** | 0 | |

Reading: with the gap and the water surface, the box settles at 78–80 %RH by itself, inside the band. The rule waits for 75 %, then mists a full 5 min to 88 % (the ceiling; 90 % is never reached), the box drains back in ~10 min, repeat. The brain plans a burst only when its model says one is needed; tonight it never was. Same box, alternating blocks, outside humidity drifting 73 → 71 %. One chip crash at 02:50 (interrupt watchdog); the laptop runner recovered it in a second, 6 s of data lost.

Figure: `docs/figures/session-2026-09-27.png`. Metrics: `data/session-2026-09-27.json`.

### 3.4 Simulation (logic test only, not evidence)
`tools/brain/run_demo.py`, 76 simulated hours with four faults, drift and a memory glitch: brain 99.2 % in band vs rules 93.1 %, 282 vs 353 mist-min/day, all faults named correctly on 7 random seeds, no false alarms. Constants in `sim_box.py` now use the measured mister strength (0.17 open / 0.10 closed) and decay. Figure `docs/figures/brain-sim-demo.png`.

## 4. What the results support, and what they do not

**Supported by measured data**
- One learned model, seeded from a 90 min step test, controls a real box and holds the target band as well as or better than the rule (100 % vs 99.4 % over the alternating hour; 95.4 % vs 96.5 % over the fault session where the brain also carried a fault).
- It uses far less water: 0 vs 14.6 mist-min per hour (27 Sep); 1.1 vs 5.0 in the 26 Sep blocks.
- It names a lid-open fault by itself (400 s) after suspecting it in 1 s, keeps controlling meanwhile, and clears its own false alarm by testing (6.5 min).
- It re-fits its model when the box changes (leak weight 3.6× within 25 min of the gap).
- The chip survives a wet sensor: bus lock-up → watchdog reboot → sensors back in 1 s.

**Not yet supported**
- Burst planning on the real box outside a fault: the brain never needed to mist in the alternating session. The only real-box bursts it planned were the three 35 s test bursts during the lid fault (26 Sep). A drier room or a fan schedule would exercise it.
- Running on the chip: the brain ran on the laptop over USB (5 s steps). The port is straightforward (6 weights, two 6×6 matrices) but not done.
- Dead-mister fault and backup switchover: not injected on the real box.
- Days-long behaviour, plants inside, more than one box: not tested.

## 5. Hardware lessons (worth a paragraph in methods)
1. The BME280 "179.4 °C / 100 %" state is the chip at power-on defaults: register writes fail on a marginal bus or after hot-replugging its clock wire, while single-byte reads still work. Power cycling does not fix it; solid SDA/SCL wiring does.
2. Two sensors' SCL wires sharing one breadboard row failed intermittently for hours; a clean rewire gave 100 % good data for 3 h.
3. Tearing the ESP32 I2C driver down and up in firmware (Wire.end/begin) crashed the chip (StoreProhibited); removed.
4. A wet BME280 locks the bus; a hardware watchdog plus re-probing recovers it without a reboot of the laptop side.
5. Corrupted reads can pass naive sanity checks (100.00 %RH, 0 °C); the filter now requires plausible temperature, pressure and step size.

## 6. What is left
| Item | Who | Box time |
|---|---|---|
| Port `brain.py` to C in `firmware/lab` and check it reproduces the laptop decisions on the recorded runs | Claude | none |
| Root-cause the 02:50 interrupt-watchdog crash | Claude | none |
| Optional: one session where the box needs misting (fan schedule or drier room), 2 h alternating | user starts it | 2 h |
| Optional: dead-mister fault with the backup mister connected | user unplugs | 30 min |
| Write the paper: methods, results (sections 3.1–3.3), limitations (section 4) | both | none |

## 7. Files
- Data and index: `data/README.md`
- Write-ups: `docs/lab-step-2026-09-25.md`, `docs/box-experiment-2026-09-25.md`, `docs/lab-session-2026-09-26.md`, `docs/lab-session-2026-09-27.md`
- Figures: `docs/figures/lab-step-2026-09-25-1910.png`, `session-2026-09-26.png`, `session-2026-09-27.png`, `box-humidity-2026-09-25.png`, `brain-sim-demo.png`
- Plan and gap: `docs/publication-plan.md`, `docs/tinyml-esp32-gap-check.md`, `docs/self-healing-gap-check.md`
- Code: `firmware/lab/`, `tools/lab/`, `tools/brain/`
- Git: commits `d43efaf`, `eb78ab6`, `aa813b7` and this one, branch `main`, not pushed.
