function GET($u) {
  for ($i = 0; $i -lt 8; $i++) {
    try { return (Invoke-WebRequest -Uri $u -TimeoutSec 12 -UseBasicParsing).Content }
    catch { Start-Sleep -Milliseconds 600 }
  }
  return "ERR"
}
$null = GET "http://192.168.0.169/api/mode?m=manual"
Start-Sleep -Milliseconds 500
foreach ($i in 1..3) {
  $a = GET "http://192.168.0.169/api/out?name=water&state=1"
  if ($a -match '"water":1') { Write-Output "cycle $i : ON  -> expect ~5V   (holding 6s)" }
  else { Write-Output "cycle $i : ON REJECTED -> $a" }
  Start-Sleep -Seconds 6
  $b = GET "http://192.168.0.169/api/out?name=water&state=0"
  if ($b -match '"water":0') { Write-Output "cycle $i : OFF -> expect ~0V   (holding 5s)" }
  else { Write-Output "cycle $i : OFF failed" }
  Start-Sleep -Seconds 5
}
Write-Output "done"
