import os
import re
import time
import shutil
import logging
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from config import UPLOAD_DIR, WORKSPACE_DIR, MAX_DOC_CHARS_IN_PROMPT
from services.ocr_service import extract_text_from_file
from services.military_law_service import search_relevant_military_laws, get_all_military_laws
from services.llm_service import llm_service
from services.case_service import case_service
from services.report_generator import generate_coi_docx

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Court of Inquiry Generation API",
    version="2.1.0",
    description="Tool for statutory Court of Inquiry analysis and draft generation"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def safe_upload_name(filename: Optional[str]) -> str:
    """Strip any client-supplied path from an upload name (anti path-traversal)
    and keep only characters that are safe on disk."""
    name = Path((filename or "upload.pdf").replace("\\", "/")).name
    name = re.sub(r"[^\w.\- ()]", "_", name).strip(" .")
    return (name or "upload.pdf")[:120]


# ----------------- Models -----------------
class LoginRequest(BaseModel):
    username: str
    password: str

class WitnessModel(BaseModel):
    id: Optional[str] = None
    name: str
    rank: str
    service_no: str
    unit: str
    role: Optional[str] = "Witness"
    ref_letter: Optional[str] = "B"
    questions: Optional[List[str]] = []
    qa_pairs: Optional[List[Dict[str, str]]] = []
    statement: Optional[str] = ""
    compiled_testimony: Optional[Dict[str, Any]] = None

class PresidingOfficerReviewModel(BaseModel):
    reviewed_by: str
    service_no: Optional[str] = ""
    checklist: Dict[str, bool]
    comments: str
    forwarded_to_draft: bool

# ----------------- Routes -----------------

@app.get("/api/health")
def health_check():
    return {"status": "ACTIVE", "system": "Court of Inquiry Generation", "code": 200}

@app.post("/api/auth/login")
def login(creds: LoginRequest):
    # Initialize a clean, empty case session on login while archiving existing case
    clean_case = case_service.start_new_case()
    return {
        "success": True,
        "token": "ADMIN-AUTH-TOKEN",
        "user": {
            "username": creds.username or "Admin",
            "name": "Admin",
            "role": "Admin"
        },
        "initial_case": clean_case
    }

# Case Management Endpoints
@app.get("/api/case/current")
def get_current_case():
    return case_service.get_state()

@app.post("/api/case/new")
def new_case():
    return case_service.start_new_case()

@app.post("/api/case/reset")
def reset_case():
    return case_service.reset_state()

@app.get("/api/cases")
def list_cases():
    return {"cases": case_service.list_all_cases()}

@app.post("/api/cases/{case_id}/load")
def load_case(case_id: str):
    try:
        loaded = case_service.load_case_by_id(case_id)
        return {"success": True, "case": loaded}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Case record not found")

@app.delete("/api/cases/{case_id}")
def delete_case(case_id: str):
    case_service.delete_case_by_id(case_id)
    return {"success": True, "cases": case_service.list_all_cases()}

@app.post("/api/upload/convening-order")
async def upload_convening_order(file: UploadFile = File(...)):
    file_name = safe_upload_name(file.filename)
    dest_path = UPLOAD_DIR / file_name
    with open(dest_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Perform OCR / PDF extraction
    ocr_result = extract_text_from_file(str(dest_path))
    
    # Process with LLM
    try:
        parsed_order = llm_service.parse_convening_order(ocr_result["text"])
    except Exception as e:
        parsed_order = {
            "executive_summary": f"Document text extracted ({ocr_result['page_count']} pages). Summary analysis note: {str(e)}",
            "subject_matter": "Court of Inquiry",
            "composition_of_court": []
        }

    case_service.state["convening_order"] = {
        "file_name": file_name,
        "raw_text": ocr_result["text"],
        "parsed": parsed_order,
        "summary": parsed_order.get("executive_summary", "")
    }

    # Dynamically set case reference from order ref if available
    order_ref = parsed_order.get("order_number")
    if order_ref and len(order_ref.strip()) > 3:
        clean_ref = "".join(c for c in order_ref if c.isalnum() or c in "-_").strip("-_")
        case_service.state["order_reference"] = order_ref
        if clean_ref:
            case_service.state["case_id"] = f"COI-{clean_ref[:25]}"

    case_service.save_state()

    return {
        "success": True,
        "file_name": file_name,
        "extracted_text_length": len(ocr_result["text"]),
        "parsed_order": parsed_order
    }

MAX_FILE_SIZE = 3 * 1024 * 1024  # 3 MB
MAX_SUPPORTING_DOCS = 12

@app.post("/api/upload/supporting-docs")
async def upload_supporting_docs(files: List[UploadFile] = File(...)):
    current_docs = case_service.state.get("supporting_docs", [])
    
    if len(current_docs) + len(files) > MAX_SUPPORTING_DOCS:
        raise HTTPException(
            status_code=400, 
            detail=f"Exceeds maximum allowed limit of {MAX_SUPPORTING_DOCS} supporting documents."
        )

    uploaded_entries = []
    for f in files:
        contents = await f.read()
        if len(contents) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400, 
                detail=f"File '{f.filename}' exceeds maximum allowed size of 3 MB."
            )
        
        f_name = safe_upload_name(f.filename)
        dest_path = UPLOAD_DIR / f_name
        with open(dest_path, "wb") as buffer:
            buffer.write(contents)

        ocr_result = extract_text_from_file(str(dest_path))

        doc_entry = {
            "id": f"doc_{len(current_docs) + len(uploaded_entries) + 1}",
            "file_name": f_name,
            "document_type": "Supporting Document",
            "size_kb": round(len(contents) / 1024, 1),
            "text_snippet": ocr_result["text"][:800],
            "full_text": ocr_result["text"]
        }
        uploaded_entries.append(doc_entry)

    case_service.state["supporting_docs"].extend(uploaded_entries)
    case_service.save_state()

    return {
        "success": True, 
        "added_count": len(uploaded_entries),
        "total_docs": len(case_service.state["supporting_docs"]),
        "supporting_docs": case_service.state["supporting_docs"]
    }

@app.delete("/api/upload/supporting-docs/{doc_id}")
def delete_supporting_doc(doc_id: str):
    case_service.state["supporting_docs"] = [
        d for d in case_service.state.get("supporting_docs", []) if d.get("id") != doc_id
    ]
    case_service.save_state()
    return {"success": True, "supporting_docs": case_service.state["supporting_docs"]}

_analysis_jobs: Dict[str, Dict[str, Any]] = {}

@app.post("/api/analyze/case-brief")
def analyze_case_brief():
    """
    Starts the LLM case-brief analysis in a background thread and returns a
    job id immediately. The frontend polls /api/analyze/status/{job_id}.

    A full analysis on the CPU-only model can take many minutes; keeping the
    HTTP request short means no proxy/browser can drop the connection while
    the model is still thinking (which used to cause 'Unexpected end of
    JSON input' on the frontend).
    """
    conv_text = case_service.state.get("convening_order", {}).get("raw_text", "")
    if not conv_text:
        raise HTTPException(status_code=400, detail="No Convening Order found. Please upload a Convening Order first.")

    supp_docs = case_service.state.get("supporting_docs", [])
    if supp_docs:
        supp_text = "\n\n".join([f"=== {d['file_name']} ===\n{d.get('full_text', '')[:MAX_DOC_CHARS_IN_PROMPT]}" for d in supp_docs])
    else:
        supp_text = "No additional supporting documents uploaded yet. Analyze based on Convening Order instructions."

    # Collate recorded witness statements
    witnesses = case_service.state.get("witnesses", [])
    witness_stmts_list = []
    for w in witnesses:
        if w.get("statement") and len(w["statement"].strip()) > 5:
            witness_stmts_list.append(
                f"Witness {w.get('ref_letter', '')} ({w.get('rank', '')} {w.get('name', '')}):\n{w['statement']}"
            )
    witness_stmts_text = "\n\n".join(witness_stmts_list)

    # Cap the law context: the full catalog is huge and slows the CPU model down.
    military_laws = get_all_military_laws()
    military_laws_str = "\n\n".join([
        f"[{law['rule_or_section']}] {law['title']}\nSummary: {law['summary']}\nRelevance: {law['relevance']}"
        for law in military_laws
    ])[:8000]

    job_id = f"analysis_{int(time.time())}"
    _analysis_jobs[job_id] = {"status": "running", "started": time.time(), "detail": ""}

    # Keep the jobs dict small (only the newest 20 survive).
    if len(_analysis_jobs) > 20:
        for old_id in list(_analysis_jobs)[:-20]:
            _analysis_jobs.pop(old_id, None)

    def _run_analysis():
        try:
            analysis = llm_service.analyze_case_and_evidence(
                convening_order_text=conv_text,
                supporting_docs_text=supp_text,
                military_laws_context=military_laws_str,
                witness_statements_text=witness_stmts_text
            )
            case_service.state["case_analysis"] = analysis
            case_service.save_state()
            _analysis_jobs[job_id]["status"] = "done"
            logger.info(f"Case-brief analysis job {job_id} finished successfully.")
        except Exception as e:
            logger.error(f"Case-brief analysis job {job_id} failed: {e}")
            _analysis_jobs[job_id]["status"] = "error"
            _analysis_jobs[job_id]["detail"] = str(e)

    threading.Thread(target=_run_analysis, daemon=True).start()
    return {"success": True, "job_id": job_id, "status": "running"}

@app.get("/api/analyze/status/{job_id}")
def analyze_status(job_id: str):
    """Polling endpoint for the background case-brief analysis job."""
    job = _analysis_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Unknown analysis job (the server may have restarted). Please run the analysis again.")
    elapsed = int(time.time() - job["started"])
    return {
        "success": job["status"] == "done",
        "status": job["status"],
        "elapsed_seconds": elapsed,
        "detail": job.get("detail", "")
    }

@app.get("/api/military-laws")
def get_military_laws(query: Optional[str] = None):
    if query:
        return search_relevant_military_laws(query)
    return get_all_military_laws()

@app.post("/api/witnesses/add")
def add_witness(witness: WitnessModel):
    w_dict = witness.model_dump()
    if not w_dict.get("id"):
        w_dict["id"] = f"wit_{len(case_service.state['witnesses']) + 1}"
    case_service.state["witnesses"].append(w_dict)
    case_service.save_state()
    return {"success": True, "witnesses": case_service.state["witnesses"]}

@app.post("/api/witnesses/generate-questions")
def generate_witness_questions(payload: Dict[str, Any]):
    witness_id = payload.get("witness_id")
    witness = next((w for w in case_service.state["witnesses"] if w["id"] == witness_id), None)
    if not witness:
        raise HTTPException(status_code=404, detail="Witness not found")

    case_analysis = case_service.state.get("case_analysis") or {}
    conv_text = case_service.state.get("convening_order", {}).get("raw_text", "")
    parsed_order = case_service.state.get("convening_order", {}).get("parsed") or {}
    
    supp_docs = case_service.state.get("supporting_docs", [])
    supp_text = "\n\n".join([f"=== {d['file_name']} ===\n{d.get('full_text', '')[:MAX_DOC_CHARS_IN_PROMPT]}" for d in supp_docs])

    # Structured overview: subject / incident exactly as extracted from the
    # uploaded Convening Order, plus the analysed case brief.
    case_overview = {
        "subject_matter": parsed_order.get("subject_matter", ""),
        "incident_details": parsed_order.get("incident_details", {}),
        "terms_of_reference": parsed_order.get("terms_of_reference", []),
        "case_analysis": case_analysis,
    }

    questions = llm_service.generate_witness_questions(
        case_overview=case_overview,
        witness_info=witness,
        supporting_docs_text=supp_text,
        convening_order_text=conv_text
    )
    witness["questions"] = questions
    # Initialize qa_pairs with the questions so each has its manual answer field
    existing_qa = {item.get("question"): item.get("answer") for item in (witness.get("qa_pairs") or [])}
    witness["qa_pairs"] = [
        {"question": q, "answer": existing_qa.get(q, "")} for q in questions
    ]
    case_service.save_state()

    return {"success": True, "witness_id": witness_id, "questions": questions, "qa_pairs": witness["qa_pairs"]}

@app.post("/api/witnesses/save-qa")
def save_witness_qa(payload: Dict[str, Any]):
    witness_id = payload.get("witness_id")
    qa_pairs = payload.get("qa_pairs", [])
    witness = next((w for w in case_service.state["witnesses"] if w["id"] == witness_id), None)
    if not witness:
        raise HTTPException(status_code=404, detail="Witness not found")

    witness["qa_pairs"] = qa_pairs
    case_service.save_state()
    return {"success": True, "witness": witness}

@app.post("/api/witnesses/compile-statement")
def compile_witness_statement(payload: Dict[str, Any]):
    witness_id = payload.get("witness_id")
    witness = next((w for w in case_service.state["witnesses"] if w["id"] == witness_id), None)
    if not witness:
        raise HTTPException(status_code=404, detail="Witness not found")

    if "qa_pairs" in payload:
        witness["qa_pairs"] = payload["qa_pairs"]
    if "statement" in payload and payload["statement"]:
        witness["statement"] = payload["statement"]

    case_analysis = case_service.state.get("case_analysis") or {}
    conv_text = case_service.state.get("convening_order", {}).get("raw_text", "")

    compiled = llm_service.compile_witness_testimony(
        witness_info=witness,
        case_overview=case_analysis,
        convening_order_text=conv_text
    )
    witness["compiled_testimony"] = compiled

    # Build joined narrative for general review and cross-correlation
    qa_lines = [f"{item.get('q', '')} {item.get('ans', '')}" for item in compiled.get("questions_by_court", [])]
    full_text = (
        f"{compiled.get('warning_declaration', '')}\n\n"
        f"{compiled.get('posting_and_duties', '')}\n\n"
        f"{compiled.get('narrative_statement', '')}\n\n"
        f"Question by the Court\n\n" +
        "\n".join(qa_lines) +
        f"\n\n{compiled.get('closing_affirmation', '')}"
    )
    witness["statement"] = full_text

    case_service.save_state()
    return {"success": True, "witness": witness, "compiled_testimony": compiled}

@app.post("/api/witnesses/save-statement")
def save_witness_statement(payload: Dict[str, Any]):
    witness_id = payload.get("witness_id")
    statement = payload.get("statement", "")
    witness = next((w for w in case_service.state["witnesses"] if w["id"] == witness_id), None)
    if not witness:
        raise HTTPException(status_code=404, detail="Witness not found")

    witness["statement"] = statement
    case_service.save_state()
    return {"success": True, "witness": witness}

@app.post("/api/presiding-officer/review")
def review_and_forward(review: PresidingOfficerReviewModel):
    case_service.state["presiding_officer_review"] = review.model_dump()
    case_service.state["presiding_officer_review"]["verified"] = True
    case_service.save_state()
    return {"success": True, "presiding_officer_review": case_service.state["presiding_officer_review"]}

@app.post("/api/coi/generate")
def generate_court_of_inquiry_draft():
    coi_draft = llm_service.generate_coi_draft_report(case_service.state)
    case_service.state["coi_draft"] = coi_draft
    case_service.state["status"] = "DRAFTED"
    case_service.state["status_label"] = "Drafted"
    case_service.save_state()
    
    # Also generate the downloadable DOCX file
    docx_file_path = generate_coi_docx(coi_draft)
    
    return {
        "success": True, 
        "coi_draft": coi_draft,
        "docx_path": docx_file_path,
        "case_state": case_service.state
    }

@app.get("/api/coi/download-docx")
def download_coi_docx():
    file_path = UPLOAD_DIR / "Court_of_Inquiry_Proceedings.docx"
    # Always rebuild from the CURRENT case's draft: the docx file name is global,
    # so serving the file as-is could hand out a different case's draft.
    if case_service.state.get("coi_draft"):
        generate_coi_docx(case_service.state["coi_draft"])
    elif not file_path.exists():
        raise HTTPException(status_code=400, detail="CoI draft not generated yet.")
            
    return FileResponse(
        str(file_path),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename="Court_of_Inquiry_Proceedings_FINAL.docx"
    )

# Mount React frontend static files if built
FRONTEND_DIST = WORKSPACE_DIR / "frontend" / "dist"
if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="assets")

    @app.get("/{full_path:path}")
    def serve_frontend(full_path: str):
        file_path = FRONTEND_DIST / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(FRONTEND_DIST / "index.html"))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
# (file touch: makes every running instance reload the case state from disk)

