# Box humidity test — 2026-09-25

Enclosure ~11 × 9 × 3 in, lid on, one end slightly open. One 5 V ultrasonic mist maker (humidity channel, GPIO25 → MOSFET board A OUT1). BME280 #1 (0x76) inside the box (control sensor); BME280 #2 (0x77) at the open end. Firmware: terrarium with `ENABLE_BME280_2`, driven over USB by `tools/box-experiment.ps1` (1 Hz `CMD STATUS`). Data: `data/box-exp-2026-09-25-1645.csv` (run 2; run 1 `…-1558.csv` was cut at 16:14 by the same sensor fault). Figure: `docs/figures/box-humidity-2026-09-25.png`.

## Results (run 2)

| Phase | Time | Inside RH | Notes |
|---|---|---|---|
| Baseline, mist off | 16:45–16:47 | 76 → 72 % | lid just closed |
| Rise, mist on continuously | 16:47–16:57 (10 min cap) | 72 → 88 % | 85 % in 42 s, 86 % at 1:50, 87 % at 2:56, 88 % at 4:24, then flat for 5.6 min. Never reached 92 %. Inside temp 29.9 → 28.6 °C (evaporative cooling). |
| Decay, mist off | 16:57–17:22 (25 min limit) | 88 → 83 % | 87 % after 5.5 min, 85 % after 7.3 min, 83 % after 11.3 min, 82 % after 22.9 min. ≈ 0.2 %/min, slowing as it approaches the room. |
| Auto 85–92 %, 10 min burst cap | 17:22–17:33 | 83 → 89 % | mist on immediately (83 < 85), ran the full 10 min cap, peak 89 %; **22 s after the burst the inside sensor read 179.4 °C / 100 % (condensation) and the runner aborted** (mist off, defaults restored). |

## Findings
1. **One mist maker cannot push this box past ~88–89 % RH at the control sensor.** The rise saturates after ~4 min; longer bursts add water droplets, not humidity. The firmware's 5 min burst cap is the right order of magnitude for this box; 10 min is too long.
2. **The box holds humidity well:** 88 → 83 % took 11 min with the mist off; one burst per ~15–20 min would hold an 85–90 % band.
3. **Condensation kills the control sensor.** Both runs ended with the BME280 inside reading 179.4 °C / 100 % and dropping off I2C (a droplet latches it into SPI mode; only a full power cycle recovers it). The sensor must be mounted high, out of the plume, with a droplet shield — or humidity readings should be taken from a sensor outside the direct mist path. This is the main design lesson for the real terrarium.
4. **Sensor placement matters more than expected:** the "open end" sensor often read 2–4 % *higher* than the inside one, because the plume flows toward the opening. The inside sensor position is not representative of the air near the mist.
5. Evaporative cooling of ≈ 1 °C per 10 min burst is measurable.

## Next
- Re-run with the inside sensor shielded/high and the reference sensor ≥ 30 cm outside the opening.
- Repeat the auto phase with the default 5 min cap and band 85–92 to measure the steady-state cycle period.
