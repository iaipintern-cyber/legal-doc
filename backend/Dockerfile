# ============================================================
# Court of Inquiry -- BACKEND image (FastAPI + OCR)
#
# Build context is the PROJECT ROOT (setup.md section 2):
#   docker build --platform linux/amd64 -f backend/Dockerfile -t legal-backend:1.0 .
# ============================================================
FROM python:3.12-slim

# Offline defaults: the LLM is ALWAYS the local Ollama daemon. There is no
# cloud provider in this image, so no API key and no outbound network needed.
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    OLLAMA_BASE_URL=http://host.docker.internal:11434 \
    OLLAMA_MODEL=gemma3:4b \
    OLLAMA_NUM_CTX=16384 \
    OLLAMA_TIMEOUT=900 \
    OLLAMA_RETRIES=2 \
    MAX_DOC_CHARS_IN_PROMPT=3500

# System packages:
#   tesseract-ocr  -> OCR for scanned PDFs / images (used by pytesseract)
#   libgl1, libglib2.0-0 -> OpenCV runtime (used by rapidocr-onnxruntime)
#   libgomp1       -> OpenMP runtime (used by onnxruntime / numpy)
RUN apt-get update && apt-get install -y --no-install-recommends \
        tesseract-ocr \
        libgl1 \
        libglib2.0-0 \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python dependencies.
# wheels-linux/ contains pre-downloaded manylinux wheels so the image can
# also be rebuilt on a PC with NO internet (see wheels-linux/README.txt).
COPY backend/requirements.txt ./
COPY backend/wheels-linux/ ./wheels-linux/
RUN pip install --no-cache-dir --find-links=./wheels-linux -r requirements.txt

# Application code (uploads/ and .env are excluded by the root .dockerignore;
# case data is bind-mounted at runtime instead)
COPY backend/ .

# Fail the build HERE, while still online, if RapidOCR cannot initialize:
# a missing packaged model must surface on the connected PC, never on the
# air-gapped one (setup.md section 2). Requires libgl1/libgomp1 (installed above).
RUN python -c "from services.ocr_service import _rapid_ocr; assert _rapid_ocr is not None, 'RapidOCR failed to initialize at build time'"

# Case uploads + saved case state live here (mount a host folder on this path)
RUN mkdir -p /app/uploads

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=5).status==200 else 1)"

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
