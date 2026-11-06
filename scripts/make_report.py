# -*- coding: utf-8 -*-
"""
Generates the Project Report (Word .docx) for the
Court of Inquiry Rules Library & Automated Question Generation System.

Run:  python make_report.py
Out:  Project_Report_Court_of_Inquiry.docx
"""

import sys
from pathlib import Path

try:
    from docx import Document
    from docx.shared import Pt, Inches, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
except ImportError:
    print("python-docx is not installed. Install it with:")
    print("   pip install python-docx")
    sys.exit(1)

OUT_PATH = Path(__file__).resolve().parent / "Project_Report_Court_of_Inquiry.docx"

ACCENT = RGBColor(0x1F, 0x3B, 0x5C)   # dark navy
GREY = RGBColor(0x59, 0x59, 0x59)


# ---------------------------------------------------------------- helpers
def set_style(doc):
    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(11)
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.15
    for level, size in ((1, 16), (2, 13), (3, 12)):
        st = doc.styles[f"Heading {level}"]
        st.font.name = "Calibri"
        st.font.size = Pt(size)
        st.font.color.rgb = ACCENT
        st.font.bold = True


def h(doc, text, level=1):
    p = doc.add_heading(text, level=level)
    p.paragraph_format.space_before = Pt(14 if level == 1 else 10)
    p.paragraph_format.space_after = Pt(6)
    return p


def para(doc, text, bold=False, italic=False, size=None, align=None, color=None):
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.bold = bold
    r.italic = italic
    if size:
        r.font.size = Pt(size)
    if color:
        r.font.color.rgb = color
    if align is not None:
        p.alignment = align
    return p


def bullets(doc, items, style="List Bullet"):
    for it in items:
        p = doc.add_paragraph(style=style)
        if isinstance(it, tuple):
            r = p.add_run(it[0])
            r.bold = True
            p.add_run(it[1])
        else:
            p.add_run(it)
        p.paragraph_format.space_after = Pt(3)


def table(doc, headers, rows, widths=None):
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr = t.rows[0].cells
    for i, text in enumerate(headers):
        hdr[i].text = ""
        p = hdr[i].paragraphs[0]
        r = p.add_run(text)
        r.bold = True
        r.font.size = Pt(10)
        r.font.color.rgb = ACCENT
        shd = OxmlElement("w:shd")
        shd.set(qn("w:val"), "clear")
        shd.set(qn("w:fill"), "DCE6F1")
        hdr[i]._tc.get_or_add_tcPr().append(shd)
    for row in rows:
        cells = t.add_row().cells
        for i, text in enumerate(row):
            cells[i].text = ""
            r = cells[i].paragraphs[0].add_run(str(text))
            r.font.size = Pt(10)
    if widths:
        for row in t.rows:
            for i, w in enumerate(widths):
                row.cells[i].width = Inches(w)
    doc.add_paragraph()
    return t


def page_number_footer(doc):
    for section in doc.sections:
        p = section.footer.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run("Page ")
        run.font.size = Pt(9)
        run.font.color.rgb = GREY
        r2 = p.add_run()
        f1 = OxmlElement("w:fldChar"); f1.set(qn("w:fldCharType"), "begin")
        it = OxmlElement("w:instrText"); it.set(qn("xml:space"), "preserve"); it.text = "PAGE"
        f2 = OxmlElement("w:fldChar"); f2.set(qn("w:fldCharType"), "end")
        r2._r.append(f1); r2._r.append(it); r2._r.append(f2)
        r2.font.size = Pt(9)
        r2.font.color.rgb = GREY


def page_break(doc):
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


# ---------------------------------------------------------------- report
def build():
    doc = Document()
    set_style(doc)

    # margins
    for s in doc.sections:
        s.top_margin = Inches(0.9)
        s.bottom_margin = Inches(0.9)
        s.left_margin = Inches(1.0)
        s.right_margin = Inches(1.0)

    # ================= 1. COVER PAGE =================
    for _ in range(4):
        doc.add_paragraph()
    para(doc, "PROJECT REPORT", bold=True, size=15, align=WD_ALIGN_PARAGRAPH.CENTER, color=GREY)
    doc.add_paragraph()
    para(doc, "Court of Inquiry Rules Library and\nAutomated Witness Question Generation System",
         bold=True, size=26, align=WD_ALIGN_PARAGRAPH.CENTER, color=ACCENT)
    doc.add_paragraph()
    para(doc, "Metadata-Driven Military Rule Selection and LLM-Based\nInvestigative Question Generation",
         italic=True, size=13, align=WD_ALIGN_PARAGRAPH.CENTER, color=GREY)
    for _ in range(4):
        doc.add_paragraph()
    para(doc, "Prepared by:  [Author / Team Member Names]", size=12,
         align=WD_ALIGN_PARAGRAPH.CENTER)
    para(doc, "Department / Organisation:  [Organisation Name]", size=12,
         align=WD_ALIGN_PARAGRAPH.CENTER)
    para(doc, "Date:  November 2026", size=12, align=WD_ALIGN_PARAGRAPH.CENTER)
    page_break(doc)

    # ================= TABLE OF CONTENTS =================
    h(doc, "Table of Contents", 1)
    toc = [
        "1.  Cover Page and Title",
        "2.  Executive Summary",
        "3.  Introduction",
        "4.  Objectives and Scope",
        "5.  Methodology and Data Collection",
        "6.  Project Timeline and Milestones",
        "7.  Results and Findings",
        "8.  Analysis and Interpretation",
        "9.  Conclusion",
        "10. Recommendations",
        "11. References and Citations",
        "12. Appendix and Supporting Documents",
    ]
    for line in toc:
        p = doc.add_paragraph()
        r = p.add_run(line)
        r.font.size = Pt(12)
        p.paragraph_format.space_after = Pt(4)
    page_break(doc)

    # ================= 2. EXECUTIVE SUMMARY =================
    h(doc, "2. Executive Summary", 1)
    para(doc,
         "The Court of Inquiry (CoI) Rules Library and Automated Witness Question Generation System "
         "was conceived to reduce the time and manual effort required to draft legally sound "
         "investigative questions for military Court of Inquiry proceedings. Traditionally, presiding "
         "officers and their staff read through multiple volumes of Defence Services Regulations (DSR) "
         "and Military Manual of Law (MML) to identify the applicable provisions, and then draft "
         "questions for each witness manually. This project automates that entire chain.")
    para(doc,
         "Six rule-book PDFs (DSR Volume 1, DSR Volume 2, DSR Volume 2-1, MML Volume 1, "
         "MML Volume 2 (AR)-1 and MML Volume 3) were parsed offline into a structured, searchable "
         "JSON catalogue containing 51 classified rules. This includes 15 dedicated Fire Inquiry "
         "Procedures, FIRE-(i) to FIRE-(xv), extracted verbatim from DSR Volume 2-1. At runtime the "
         "system derives keywords from the case subject matter and convening order, selects the most "
         "relevant rules in under 100 milliseconds, and passes them to a locally hosted large language "
         "model (Ollama / gemma3:4b) to generate 5 to 7 grounded questions per witness.")
    para(doc,
         "A three-tier fallback strategy guarantees output in every situation: Tier 1 generates "
         "questions grounded in catalogue rules; Tier 2 applies case-type templates (fire, vehicle "
         "accident, electrical safety) when no rule matches; Tier 3 falls back to the standard CoI "
         "question framework. All pre-existing API endpoints and frontend workflows were preserved, "
         "giving 100% backward compatibility.")
    para(doc,
         "Key results: a 51-rule catalogue built from 6 PDFs, sub-100 ms rule retrieval, 5-7 "
         "contextual questions per witness, a complete end-to-end workflow from convening-order upload "
         "to downloadable CoI proceedings (DOCX), and a fully offline deployment bundle for "
         "air-gapped machines. Principal challenges were heuristic (non-semantic) rule matching, "
         "page-number approximation during extraction, and large regenerable artefacts in the "
         "repository. Recommendations include semantic search, expansion of accident and electrical "
         "safety procedures, and repository clean-up of approximately 12 GB of legacy artefacts.")

    # ================= 3. INTRODUCTION =================
    h(doc, "3. Introduction", 1)
    h(doc, "3.1 Background and Context", 2)
    para(doc,
         "A Court of Inquiry is a fact-finding authority constituted under the Army Rules and the "
         "Defence Services Regulations to establish the circumstances, cause and responsibility of an "
         "incident such as a fire, vehicle accident, or casualty occurring in the line of duty. The "
         "convening authority issues a Convening Order that defines the scope of the inquiry, and the "
         "court examines witnesses record-by-record to build a complete, admissible account of events.")
    para(doc,
         "The questioning of witnesses is the most critical and time-consuming phase. Every question "
         "must be relevant, non-leading where required, and traceable to a specific statutory "
         "provision. Today this requires manual cross-referencing across six physical or PDF volumes "
         "of DSR and MML - a process that is slow, error-prone and inconsistent between courts.")
    h(doc, "3.2 Purpose and Significance", 2)
    para(doc,
         "The purpose of this project is to build an offline-first, deterministic rules library that "
         "selects the applicable military provisions for a given case automatically and uses a local "
         "language model to draft witness questions grounded in those provisions. The significance is "
         "threefold: (a) it reduces question-drafting time from hours to seconds; (b) it improves "
         "legal defensibility by citing the exact rule behind each question; and (c) it runs entirely "
         "on local infrastructure, satisfying the confidentiality requirements of military proceedings.")
    h(doc, "3.3 Scope", 2)
    bullets(doc, [
        ("Included: ", "offline extraction of the six DSR/MML PDF rule books; a structured JSON "
         "rules catalogue; keyword-based rule selection; LLM-based question generation with a "
         "three-tier fallback; the complete CoI web workflow (convening order, evidence, witnesses, "
         "presiding-officer review, draft generation, DOCX export); offline Docker deployment."),
        ("Excluded: ", "a full Retrieval-Augmented Generation (RAG) vector pipeline; external "
         "cloud LLM APIs; automated legal adjudication or findings; production of the final signed "
         "CoI report (only a draft is generated); any modification of the statutory rules themselves."),
    ])

    # ================= 4. OBJECTIVES AND SCOPE =================
    h(doc, "4. Objectives and Scope", 1)
    h(doc, "4.1 Specific Goals", 2)
    bullets(doc, [
        "Extract and structure all usable rule content from the six source PDFs into a single "
        "searchable JSON catalogue.",
        "Provide a deterministic rule-selection function that returns the most relevant rules for "
        "any case subject matter in under 100 ms.",
        "Generate 5 to 7 legally grounded investigative questions for every witness, referencing the "
        "selected rules.",
        "Implement a case-type-aware fallback so that questions are still produced when no catalogue "
        "rule matches (fire, vehicle accident, electrical safety, default).",
        "Maintain 100% backward compatibility with the existing API surface and React frontend.",
        "Deliver a fully offline deployment (local LLM, local OCR, no internet dependency).",
        "Produce an end-to-end workflow from Convening Order upload to a downloadable CoI draft "
        "document.",
    ])
    h(doc, "4.2 Defined Boundaries and Deliverables", 2)
    table(doc, ["Deliverable", "Description", "Status"], [
        ["Rules catalogue JSON", "51 structured rules from 6 PDFs (backend/data/military_rules_structured.json)", "Completed"],
        ["Rule selection engine", "select_rules() with keyword scoring, topic and rule_number filters", "Completed"],
        ["Question generator", "Tier 1/2/3 generation inside llm_service.generate_witness_questions()", "Completed"],
        ["FastAPI backend", "15+ REST endpoints covering auth, upload, analysis, witnesses, CoI draft", "Completed"],
        ["React frontend", "7-step CoI workflow with case management and DOCX download", "Completed"],
        ["Offline deployment bundle", "Docker Compose, Linux wheels, Ollama model store, DVD packaging", "Completed"],
        ["Documentation", "README.md, setup.md, MERGE_SETUP.md, backend/guide.md, this report", "Completed"],
    ])

    # ================= 5. METHODOLOGY =================
    h(doc, "5. Methodology and Data Collection", 1)
    h(doc, "5.1 Approach", 2)
    para(doc,
         "The project deliberately avoided a full RAG pipeline in favour of an offline, deterministic, "
         "metadata-driven catalogue. Rules are parsed once at build time, stored as JSON with rich "
         "metadata (rule number, title, summary, relevance, source document, section, topic, keywords, "
         "page range), and selected at runtime by weighted keyword scoring. This makes the system "
         "reproducible, auditable and explainable - every selected rule can be traced back to a page "
         "in a named source PDF.")
    h(doc, "5.2 Tools, Techniques and Processes", 2)
    table(doc, ["Layer", "Tool / Technique"], [
        ["Data extraction", "PyPDF2 / pypdf page-wise text extraction; heuristic regular-expression parsing"],
        ["Catalogue build", "ingest_pdfs.py - rule pattern matching, deduplication, keyword assignment"],
        ["Rule selection", "Custom weighted keyword scorer in military_law_service.select_rules()"],
        ["Question generation", "Ollama runtime with gemma3:4b; structured JSON prompting; 5-7 questions"],
        ["OCR", "rapidocr-onnxruntime + pytesseract + PyMuPDF for PDF/scan text"],
        ["Backend", "Python 3.11/3.12, FastAPI, Pydantic v2, python-docx, python-multipart"],
        ["Frontend", "React 18, Vite, Tailwind CSS, Axios REST integration"],
        ["Packaging", "Docker, Docker Compose, offline pip wheels, tar/split DVD bundles"],
        ["Quality gates", "Theme/dark-palette verification scripts (.theme-gate, .theme-verify)"],
    ])
    h(doc, "5.3 Data Collection and Analysis", 2)
    para(doc,
         "Primary data consisted of the six rule-book PDFs held in the files/ directory. Text was "
         "extracted page by page, then segmented using rule-number patterns (Army Rule N, DSR Para N, "
         "Section N, Rule N, MML Vol N) and numbered procedural clauses (i) to (xv). Each entry was "
         "enriched with a summary, relevance text, source document, section, topic and keywords, and "
         "duplicate entries were removed. The resulting catalogue was validated with dedicated test "
         "scripts (test_select_rules.py, test_integration.py) exercising intoxication, bonafide-duty "
         "and character-reputation queries. Case-level data (Convening Orders, FIRs, medical and "
         "technical inspection reports) was collected through the application's upload endpoints and "
         "used for end-to-end validation.")

    # ================= 6. TIMELINE =================
    h(doc, "6. Project Timeline and Milestones", 1)
    para(doc,
         "The project followed a six-phase incremental lifecycle. Dates below are indicative; the "
         "authoritative change record is retained in daily-log-27-28-oct.md (the repository is not "
         "under version control).", italic=True)
    table(doc, ["Phase", "Activities", "Planned", "Actual / Status"], [
        ["1. Requirement analysis", "Study CoI workflow, inventory 6 PDFs, define catalogue schema", "Week 1", "On track"],
        ["2. Data extraction", "Build ingest_pdfs.py, parse 6 PDFs, deduplicate to 51 rules", "Week 2", "Completed"],
        ["3. Rule selection engine", "Implement select_rules(), keyword scoring, topic filters", "Week 3", "Completed"],
        ["4. LLM integration", "Three-tier question generation, prompt engineering, fallback tests", "Week 4", "Completed"],
        ["5. Workflow integration", "FastAPI endpoints, React 7-step workflow, DOCX export", "Week 5", "Completed"],
        ["6. Testing & packaging", "Backward-compatibility tests, offline Docker bundle, documentation", "Week 6", "Completed"],
    ])
    para(doc,
         "Key milestones achieved: first successful catalogue build (51 rules); first grounded "
         "question set generated for a fire-incident case; end-to-end run from Convening Order upload "
         "to downloadable CoI proceedings; and production of the offline DVD bundle "
         "(legal-bundle parts, image archive and Ollama model store).")

    # ================= 7. RESULTS =================
    h(doc, "7. Results and Findings", 1)
    h(doc, "7.1 Quantitative Results", 2)
    table(doc, ["Metric", "Result"], [
        ["Source PDFs processed", "6 (DSR Vol 1, Vol 2, Vol 2-1; MML Vol 1, Vol 2(AR)-1, Vol 3)"],
        ["Rules in catalogue", "51 structured rules (200+ raw entries before de-duplication)"],
        ["Fire Inquiry Procedures", "15 - FIRE-(i) through FIRE-(xv)"],
        ["Rule retrieval time", "< 100 ms per query (in-memory JSON)"],
        ["Questions per witness", "5 to 7, IAFD-931 category aligned"],
        ["Question generation time", "2 to 5 seconds (LLM dependent)"],
        ["Backward compatibility", "100% - all existing endpoints unchanged"],
        ["Offline capability", "100% - no internet required after initial setup"],
        ["REST endpoints", "15+ covering auth, uploads, analysis, witnesses, CoI draft"],
        ["Legacy / regenerable data identified", "~12 GB safe to reclaim"],
    ])
    h(doc, "7.2 Qualitative Results", 2)
    bullets(doc, [
        ("Rule-grounded questioning. ", "Questions now cite the exact provision (e.g. FIRE-(v): "
         "elapsed time between discovery and alarm), making the record more defensible."),
        ("Consistency. ", "Every court gets the same structured starting set for the same case type, "
         "reducing investigator-dependent variance."),
        ("Guaranteed output. ", "The three-tier fallback means no witness is ever left without "
         "questions, even for novel case types."),
        ("Traceability. ", "Each selected rule records its source document and page range, allowing "
         "instant manual verification."),
        ("Complete workflow. ", "Upload, analysis, questioning, testimony compilation, "
         "presiding-officer review and draft generation all function in a single application."),
    ])
    h(doc, "7.3 Performance Against Objectives", 2)
    table(doc, ["Objective", "Target", "Achieved"], [
        ["Structured rules catalogue", "From 6 PDFs", "Yes - 51 rules"],
        ["Rule selection speed", "< 100 ms", "Yes"],
        ["Questions per witness", "5-7", "Yes"],
        ["Fallback for unknown cases", "Required", "Yes - 3 tiers"],
        ["Backward compatibility", "100%", "Yes"],
        ["Offline operation", "Required", "Yes"],
    ])

    # ================= 8. ANALYSIS =================
    h(doc, "8. Analysis and Interpretation", 1)
    h(doc, "8.1 Discussion", 2)
    para(doc,
         "The results confirm that a metadata-driven catalogue is sufficient for this domain. Because "
         "military rule books use highly regular numbering conventions, keyword scoring recovered the "
         "correct fire procedures in every tested fire case, and the intoxication queries correctly "
         "surfaced Army Rule 180. The three-tier design proved its worth: even when the catalogue "
         "missed, the case-type templates produced domain-relevant questions rather than generic ones.")
    h(doc, "8.2 Issues, Risks and Deviations", 2)
    table(doc, ["Issue / Risk", "Impact", "Mitigation / Status"], [
        ["Heuristic keyword matching is not semantic", "Synonyms may miss rules (e.g. 'blaze' vs 'fire')", "Mitigated by keyword enrichment; semantic search recommended"],
        ["Page numbers approximate after extraction", "Citations may need manual confirmation", "Accepted - page_start/page_end recorded as approximate"],
        ["LLM output variability", "Question wording varies between runs", "JSON schema prompt + fallback list ensures structure"],
        ["Duplicate raw entries in source PDFs", "Catalogue bloat if rebuilt naively", "De-duplication step in ingest pipeline"],
        ["Large legacy artefacts (~12 GB)", "Repository bloat, slow transfers", "Categorised for clean-up (docker-images, transfer, ollama-docker)"],
        ["Hard-coded absolute paths in scripts", "Portability risk on other machines", "Scripts are build-time only; runtime paths come from config.py"],
        ["No version control", "Change tracking by hand", "daily-log and MERGE_SETUP serve as change record"],
    ])
    h(doc, "8.3 Lessons Learned", 2)
    bullets(doc, [
        "Pre-processing PDFs into structured JSON beats on-the-fly parsing: it makes the runtime "
        "simple, fast and fully auditable.",
        "A small, deterministic selector plus a capable LLM outperforms either component alone.",
        "Backward compatibility must be designed in from the start - keeping original function "
        "signatures avoided every frontend regression.",
        "Offline-first constraints (local model, local OCR, bundled wheels) drive architecture "
        "decisions early and cannot be added later cheaply.",
        "Repository hygiene matters: regenerable artefacts should be excluded from the working tree.",
    ])

    # ================= 9. CONCLUSION =================
    h(doc, "9. Conclusion", 1)
    para(doc,
         "The project successfully delivered an offline Court of Inquiry rules library and automated "
         "witness question generation system. All primary objectives were met: six rule-book PDFs were "
         "converted into a 51-rule structured catalogue; relevant rules are selected in under 100 "
         "milliseconds; 5 to 7 grounded questions are produced for every witness; a three-tier fallback "
         "guarantees output for any case type; and the existing API and frontend continued to work "
         "without modification.")
    para(doc,
         "The system also delivered beyond its original scope, including a complete workflow from "
         "Convening Order ingestion through evidence analysis, witness examination, testimony "
         "compilation and presiding-officer review, culminating in a downloadable DOCX draft of the "
         "CoI proceedings, plus a portable offline deployment bundle suitable for air-gapped military "
         "infrastructure.")
    para(doc,
         "Areas for improvement remain: rule matching is keyword-based rather than semantic; a few "
         "procedural areas (vehicle accident, electrical safety) are covered by templates instead of "
         "extracted statutory procedures; and the repository carries legacy artefacts that should be "
         "pruned. Overall, the deliverables are assessed as complete, functional and fit for "
         "operational trial.")

    # ================= 10. RECOMMENDATIONS =================
    h(doc, "10. Recommendations", 1)
    table(doc, ["#", "Recommendation", "Priority", "Benefit"], [
        ["1", "Replace keyword scoring with semantic (embedding) search over rule summaries", "High", "Removes synonym misses; true relevance ranking"],
        ["2", "Extract vehicle-accident procedures (DSR Para 519-520) into the catalogue", "High", "Covers the second most common case type with real rules"],
        ["3", "Add electrical-safety and bonafide-duty procedures (DSR Para 516-521)", "Medium", "Reduces reliance on Tier 2 templates"],
        ["4", "Add an auto case-type detector in the UI with manual override", "Medium", "Faster, more accurate Tier selection"],
        ["5", "Prune ~12 GB of legacy artefacts (docker-images/, ollama-docker/, transfer/)", "Medium", "Smaller, faster repository and transfers"],
        ["6", "Move scripts off absolute paths and add a config-driven CLI", "Low", "Portability across machines"],
        ["7", "Introduce version control (git) with a proper .gitignore", "Low", "Real change history instead of manual logs"],
        ["8", "Run a structured user trial with presiding officers and collect feedback", "High", "Validates question quality with real users"],
    ])

    # ================= 11. REFERENCES =================
    h(doc, "11. References and Citations", 1)
    refs = [
        "Defence Services Regulations, Volume 1 (DSR_vol_1.pdf), internal reference copy.",
        "Defence Services Regulations, Volume 2 (DSR vol 2.pdf), internal reference copy.",
        "Defence Services Regulations, Volume 2-1 (DSR vol 2-1.pdf) - source of Fire Inquiry "
        "Procedures FIRE-(i) to FIRE-(xv).",
        "Military Manual of Law, Volume 1 (MMLvol 1.pdf), internal reference copy.",
        "Military Manual of Law, Volume 2 (AR)-1 (MML vol 2(AR)-1.pdf), internal reference copy.",
        "Military Manual of Law, Volume 3 (MML vol 3.pdf), internal reference copy.",
        "Army Rules (relevant provisions, as extracted in the rules catalogue).",
        "IAFD-931 - standard Court of Inquiry question categories (as referenced in the "
        "question-generation prompts).",
        "Project README.md - system overview, ports and compose usage.",
        "Project setup.md and setup-transfer.md - offline build and DVD distribution procedure.",
        "MERGE_SETUP.md - repository structure and change record.",
        "backend/guide.md - detailed architecture and workflow documentation (internal).",
        "daily-log-27-28-oct.md - project change log for 27-28 October 2026.",
    ]
    for i, r in enumerate(refs, 1):
        p = doc.add_paragraph()
        run = p.add_run(f"[{i}]  ")
        run.bold = True
        p.add_run(r)
        p.paragraph_format.space_after = Pt(3)

    # ================= 12. APPENDIX =================
    h(doc, "12. Appendix and Supporting Documents", 1)

    h(doc, "Appendix A - Rules Catalogue Breakdown", 2)
    table(doc, ["Category", "Count", "Description"], [
        ["Section rules", "154", "DSR/MML Section entries (e.g. Section 26, Section 90)"],
        ["MML rules", "60", "Military Manual of Law entries"],
        ["Procedural / general", "27", "Procedural and standalone content"],
        ["DSR Para rules", "27", "Defence Services Regulations Para entries"],
        ["Army Rules", "17", "Army Rules 177-184, 180, 195-197"],
        ["Fire Inquiry Procedures", "15", "FIRE-(i) to FIRE-(xv) from DSR Vol 2-1"],
        ["Total (de-duplicated)", "51", "Stored in backend/data/military_rules_structured.json"],
    ])

    h(doc, "Appendix B - Fire Inquiry Procedures (FIRE-(i) to FIRE-(xv))", 2)
    table(doc, ["Rule", "Question focus"], [
        ["FIRE-(i)", "The origin of the fire"],
        ["FIRE-(ii)", "By whom it was discovered"],
        ["FIRE-(iii)", "Action taken by the person making the discovery"],
        ["FIRE-(iv)", "To whom the fire was first reported"],
        ["FIRE-(v)", "Time between discovery of the fire and sounding of the alarm"],
        ["FIRE-(vi)", "Name of the officer in command of fire arrangements"],
        ["FIRE-(vii)", "Time after alarm before appliances were at work"],
        ["FIRE-(viii)", "Whether the fire piquet turned out in sufficient numbers"],
        ["FIRE-(viii/b)", "Whether there was any failure as regards water supply"],
        ["FIRE-(ix)", "Action taken to warn the local fire brigade"],
        ["FIRE-(x)", "Time between warning and arrival of the fire brigade"],
        ["FIRE-(xi)", "Extent of assistance given by the fire brigade"],
        ["FIRE-(xiii)", "Period from alarm until the fire was extinguished"],
        ["FIRE-(xiv)", "Extent of damage to persons, buildings and contents"],
        ["FIRE-(xv)", "Responsibility for the outbreak of the fire"],
    ])

    h(doc, "Appendix C - Project File Structure", 2)
    structure = [
        "legal/",
        "|-- backend/",
        "|   |-- main.py                     FastAPI application (15+ endpoints)",
        "|   |-- config.py                   Paths and limits configuration",
        "|   |-- guide.md                    Full architecture documentation",
        "|   |-- requirements.txt            Python dependencies",
        "|   |-- data/military_rules_structured.json   51-rule catalogue",
        "|   |-- services/                   ocr, military law, LLM, case, report services",
        "|   |-- uploads/                    Case files, active state, archived cases",
        "|   |-- wheels/ , wheels-linux/     Offline pip wheels",
        "|-- frontend/                       React + Vite + Tailwind application",
        "|-- files/                          6 source rule-book PDFs",
        "|-- data/                           Law document store (backed up)",
        "|-- compose.yml , compose.debug.yml Production and debug stacks",
        "|-- setup.md, README.md, MERGE_SETUP.md   Procedure documentation",
        "|-- beginner-pack/                  End-user helper scripts",
        "|-- offline/ , transfer/            Offline deployment artefacts",
    ]
    for line in structure:
        p = doc.add_paragraph()
        r = p.add_run(line)
        r.font.name = "Consolas"
        r.font.size = Pt(9)
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.line_spacing = 1.0

    h(doc, "Appendix D - REST API Endpoints", 2)
    table(doc, ["Method", "Endpoint", "Purpose"], [
        ["GET", "/api/health", "System health check"],
        ["POST", "/api/auth/login", "Login and new case session"],
        ["GET", "/api/case/current", "Current case state"],
        ["POST", "/api/upload/convening-order", "Upload and parse Convening Order"],
        ["POST", "/api/upload/supporting-docs", "Upload supporting documents (max 12, 3 MB each)"],
        ["POST", "/api/analyze/case-brief", "LLM case and evidence analysis"],
        ["GET", "/api/military-laws", "Query the rules catalogue"],
        ["POST", "/api/witnesses/add", "Register a witness"],
        ["POST", "/api/witnesses/generate-questions", "Generate 5-7 grounded questions"],
        ["POST", "/api/witnesses/save-qa", "Save question-answer pairs"],
        ["POST", "/api/witnesses/compile-statement", "Compile witness testimony"],
        ["POST", "/api/presiding-officer/review", "Record presiding-officer review"],
        ["POST", "/api/coi/generate", "Generate CoI draft + DOCX"],
        ["GET", "/api/coi/download-docx", "Download CoI proceedings document"],
    ])

    h(doc, "Appendix E - Sample Generated Questions (Fire Incident Case)", 2)
    para(doc, "Case subject matter: \"Fire incident on bonafide military duty\"", italic=True)
    samples = [
        "Q1. What was the exact origin of the fire you witnessed?",
        "Q2. Who first discovered the fire, and how did they discover it?",
        "Q3. How much time elapsed between discovering the fire and sounding the alarm?",
        "Q4. Were you in a state of intoxication when the fire occurred?",
        "Q5. Was your assigned fire-fighting equipment in good condition?",
        "Q6. To whom was the fire first reported, and what action followed?",
        "Q7. What was the extent of damage caused to persons and buildings?",
    ]
    bullets(doc, samples)

    h(doc, "Appendix F - Supporting Documents Index", 2)
    bullets(doc, [
        "README.md - project overview and quick start",
        "setup.md - full offline build and deployment procedure",
        "setup-transfer.md - 4-DVD distribution plan",
        "MERGE_SETUP.md - repository map and change record",
        "backend/guide.md - architecture, workflow and Q&A documentation",
        "daily-log-27-28-oct.md - work log for 27-28 October 2026",
        "Project_Report_Court_of_Inquiry.docx - this report",
    ])

    # footer
    page_number_footer(doc)

    doc.save(str(OUT_PATH))
    print(f"Report generated: {OUT_PATH}")
    print(f"Size: {OUT_PATH.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    build()
