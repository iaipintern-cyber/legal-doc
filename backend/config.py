import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
WORKSPACE_DIR = BASE_DIR.parent
DATA_DIR = WORKSPACE_DIR / "data"
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# ------------------------------------------------------------------
# LLM: runs 100% LOCAL through Ollama (air-gapped / offline PC).
#       There is no cloud provider in this build -- no API key, no
#       network egress, nothing to comment out.
# ------------------------------------------------------------------
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:4b")

# Context window per request. gemma3:4b advertises 131072, but this machine
# is CPU-only -- a huge window means a much slower prefill and a large KV
# cache. 16384 comfortably fits the Convening Order + 12 exhibits + military
# laws + the JSON response.
OLLAMA_NUM_CTX = int(os.getenv("OLLAMA_NUM_CTX", "16384"))

# Seconds to wait for a completion. On CPU the case-analysis prompt takes
# roughly 3-5 minutes, so this must be generous (was 180 and was timing out).
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "900"))

# Extra attempts ONLY for connection failures (e.g. Ollama still starting).
# Read timeouts are never retried -- retrying a slow CPU just wastes minutes.
OLLAMA_RETRIES = int(os.getenv("OLLAMA_RETRIES", "2"))

# Characters of each supporting document's OCR text that are sent in a prompt.
# Keeps 12 exhibits from blowing past OLLAMA_NUM_CTX.
MAX_DOC_CHARS_IN_PROMPT = int(os.getenv("MAX_DOC_CHARS_IN_PROMPT", "3500"))

