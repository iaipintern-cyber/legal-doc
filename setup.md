# Offline Linux x86_64 Deployment

## 1. What to carry

The target is Linux `x86_64`, called `linux/amd64` by Docker. Windows images,
Windows Python wheels, `.exe` installers, and Windows `node_modules` are not
usable there. Build Linux images on the connected Windows PC using Docker
Desktop in **Linux containers** mode and its WSL2 integration.

| Item | Required on the offline PC? | How it arrives |
| --- | --- | --- |
| Docker Engine | Yes, already installed | Check the daemon is running |
| Docker Compose plugin 2.24.4+ | Yes | Carry the Linux x86_64 standalone Compose plugin if missing |
| Python 3.12 | Inside backend only | Included in `legal-backend:1.0`; no host installer needed |
| Python dependencies, RapidOCR models, Tesseract English data | Yes | Included in backend image |
| Production frontend and Nginx | Yes | Included in `legal-frontend:1.0` |
| Ollama server | Yes | `ollama/ollama:0.6.8` Linux amd64 image |
| `gemma3:4b` weights and manifests | Yes, separately from image | Exported Ollama directory |
| Node.js and frontend dependencies | Only for live source debugging | Included in `legal-frontend-debug:1.0` |
| Application source, Compose files, Dockerfiles, law data | Yes | Source archive |
| Existing case uploads | Only if approved for transfer | Review `backend/uploads` before packaging |
| Browser, GNU tar, gzip, split, sha256sum, curl | Yes | Normally supplied by Linux; check before transfer |

Use CPU inference initially. No NVIDIA drivers or container toolkit are needed
for this configuration. Allow at least 16 GB RAM (more is preferable), adequate
swap, and roughly 30 GB free disk for images, archives, extraction, and models;
measure your actual bundle rather than treating this as a guaranteed minimum.
GPU acceleration requires target GPU/driver details and is not configured here.
Check the CPU supports the instructions required by the chosen Ollama build;
`x86_64` alone does not prove CPU instruction compatibility.

Only one deployment guide is needed: this file. No host Python, Node.js, Ollama
installer, Windows executable, or pip/npm downloads are needed offline.

## 2. Prepare on the internet-connected Windows PC

Install/start Docker Desktop with Linux containers, enable WSL2 integration,
then open a **WSL Bash terminal**. All commands below are Linux/Bash commands,
not PowerShell. Use the project directory mounted from Windows:

```bash
cd /mnt/d/WORKSPACE/legal
docker version
docker info --format '{{.OSType}}/{{.Architecture}}'
docker compose version
mkdir -p offline/images offline/ollama transfer
```

The Docker engine must report Linux. The host architecture can differ, but all
exported images below must report `linux/amd64`. Internet is required during
this preparation phase only. Do not copy a Windows virtual environment or
`node_modules`. Docker's build context excludes these and local `.env` files.

Build and pull all runtime images explicitly for the target:

```bash
docker build --platform linux/amd64 -f backend/Dockerfile -t legal-backend:1.0 .
docker build --platform linux/amd64 -f frontend/Dockerfile --target production -t legal-frontend:1.0 .
docker build --platform linux/amd64 -f frontend/Dockerfile --target debug -t legal-frontend-debug:1.0 .
docker pull --platform linux/amd64 ollama/ollama:0.6.8
docker image inspect legal-backend:1.0 legal-frontend:1.0 legal-frontend-debug:1.0 ollama/ollama:0.6.8 --format '{{.RepoTags}} {{.Os}}/{{.Architecture}}'
```

Stop if any image is not `linux/amd64`. Backend build initializes RapidOCR so
missing packaged models fail online, rather than during the offline startup.
Keep these exact image archives for repeat deployment: dependencies in the
Dockerfiles are not fully version-locked, so later rebuilds may differ.

Download the model using the same Ollama image that will run offline. The
preparation container has internet; production will not:

```bash
docker run -d --name legal-model-download --platform linux/amd64 -v "$PWD/offline/ollama:/root/.ollama" ollama/ollama:0.6.8
docker exec legal-model-download ollama pull gemma3:4b
docker exec legal-model-download ollama list
docker exec legal-model-download ollama run gemma3:4b 'Reply with exactly: READY'
docker stop legal-model-download
docker rm legal-model-download
```

Keep both `offline/ollama/models/blobs` and `offline/ollama/models/manifests`.
An Ollama image does **not** contain model weights. Do not run `ollama pull`
on the air-gapped PC. Remove an old download container first if its name is
already in use, after confirming you no longer need it.

Export all images, including the optional debugging image:

```bash
docker save legal-backend:1.0 legal-frontend:1.0 legal-frontend-debug:1.0 ollama/ollama:0.6.8 | gzip -1 > offline/images/legal-images.tar.gz
```

If Compose is absent on the target, also carry its plugin (download online):

```bash
curl -fL https://github.com/docker/compose/releases/download/v2.39.4/docker-compose-linux-x86_64 -o offline/docker-compose-linux-x86_64
curl -fL https://github.com/docker/compose/releases/download/v2.39.4/docker-compose-linux-x86_64.sha256 -o offline/docker-compose-linux-x86_64.sha256
(cd offline && sha256sum -c docker-compose-linux-x86_64.sha256)
```

If downloads are blocked, obtain the same Linux x86_64 plugin through your
approved software channel. Do not substitute the Windows Compose executable.

## 3. Test before burning DVDs

```bash
docker compose -f compose.yml config --quiet
docker compose -f compose.yml -f compose.debug.yml config --quiet
docker compose up -d --pull never --no-build
docker compose ps
curl --fail http://127.0.0.1:8080/api/health
docker compose exec ollama ollama list
docker compose exec ollama ollama run gemma3:4b 'Reply with exactly: READY'
docker compose exec backend python -c "from services.ocr_service import _rapid_ocr; assert _rapid_ocr is not None; print('RapidOCR ready')"
docker compose exec backend tesseract --list-langs
```

Open `http://localhost:8080`. Test an actual scanned document, a digital PDF,
case persistence after restarting, and report generation while the internet
connection is disconnected. This is the acceptance gate before transfer.
`/api/health` checks the web API only, not model inference or OCR accuracy.

The production network is internal, the model API has no published port, and
the backend receives an empty `GROQ_API_KEY` so its cloud fallback cannot run.
Only the frontend is published, on loopback. Do not expose this app to a LAN:
its existing login is a placeholder, not production authentication.

```bash
docker compose down
```

Review the source for embedded credentials before creating a bundle. The
previous embedded cloud key has been removed from `backend/config.py`; rotate
it if valid and review local configuration too. Excluding `.env` alone does not
remove source literals.
Review case documents for transfer authorization. Do not package unrelated
documents, credentials, host toolchains, or previous archives.

## 4. Package for 4.3 GB DVDs or NAS

DVD is sufficient; NAS is optional and usually faster for repeat updates.
Neither method needs internet on the target. Use an approved internal NAS
only if network access is permitted by your security policy.

Archive just the application and deployment files, excluding local tooling:

```bash
tar --exclude='node_modules' --exclude='dist' --exclude='.venv' --exclude='venv' --exclude='__pycache__' --exclude='*.pyc' --exclude='.env' --exclude='.env.*' --exclude='*.bat' --exclude='*.exe' --exclude='wheels' -czf offline/legal-source.tar.gz backend frontend data compose.yml compose.debug.yml .dockerignore setup.md README.md
tar -czf transfer/legal-bundle.tar.gz -C offline .
split --bytes=3800000000 --numeric-suffixes=0 --suffix-length=3 transfer/legal-bundle.tar.gz transfer/legal-bundle.part-
(cd transfer && sha256sum legal-bundle.part-* > SHA256SUMS)
du -h transfer/legal-bundle.tar.gz
ls -lh transfer/legal-bundle.part-*
```

Each part is 3.8 billion bytes, safely below a 4.3 GB DVD capacity. Use a data
DVD with UDF support for large files. Burn **one part per DVD**, plus a copy
of `SHA256SUMS` and this guide on every disc. Label discs with part numbers.
The number of DVDs is total archive bytes divided by 3,800,000,000, rounded up;
Gemma weights plus images may require several discs. Do not burn the unsplit
archive to one DVD. Checksums detect corruption, not malicious replacement;
retain an approved trusted copy of the checksum manifest.

For NAS, copy either the full archive and its SHA256 hash, or all the numbered
parts and `SHA256SUMS`. Transfer the same verified artifacts without rebuilding.

## 5. Restore on the offline Linux PC

Run as a user already permitted to use Docker. If your account needs privileged
installation or DVD mounting, have an administrator perform that step under
your site's policy. Do not change Docker socket permissions to world-writable.

```bash
uname -m
docker version
docker compose version
mkdir -p "$HOME/legal-transfer" "$HOME/legal-staging" "$HOME/legal"
```

`uname -m` must report `x86_64`. Copy every numbered part and one `SHA256SUMS`
from the DVDs into `$HOME/legal-transfer`. For each mounted DVD, for example:

```bash
cp /media/$USER/DVD_LABEL/legal-bundle.part-* "$HOME/legal-transfer/"
cp /media/$USER/DVD_LABEL/SHA256SUMS "$HOME/legal-transfer/"
```

Replace the DVD path with the actual mount path. Then verify and join in order:

```bash
cd "$HOME/legal-transfer"
sha256sum -c SHA256SUMS
cat legal-bundle.part-* > legal-bundle.tar.gz
gzip -t legal-bundle.tar.gz
tar -xzf legal-bundle.tar.gz -C "$HOME/legal-staging"
```

Do not continue after a failed checksum; recopy or reburn the affected part.
For a full archive from NAS, check its separately transferred trusted hash
and extract it directly instead of joining parts.

If Compose is missing or older than 2.24.4, install the carried plugin for your
own account (Docker Engine is already installed):

```bash
(cd "$HOME/legal-staging" && sha256sum -c docker-compose-linux-x86_64.sha256)
mkdir -p "$HOME/.docker/cli-plugins"
cp "$HOME/legal-staging/docker-compose-linux-x86_64" "$HOME/.docker/cli-plugins/docker-compose"
chmod +x "$HOME/.docker/cli-plugins/docker-compose"
docker compose version
```

Restore source, models, and images. Use a fresh destination for initial setup;
do not overwrite an existing deployment's cases when applying an update.

```bash
cd "$HOME/legal"
tar -xzf "$HOME/legal-staging/legal-source.tar.gz"
mkdir -p offline backend/uploads data
cp -a "$HOME/legal-staging/ollama" offline/
gzip -dc "$HOME/legal-staging/images/legal-images.tar.gz" | docker load
docker image inspect legal-backend:1.0 legal-frontend:1.0 legal-frontend-debug:1.0 ollama/ollama:0.6.8 --format '{{.RepoTags}} {{.Os}}/{{.Architecture}}'
docker compose -f compose.yml config --quiet
docker compose up -d --pull never --no-build
docker compose ps
curl --fail http://127.0.0.1:8080/api/health
docker compose exec ollama ollama list
docker compose exec ollama ollama run gemma3:4b 'Reply with exactly: READY'
```

Open **http://localhost:8080** on that Linux PC and repeat the acceptance tests
in section 3. The image platform must be `linux/amd64`. If a saved tar archive
already exists elsewhere, load it with `docker load -i ARCHIVE.tar` and inspect
the loaded images with the same command. A filename does not prove platform
compatibility. Do not use Windows-container archives.

## 6. Debug with mounted source, entirely offline

```bash
cd "$HOME/legal"
docker compose down
docker compose -f compose.yml -f compose.debug.yml up -d --pull never --no-build
```

Open **http://localhost:5173**; API documentation is at
**http://localhost:8000/docs**. Backend Python changes reload Uvicorn. Frontend
source changes use Vite's live reload. Vite proxies `/api` to the backend
container, not to the host's localhost. Source mounts preserve the images'
Python packages and frontend dependencies. The named `frontend_node_modules`
volume is initialized from the debug image on first start; never populate it
with Windows `node_modules`.

If package manifests/requirements change, rebuild and re-export the affected
image on the connected PC. After updating the debug image, refresh its old
dependency volume using `docker volume rm legal_frontend_node_modules` while
the stack is stopped. Do not remove unrelated volumes or model/case folders.
Production uses the compiled frontend in its image: editing React source does
not change the production UI until that image is rebuilt.

Return to production:

```bash
docker compose -f compose.yml -f compose.debug.yml down
docker compose up -d --pull never --no-build
```

## 7. Operations and troubleshooting

```bash
docker compose logs --tail=100 backend ollama frontend
docker compose restart
docker compose down
```

- `pull access denied` / missing image: load the carried image archive; do not
  build or pull offline. `pull_policy: never` prevents automatic pulls.
- Missing model: verify both blobs and manifests are under
  `offline/ollama/models`, then check `ollama list` inside the container.
- Model too slow: CPU inference can exceed the backend's existing 180-second
  Ollama request timeout. Measure on the actual hardware; more capable hardware
  or a deliberate timeout/model change may be needed. Nginx allows 1200 seconds.
- RapidOCR failure: check startup logs and run the OCR checks in section 3.
  Tesseract English is bundled as fallback; other language data must be added
  to the image on the connected PC before export.
- Permission denied on bind mounts: check ownership and SELinux policy. On
  SELinux-enforcing hosts, have your administrator apply appropriate labels or
  `:Z`/`:z` mount options; do not disable SELinux globally.
- Backups: stop the stack and back up `backend/uploads` (cases), `data` (law
  documents), and `offline/ollama` (model). Keep a verified image archive too.
- Updates: transfer replacement images, load them, and recreate containers;
  preserve the existing case and model directories. Never prune blindly.

This configuration prevents container internet access but is not a substitute
for host security policy. Loopback binding is intentional. Authentication,
authorization, TLS, and multi-user case isolation require separate work before
any shared-network deployment.

--- ADDENDUM — executed 2026-10-27 (this PC) ---
Images built (all linux/amd64): legal-backend:1.0 legal-frontend:1.0
legal-frontend-debug:1.0 ollama/ollama:0.6.8
Model: gemma3:4b pulled to offline/ollama/ and verified (READY reply).
Archives: offline/legal-source.tar.gz (209 MB),
offline/images/legal-images.tar.gz (1.81 GB).
Split parts: transfer/legal-bundle.part-000 (3.8 GB), part-001 (2.08 GB).
Checks: compose config OK / compose up OK / RapidOCR OK /
tesseract eng+osd OK / health OK (verified container-to-container).
No .env / node_modules / Windows .bat included. No registry push.
No unrelated images, volumes or containers deleted.
See setup-transfer.md for the beginner DVD burn + restore steps.

## 5.1 Beginner: where to run every command (offline PC)

Open one terminal window. All commands below are pasted into that terminal
and run as the normal (non-root) user. Each step says which folder you must
be in first (the `cd` line). Run them in the numbered order.

STEP 1 — copy DVDs (run anywhere):
```bash
mkdir -p "$HOME/legal-transfer"
cp /media/$USER/DVD_LABEL/* "$HOME/legal-transfer/"
```

STEP 2 — verify + join parts (folder: $HOME/legal-transfer):
```bash
cd "$HOME/legal-transfer"
sha256sum -c SHA256SUMS
cat legal-bundle.part-* > legal-bundle.tar.gz
gzip -t legal-bundle.tar.gz
```

STEP 3 — extract (folder: $HOME/legal-transfer):
```bash
cd "$HOME/legal-transfer"
mkdir -p "$HOME/legal-staging" "$HOME/legal"
tar -xzf legal-bundle.tar.gz -C "$HOME/legal-staging"
```

STEP 4 — restore source + model (folder: $HOME/legal-transfer):
```bash
cd "$HOME/legal-transfer"
tar -xzf offline/legal-source.tar.gz -C "$HOME/legal"
mkdir -p "$HOME/legal/offline"
cp -a offline/ollama "$HOME/legal/offline/"
```

STEP 5 — load images (folder: $HOME/legal-transfer):
```bash
cd "$HOME/legal-transfer"
gzip -dc offline/images/legal-images.tar.gz | docker load
docker image inspect legal-backend:1.0 legal-frontend:1.0 \
  legal-frontend-debug:1.0 ollama/ollama:0.6.8 \
  --format '{{.RepoTags}} {{.Os}}/{{.Architecture}}'
```

STEP 6 — start (folder: $HOME/legal):
```bash
cd "$HOME/legal"
docker compose config --quiet
docker compose up -d --pull never --no-build
docker compose ps
curl --fail http://127.0.0.1:8080/api/health
```

STEP 7 — test model + OCR (folder: $HOME/legal):
```bash
cd "$HOME/legal"
docker compose exec ollama ollama list
docker compose exec ollama ollama run gemma3:4b 'Reply with exactly: READY'
docker compose exec backend tesseract --list-langs
```

STEP 8 — open browser: http://localhost:8080
STEP 9 — stop: cd "$HOME/legal" then docker compose down
