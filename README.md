# Court of Inquiry Generation System -- offline (air-gapped) deployment

Army Rules 177-180 Court of Inquiry generation: FastAPI backend + React/Vite
frontend + local Ollama LLM (`gemma3:4b`), running 100% offline in Docker.

## Single source of truth for deployment

**Read [`setup.md`](setup.md).** It contains the full procedure:

1. What to carry to the offline PC
2. Prepare on the internet-connected Windows PC (builds, model download, export)
3. Test before burning DVDs (acceptance gate)
4. Package for 4.3 GB DVDs or NAS
5. Restore on the offline Linux PC
6. Debug with mounted source, entirely offline
7. Operations and troubleshooting

## Quick reference

| Item | Value |
| --- | --- |
| Production UI | http://localhost:8080 (loopback only) |
| Health check | http://localhost:8080/api/health |
| Debug UI | http://localhost:5173 (compose.debug.yml) |
| API docs (debug) | http://localhost:8000/docs |
| Images | `legal-backend:1.0`, `legal-frontend:1.0`, `legal-frontend-debug:1.0`, `ollama/ollama:0.6.8` -- all `linux/amd64` |
| Model store | `offline/ollama/models/{blobs,manifests}` |
| Compose files | `compose.yml` (production), `compose.debug.yml` (debug overlay) |

```bash
# production
docker compose up -d --pull never --no-build
docker compose down

# debug (mounted source + live reload)
docker compose -f compose.yml -f compose.debug.yml up -d --pull never --no-build
docker compose -f compose.yml -f compose.debug.yml down
```

## Repository layout

- `backend/` -- FastAPI service (`main.py`, `config.py`, `services/`)
- `frontend/` -- React/Vite source (built into `legal-frontend:1.0`)
- `offline/` -- generated on the connected PC: image archive, model store, Compose plugin
- `transfer/` -- generated: `legal-bundle.tar.gz` split into DVD parts + `SHA256SUMS`
- `docker-images/`, `ollama-docker/` -- legacy artifacts from an earlier scheme; not used by setup.md

> Do not expose this app to a LAN. Its login is a placeholder, not production
> authentication. See setup.md sections 3 and 7.
