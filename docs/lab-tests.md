# Lab tests for the paper (new bench build)

Firmware: `firmware/lab/lab.ino`. Logger: `tools/lab/logger.py`. Data lands in `data/`.

The board needs: inside BME280 at 0x76, outside BME280 at 0x77 (SDO to 3V3), both on SDA D21 and SCL D22. Mist A on GPIO25 (board A OUT1), mist B on GPIO16 (board A OUT2).

## Before every run
- Water in the tank, both mist discs under water.
- Inside sensor high up, away from the mist, with a small roof over it.
- Outside sensor on the table, about 30 cm from the box.
- Close the TerrariumTester app. Only one program can use the USB port.

## The tests, in order

| # | Test | Command | How long | You do |
|---|---|---|---|---|
| 1 | Step tests: how fast each mister wets the box and how fast it dries | `python tools/lab/logger.py --protocol step` | about 3 h | nothing |
| 2 | Baseline: current on/off rules, 75 to 90 % | `python tools/lab/logger.py --protocol baseline` | 3 days | keep the tank full |
| 3 | Brain run | comes after the brain is ported to the chip | 3 days | keep the tank full |
| 4 | Break things on purpose | run with the brain, mark each fault | 1 afternoon | open lid, unplug a mister, unplug a sensor |

## During a run
- To note something in the data, put one line in `data/lab-cmd.txt`, for example `MARK lid open` or `MARK refilled tank`. The logger sends it within a second.
- To stop cleanly, create an empty file `data/STOP`. Both mists go off.

## Safety built into the firmware
- Mist switches off if the inside sensor stops giving sane readings, in rules mode.
- Every burst stops at the cap (5 min by default). A manual mist switches off after 10 min.
- A lost sensor is retried every 5 s, so a sensor that recovers comes back without a reboot.
- After a reset the board resumes rules mode, but never resumes a manual mist.
