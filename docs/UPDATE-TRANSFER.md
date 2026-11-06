# Code + Image Update Transfer — 03 Nov 2026

> **Plain-text DVD version:** `DVD-TRANSFER-COMMANDS.txt` — same steps in
> copy-paste form plus the exact burn list for one 4.3 GB DVD.
> Its checksum file `DVD-SHA256SUMS.txt` covers only the files actually
> burned (code part + two image tars).

Update for the air-gapped Linux PC that already runs the full stack
(frontend + backend + Ollama `gemma3:4b` from the original bundle).

Everything below has been rebuilt/verified **on this PC** against the
current source code (all 187 source files hash-verified identical).

---

## What Changed in This Update

| Area | Files changed (03 Nov 2026) |
|------|----------------------------|
| Backend | `backend/main.py`, `backend/services/llm_service.py`, `backend/services/report_generator.py` |
| Frontend | `frontend/src/App.jsx`, `frontend/src/components/WitnessStep.jsx`, `frontend/src/components/CoiDraftStep.jsx`, `frontend/src/index.css` |

Effect: case/user persistence across reloads (`coi_user` localStorage),
new Witness "Unit" field, restyled CoI draft document (`draft-page`).

| Artifact | Status |
|----------|--------|
| `offline/transfer/legal-code.part-000` | ✅ current — 187/187 files hash-identical to source, SHA256SUMS valid |
| `docker-images/legal-backend.tar` | ✅ **rebuilt today** with the new code, tags `:1.0` + `:latest` |
| `docker-images/legal-frontend.tar` | ✅ **rebuilt today** with the new code, tags `:1.0` + `:latest` |
| `docker-images/legal-ollama-gemma3-4b.tar` | ⏭️ unchanged (model did not change) — do **not** re-transfer |
| `compose.yml` | ⏭️ unchanged — byte-identical to the original transfer |

---

## Files to Transfer (2 sets)

Copy these from this PC:

| File | Size | Source folder |
|------|------|---------------|
| `legal-code.part-000` | 443 MB | `offline\transfer\` |
| `legal-backend.tar` | 587 MB | `docker-images\` |
| `legal-frontend.tar` | 20 MB | `docker-images\` |
| `DVD-SHA256SUMS.txt` | ~200 B | project root — covers the 3 files above |
| `DVD-TRANSFER-COMMANDS.txt` | ~11 KB | project root (this file's plain-text twin) |
| `code-update-strategy.md` | ~20 KB | project root (optional reference) |
| `UPDATE-TRANSFER.md` (this file) | — | project root |

**Total: ~1.05 GB — fits on one 4.3 GB DVD** (about 3.2 GB left free).

**Not needed:** `legal-ollama-gemma3-4b.tar` (6 GB — model unchanged, already on the offline PC), `compose.yml` (unchanged), any Ollama models.

---

## On the Offline PC

Project dir is `$HOME/legal/` (unchanged). Transfer dir: `$HOME/legal-transfer/`.

### STEP 1 — Verify checksums

```bash
cd "$HOME/legal-transfer"
sha256sum -c DVD-SHA256SUMS.txt
#   legal-code.part-000: OK
#   legal-backend.tar: OK
#   legal-frontend.tar: OK
```

If you instead copied the per-folder checksum files, note that
`docker-images/SHA256SUMS.txt` also lists the 6 GB ollama tar you did not
transfer — use `sha256sum -c --ignore-missing SHA256SUMS.txt` in that case.

If a hash fails: recopy that file from this PC, do not continue.

### STEP 2 — Overlay the updated source (keeps source tree in sync)

Same as `offline-commands.md` Steps 3–4:

```bash
mkdir -p "$HOME/legal-staging-code"
cat legal-code.part-000 > legal-code.tar.gz
gzip -t legal-code.tar.gz
tar -xzf legal-code.tar.gz -C "$HOME/legal-staging-code"

cp -a "$HOME/legal-staging-code/backend/."  "$HOME/legal/backend/"
cp -a "$HOME/legal-staging-code/frontend/." "$HOME/legal/frontend/"
```

The `cp -a` overlay **preserves** `backend/uploads/` (case data) and does not touch `data/` or `offline/ollama/`.

### STEP 3 — Load the prebuilt images (REPLACES the slow rebuild)

Fastest option — no `docker build` needed, images already contain the new code
(verified byte-identical to source on this PC):

```bash
docker load -i legal-backend.tar     # -> Loaded image: legal-backend:1.0 (and :latest)
docker load -i legal-frontend.tar    # -> Loaded image: legal-frontend:1.0 (and :latest)
```

Both tags are inside each tar, so `compose.yml` (`legal-backend:1.0`,
`legal-frontend:1.0`) finds them immediately.

> **Alternative:** if you prefer rebuilding on the offline PC instead of
> loading tars, run `offline-commands.md` Step 5 (`docker build`) — the source
> overlay in Step 2 above is identical. Do **not** do both; loading the tars
> is equivalent and much faster (~2 min vs ~20 min).

### STEP 4 — Restart the stack

```bash
cd "$HOME/legal"
docker compose up -d --pull never --no-build
```

### STEP 5 — Verify

```bash
docker ps
#   legal-backend   healthy (legal-backend:1.0)
#   legal-frontend  healthy (legal-frontend:1.0)
#   legal-ollama    Up     (ollama/ollama:0.6.8)

curl --fail http://127.0.0.1:8080/api/health
#   {"status":"ACTIVE", ...}

# Confirm the NEW frontend bundle is being served (must print a line):
curl -s http://127.0.0.1:8080/ | grep -o 'assets/index-[A-Za-z0-9_-]*\.js' | head -1
curl -s http://127.0.0.1:8080/assets/index-*.js | grep -o 'coi_user' | head -1

# Model still fine:
docker compose exec ollama ollama run gemma3:4b 'Reply with exactly: READY'
```

Then open `http://localhost:8080` and smoke-test: reload mid-flow (case
state should now persist), add a Witness with a Unit, check the draft page
is white/black document styled.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `sha256sum -c` fails | Recopy that single file; do not mix copies from different runs |
| `docker load` says "manifest type not supported" | Offline Docker too old for OCI tars → fall back to rebuild path (`offline-commands.md` Step 5) |
| compose: "image not found" | `docker images \| grep legal` — the load step was skipped or failed |
| UI looks old after update | Frontend is compiled into the image — ensure Step 3 load + Step 4 restart both ran |
| `/api/health` fails | `docker ps` — backend not healthy; `docker logs legal-backend` |

---

## Rollback

Old images become dangling but are not deleted by `docker load`. To roll back:

```bash
docker images -a | grep -E 'legal-(backend|frontend)'
docker tag <OLD_IMAGE_ID> legal-backend:1.0     # if the old image still exists
docker compose up -d --pull never --no-build
```

Source rollback: the previous `legal-code.part-000` from DVD 2 (keep it until
the update is accepted).
