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

[ -f assets/cp210x/silabser.inf ] || { echo "!! assets/cp210x is missing the CP210x driver files"; exit 1; }

echo "== building"
python -m PyInstaller --noconfirm --onefile --console --name TerrariumConsole \
  --add-data "$(pwd -W 2>/dev/null || pwd)/assets;assets" \
  --hidden-import serial.tools.list_ports \
  --distpath dist --workpath build --specpath build terrarium_console.py > build.log 2>&1

ls -la dist/TerrariumConsole.exe
cp dist/TerrariumConsole.exe "$ROOT/TerrariumConsole.exe"
echo "== done: $ROOT/TerrariumConsole.exe"
