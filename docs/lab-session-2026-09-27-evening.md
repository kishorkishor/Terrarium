# Lab session 2026-09-27, 20:03 to 22:33: rule vs brain on a DRY, leaky box, plus a dead-mister fault

Rig as in the night session (`docs/lab-session-2026-09-27.md`): lid propped 4 cm, one sensor in, one out, one mist maker, both sensors 100 % valid in every block. Room at 68.6–69.6 %RH (5 % drier than the night before), box at 69 %RH at the start. Brain on the laptop, seeded from the 25 Sep step test; the seed covariance was set small (0.05) for all five blocks so the seeded weights are trusted (a discarded 19:58 run with the lid off had tripped a spurious wear warning at 10 s with the old p0 = 100). Blocks: brain, rule, brain, rule, brain with a **software dead-mister fault** (the brain's mist commands were dropped before reaching the firmware from 22:09:48 to 22:21:48; the brain was not told). Data `data/lab-brain-2026-09-27-2003.csv`, `lab-baseline-2026-09-27-2033.csv`, `lab-brain-2026-09-27-2103.csv`, `lab-baseline-2026-09-27-2133.csv`, `lab-brain-2026-09-27-2203.csv` (+ `.brain.csv`, `.events.txt`). Figure `docs/figures/session-2026-09-27-2003.png`. Metrics `data/session-2026-09-27-2003.json`.

| Block | Start | In 75–90 % | Below 75 % | Mist min | Bursts | RH range |
|---|---|---|---|---|---|---|
| Brain (from a dry box) | 20:03 | 74.3 % | 25.7 % | 24.1 | 6 | 69.2–82.5 |
| Rule | 20:33 | 65.6 % | 34.4 % | 18.2 | 4 | 72.8–79.8 |
| Brain | 21:03 | **99.4 %** | 0.6 % | 24.0 | 6 | 74.2–82.2 |
| Rule | 21:33 | 90.9 % | 9.1 % | 16.3 | 4 | 73.8–82.0 |
| Brain, dead-mister fault 22:09–22:21 | 22:03 | 78.9 % | 21.1 % | 13.9 | 5 | 72.3–82.7 |

## Control
- On this box (room 69 %, 4 cm gap) the passive equilibrium is about 74 %RH, just under the band, and one mist maker cannot reach the brain's 88 % target: the box tops out near 82 %. Both controllers therefore mist most of the time.
- **Paired comparison, same box, alternating:** brain 74.3 vs rule 65.6 % in band (from a dry start), brain 99.4 vs rule 90.9 % (from an in-band start). The brain leads in both pairs, by holding the band from below with full bursts and 60 s rests, where the rule's fixed 180 s rest lets the box fall below 75 % every cycle. Cost: about 40 % more mist (24 vs 16–18 min per 30 min).
- Model: leak weight −0.036 (seed) → −0.227, −0.161, −0.127 at the end of the three brain blocks; mister weight 1.61 → 1.53, 1.47, 1.38.
- Design lesson: when the target is unreachable the planner falls back to maximum-length bursts; a "hold the lower edge" mode would use less water for the same time in band.

## Dead-mister fault (negative result)
For 12 minutes the brain commanded 450 s of misting that never reached the box. Humidity fell from 80.8 to 72.3 % (61 % in band during the window). **The brain did not declare a fault.** Replaying the block offline shows why: its mister check compares the measured gain during misting with the model's expectation *after subtracting the modelled leak*, and on this box the leak term is large and imprecise, so the check's ratio during the fault (0.46–1.5) overlapped the healthy range (0.5–1.5). A raw burst-onset check (rise in the first 60 s of a burst versus expectation) was tried offline and fired false alarms in healthy blocks because the seeded mister weight over-predicts the first-minute rise at this sensor position by about 4×; it was not adopted. The lid-open fault of 26 Sep was detected because it changes the leak by an order of magnitude; a dead mister on a box near its passive equilibrium changes humidity by only a few percent, which is inside the model's error. Remedies for the next version: a direct actuator check (mist-maker current or a droplet sensor), or a calibrated onset signature measured at commissioning rather than predicted by the model.

## Audit 2026-09-28: what drove the control difference
Burst logs: 15 of the brain's 18 planned bursts ran to the 300 s cap (the first burst of each block was 125, 80 and 80 s, planned with the closed-box seed; within 2.5–3 min the fast leak estimate rose 2.3–4.1× and every later plan went to the cap). Every rule burst also stopped at the cap (except those cut by a block end). The controllers therefore differed only in trigger (77 vs 75 %) and rest (60 vs 180 s): a rule with those settings would issue the same commands except for the first burst of each block. The better time in band and the extra water are effects of the settings, not of learning. Prepared follow-up: matched rule (`logger.py --protocol baseline --rule-lo 77 --rule-hi 88 --rule-cool 60`) vs brain, 4 × 30 min.
