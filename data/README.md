# Measured data (real box, real sensors)

All files are 1 Hz unless stated. Times are the laptop clock (Bangladesh, UTC+6). Humidity in %RH, temperature in °C, pressure in hPa. `in` = BME280 inside the box (0x76, the control sensor), `out` = BME280 outside on the table (0x77, reference). Nothing here is simulated. Write-ups: `docs/RESULTS.md` (all results, audited 28 Sep) and the per-session notes in `docs/`.

## Characterisation and early runs (25 Sep)

| File | Time | What | Notes |
|---|---|---|---|
| `box-2026-09-25-1521.csv` | 15:21 | first logger trial, 10 s status lines, old firmware | integer RH; light/soil columns empty or floating |
| `box-exp-2026-09-25-1558.csv` + `.notes.txt` | 15:58 | box test run 1: baseline, rise, decay | cut short, inside sensor fogged |
| `box-exp-2026-09-25-1645.csv` + `.notes.txt` | 16:45 | box test run 2: baseline, 10 min rise, 25 min decay, auto 85–92 | one end of box open; ended by fogged sensor. `docs/box-experiment-2026-09-25.md` |
| `lab-step-2026-09-25-1910.csv` + `.events.txt` + `.fit.json` | 19:10 | **step test, 3 rounds**, lid closed, one mister | 100 % valid. `docs/lab-step-2026-09-25.md`. The model seed for every learning run |
| `lab-baseline-2026-09-25-2046.csv`, `-2115.csv` | 20:46, 21:15 | production rule, lid closed | first froze after 13 min (bus lock-up), second stopped after 41 min |

## Fault session (26 Sep, lid 1 cm), `docs/lab-session-2026-09-26.md`

| File | Time | What | Notes |
|---|---|---|---|
| `lab-baseline-2026-09-26-1034.csv` | 21:53–22:37 | production rule | first 8 min the mister was dry; use rows after "mode RULES" at 22:22 |
| `lab-brain-2026-09-26-2237.csv` + `.brain.csv/.json` | 22:37–23:14 | learning controller; lid-off fault 23:02, "lid open / leak" 23:08:51 | runner stopped at the 23:12:57 chip restart (106 s without control) |
| `lab-brain-2026-09-26-2314.csv` + `.brain.csv/.json` | 23:14–23:24 | learning; wet-tissue test; false alarm withdrawn 23:23:03 | |
| `session-2026-09-26.json` | | per-block metrics | |
| `lab-baseline-2026-09-26-2330.csv`, `-2345.csv`, `lab-brain-2026-09-26-2343.*`, `-2346.*`, `lab-log-2026-09-27-0016.csv`, `-0027.csv` | 23:30–00:30 | aborted attempts (bus faults, firmware crash) and wiring checks | not for analysis |

## Alternating sessions (27 Sep, lid 4 cm)

| File | Time | What | Notes |
|---|---|---|---|
| `lab-baseline-2026-09-27-0055.csv`, `lab-brain-2026-09-27-0125.*`, `lab-baseline-2026-09-27-0155.csv`, `lab-brain-2026-09-27-0225.*` | 00:55–02:55 | night: rule, learning, rule, learning (room 71–73 %) | 100 % valid; restart at 02:50 (~20 s). `docs/lab-session-2026-09-27.md`; `session-2026-09-27-0055.json` |
| `lab-brain-2026-09-27-2003.*`, `lab-baseline-2026-09-27-2033.csv`, `lab-brain-2026-09-27-2103.*`, `lab-baseline-2026-09-27-2133.csv`, `lab-brain-2026-09-27-2203.*` | 20:03–22:33 | evening, dry box (room 69 %): learning, rule, learning, rule, learning with software dead mister 22:09–22:21 | 100 % valid. `docs/lab-session-2026-09-27-evening.md`; `session-2026-09-27-2003.json` |

## Dry-start test (28 Sep, lid 1 cm, matched rule vs learning), `docs/RESULTS.md` 3.5

| File | Time | What | Notes |
|---|---|---|---|
| `lab-lidcycle-2026-09-28-1526.*` (+ `-c2.brain.csv/.json`, `.cycles.json`, `.out`) | 15:26–17:16 | pair 1: c1 matched rule, c2 learning | **c3 (rule) invalid**: inside humidity channel froze at 61.3 % from 17:07:48 |
| `lab-lidcycle-2026-09-28-1733.*` (+ `-c2.brain.csv/.json`, `.cycles.json`) and `lab-lidcycle.out` | 17:33–18:21 | pair 2: c1 matched rule, c2 learning | tray refilled before; mister weak at first |

## Not for analysis: `scrap/`
Runner page-bug trials (25 Sep), a 3-minute run with the lid off (27 Sep 19:58), and two aborted dry-start starts (28 Sep 15:13 lid not removed; 17:20 fog check failed after refilling).

## Columns
`lab-*.csv`: `pc_time, phase, ms, t_in, rh_in, p_in, t_out, rh_out, p_out, mistA, mistB, mode, in_ok, out_ok, tank_ok, event`. Rows with an empty `ms` are events (commands, MARK lines, sensor lost/OK). Use only rows with `in_ok = 1`. In `lab-lidcycle-*` the `phase` column is `c<k>-dry`, `c<k>-close`, `c<k>-rule` or `c<k>-learning`. `*.brain.csv`: the learning controller's state every 5 s (command, planned burst, fault, z, mister and leak weights).

Tools: `firmware/lab/` (board), `tools/lab/logger.py` (record, protocols, live page), `tools/lab/brain_runner.py` (learning controller), `tools/lab/lid_cycle_test.py` (dry-start test), `tools/lab/analyze_step.py`, `tools/lab/analyze_session.py`.
