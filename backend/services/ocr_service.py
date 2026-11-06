import fitz  # PyMuPDF
import os
import io
import logging
from pathlib import Path
from PIL import Image

logger = logging.getLogger(__name__)

# Initialize RapidOCR once if available
_rapid_ocr = None
try:
    from rapidocr_onnxruntime import RapidOCR
    _rapid_ocr = RapidOCR()
    logger.info("RapidOCR initialized successfully for offline scanned PDF and image OCR.")
except Exception as e:
    logger.warning(f"RapidOCR not available: {e}. Will fallback to pytesseract if installed.")

def _ocr_image_bytes(image_bytes: bytes) -> str:
    """Performs OCR on image bytes using RapidOCR or pytesseract."""
    # 1. Try RapidOCR first (fast, offline, no system binary required)
    if _rapid_ocr is not None:
        try:
            results, _ = _rapid_ocr(image_bytes)
            if results:
                lines = [item[1] for item in results if len(item) > 1 and item[1]]
                return "\n".join(lines).strip()
        except Exception as ocr_err:
            logger.warning(f"RapidOCR execution error: {ocr_err}")

    # 2. Try pytesseract as fallback
    try:
        import pytesseract
        img = Image.open(io.BytesIO(image_bytes))
        return pytesseract.image_to_string(img).strip()
    except Exception as pytess_err:
        logger.warning(f"pytesseract fallback error: {pytess_err}")

    return ""

def extract_text_from_file(file_path: str) -> dict:
    """
    Extracts text from PDF (both digital soft-copy and scanned hard-copy) or image file.
    Returns dict with raw_text, page_count, pages list, and metadata.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    ext = path.suffix.lower()
    
    if ext == ".pdf":
        doc = fitz.open(file_path)
        pages = []
        raw_text_parts = []
        
        for i, page in enumerate(doc):
            # 1. First attempt: Direct digital text extraction (fast, perfect for online/soft-copy PDFs)
            text = page.get_text().strip()
            
            # 2. Second attempt: If text is empty or too short (< 25 characters), it's a scanned page!
            if len(text) < 25:
                try:
                    pix = page.get_pixmap(dpi=150)
                    img_bytes = pix.tobytes("png")
                    scanned_text = _ocr_image_bytes(img_bytes)
                    if len(scanned_text) > len(text):
                        text = scanned_text
                except Exception as page_ocr_err:
                    logger.warning(f"Scanned OCR failed on page {i+1}: {page_ocr_err}")
            
            cleaned_text = text.strip()
            pages.append({"page_number": i + 1, "text": cleaned_text})
            if cleaned_text:
                raw_text_parts.append(cleaned_text)
                
        doc.close()
        full_text = "\n\n".join(raw_text_parts)
        return {
            "file_name": path.name,
            "page_count": len(pages),
            "pages": pages,
            "text": full_text
        }
        
    elif ext in [".png", ".jpg", ".jpeg", ".bmp", ".tiff"]:
        try:
            with open(file_path, "rb") as f:
                img_bytes = f.read()
            text = _ocr_image_bytes(img_bytes)
            return {
                "file_name": path.name,
                "page_count": 1,
                "pages": [{"page_number": 1, "text": text}],
                "text": text
            }
        except Exception as e:
            return {
                "file_name": path.name,
                "page_count": 1,
                "pages": [{"page_number": 1, "text": f"Error performing OCR: {e}"}],
                "text": ""
            }
    else:
        # Fallback for plain text, txt, md, etc.
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
        return {
            "file_name": path.name,
            "page_count": 1,
            "pages": [{"page_number": 1, "text": text.strip()}],
            "text": text.strip()
        }
