#!/bin/bash
# Rebuild TerrariumConsole.exe after ANY change to the firmware or the console.
# The exe carries a snapshot of firmware/ inside it, so an old exe flashes old code.
#
#   cd TERRARIUM/tools/console && ./build.sh
#
# Needs: Python 3 with pyserial + pyinstaller  (pip install pyserial pyinstaller)
set -e
cd "$(dirname "$0")"
ROOT="$(cd ../.. && pwd)"

echo "== staging firmware from $ROOT/firmware"
rm -rf assets/firmware
mkdir -p assets/firmware/bench-web assets/firmware/i2c-scan
cp -r "$ROOT/firmware/terrarium" assets/firmware/
cp "$ROOT/firmware/bench-web/bench-web.ino" assets/firmware/bench-web/
cp "$ROOT/firmware/i2c-scan/i2c-scan.ino" assets/firmware/i2c-scan/
# never ship a stale generated secret; the console regenerates it from config.h
rm -f assets/firmware/bench-web/wifi_secret.h

# version stamp: a new exe over an old work folder replaces the sketches
# (ensure_work_firmware compares this against %LOCALAPPDATA%'s copy)
date +%s > assets/firmware/VERSION

[ -f assets/cp210x/silabser.inf ] || { echo "!! assets/cp210x is missing the CP210x driver files"; exit 1; }
[ -d assets/libraries/Adafruit_BME280_Library ] || { echo "!! assets/libraries is missing the bundled sensor libraries"; exit 1; }

# the exe embeds config.h - warn when it is about to carry a real network
if ! grep -q 'YOUR_WIFI_NAME' "$ROOT/firmware/terrarium/config.h"; then
  echo "!! firmware/terrarium/config.h holds a real Wi-Fi name - this exe will carry it."
  echo "   Fine for private use; do NOT publish this build."
fi

echo "== building"
python -m PyInstaller --noconfirm --onefile --console --name TerrariumConsole \
  --add-data "$(pwd -W 2>/dev/null || pwd)/assets;assets" \
  --hidden-import serial.tools.list_ports \
  --distpath dist --workpath build --specpath build terrarium_console.py > build.log 2>&1

ls -la dist/TerrariumConsole.exe
cp dist/TerrariumConsole.exe "$ROOT/TerrariumConsole.exe"
echo "== done: $ROOT/TerrariumConsole.exe"
