# Serial data logger for the terrarium bench / box experiments.
# Reads the firmware's 10 s status line from COM3 and appends one CSV row per line.
#   [Ns] temp T  RH H  room T2/H2  lux L  soil S% (raw a/b)  leak N[!]  tank:OK  auto  water:0 mist:1 light:1  rssi R
# Also records the firmware's "[hum] ... mist on/off" and "[water]" events in the event column.
# Stops when -Hours elapse or when the file named by -StopFile appears. Pure ASCII.
param(
  [string]$Port = "COM3",
  [string]$Out = "",
  [double]$Hours = 6,
  [string]$StopFile = ""
)
$ErrorActionPreference = "Continue"
if ($Out -eq "") { $Out = Join-Path $PSScriptRoot ("..\data\box-" + (Get-Date -Format "yyyy-MM-dd-HHmm") + ".csv") }
if ($StopFile -eq "") { $StopFile = Join-Path $PSScriptRoot "..\data\STOP-LOGGER" }
$dir = Split-Path $Out
if (!(Test-Path $dir)) { New-Item -ItemType Directory -Path $dir | Out-Null }
if (!(Test-Path $Out)) {
  "pc_time,uptime_s,temp_in_c,rh_in_pct,temp_room_c,rh_room_pct,lux,soil_pct,soil_raw1,soil_raw2,leak_raw,tank_ok,mode,water,mist,light,rssi,event" | Out-File -FilePath $Out -Encoding ascii
}
$p = New-Object System.IO.Ports.SerialPort($Port, 115200, "None", 8, "one")
$p.ReadTimeout = 2000
$p.Open()
$deadline = (Get-Date).AddHours($Hours)
$rx = '^\[(\d+)s\] temp (\S+)\s+RH (\S+)\s+room (\S+)/(\S+)\s+lux (\S+)\s+soil (\d+)% \(raw (\d+)/(\d+)\)\s+leak (\d+)(!?)\s+tank:(\S+)\s+(\S+)\s+water:(\d) mist:(\d) light:(\d)\s+rssi (-?\d+)'
$pendingEvent = ""
$rows = 0
while ((Get-Date) -lt $deadline -and !(Test-Path $StopFile)) {
  try { $line = $p.ReadLine() } catch { continue }
  $line = $line -replace "[^\x20-\x7e]", ""
  if ($line -match '^\[(hum|water)\]') { $pendingEvent = ($pendingEvent + " " + $line).Trim(); continue }
  $m = [regex]::Match($line, $rx)
  if (!$m.Success) { continue }
  $g = $m.Groups
  $tank = if ($g[12].Value -eq "OK") { 1 } else { 0 }
  $ev = $pendingEvent -replace ",", ";"
  $row = ((Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $g[1].Value, $g[2].Value, $g[3].Value, $g[4].Value, $g[5].Value, $g[6].Value, $g[7].Value, $g[8].Value, $g[9].Value, $g[10].Value, $tank, $g[13].Value, $g[14].Value, $g[15].Value, $g[16].Value, $g[17].Value, $ev) -join ","
  Add-Content -Path $Out -Value $row -Encoding ascii
  $pendingEvent = ""
  $rows++
}
$p.Close()
"logger stopped after $rows rows -> $Out" | Add-Content -Path (Join-Path $dir "logger.log")
