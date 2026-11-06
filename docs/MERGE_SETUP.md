# MERGE SETUP — bringing new/updated code into the Dockerized project

**Purpose:** keep this file in mind whenever a "new code" zip/folder arrives.
**Golden rule:** the ZIP supplies **application code only**. The Docker setup lives *here* and is
never redone or overwritten — the existing Dockerfiles/compose keep building the new code as-is.
You do NOT "set up Docker again" for new code; you merge code into this tree, then rebuild.

_Last verified: 2026-11-06. Backend in tree = your edits through Nov 06; frontend = dark olive/red
theme + Nov 03–06 updates. Version control: https://github.com/iaipintern-cyber/legal-doc (private)._

---

## 0. Project structure (keep it like this — no clutter)

```
legal/                    <- this repo root
├── backend/              <- FastAPI app (only backend things live inside)
├── frontend/             <- Vite + React app (only frontend things live inside)
├── data/                 <- shared law data (README)
├── docs/                 <- MERGE_SETUP.md, UPDATE-TRANSFER.md, DVD transfer notes
├── scripts/              <- gate / package / verify automation + ingest & report tools
├── tests/                <- standalone dev test scripts
├── beginner-pack/        <- beginner guide
├── files/                <- the 6 law-book PDFs (LOCAL ONLY — never in git, never in images)
├── offline/              <- packaged artifacts (LOCAL ONLY, multi-GB)
├── transfer/             <- DVD bundle + parts (LOCAL ONLY, multi-GB)
├── compose.yml, compose.debug.yml, .dockerignore, .gitignore, README.md, setup.md
```
Legacy dirs `docker-images/` and `ollama-docker/` were removed on 2026-11-06 (parked in
`..\_cleanup_backup_2026-11-06\`), together with dead one-shot scripts and stale scratch `.md`s.

## 1. PROTECTED — never overwritten by any code zip

| File / folder | Why |
|---|---|
| `compose.yml` (project `legal`, frontend 127.0.0.1:8080, volumes) | canonical stack definition |
| `compose.debug.yml` | offline debug stack (setup.md §6) |
| `.dockerignore` (root), `backend/.dockerignore`, `frontend/.dockerignore` | keep `.env`, `node_modules`, caches OUT of images |
| `backend/Dockerfile`, `frontend/Dockerfile` (production + debug targets) | proven, gated builds |
| `setup.md`, `README.md`, `docs/MERGE_SETUP.md`, `docs/UPDATE-TRANSFER.md` | procedure docs |
| `backend/wheels/`, `backend/wheels-linux/` | offline pip wheels |
| `offline/`, `transfer/` | packaged artifacts (rewritten only by the pipeline) |
| `scripts/.theme-gate.ps1`, `scripts/.theme-package.sh`, `scripts/.theme-verify.ps1` | gate / package / verify automation |
| `scripts/ingest_pdfs.py`, `scripts/make_report.py`, `tests/*` | ingestion provenance & tools |
| `docs/`, `tests/`, `beginner-pack/`, `files/` | stable folders — code zips never touch them |

If the zip contains its own `Dockerfile` / `compose*.yml` → **ignore them by default**.
Exception: a build fails and the fix provably requires an infra edit → change the **minimum**,
and report the change + reason.

## 2. TAKE FROM THE ZIP (application code)

- **Frontend:** `frontend/src/`, `frontend/public/`, `frontend/index.html`, `frontend/vite.config.js`
- **Always as a pair:** `frontend/package.json` **+** `frontend/package-lock.json`
  (a mismatched pair breaks `npm ci` in the build)
- **Backend:** `backend/main.py`, `backend/config.py`, `backend/services/*.py`, `backend/guide.md`,
  `backend/requirements.txt`
- **Only if the new code expects it:** `backend/data/*.json` (law data must match what the code reads)
- **Decide deliberately:** `backend/uploads/` — taking it ships YOUR local cases with the source
  archive; leaving it keeps the offline PC's own cases untouched

## 3. NEVER merge, NEVER ship (hard rules)

`.env`, `.env.*`, `node_modules/`, `.venv/`, `venv/`, `__pycache__/`, `*.pyc`, `dist/`,
`id_ed25519*`, `*.bat`, `*.exe`, `*.pdf`, `*.docx`, anything under `files/` or `backend/uploads/`
with real case content.

These equal the forbidden-scan inside `scripts/.theme-verify.ps1` **and** are enforced by
`.gitignore` — one hit = packaging FAILED / not committed.
New environment variables → append by hand to the local `backend/.env` only (it never leaves
this PC; `.dockerignore` + `.gitignore` keep it out of everything).

## 4. Merge procedure

1. Extract the zip to a **TEMP folder** — never extract on top of the project.
2. Compare: zip's `frontend/` + `backend/` file lists and mtimes vs the project.
3. Copy **only** the §2 paths from the zip into the project (overwrite allowed there).
4. Check §3 didn't sneak in: no `.env`, no `node_modules`, no `__pycache__`, no PDFs arrived.
5. If frontend styling changed → update palette strings in `scripts/.theme-gate.ps1` and
   `scripts/.theme-verify.ps1` (currently assert dark palette `5d7430` / `171b0e` / `10140a`,
   red `b33324` / `c23a2c`, and old= `556b2f|9b2b20|c9d0a6|f7f6ea|44521e|3e4a21`).
6. Write down what functionally changed → the gate (§6) must exercise exactly that.

## 5. Build — PowerShell only (see §9), context = project root

```powershell
cd "C:\Users\Idex\Documents\legal final\legal\legal"
docker.exe build --platform linux/amd64 -f backend/Dockerfile  -t legal-backend:1.0 .
docker.exe build --platform linux/amd64 -f frontend/Dockerfile --target production -t legal-frontend:1.0 .
docker.exe build --platform linux/amd64 -f frontend/Dockerfile --target debug      -t legal-frontend-debug:1.0 .
docker.exe image inspect legal-backend:1.0 legal-frontend:1.0 legal-frontend-debug:1.0 ollama/ollama:0.6.8 --format '{{.RepoTags}} {{.Os}}/{{.Architecture}}'
```

- All four MUST print `linux/amd64` — stop if any differs.
- `ollama/ollama:0.6.8` is **never rebuilt** (model image is carried as-is).
- Build failure → smallest fix in Dockerfile / compose / lockfile only, reported; no app-logic edits.

## 6. Acceptance gate (setup.md §3)

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ".\scripts\.theme-gate.ps1"   # -> THEME_GATE_OK
```

`config` → `up -d --pull never --no-build` → backend healthy → HTTP 200s → served-palette check →
`down`. Extend with checks for whatever the new code added (upload/generate/download flows).

## 7. Package (setup.md §2 + §4 recipe)

```powershell
# 1) strip the SSH keys every compose run re-creates inside the model mount:
Get-ChildItem ".\offline\ollama" -File -Force -Filter 'id_ed25519*' | Remove-Item -Force

# 2) export + source + bundle + split (expect PACKAGE_DONE):
wsl -e bash "/mnt/c/Users/Idex/Documents/legal final/legal/legal/scripts/.theme-package.sh"

# 3) verification battery (expect THEME_VERIFY_OK):
powershell -NoProfile -ExecutionPolicy Bypass -File ".\scripts\.theme-verify.ps1"
```

Pipeline inside step 2: `docker save | gzip -1` (`.partial` → sync → rename) → source tar with the
setup.md §4 excludes → `transfer\legal-bundle.tar.gz` → split at 3,800,000,000 → `part-000` +
`part-001` + `SHA256SUMS`.
Verify = full gzip streams (CRC), forbidden-content scan, uploads↔disk match, every SHA256,
parts-sum==bundle, rejoin round-trip, `docker load` ID-fidelity + `linux/amd64`.

## 8. Ship to the offline Linux PC

Carry: `transfer\legal-bundle.part-000`, `transfer\legal-bundle.part-001`, `transfer\SHA256SUMS`
(≈5.9 GB → 2 DVDs or one USB). **Never send `legal.zip`** (contains `.env`, `node_modules`, junk).

```bash
sha256sum -c SHA256SUMS                                   # both parts must say OK
cat legal-bundle.part-000 legal-bundle.part-001 > legal-bundle.tar.gz   # correct by construction
tar -xzf legal-bundle.tar.gz
gzip -dc offline/images/legal-images.tar.gz | docker load
docker compose -f compose.yml config --quiet
docker compose up -d --pull never --no-build              # updating an existing stack
# fresh install instead: follow setup.md §5 (compose plugin install, first up)
```

⚠️ The source archive contains **this PC's `backend/uploads` cases** — extracting it over the
offline deployment replaces *its* cases: back them up first, or skip that folder when you only
want the app update.

## 9. This machine's quirks (remember)

- WSL's native `docker` socket is broken → **always `docker.exe`**: directly in PowerShell, or as
  `docker.exe` from inside WSL. Plain WSL bash is for tar/sed/grep/split (and the helper scripts).
- PowerShell shows Docker's stderr as red `NativeCommandError` noise — judge success by the exit
  markers (`CONFIG_OK`, `*_OK`, `PACKAGE_DONE`, `THEME_VERIFY_OK`), not by red text.
- The app is **live on this PC** — new cases keep appearing in `backend/uploads`; verification
  therefore uses dynamic disk-match, never fixed file counts.
- **Git**: repo = `github.com/iaipintern-cyber/legal-doc` (private, branch `main`).
  `.gitignore` blocks secrets/PDFs/case data — but **always review `git status` before commit**;
  if something unexpected appears under `uploads/`/`files/`/`*.pdf`, it means the pattern was
  outsmarted — fix the ignore, don't commit. Backup of pre-GitHub cleanup:
  `C:\Users\Idex\Documents\legal final\_cleanup_backup_2026-11-06\`.

## 10. Never-do constraints

No registry push · no `docker system prune` · never delete images/volumes/containers you did not
create · no Docker Desktop settings changes · `linux/amd64` only · no `.env`/`node_modules`/venv/
`__pycache__`/`.bat`/`.exe`/`*.pdf`/case data in any image, archive, or commit · infra edits =
smallest possible + reported.

## 11. Current state (update this section after every round)

- Images (all `linux/amd64`): `legal-backend:1.0`, `legal-frontend:1.0`, `legal-frontend-debug:1.0`,
  `ollama/ollama:0.6.8`.
- UI theme: dark olive + red — canvas `#171b0e`, chrome `#10140a`, primary `#5d7430`,
  red `#b33324`/`#c23a2c`; dashboard no longer shows the "IN LIEU OF IAFD – 931" badge.
- **⚠️ Artifacts are STALE**: package from 2026-10-29 predates the Nov 03–06 code → rebuild
  backend + frontend → re-gate → re-package before anything ships (§5→§7).
- Git: repo `iaipintern-cyber/legal-doc`, private, branch `main`; sanitized snapshot pushed
  (see `.gitignore`).
- Automation now lives in `scripts/` (gate/package/verify) and docs in `docs/`; dead one-shot
  scripts and stale `.md`s were removed 2026-11-06 with backup in
  `..\_cleanup_backup_2026-11-06\`.
