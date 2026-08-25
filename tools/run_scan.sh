#!/bin/bash
CFG="C:\Users\kisho\Desktop\TERRARIUM\tools\arduino-cli.yaml"
SK="C:\Users\kisho\Desktop\TERRARIUM\firmware\i2c-scan"
OUT=/c/Users/kisho/Desktop/TERRARIUM/tools/scan-result.txt
: > "$OUT"
echo "waiting for COM3 to be released..." >> "$OUT"
ST=$(powershell.exe -NoProfile -Command '$ok=$false; for($i=0;$i -lt 700;$i++){ try{$p=New-Object System.IO.Ports.SerialPort("COM3",115200);$p.Open();$p.Close();$ok=$true;break}catch{Start-Sleep -Seconds 3} }; if($ok){"FREE"}else{"TIMEOUT"}' | tr -d '\r')
echo "port state: $ST" >> "$OUT"
if [ "$ST" != "FREE" ]; then echo "gave up waiting" >> "$OUT"; exit 1; fi
echo "=== uploading scanner ===" >> "$OUT"
./arduino-cli.exe upload -p COM3 --fqbn esp32:esp32:esp32 --config-file "$CFG" "$SK" >> "$OUT" 2>&1
echo "=== serial output ===" >> "$OUT"
powershell.exe -NoProfile -Command '
$p = New-Object System.IO.Ports.SerialPort("COM3",115200,"None",8,"one")
$p.ReadTimeout = 1500
$p.Open()
$p.DtrEnable=$false; $p.RtsEnable=$true; Start-Sleep -Milliseconds 150
$p.RtsEnable=$false
$sw=[Diagnostics.Stopwatch]::StartNew()
while($sw.Elapsed.TotalSeconds -lt 18){ try{ $p.ReadLine() }catch{} }
$p.Close()' >> "$OUT" 2>&1
echo "=== done ===" >> "$OUT"
