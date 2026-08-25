# Terrarium firmware — flash & first run

Board: **ESP32 DevKit V1 (WROOM-32)**. Controls watering mist, humidity mist,
and grow light; serves an Android-friendly dashboard from the board itself.

## 1 · One-time IDE setup

1. Install [Arduino IDE](https://www.arduino.cc/en/software).
2. **File → Preferences → Additional boards manager URLs**, paste:
   `https://espressif.github.io/arduino-esp32/package_esp32_index.json`
3. **Tools → Board → Boards Manager** → search `esp32` → install **esp32 by Espressif Systems**.
4. **Tools → Manage Libraries** → install:
   - `Adafruit BME280 Library` — say **Install all** when it asks about dependencies
   - `BH1750` (by Christopher Laws)

## 2 · Configure

Open `config.h` and edit:

- `WIFI_SSID` / `WIFI_PASS` — your home Wi-Fi (2.4 GHz only; ESP32 cannot see 5 GHz networks)
- `SOILx_ADC_DRY` / `SOILx_ADC_WET` — after bench calibration (bring-up step 6)
- The `ENABLE_*` flags — set to 0 for anything not wired yet

Everything else (thresholds, photoperiod, brightness) is editable live from
the phone and survives reboots.

## 3 · Flash

1. Plug in the board (micro-USB). If no COM port appears, install the
   [CP210x driver](https://www.silabs.com/developers/usb-to-uart-bridge-vcp-drivers).
2. **Tools → Board → esp32 → DOIT ESP32 DEVKIT V1**, pick the COM port.
3. Upload. If it hangs at `Connecting...`, hold the **BOOT** button on the
   board until upload starts.
4. **Tools → Serial Monitor** at **115200** — it prints the IP address.

## 4 · Open the app

- Same Wi-Fi: browse to the printed IP, or `http://terrarium.local`.
- No Wi-Fi available: the board makes its own hotspot **Terrarium**
  (password `terrarium123`) → browse to `http://192.168.4.1`.
- In Chrome: **⋮ → Add to Home screen** — it now opens like an app.

## What the logic does

| Thing | Behaviour |
|---|---|
| Watering | Soil avg below threshold → mist burst 90 s → 20 min soak → re-check. Hard cap 30 min/day. |
| Humidity | Below low limit → mist on until high limit, max 5 min per burst, 3 min cooldown. |
| Grow light | On within photoperiod when lux is below the on-threshold; off above the off-threshold. No NTP → lux rules alone. |
| Manual mode | Buttons control outputs; mist auto-off after 10 min if forgotten. |
| **Interlock** | Float switch says empty → **both mist channels forced off, even in manual.** Buzzer (if fitted) sounds. |
| Offline | All of the above runs on the board. Wi-Fi loss changes nothing. |

## Files

- `terrarium.ino` — logic, safety, web API
- `config.h` — pins, credentials, calibration, all tunables
- `webui.h` — the dashboard page served to the phone
