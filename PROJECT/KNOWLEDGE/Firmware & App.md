---
tags: [terrarium, firmware]
updated: 2026-08-06
---

# Firmware & App

Location: `TERRARIUM/firmware/terrarium/` — three files + README.

| File | Purpose |
|---|---|
| `terrarium.ino` | control logic, safety interlock, web server + JSON API |
| `config.h` | **everything you edit**: Wi-Fi, pins, calibration, thresholds, ENABLE flags |
| `webui.h` | the phone dashboard (served from flash) |

## Flash (short version)
Arduino IDE → boards **esp32 by Espressif** → board **ESP32 Dev Module** (the generic
profile — DOIT DEVKIT V1 exists but is buried and identical for our purposes) →
libraries **Adafruit BME280** (accept deps) + **BH1750** (C. Laws) → edit `config.h`
Wi-Fi → upload → Serial 115200 prints the IP. Board enumerates on **COM3**.

> [!warning] IDE quirk that costs an hour
> Opening a sketch in a **second** IDE window silently reverts the board to `uno`.
> Symptom: `WebServer.h: No such file or directory`. Fix: re-pick board + port in
> that window. Arduino 1.x only saves preferences on exit, so the last window to
> close wins.

## Flash from the command line (faster loop)
`arduino-cli` lives in `TERRARIUM/tools/`, configured to reuse the IDE's own
ESP32 core 3.3.11 and libraries — no duplicate downloads.

```
cd TERRARIUM/tools
./arduino-cli.exe compile --fqbn esp32:esp32:esp32 --config-file arduino-cli.yaml ../firmware/terrarium
./arduino-cli.exe upload -p COM3 --fqbn esp32:esp32:esp32 --config-file arduino-cli.yaml ../firmware/terrarium
```

> [!danger] Close the Serial Monitor before uploading
> Only one program may own COM3. The IDE's monitor window (process `javaw`, window
> title `COM3`) blocks both uploads and any external serial read with
> "Access to the port is denied". `tools/run_scan.sh` waits for the port, uploads
> the scanner, then captures 18s of output to `tools/scan-result.txt`.

## Bench tool: I2C scanner
`firmware/i2c-scan/i2c-scan.ino` — sweeps every address and names what answers.
Flash it whenever a sensor reports NOT FOUND.

| Result | Meaning |
|---|---|
| `0x76` / `0x77` | BME280 alive and correctly wired |
| `0x23` | BH1750 alive (ADDR tied to GND) |
| `0x5C` | BH1750 alive but ADDR is high — pull ADDR to GND |
| nothing | power or the two bus wires — **not** the sensors |

> [!tip] The pin trap on this board
> `D21` and `D22` are **not adjacent** — the silk runs `… D19 D21 RX0 TX0 D22 D23`.
> Wiring SCL by counting one pin over from SDA lands it on `RX0` and the whole bus
> goes silent. Read the printed label, never the position.

## The app
- Same Wi-Fi: open the IP or `http://terrarium.local`
- No router: board makes hotspot **Terrarium** / `terrarium123` → `http://192.168.4.1`
- Chrome ⋮ → **Add to Home screen** = it behaves like an installed app
- Live cards (temp · RH · soil avg+each · lux) · AUTO/MANUAL toggle · per-output buttons ·
  thresholds saved to flash (survive reboot)

## Behaviour (AUTO)

| Thing | Logic |
|---|---|
| Watering (GPIO16) | soil avg < threshold → mist burst **90s** → **20min soak** → re-check · hard cap 30min/day |
| Humidity (GPIO25) | RH < low → mist on until RH ≥ high · max 5min burst · 3min cooldown · no RH reading = never mist blind |
| Grow light (GPIO19) | photoperiod window (NTP, UTC+6) **and** lux < on-threshold · PWM brightness |
| Fans (17/18) | temp hysteresis (flag-enabled) |
| **Interlock** | tank empty → **both mist channels forced OFF, even in MANUAL** · buzzer if fitted |
| Manual | buttons live · mist auto-off after 10min if forgotten |
| Offline | all logic local; Wi-Fi loss changes nothing (capstone claim — demo with router off) |

## Measured calibration (2026-08-10, first bring-up)

| Constant | Value | How it was taken |
|---|---|---|
| `SOIL1_ADC_DRY` | **2470** | probe held in open air |
| `SOIL1_ADC_WET` | **1070** | probe in water to the white line |
| `SOIL2_ADC_DRY` | **2485** | same, second probe |
| `SOIL2_ADC_WET` | **1070** | matched unit, same water test |

Validation: dry probe computed 6%, submerged probe 100%, average 52% — the
two-point map is correct. Both probes agreed within 20 counts when dry, which
is why one wet reading was enough for the pair.

> [!note] Reading the board without Wi-Fi
> The firmware prints one status line every 10s over USB serial:
> `[40s] temp 31.6  RH 75  lux --  soil 52% (raw 2394/1069)  tank:OK  auto  water:0 mist:0 light:0  rssi -65`
> Raw ADC is in there deliberately — it is what you recalibrate from, and it is
> the log to screenshot for the report. Serial stays reliable when Wi-Fi does not.

## config.h — what actually gets edited
- `WIFI_SSID / WIFI_PASS` (2.4GHz only)
- `SOIL1_ADC_DRY/WET`, `SOIL2_…` — from stage-1 calibration
- `FLOAT_EMPTY_STATE` — flip if your float reads inverted (stage-1 meter note)
- `ENABLE_FLOAT / ENABLE_LEAK / ENABLE_FAN_EXH / ENABLE_FAN_CIRC / ENABLE_BUZZER / ENABLE_SOIL2`
- Defaults: soil dry 35% · RH 75→90 · lux 800/2000 · photoperiod 07–19 · brightness 220

Unwired sensors degrade gracefully (read `--`, logic that needs them stays off).
Pins are identical to [[Pin Map]]. Test rig: [[Simulation & Testing]].

## Terrarium Console — the one-file setup tool
`TerrariumConsole.exe` (project root; source in `tools/console/`). Copy it to any Windows
laptop and run it: opens `http://localhost:8765`, finds the board on USB and Wi-Fi (mDNS →
last IP → hotspot 192.168.4.1 → subnet scan), runs eight checks (internet, driver, USB,
port free, toolchain, board on Wi-Fi, firmware, sensors) each with a plain-English reason
and a **Fix** button, installs the bundled CP210x driver (UAC) and arduino-cli (reusing an
existing IDE core when present), flashes any sketch, streams serial, embeds the dashboard.
`--auto` fixes everything without asking. Installs live in `%LOCALAPPDATA%\TerrariumConsole`.

> [!warning] The exe is a snapshot
> It carries a copy of `firmware/` — including `config.h` with the Wi-Fi password. After any
> firmware edit run `tools/console/build.sh`, and never post the exe publicly.

## MOSFET board: the 5 V input finding (2026-08-12)
The "F5305S" is an **opto-isolated** 60N03 board. Its input LEDs need more current than a
3.3 V GPIO supplies — at 3.3 V the `IN` indicator glows dimly and the channel never switches.
Fix with zero parts: wire every `PWMn` terminal to **`VIN` (5 V)** and each `GNDn` to its
**GPIO**, so the ESP32 *sinks* the opto. Logic inverts; `MOSFET_ACTIVE_LOW 1` in `config.h`
handles it (including the light's PWM). No 10 k pulldowns in this arrangement.
Switching a bare motor with no flyback diode reset the ESP32 — diodes are not optional.
