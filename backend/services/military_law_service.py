import os
import re
from pathlib import Path
from typing import List, Dict, Any
from config import DATA_DIR
import json

# ---------------------------------------------------------------------------
# Load structured rules catalog from JSON (Phase 1 output)
# ---------------------------------------------------------------------------
CATALOG_PATH = Path(__file__).parent.parent / "data" / "military_rules_structured.json"

def _load_catalog() -> List[Dict[str, Any]]:
    """Load the structured rules catalog from JSON, fallback to empty list."""
    try:
        with open(CATALOG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("rules", [])
    except Exception as e:
        print(f"Warning: Could not load rules catalog from {CATALOG_PATH}: {e}")
        return []

#: Rules catalog loaded at module import time.
MILITARY_LAW_CATALOG: List[Dict[str, Any]] = _load_catalog()

#: Fallback hardcoded list (kept for backward compatibility; will be
#:  identical to the first 7 entries of MILITARY_LAW_CATALOG when the JSON
#:  is built from the original knowledge base).
MILITARY_LAW_KNOWLEDGE_BASE: List[Dict[str, Any]] = [
    {
        "source": "Army Rules 1954 - Chapter VI (Courts of Inquiry)",
        "rule_or_section": "Army Rule 177",
        "title": "Courts of Inquiry - Assembly and Composition",
        "summary": "A Court of Inquiry is an assembly of officers or of officers and junior commissioned officers directed to collect evidence, and if so required, to report with regard to any matter referred to them.",
        "relevance": "Statutory basis for convening and constitution of the Court of Inquiry under In lieu of IAFD-931."
    },
    {
        "source": "Army Rules 1954 - Chapter VI (Courts of Inquiry)",
        "rule_or_section": "Army Rule 179",
        "title": "Procedure of Court of Inquiry - Warning and Oath",
        "summary": "Witnesses are duly warned under oath/affirmation. Statements are recorded with Question by the Court. The witness affirms that the statement was read out in a language they understand and signs it as correct.",
        "relevance": "Mandates formal warning of witnesses, recording sequential Question by the Court (Q&A), and obtaining signature with Presiding Officer certification."
    },
    {
        "source": "Army Rules 1954 - Chapter VI (Courts of Inquiry)",
        "rule_or_section": "Army Rule 180",
        "title": "Procedure when Character or Military Reputation is Affected",
        "summary": "Whenever an inquiry affects the character or military reputation of any person subject to the Act, full opportunity must be afforded to him of being present throughout, making statements, and cross-examining witnesses.",
        "relevance": "CRITICAL: The court must explicitly record whether any blame attaches to the individual or if they are completely exonerated."
    },
    {
        "source": "Defence Services Regulations (DSR) / Regulations for the Army",
        "rule_or_section": "DSR Para 516 & 517",
        "title": "Inquiry into Injuries Sustained by Personnel (IAFD-931)",
        "summary": "Whenever an officer or soldier sustains severe injury or fracture, a Court of Inquiry is convened to establish: (a) Exact circumstances and location, (b) Whether individual was on bonafide military duty, (c) Whether attributable to military service, (d) Whether intoxicated, (e) Whether to blame.",
        "relevance": "Direct governing regulation for injury inquiries (e.g. fracture distal end of radius sustained on bicycle or vehicle movement)."
    },
    {
        "source": "Entitlement Rules for Casualty Pensionary Awards",
        "rule_or_section": "Rule 12 - Duty Context & Journey",
        "title": "Bonafide Military Duty and Journey to/from Office",
        "summary": "Personnel traveling between their official residence/quarter and place of duty are deemed to be on bonafide military duty. Injuries sustained during this journey are attributable to military service unless caused by willful negligence or intoxication.",
        "relevance": "Foundational rule establishing that commuting between Govt Md Accn / APS Colony and Main Office on bicycle/vehicle is bonafide military duty."
    },
    {
        "source": "Army Act 1950 - Chapter VII",
        "rule_or_section": "Section 48",
        "title": "Intoxication and Sobriety Verification",
        "summary": "Mandatory investigative query in all accident/injury inquiries to ascertain whether the individual was under the influence of liquor or intoxicating substances at the time of occurrence.",
        "relevance": "Presiding Officer must record specific question: 'Were you in a state of intoxication when fell down / when accident occurred?'."
    },
    {
        "source": "Defence Services Regulations (DSR) / Regulations for the Army",
        "rule_or_section": "DSR Para 519 & 520",
        "title": "Vehicular & Conveyance Accidents and Property Damage",
        "summary": "Investigates mechanical fitness of vehicle/bicycle, road condition (e.g. rain/slippery), pre-movement maintenance, speed, reporting to ADM JCO, and financial damage.",
        "relevance": "Governs mechanical fitness questions and adverse weather conditions (slippery road due to rain)."
    },
    {
        "source": "Army Order (AO) / Regulations for the Army",
        "rule_or_section": "Medical Evaluation & Sick Leave",
        "title": "Hospital Admission, Categorization & Sick Leave",
        "summary": "Requires recording of admission at Military Hospital / Base Hospital, clinical diagnosis (e.g. plaster application), temporary low medical category (e.g. A4(T-4)), and grant of sick leave.",
        "relevance": "Findings must document evacuation to BH Delhi Cantt, treatment details, categorization downgrade to A4(T-4), and leave grant."
    }
]


# ---------------------------------------------------------------------------
# Rule-selection logic: metadata filters + keyword scoring
# ---------------------------------------------------------------------------

def select_rules(
    query: str,
    *,
    doc_type: str = None,
    topic: str = None,
    rule_numbers: List[str] = None,
    max_results: int = 5,
    catalog: List[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Select rules from the catalog using metadata filters and keyword scoring.

    Selection order:
    1. Filter by doc_type (source_document contains doc_type substring)
    2. Filter by topic (keyword match in title or summary)
    3. Filter by specific rule_numbers
    4. Keyword scoring on query terms against rule_or_section + title + summary
       — always runs to rank the filtered set, never skips.
    5. Return top-max_results; if no matches, return first max_results from catalog
    """
    sel = catalog if catalog else MILITARY_LAW_CATALOG

    # Normalise query
    q = query.lower().strip()
    q_keywords = [w for w in re.findall(r'\b\w+\b', q) if len(w) > 2]

    # Start with all catalog rules
    selected = list(sel)

    # --- Filter by document type ---
    if doc_type:
        selected = [r for r in selected if doc_type.lower() in r.get("source_document", "").lower()]

    # --- Filter by topic keyword ---
    if topic:
        tk = topic.lower()
        selected = [r for r in selected if tk in r.get("title", "").lower() or tk in r.get("summary", "").lower()]

    # --- Filter by specific rule numbers ---
    if rule_numbers:
        rn_set = {str(n).strip().lower() for n in rule_numbers}
        selected = [r for r in selected if r.get("rule_or_section", "").lower() in rn_set]

    # --- Keyword scoring (ALWAYS runs to rank the filtered set) ---
    # Even if selected is non-empty, score and re-rank by relevance
    scored = []
    for r in selected:
        text = f"{r.get('rule_or_section', '')} {r.get('title', '')} {r.get('summary', '')}".lower()
        score = sum(1 for kw in q_keywords if kw in text)
        if score > 0:
            scored.append((score, r))
        elif score == 0 and not scored:  # allow one zero-score entry as fallback
            scored.append((0, r))
    scored.sort(key=lambda x: (x[0] > 0, x[0]), reverse=True)  # score>0 first, then by score
    selected = [r for _, r in scored[:max_results]]

    # If truly nothing matched (scored empty), return first max_results from catalog
    if not scored:
        selected = sel[:max_results]

    return selected


def search_relevant_military_laws(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """
    Public API: select rules using a free-text query + optional metadata.
    Defaults to the loaded catalog (which includes the original 7 hardcoded rules).
    """
    return select_rules(query, max_results=max_results)


def get_all_military_laws() -> List[Dict[str, Any]]:
    """Return the full catalog (useful for seeding or debug)."""
    return MILITARY_LAW_CATALOG


def get_military_rulebook_summary() -> str:
    """Return a formatted string of all rules — useful for LLM prompts when no
    RAG/vector store is available (backward-compatible)."""
    lines = []
    for law in MILITARY_LAW_CATALOG:
        lines.append(f"[{law.get('rule_or_section', '')}] {law.get('title', '')}\n"
                     f"Summary: {law.get('summary', '')}\n"
                     f"Standard Mandate: {law.get('relevance', '')}\n")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Procedural checklists mandated by the rulebook (e.g. the fire-inquiry
# points). A checklist is any rule group whose rule_or_section looks like
# "<Section> (<roman numeral>)" and whose `section` is stable, such as
# "Fire Inquiry (i)" ... "Fire Inquiry (xv)". Each point becomes a MANDATORY
# item the Court must cover with witness questions.
# ---------------------------------------------------------------------------
_ROMAN_ORDER = [
    "i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x",
    "xi", "xii", "xiii", "xiv", "xv", "xvi", "xvii", "xviii", "xix", "xx",
]


def get_procedural_checklists() -> List[Dict[str, Any]]:
    """Detect every checklist-style rule group in the ingested catalog.

    Returns one dict per group:
        {"section": ..., "subject": ..., "points": [summaries in order]}
    """
    groups: Dict[str, List[tuple]] = {}
    for r in MILITARY_LAW_CATALOG:
        section = (r.get("section") or "").strip()
        ros = (r.get("rule_or_section") or "").strip()
        if not section:
            continue
        m = re.fullmatch(
            rf"{re.escape(section)}\s*\(([ivx]+)\)", ros, re.IGNORECASE
        )
        if not m:
            continue
        roman = m.group(1).lower()
        idx = _ROMAN_ORDER.index(roman) if roman in _ROMAN_ORDER else -1
        if idx < 0:
            continue
        summary = (r.get("summary") or r.get("title") or "").strip()
        if summary:
            groups.setdefault(section, []).append((idx, summary))

    checklists: List[Dict[str, Any]] = []
    for section, items in groups.items():
        items.sort(key=lambda t: t[0])
        points = [p for _, p in items]
        if len(points) >= 3:  # a real checklist has several points
            subject = re.sub(r"\s*inquiry\s*$", "", section.lower(), flags=re.I).strip()
            checklists.append({
                "section": section,
                "subject": subject or section.lower(),
                "points": points,
            })
    return checklists


def get_mandatory_checklist(case_text: str) -> List[str]:
    """If the case matches a topic that has an ingested procedural checklist,
    return the ordered checklist points. Empty list when nothing matches."""
    if not case_text:
        return []
    low = " ".join(str(case_text).lower().split())
    for cl in get_procedural_checklists():
        subject = cl.get("subject", "")
        if subject and subject in low:
            return cl["points"]
    return []