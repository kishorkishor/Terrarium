# Box humidity characterisation: 1 Hz logger + scripted protocol, self-contained.
# Polls the firmware with "CMD STATUS" once per second, logs one CSV row per reply,
# and walks the board through phases:
#   P0 baseline   mist off, 2 min
#   P1 rise       manual mist ON until inside RH >= RISE_TARGET or RISE_MAX_S
#   P2 decay      mist off until inside RH <= DECAY_TARGET or DECAY_MAX_S
#   P3 auto-cap10 auto, band 85-92, burst cap 600 s, AUTO1_S
#   P4 auto-80-90 auto, band 80-90, burst cap 600 s, AUTO2_S
#   P5 restore    firmware defaults back (SET persists to NVS), auto mode
# Stops early (and still restores) when the STOP file appears. Pure ASCII.
param(
  [string]$Port = "COM3",
  [string]$Out = "",
  [string]$StopFile = "",
  [int]$RISE_TARGET = 95, [int]$RISE_MAX_S = 600,
  [int]$DECAY_TARGET = 80, [int]$DECAY_MAX_S = 1500,
  [int]$AUTO1_S = 2400, [int]$AUTO2_S = 1800
)
$ErrorActionPreference = "Continue"
$dataDir = Join-Path $PSScriptRoot "..\data"
if (!(Test-Path $dataDir)) { New-Item -ItemType Directory -Path $dataDir | Out-Null }
$stamp = Get-Date -Format "yyyy-MM-dd-HHmm"
if ($Out -eq "") { $Out = Join-Path $dataDir ("box-exp-" + $stamp + ".csv") }
if ($StopFile -eq "") { $StopFile = Join-Path $dataDir "STOP-LOGGER" }
$notes = Join-Path $dataDir ("box-exp-" + $stamp + ".notes.txt")
"pc_time,uptime_s,phase,temp_in_c,rh_in_pct,temp_room_c,rh_room_pct,mist,water,mode,humLo,humHi,humMax,event" | Out-File -FilePath $Out -Encoding ascii
function Note($s) { $line = (Get-Date -Format "HH:mm:ss") + "  " + $s; Add-Content -Path $notes -Value $line -Encoding ascii }

$p = New-Object System.IO.Ports.SerialPort($Port, 115200, "None", 8, "one")
$p.ReadTimeout = 900; $p.NewLine = "`n"
$p.Open()
Start-Sleep -Milliseconds 300

$script:events = ""
function Send($cmd) {
  # send one command, return the parsed #R reply (or $null); stray [hum]/[water] lines are kept as events
  $p.DiscardInBuffer()
  $p.WriteLine($cmd)
  $sw = [Diagnostics.Stopwatch]::StartNew()
  while ($sw.ElapsedMilliseconds -lt 1500) {
    try { $l = $p.ReadLine() } catch { continue }
    $l = $l -replace "[^\x20-\x7e]", ""
    if ($l -match '^\[(hum|water)\]') { $script:events = ($script:events + " " + $l).Trim(); continue }
    if ($l.StartsWith("#R ")) {
      try { return ($l.Substring(3) | ConvertFrom-Json) } catch { return $null }
    }
  }
  return $null
}
function Cfg($kv) { $r = Send ("CMD SET " + $kv); Note ("SET " + $kv + " -> humLo=" + $r.cfg.humLo + " humHi=" + $r.cfg.humHi + " humMax=" + $r.cfg.humMax + " manMax=" + $r.cfg.manMax) }
function Mode($m) { $r = Send ("CMD MODE " + $m); Note ("MODE " + $m + " -> " + $r.mode) }
function Mist($v) { $r = Send ("CMD OUT hum " + $v); Note ("OUT hum " + $v + " -> mist=" + $r.out.hum + $(if ($r.err) { " ERR " + $r.err } else { "" })) }

$phase = "P0-baseline"; $phaseStart = Get-Date; $stopped = $false; $script:bad = 0
Note "START protocol; file $Out"
Cfg "soilDry=5 waterRun=10 waterCap=1 manMax=20 humCool=180"
Mode "manual"; Mist 0

function Elapsed { return ((Get-Date) - $script:phaseStart).TotalSeconds }
function GoTo($name) { $script:phase = $name; $script:phaseStart = Get-Date; Note ("PHASE " + $name) }

while ($true) {
  if (Test-Path $StopFile) { Note "STOP file seen"; $stopped = $true; break }
  $r = Send "CMD STATUS"
  if ($r -ne $null) {
    $ev = $script:events -replace ",", ";"; $script:events = ""
    $row = ((Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $r.up, $phase, $r.temp, $r.hum, $r.temp2, $r.hum2, $r.out.hum, $r.out.water, $r.mode, $r.cfg.humLo, $r.cfg.humHi, $r.cfg.humMax, $ev) -join ","
    Add-Content -Path $Out -Value $row -Encoding ascii
    $rh = [double]$r.hum
    $e = Elapsed
    # sensor sanity: a wet / latched BME280 returns ~179 C or a stuck 100 %. 30 s of that = abort (mist off, restore).
    if (($r.temp -ne $null -and [double]$r.temp -gt 60) -or $rh -ge 100 -or $r.temp -eq $null) { $script:bad++ } else { $script:bad = 0 }
    if ($script:bad -ge 30) { Note ("SENSOR BAD for 30 s (temp=" + $r.temp + " rh=" + $r.hum + ") -> abort"); Mist 0; $stopped = $true; break }
    switch ($phase) {
      "P0-baseline" { if ($e -ge 120) { GoTo "P1-rise"; Mist 1 } }
      "P1-rise"     { if ($rh -ge $RISE_TARGET -or $e -ge $RISE_MAX_S) { Note ("rise ended at RH " + $rh + " after " + [int]$e + " s"); Mist 0; GoTo "P2-decay" } }
      "P2-decay"    { if ($rh -le $DECAY_TARGET -or $e -ge $DECAY_MAX_S) { Note ("decay ended at RH " + $rh + " after " + [int]$e + " s"); Cfg "humLo=85 humHi=92 humMax=600"; Mode "auto"; GoTo "P3-auto-85-92-cap600" } }
      "P3-auto-85-92-cap600" { if ($e -ge $AUTO1_S) { Cfg "humLo=80 humHi=90 humMax=600"; GoTo "P4-auto-80-90-cap600" } }
      "P4-auto-80-90-cap600" { if ($e -ge $AUTO2_S) { GoTo "P5-restore"; break } }
    }
    if ($phase -eq "P5-restore") { break }
  }
  Start-Sleep -Milliseconds 1000
}
# restore firmware defaults (SET persists to NVS) and leave the board in auto
Cfg "soilDry=35 humLo=75 humHi=90 humMax=300 humCool=180 waterRun=90 waterSoak=20 waterCap=30 manMax=10"
Mode "auto"
Note ("END protocol (stopped=" + $stopped + ")")
$p.Close()
