# Lab session 2026-09-26, 22:22 to 23:24: old rule vs brain on the real box, with injected faults

Rig: box with lid propped about 1 cm on one edge, one BME280 inside (0x76, high, shielded), one outside (0x77, on the table), one ultrasonic mist maker (channel A). Firmware `firmware/lab` (1 Hz data, RH to 0.01 %). The **brain ran on the laptop** (`tools/lab/brain_runner.py`, `tools/brain/brain.py`): every 5 s it read the inside sensor and sent the mist command over USB. It was pre-taught from the 25 Sep step test (least squares on the same six features) and kept learning during the run. Data: `data/lab-baseline-2026-09-26-1034.csv` (rule), `data/lab-brain-2026-09-26-2237.csv` and `-2314.csv` (brain, plus `.brain.csv` model logs and `.events.txt`). Figure: `docs/figures/session-2026-09-26.png`. Analysis: `tools/lab/analyze_session.py`.

## Blocks

| Block | Start | Minutes | In 75–90 % | Above 90 % | Below 75 % | Mist min | Switch-ons |
|---|---|---|---|---|---|---|---|
| Old rule (75/90, 5 min cap) | 22:22 | 15.1 | 96.5 % | 0.0 % | 3.5 % | 5.0 | 1 |
| Brain, incl. lid-off fault | 22:37 | 37.1 | 95.4 % | 0.1 % | 4.5 % | 1.1 | 3 |
| Brain, wet-sensor test and recovery | 23:14 | 10.1 | 59.3 % | 3.3 % | 37.4 % | 1.5 | 1 |

The rule's one burst ran the full 5 min cap (70.8 to 88.2 %). The brain, during the lid fault, held the band with three bursts of about 35 s. Before the fault it correctly did nothing: the rule had left the box at 87 % and, with a 1 cm gap, the box did not fall below the brain's start point in 25 min.

## Faults

| Injected | When | Brain's response |
|---|---|---|
| Lid fully off | 23:02:11 | "suspect loss" after 1 s; quiet watch 4 min; three short test bursts; **"lid open / leak" after 400 s**. Kept controlling with the fast model in the meantime. |
| Lid back, 1 cm gap | 23:10:47 | Humidity recovered; fault state held until the box behaved normally again (by design, 10 min of agreement). |
| Wet tissue on inside sensor | 23:12:50 | Sensor did not stick (read 89–90 %, warmed to 32 °C). The sensor **locked up the I2C bus**; the firmware watchdog rebooted the chip at 23:12:57 and the sensors were re-found within 1 s. The laptop runner did not handle the reboot and was restarted at 23:14 (fixed in `brain_runner.py`). |
| Tissue removed | 23:16:30 | Reading fell 90 to 74 % in 40 s (sensor drying). Brain raised "suspect loss" at 23:16:37, ran its quiet-then-mist test, and at 23:23:03 concluded **"false alarm, nothing wrong"** and cleared it. |

## What the model learned
Seed (closed box, 25 Sep): mist 1.61, leak −0.036, bias 0.19 (per 5 s step, absolute humidity). After 25 min with the 1 cm gap, before any fault: leak −0.131, bias 1.00, i.e. the slow learner re-fitted the leakier box on its own. Full traces in `data/lab-brain-2026-09-26-2237.brain.csv`.

## Honest limitations
1. **Short.** 15 min of rule and 47 min of brain, one evening. The 1 cm gap gave about one humidity cycle per hour, so the rule-versus-brain comparison rests on one burst each. Next session: 3–4 cm gap, alternate 30 min blocks.
2. **Brain on the laptop, not on the chip.** The model is six weights and two 6×6 matrices; the port is straightforward but not done.
3. **Wet-sensor fault did not reproduce** the fogging seen on 25 Sep (179 °C / 100 %). It did reproduce the bus lock-up and the watchdog recovery.
4. **One false alarm** (sensor drying after the tissue), self-cleared in 6.5 min. A temperature check would prevent it: the reading fell while the sensor's own temperature fell 2 °C.
