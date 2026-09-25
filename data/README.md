# Measured data (real box, real sensors)

All files are 1 Hz unless stated. Times are the laptop clock (Bangladesh, UTC+6). Humidity in %RH, temperature in °C, pressure in hPa. `in` = BME280 inside the box (0x76), `out` = BME280 outside on the table (0x77). Nothing here is simulated.

| File | Date | What | Notes |
|---|---|---|---|
| `box-2026-09-25-1521.csv` | 25 Sep 15:21 | first logger trial, 10 s status lines, old firmware | integer RH |
| `box-exp-2026-09-25-1558.csv` + `.notes.txt` | 25 Sep 15:58 | box test run 1: baseline, rise, decay | cut short, inside sensor fogged |
| `box-exp-2026-09-25-1645.csv` + `.notes.txt` | 25 Sep 16:45 | box test run 2: baseline, 10 min rise, 25 min decay, auto 85–92 | one end of box open; ended by fogged sensor. Write-up `docs/box-experiment-2026-09-25.md` |
| `lab-step-2026-09-25-1910.csv` + `.events.txt` + `.fit.json` | 25 Sep 19:10 | **step test, 3 rounds**, lid closed, mist A only, RH to 0.01 % | 100 % good rows. Write-up `docs/lab-step-2026-09-25.md` |
| `lab-baseline-2026-09-25-2046.csv` + `.events.txt` | 25 Sep 20:46 | on/off rules 75–90 %, lid closed | board froze at 20:59 (bus lock-up), 13 min of data |
| `lab-baseline-2026-09-25-21xx.csv` | 25 Sep 21:2x | on/off rules 75–90 %, restarted with watchdog firmware | running |
| `scrap/` | | aborted trials of the runner (page bugs), a minute each | ignore |

Columns of `lab-*.csv`: `pc_time, phase, ms, t_in, rh_in, p_in, t_out, rh_out, p_out, mistA, mistB, mode, in_ok, out_ok, tank_ok, event`. Rows with an empty `ms` are events (commands, MARK lines, sensor lost/OK). Use only rows with `in_ok = 1`.

Tools: `firmware/lab/` (board), `tools/lab/logger.py` (record + protocols + live page), `tools/lab/analyze_step.py` (fit).
