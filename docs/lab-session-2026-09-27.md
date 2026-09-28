# Lab session 2026-09-27, 00:55 to 02:55: old rule vs brain, alternating 30 min blocks

Rig as on 26 Sep (`docs/lab-session-2026-09-26.md`) but with the lid propped **4 cm** and the sensor wiring redone (both sensors 100 % good in a 2 min check before the start). Brain on the laptop (`tools/lab/brain_runner.py`), pre-seeded from the 25 Sep step test, learning throughout. Data: `data/lab-baseline-2026-09-27-0055.csv`, `lab-brain-2026-09-27-0125.csv`, `lab-baseline-2026-09-27-0155.csv`, `lab-brain-2026-09-27-0225.csv` (+ `.brain.csv`, `.events.txt`). Figure `docs/figures/session-2026-09-27-0055.png`. Metrics `data/session-2026-09-27-0055.json`.

| Block | Start | Minutes | In 75–90 % | Below 75 % | Mist min | Bursts | RH min | RH max |
|---|---|---|---|---|---|---|---|---|
| Old rule | 00:55 | 30.1 | 98.9 % | 1.1 % | 10.2 | 3 | 72.4 | 87.1 |
| Brain | 01:25 | 30.1 | **100.0 %** | 0.0 % | **0.0** | 0 | 76.8 | 82.0 |
| Old rule | 01:55 | 30.0 | 99.9 % | 0.1 % | 4.4 | 1 | 75.0 | 88.0 |
| Brain | 02:25 | 30.1 | **100.0 %** | 0.0 % | **0.0** | 0 | 79.2 | 87.9 |
| **Rule total** | | 60 | 99.4 % | | **14.6** | 4 | | |
| **Brain total** | | 60 | 100.0 % | | **0.0** | 0 | | |

Every reading in all four blocks was good (no sensor dropouts). One board crash at 02:50:2x (interrupt watchdog on core 0, during the last brain block); the runner detected the restart, re-armed manual mode and the brain kept its memory. Data gap 18 s; about 20 s without control.

## What happened
1. **The rule mists when it doesn't need to.** Each rule burst ran to its 5 min cap (the box's ceiling is 88 %, so 90 % is never reached), pushing the box to 87–88 %; it then drained back to 75 % in about 10 min and the rule fired again. With the 4 cm gap and the water surface in the box, the box settles by itself at about 78–80 %RH, inside the band.
2. **The brain never misted, and the box stayed in band the whole hour.** *Correction (audit 28 Sep):* this was not a model judgement. The brain mists whenever the reading is below 77 %; at its 5 s sampling that never happened (1 Hz minimum 76.8 %). Both brain blocks began just after a rule burst (79.3 and 87.6 % at block start), so carry-over favoured them.
3. **Same box for both.** Blocks alternated, and each brain block inherited the rule's end state (75–88 %). Outside humidity drifted 73 → 71 % over the two hours, so conditions were, if anything, drier for the later blocks.
4. **The brain's model followed the box:** leak weight −0.036 (seed, closed box) → −0.044 after block 1 → −0.093 after block 2, bias 0.19 → 0.21 → 0.53, i.e. it re-fitted the leakier, 4 cm-gap box without any misting data.

## Honest reading
- *Corrected reading:* this session is not evidence of water saving (trigger not crossed; carry-over from rule bursts). It shows only that the box barely needed misting that night. A drier room, or a fan schedule, would make the brain mist and would test its burst planning; the 26 Sep session (three 35 s bursts during the lid fault, 92 %+ in band) is the only real-box evidence of that so far.
- Two hours, one night, one box. No plants inside during these sessions.
- Brain on the laptop over USB, not yet on the chip.
- The 02:50 crash is a firmware robustness issue (interrupt watchdog, not the task watchdog), still to be root-caused; the laptop runner covered it.
