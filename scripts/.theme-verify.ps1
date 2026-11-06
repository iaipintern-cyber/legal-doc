# NTFS-side verification of the refreshed transfer artifacts.
# Same battery used for the original package: every large file is read by
# Windows-native tools (authoritative; never trust WSL page-cache views).
$ErrorActionPreference = 'Continue'
$root = "C:\Users\Idex\Documents\legal final\legal\legal"
Set-Location $root
$script:fail = 0
function Fail($m) { Write-Output "FAIL: $m"; $script:fail = 1 }

# ---- V1. source archive ----
Write-Output "=== V1. source archive (full bsdtar stream = gzip CRC check) ==="
$src = Join-Path $root "offline\legal-source.tar.gz"
try {
  $entries = & tar -tzf $src 2>&1
  if ($LASTEXITCODE -ne 0) { throw "tar exit $LASTEXITCODE" }
} catch { Fail("source tar stream: $_"); $entries = @() }
$srcCount = ($entries | Measure-Object).Count
Write-Output "  entries = $srcCount"
$forbidden = @($entries | Where-Object { $_ -match '\.env($|\.|/)|node_modules|/\.venv/|/venv/|__pycache__|\.pyc$|\.bat$|\.exe$|/wheels/' })
Write-Output ("  forbidden entries = " + $forbidden.Count)
if ($forbidden.Count -gt 0) { $forbidden | Select-Object -First 10; Fail("forbidden entries in source") }
# Dynamic completeness (no fixed counts): the operator uses the app live, so
# backend/uploads may GROW after packaging. Assert instead that every packaged
# upload file exists on disk, and that the package never holds fewer uploads
# than the original 42-file baseline.
$uploads = @($entries | Where-Object { $_ -like 'backend/uploads/*' -and $_ -notlike '*/' })
$upDir = Join-Path $root "backend\uploads"
$diskUp = @()
if (Test-Path $upDir) {
  $diskUp = @(Get-ChildItem $upDir -Recurse -File | ForEach-Object { $_.FullName.Substring($upDir.Length + 1) })
}
$missingUp = @()
foreach ($u in $uploads) {
  $rel = ($u -replace '^backend/uploads/', '') -replace '/', '\'
  if ($diskUp -notcontains $rel) { $missingUp += $rel }
}
Write-Output ("  uploads in tar = " + $uploads.Count + " ; on disk now = " + $diskUp.Count)
if ($uploads.Count -lt 42) { Fail("uploads $($uploads.Count) below original 42-file baseline") }
if ($missingUp.Count -gt 0) { $missingUp | Select-Object -First 10; Fail("packaged uploads missing on disk: $($missingUp.Count)") }
if ($uploads.Count -ge 42 -and $missingUp.Count -eq 0) { Write-Output "  UPLOADS_COMPLETE tar->disk, baseline>=42" }
# Informational only: packaged files since deleted/renamed on disk (live edits).
$missingAny = @()
foreach ($e in @($entries | Where-Object { $_ -notlike '*/' })) {
  if (-not (Test-Path (Join-Path $root ($e -replace '/', '\')))) { $missingAny += $e }
}
Write-Output ("  packaged entries no longer on disk (informational) = " + $missingAny.Count)
$missingAny | Select-Object -First 10 | ForEach-Object { Write-Output "    gone-from-disk: $_" }
$css = (& tar -xOf $src frontend/src/index.css) -join "`n"
$jsx = (& tar -xOf $src frontend/src/App.jsx) -join "`n"
$text = $css + "`n" + $jsx
$hasNew = ($text -match '5d7430') -and ($text -match '171b0e|10140a')
$hasOld = ($text -match '556b2f|c9d0a6|f7f6ea|44521e|3e4a21')
Write-Output "  palette in packaged source: new=$hasNew old=$hasOld"
if (-not $hasNew) { Fail("new palette missing in packaged source") }
if ($hasOld) { Fail("old palette present in packaged source") }
$srcHash = (Get-FileHash $src -Algorithm SHA256).Hash
Write-Output "  SHA256 = $srcHash"

# ---- V2. images archive ----
Write-Output "=== V2. images archive (full stream) ==="
$img = Join-Path $root "offline\images\legal-images.tar.gz"
try {
  $ientries = & tar -tzf $img 2>&1
  if ($LASTEXITCODE -ne 0) { throw "tar exit $LASTEXITCODE" }
} catch { Fail("images tar stream: $_"); $ientries = @() }
$icount = ($ientries | Measure-Object).Count
Write-Output "  entries = $icount"
$manifest = (& tar -xOf $img manifest.json) -join "`n"
$tags = @('legal-backend:1.0','legal-frontend:1.0','legal-frontend-debug:1.0','ollama/ollama:0.6.8')
foreach ($t in $tags) { if ($manifest -notmatch [regex]::Escape($t)) { Fail("RepoTag missing in manifest: $t") } }
Write-Output "  RepoTags checked: 4"
$imgHash = (Get-FileHash $img -Algorithm SHA256).Hash
Write-Output "  SHA256 = $imgHash"

# ---- V3. bundle inventory ----
Write-Output "=== V3. bundle (full stream + inventory) ==="
$bun = Join-Path $root "transfer\legal-bundle.tar.gz"
try {
  $bentries = & tar -tzf $bun 2>&1
  if ($LASTEXITCODE -ne 0) { throw "tar exit $LASTEXITCODE" }
} catch { Fail("bundle tar stream: $_"); $bentries = @() }
$blobs = @($bentries | Where-Object { $_ -match 'ollama/models/blobs/sha256-' }).Count
$mani = @($bentries | Where-Object { $_ -match 'gemma3/4b$' }).Count
$bImg = @($bentries | Where-Object { $_ -match 'images/legal-images.tar\.gz$' }).Count
$bSrc = @($bentries | Where-Object { $_ -match 'legal-source\.tar\.gz$' }).Count
$bPlug = @($bentries | Where-Object { $_ -match 'docker-compose-linux-x86_64(\.sha256)?$' }).Count
Write-Output "  model blobs=$blobs (want 7), gemma manifest=$mani (want 1), images=$bImg (want 1), source=$bSrc (want 1), plugin+sha=$bPlug (want 2)"
if ($blobs -ne 7) { Fail("bundle model blobs $blobs != 7") }
if ($mani -lt 1) { Fail("bundle gemma manifest missing") }
if ($bImg -ne 1) { Fail("bundle images archive missing") }
if ($bSrc -ne 1) { Fail("bundle source archive missing") }
if ($bPlug -ne 2) { Fail("bundle compose plugin entries $bPlug != 2") }
$stray = @($bentries | Where-Object { $_ -match 'id_ed25519' }).Count
Write-Output "  stray container keys = $stray (want 0)"
if ($stray -ne 0) { $bentries | Where-Object { $_ -match 'id_ed25519' } | Select-Object -First 5; Fail("stray id_ed25519 in bundle") }
$bunHash = (Get-FileHash $bun -Algorithm SHA256).Hash
Write-Output "  SHA256 = $bunHash"

# ---- V4. parts + SHA256SUMS + rejoin ----
Write-Output "=== V4. split parts vs SHA256SUMS ==="
$sumFile = Join-Path $root "transfer\SHA256SUMS"
$sums = @(Get-Content $sumFile)
Write-Output ("  SHA256SUMS lines = " + $sums.Count)
foreach ($line in $sums) {
  $bits = ($line -split '\s+', 2)
  if ($bits.Count -ne 2) { Fail("bad SHA256SUMS line: $line"); continue }
  $p = Join-Path $root ("transfer\" + $bits[1])
  if (-not (Test-Path $p)) { Fail("missing part: " + $bits[1]); continue }
  $h = (Get-FileHash $p -Algorithm SHA256).Hash
  if ($h -ne $bits[0].ToUpper()) { Fail("part hash mismatch: " + $bits[1]) }
  else { Write-Output ("  PART_OK " + $bits[1] + " bytes=" + (Get-Item $p).Length) }
}
$partSum = (Get-ChildItem (Join-Path $root "transfer\legal-bundle.part-*") | Measure-Object Length -Sum).Sum
$bunLen = (Get-Item $bun).Length
Write-Output "  parts sum = $partSum ; bundle = $bunLen"
if ($partSum -ne $bunLen) { Fail("parts sum != bundle size") }

Write-Output "=== V5. rejoin round-trip ==="
$rejoin = Join-Path $env:TEMP "legal-rejoin-test.tar.gz"
if (Test-Path $rejoin) { Remove-Item $rejoin -Force }
cmd /c "copy /b `"$root\transfer\legal-bundle.part-*`" + `"$sumFile`" `"$rejoin.partprobe`"" | Out-Null
# real rejoin: just the parts (wildcard copy), no manifest
if (Test-Path "$rejoin.partprobe") { Remove-Item "$rejoin.partprobe" -Force }
$partList = (Get-ChildItem (Join-Path $root "transfer\legal-bundle.part-*") | Sort-Object Name | ForEach-Object { $_.FullName })
$argLine = ($partList | ForEach-Object { "`"$_`"" }) -join ' + '
cmd /c "copy /b $argLine `"$rejoin`"" | Out-Null
if (-not (Test-Path $rejoin)) { Fail("rejoin copy failed") } else {
  $rh = (Get-FileHash $rejoin -Algorithm SHA256).Hash
  if ($rh -eq $bunHash) { Write-Output "  REJOIN_MATCH parts reassemble byte-identical" }
  else { Fail("rejoin hash $rh != bundle $bunHash") }
  Remove-Item $rejoin -Force
}

# ---- V6. docker load fidelity ----
Write-Output "=== V6. docker load from the shipped archive ==="
$before = @{}
foreach ($t in $tags) { $before[$t] = (docker.exe image inspect $t --format '{{.Id}}' 2>$null) }
$loadOut = docker.exe load -i $img 2>&1 | Out-String
Write-Output $loadOut
foreach ($t in $tags) {
  $id = docker.exe image inspect $t --format '{{.Id}}' 2>$null
  $plat = docker.exe image inspect $t --format '{{.Os}}/{{.Architecture}}' 2>$null
  if ($id -ne $before[$t]) { Fail("ID changed on load: $t ($($before[$t]) -> $id)") }
  if ($plat -ne 'linux/amd64') { Fail("platform $t = $plat") }
  Write-Output "  $t id UNCHANGED $plat"
}

Write-Output ""
if ($script:fail -eq 0) { Write-Output "=== THEME_VERIFY_OK ===" } else { Write-Output "=== THEME_VERIFY_FAILED ==="; exit 1 }
