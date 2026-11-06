#!/usr/bin/env bash
# Re-export all four images (setup.md section 2) + rebuild the transfer bundle
# (setup.md section 4) after the UI theme refresh.
# Writes go to .partial first, then sync + rename (WSL page-cache safety);
# every artifact is re-verified NTFS-side afterwards by .theme-verify.ps1.
set -uo pipefail
cd "/mnt/c/Users/Idex/Documents/legal final/legal/legal" || exit 1

IMG=offline/images/legal-images.tar.gz
SRC=offline/legal-source.tar.gz
BUN=transfer/legal-bundle.tar.gz

echo "=== P1. export images (docker save | gzip -1) ==="
if docker.exe compose ps -q 2>/dev/null | grep -q .; then
  echo "FAIL_STACK_STILL_UP"; exit 80
fi
rm -f "$IMG.partial"
docker.exe save legal-backend:1.0 legal-frontend:1.0 legal-frontend-debug:1.0 ollama/ollama:0.6.8 | gzip -1 > "$IMG.partial"
rc=$?
sync
if [ "$rc" != "0" ]; then echo "FAIL_SAVE rc=$rc"; exit 81; fi
sz=$(stat -c %s "$IMG.partial")
if [ "$sz" -lt 1000000000 ]; then echo "FAIL_SAVE_SIZE=$sz"; exit 82; fi
mv -f "$IMG.partial" "$IMG"
sync
echo "IMAGES_WRITTEN bytes=$sz"

echo "=== P2. source archive (setup.md section 4 recipe) ==="
rm -f "$SRC.partial"
tar --exclude='node_modules' --exclude='dist' --exclude='.venv' --exclude='venv' \
    --exclude='__pycache__' --exclude='*.pyc' --exclude='.env' --exclude='.env.*' \
    --exclude='*.bat' --exclude='*.exe' --exclude='wheels' \
    -czf "$SRC.partial" backend frontend data compose.yml compose.debug.yml .dockerignore setup.md README.md
rc=$?
sync
[ "$rc" = "0" ] || { echo "FAIL_SOURCE_TAR rc=$rc"; exit 83; }
mv -f "$SRC.partial" "$SRC"
sync
echo "SOURCE_WRITTEN bytes=$(stat -c %s "$SRC")"

echo "=== P3. bundle ==="
rm -f "$BUN.partial"
tar -czf "$BUN.partial" -C offline .
rc=$?
sync
[ "$rc" = "0" ] || { echo "FAIL_BUNDLE_TAR rc=$rc"; exit 84; }
mv -f "$BUN.partial" "$BUN"
sync
echo "BUNDLE_WRITTEN bytes=$(stat -c %s "$BUN")"

echo "=== P4. split + checksums ==="
rm -f transfer/legal-bundle.part-*
split --bytes=3800000000 --numeric-suffixes=0 --suffix-length=3 "$BUN" transfer/legal-bundle.part- || { echo "FAIL_SPLIT"; exit 85; }
(cd transfer && sha256sum legal-bundle.part-* > SHA256SUMS) || { echo "FAIL_SHA"; exit 86; }
cat transfer/SHA256SUMS
ls -l transfer/legal-bundle.part-* | awk '{print $5, $9}'
echo "=== PACKAGE_DONE ==="
