# Acceptance gate after the UI theme rebuild, via docker.exe (WSL integration
# socket is absent after the Docker Desktop restart; the Windows pipe works).
$ErrorActionPreference = 'Continue'
$root = "C:\Users\Idex\Documents\legal final\legal\legal"
Set-Location $root
function Stop-Stack { docker.exe compose -f compose.yml down 2>$null | Out-Null }

Write-Output "=== G1. compose config quiet ==="
docker.exe compose -f compose.yml config --quiet
if ($LASTEXITCODE -ne 0) { Write-Output "FAIL_CONFIG"; exit 41 }
Write-Output "CONFIG_OK"

Write-Output "=== G2. clean down + up (pull never, no build) ==="
docker.exe compose -f compose.yml down 2>$null | Out-Null
docker.exe compose -f compose.yml up -d --pull never --no-build
if ($LASTEXITCODE -ne 0) { Write-Output "FAIL_UP"; exit 42 }
Write-Output "UP_OK"

Write-Output "=== G3. wait for backend healthy ==="
$healthy = $false; $h = ""; $i = 0
for ($i = 1; $i -le 60; $i++) {
  Start-Sleep -Seconds 2
  $h = docker.exe compose ps backend --format "{{.Health}}" 2>$null | Select-Object -First 1
  if ($h -eq "healthy") { $healthy = $true; break }
}
if (-not $healthy) {
  Write-Output "FAIL_HEALTH last=$h"
  docker.exe compose ps
  docker.exe compose logs --tail 40 backend
  Stop-Stack
  exit 43
}
Write-Output "BACKEND_HEALTHY after $($i*2 - 2)s"

Write-Output "=== G4. HTTP through the published frontend ==="
try {
  $r = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:8080/api/health" -TimeoutSec 30
  if ($r.StatusCode -ne 200) { throw "status $($r.StatusCode)" }
} catch { Write-Output "FAIL_HEALTH_HTTP=$($_.Exception.Message)"; Stop-Stack; exit 44 }
Write-Output "HEALTH_200"

try {
  $r2 = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:8080/" -TimeoutSec 30
  if ($r2.StatusCode -ne 200) { throw "status $($r2.StatusCode)" }
  $html = $r2.Content
} catch { Write-Output "FAIL_ROOT=$($_.Exception.Message)"; Stop-Stack; exit 45 }
Write-Output "ROOT_200"

Write-Output "=== G5. served UI carries the olive/red theme ==="
if ($html -notmatch 'Court of Inquiry Generation') { Write-Output "FAIL_TITLE"; Stop-Stack; exit 46 }
if ($html -notmatch 'theme-color') { Write-Output "FAIL_THEME_META"; Stop-Stack; exit 47 }
$m = [regex]::Match($html, '/assets/[^"]+\.css')
if (-not $m.Success) { Write-Output "FAIL_NO_CSS_ASSET"; Stop-Stack; exit 48 }
$assetUrl = "http://127.0.0.1:8080" + $m.Value
try { $css = (Invoke-WebRequest -UseBasicParsing -Uri $assetUrl -TimeoutSec 30).Content }
catch { Write-Output "FAIL_CSS_FETCH=$($_.Exception.Message)"; Stop-Stack; exit 49 }
$olive = ([regex]::Matches($css, '#5d7430|#171b0e|#10140a')).Count
$red = ([regex]::Matches($css, '#b33324|#c23a2c')).Count
$old = ([regex]::Matches($css, '556b2f|9b2b20|c9d0a6|f7f6ea|44521e|3e4a21')).Count
Write-Output "asset=$($m.Value) olive=$olive red=$red old=$old"
if ($olive -eq 0 -or $red -eq 0 -or $old -ne 0) { Write-Output "FAIL_SERVED_PALETTE"; Stop-Stack; exit 50 }
Write-Output "SERVED_PALETTE_OK"

Write-Output "=== G6. containers + compose down ==="
docker.exe compose ps
Stop-Stack
if ($LASTEXITCODE -ne 0) { Write-Output "FAIL_DOWN"; exit 51 }
Write-Output "DOWN_OK"
Write-Output "=== THEME_GATE_OK ==="
