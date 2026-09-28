# Terrarium brain: everything so far (as of 2026-09-28, audited)

> **Audit 2026-09-28.** A burst-level re-analysis corrected three claims made earlier: (1) the learning controller's control advantage over the production rule comes from its trigger (77 vs 75 %) and rest (60 vs 180 s), not from learning (15 of 18 evening bursts ran at the same 300 s cap); (2) the night session's zero misting is not evidence of water saving (trigger never crossed, and each learning block began just after a rule burst); (3) the 26 Sep 23:12 reboot was a crash in the first firmware's bus-recovery routine, not a watchdog recovery, and 106 s passed without control; the 27 Sep 02:50 restart cost about 20 s, not 6 s.

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
| Lid fully off (23:02:11) | "suspect loss" after **1 s**; quiet watch; three test bursts of 10–40 s (fast model, 84 % target); **"lid open / leak" after 400 s**; kept controlling with the fast model meanwhile |
| Lid back (23:10:47) | recovered; fault held until the box behaved normally for 10 min (by design) |
| Wet tissue on sensor (23:12:50) | sensor did not stick, but the bus fault **crashed the first firmware's bus-recovery routine** (StoreProhibited panic); the chip restarted and both sensors were back at 23:12:56; the laptop runner did not handle the restart, so **106 s passed without control** |
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

Reading: with the gap and the water surface, the box settles at 78–80 %RH by itself, inside the band. The rule waits for 75 %, then mists a full 5 min to 88 % (the ceiling; 90 % is never reached), the box drains back in ~10 min, repeat. **Correction (audit):** the brain did not judge that no misting was needed: its 77 % trigger was never crossed at its 5 s sampling, and both brain blocks began just after a rule burst (79.3 and 87.6 % at block start), so carry-over favoured them. This session is **not** evidence of water saving. Outside humidity drifted 73 → 71 %. One chip restart at 02:50 (interrupt watchdog); the laptop runner resumed control after about 20 s (18 s data gap).

Figure: `docs/figures/session-2026-09-27-0055.png`. Metrics: `data/session-2026-09-27-0055.json`.

### 3.4 Rule vs brain on a dry, leaky box, with a dead-mister fault, 27 Sep 20:03–22:33 (`docs/lab-session-2026-09-27-evening.md`)
Lid 4 cm, room 69 %RH, box 69 %RH at start; 100 % valid readings in all five blocks.

| Block | In 75–90 % | Below 75 % | Mist min | Bursts |
|---|---|---|---|---|
| Brain (dry start) | 74.3 % | 25.7 % | 24.1 | 6 |
| Rule | 65.6 % | 34.4 % | 18.2 | 4 |
| Brain | **99.4 %** | 0.6 % | 24.0 | 6 |
| Rule | 90.9 % | 9.1 % | 16.3 | 4 |
| Brain, dead-mister fault 22:09–22:21 | 78.9 % | 21.1 % | 13.9 | 5 |

Reading: the box's passive equilibrium is ~74 %RH and one mister tops out near 82 %, so both controllers mist most of the time. The brain leads both pairs (74.3 vs 65.6, 99.4 vs 90.9 % in band) by resting 60 s instead of 180 s, at ~40 % more mist. **Dead mister (software-injected, 12 min, 450 s of commanded mist lost): not detected.** The leak-corrected mister check has no discriminating power on a leaky box near equilibrium; an offline burst-onset check false-alarmed on healthy blocks and was not adopted. Figure `docs/figures/session-2026-09-27-2003.png`.

### 3.5 Dry-start test at 1 cm, matched rule vs learning, 28 Sep 15:45–18:21 (`tools/lab/lid_cycle_test.py`)
At 1 cm the box holds ~80 %RH by itself (room 64–66 %), above both controllers' 77 % trigger, so each cycle started with the lid off until the inside reading fell to 73 %, then lid back at 1 cm and one controller for 20 min. Rule matched to the brain: below 77 %, stop at 88 % or 300 s, rest 60 s. Data: `data/lab-lidcycle-2026-09-28-1526.csv` (pair 1; its cycle 3 is invalid, see below) and `data/lab-lidcycle-2026-09-28-1733.csv` (pair 2), with `.brain.csv`, `.events.txt`, `.cycles.json`.

| Pair, controller | Start %RH | Mist s | Bursts | Peak %RH | End %RH | In band | Mister strength, first 60 s of bursts (g/m³/s) |
|---|---|---|---|---|---|---|---|
| 1, rule | 72.4 | 300 | 1 | 87.7 | 80.2 | 98.1 % | 0.20 |
| 1, learning | 70.6 | 155 | 1 | 82.4 | 79.7 | 94.5 % | 0.09 |
| 2, rule | 70.4 | 1021 | 4 | 83.2 | 77.3 | 78.8 % | 0.04–0.10 |
| 2, learning | 74.4 | 726 | 3 | 87.8 | 85.9 | 97.9 % | 0.13–0.17 |

Reading: the brain's first bursts were model-sized (155 s, 120 s) against the rule's 300 s cap; in pair 1 it used half the mist and both ended near the box's own ~80 %. **Inconclusive about water:** the mister's delivered strength varied up to fivefold between cycles, weakest just after the tray was refilled before pair 2 (overfilled tray), so the rule faced a weak mister in pair 2 and the brain a weaker one in pair 1. The lid position may also have shifted between pairs (the sensor cable was re-taped). One cycle per controller per pair cannot separate controller from actuator variability.

Two hardware findings from this run:
- **Frozen humidity channel (17:07:48).** A bus glitch while the lid was moved cleared the BME280's ctrl_hum; the Adafruit library converted the chip's "not measured" value (raw 0x8000) into a steady ~61.3 % that drifted only with temperature, while the box was full of mist; the rule kept misting. Range checks and a 12-identical-readings stuck check both miss this. Firmware fix (`readRawHum` in `firmware/lab/lab.ino`): read the raw humidity register every sample and reject 0x8000, and verify ctrl_hum after init. It caught a failed setup on the next glitch (17:36:40) and recovered.
- **ESP32 restarts explained.** 27 Sep 02:50 and 28 Sep 16:06 share one signature (decoded with addr2line against the matching ELF): the Arduino loop task blocked in the ESP-IDF I2C master driver, the driver's ISR waited on a spinlock (`xQueueGenericSendFromISR` / `xQueueGiveFromISR`), the 15 s task watchdog fired, and its panic handler tripped the interrupt watchdog. Recovery ~20 s each time. The 16:06 one happened as the lid was about to be handled.

### 3.6 Simulation (logic test only, not evidence)
`tools/brain/run_demo.py`, 76 simulated hours with four faults, drift and a memory glitch: brain 99.2 % in band vs rules 93.1 %, 282 vs 353 mist-min/day, all faults named correctly on 7 random seeds, no false alarms. Constants in `sim_box.py` now use the measured mister strength (0.17 open / 0.10 closed) and decay. Figure `docs/figures/brain-sim-demo.png`.

## 4. What the results support, and what they do not

**Supported by measured data**
- One learned model, seeded from a 90 min step test, controls a real box at least as well as the production rule (99.4 vs 90.9 % and 74.3 vs 65.6 % in band in the evening pairs). **But the burst logs attribute this to its trigger and rest settings, not to learning:** 15 of its 18 evening bursts ran to the same 300 s cap as the rule. Water: no saving shown (night result confounded by carry-over; evening used ~40 % more mist).
- Learning changed its decisions: each block began with the closed-box seed (planned 80–125 s); within one burst cycle (2.5–3 min) the leak estimate rose 2.3–4.1× and later plans went to the cap.
- It names a lid-open fault by itself (400 s) after suspecting it in 1 s, keeps controlling meanwhile, and clears its own false alarm by testing (6.5 min).
- It re-fits its model when the box changes (leak weight 3.6× within 25 min of the gap).
- A wet sensor faulted the bus; the first firmware's recovery routine crashed the chip (it restarted and re-found the sensors in 6 s); the routine was removed.

**Not yet supported**
- Burst planning was exercised on a dry box (27 Sep evening): with the target unreachable the planner falls back to maximum bursts, which wins time-in-band at a water cost. A lower-edge holding mode is the obvious next improvement.
- **Control/water advantage from learning:** not shown. The matched-rule dry-start test at 1 cm (3.5) was inconclusive because the mister's output varied up to fivefold between cycles; it would need many more cycles and a measured mister output.
- **Dead-mister detection failed on the real box** (27 Sep evening): humidity-only checks cannot see a dead mister on a leaky box near its passive equilibrium. Needs a direct actuator signal or a commissioning-time onset signature.
- Running on the chip: the brain ran on the laptop over USB (5 s steps). The port is straightforward (6 weights, two 6×6 matrices) but not done.
- Days-long behaviour, plants inside, more than one box: not tested.

## 5. Hardware lessons (worth a paragraph in methods)
1. The BME280 "179.4 °C / 100 %" state is the chip at power-on defaults: register writes fail on a marginal bus or after hot-replugging its clock wire, while single-byte reads still work. Power cycling does not fix it; solid SDA/SCL wiring does.
2. Two sensors' SCL wires sharing one breadboard row failed intermittently for hours; a clean rewire gave 100 % good data for 3 h.
3. Tearing the ESP32 I2C driver down and up in firmware (Wire.end/begin) crashed the chip (StoreProhibited); removed.
4. A wet BME280 faults the bus. With the recovery routine removed, re-probing every 5 s plus the task watchdog handled later faults. The two interrupt-watchdog restarts that remained (27 Sep 02:50, 28 Sep 16:06) were traced to the ESP-IDF I2C driver (3.5) and cost about 20 s each.
5. Corrupted reads can pass naive sanity checks (100.00 %RH, 0 °C); the filter now requires plausible temperature, pressure and step size.

## 6. What is left
| Item | Box time |
|---|---|
| Port `brain.py` to C in `firmware/lab` and check it reproduces the laptop decisions on the recorded runs | none |
| Matched rule vs learning with a steady, measured mister output, several cycles each (the water question) | several hours |
| Lid-off and dead-mister faults under the production rule, to measure what the brain's recovery saves | 1–2 h |
| Dead-mister detection from a direct signal (mister current) or a commissioning-time onset signature | 1 h |

## 7. Files
- Data and index: `data/README.md`
- Write-ups: `docs/lab-step-2026-09-25.md`, `docs/box-experiment-2026-09-25.md`, `docs/lab-session-2026-09-26.md`, `docs/lab-session-2026-09-27.md`, `docs/lab-session-2026-09-27-evening.md`
- Figures: `docs/figures/lab-step-2026-09-25-1910.png`, `session-2026-09-26.png`, `session-2026-09-27-0055.png`, `session-2026-09-27-2003.png`, `box-humidity-2026-09-25.png`, `brain-sim-demo.png`
- Plan and gap: `docs/publication-plan.md`, `docs/tinyml-esp32-gap-check.md`, `docs/self-healing-gap-check.md`
- Code: `firmware/lab/`, `tools/lab/`, `tools/brain/`
- Paper: `docs/paper/` (built by `tools/paper/build_paper.js`, figures by `tools/paper/paper_figures.py`)
