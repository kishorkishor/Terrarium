# Terrarium Console

One file. Copy `TerrariumConsole.exe` to any Windows laptop, double-click it, and it:

1. opens **http://localhost:8765** in your browser
2. finds the ESP32 on USB and on the Wi-Fi (tries `terrarium.local`, the last known
   address, the board's own hotspot, then scans the whole subnet)
3. runs eight checks — internet, USB driver, board on USB, serial port free,
   toolchain, board on Wi-Fi, firmware, sensors — and explains every failure in
   plain words with a **Fix** button
4. installs what's missing when you ask: the CP210x USB driver (Windows shows a
   UAC prompt — click Yes) and the arduino-cli toolchain (downloaded on first use;
   if Arduino IDE is already on the PC its ESP32 core is reused, no download)
5. flashes the terrarium firmware, or the bench tools, to the board
6. streams the board's serial log live, and can embed the board's dashboard

```
TerrariumConsole.exe            normal
TerrariumConsole.exe --auto     also install driver + toolchain without asking
TerrariumConsole.exe --no-browser
```

Everything it installs goes in `%LOCALAPPDATA%\TerrariumConsole` — nothing else
on the machine is touched. Delete that folder to uninstall.

## First run on a new laptop

1. Plug the ESP32 in with a **data** USB cable.
2. Run the exe. Windows SmartScreen will say "unrecognised app" because it isn't
   code-signed — click **More info → Run anyway**.
3. If **USB driver** is red, press its Fix button, approve the UAC prompt.
4. If **Toolchain** is amber and you want to flash firmware, press its Fix button
   and wait (a few hundred MB the first time, unless Arduino IDE is already there).
5. If **Board on Wi-Fi** is red: the firmware joins the Wi-Fi named in its config.
   Either join that network with the laptop, or type the new network into the
   Wi-Fi box, **Save**, then **Flash terrarium firmware**. With no router at all the
   board makes its own hotspot `Terrarium` / `terrarium123` at `192.168.4.1`.

## What the checks mean when they fail

| Check | Usual cause |
|---|---|
| Board on USB | charge-only cable, or driver not installed |
| Serial port | the Arduino IDE's Serial Monitor is holding the port — close that window |
| Board on Wi-Fi | laptop on a different network / 5 GHz band / board powered off |
| Sensors: BME280 | CSB must be wired to 3V3 *before* power-up; unplug USB fully and replug |
| Sensors: BH1750 | ADDR to GND, SDA D21, SCL D22 (they are not adjacent pins) |
| Sensors: soil ~0 | probe unplugged or VCC not on 3V3 |

## Security note

The exe contains the firmware source, **including `config.h`** — whatever
Wi-Fi is in that file at build time ships inside the exe (`build.sh` warns
when it isn't the placeholders). The published build carries only
`YOUR_WIFI_NAME` / `YOUR_WIFI_PASSWORD`; real credentials are entered at
runtime (console Wi-Fi box, or the board's own dashboard) and stay on this
machine / the board.

## Rebuilding after firmware changes

The exe carries a *snapshot* of `firmware/`. After editing any sketch:

```
cd TERRARIUM/tools/console
./build.sh
```

That restages the firmware, rebuilds, and copies the new exe to the project root.
Needs Python 3 with `pyserial` and `pyinstaller`.

## Files

- `terrarium_console.py` — the whole application (~500 lines, stdlib + pyserial)
- `assets/console.html` — the page it serves
- `assets/firmware/` — snapshot of the sketches it can flash
- `assets/cp210x/` — Silicon Labs CP210x VCP driver (see the licence file inside)
