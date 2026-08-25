function GET($u) {
  for ($i = 0; $i -lt 10; $i++) {
    try { return (Invoke-WebRequest -Uri $u -TimeoutSec 12 -UseBasicParsing).Content }
    catch { Start-Sleep -Milliseconds 700 }
  }
  return "ERR"
}
Start-Sleep -Seconds 15
foreach ($n in @("water","hum","light","buzz","fan")) {
  $on  = GET "http://192.168.0.169/api/out?name=$n&state=1"
  Start-Sleep -Milliseconds 600
  $off = GET "http://192.168.0.169/api/out?name=$n&state=0"
  if ($on -eq "ERR" -or $off -eq "ERR") { Write-Output "$n : ERR"; continue }
  $a = ($on  | ConvertFrom-Json).out.$n
  $b = ($off | ConvertFrom-Json).out.$n
  Write-Output "$n : on=$a off=$b"
  Start-Sleep -Milliseconds 400
}
