import os
import re
import json
from pathlib import Path
from datetime import datetime
from pypdf import PdfReader

# --- Configuration ---
PDFS_DIR = Path(r"C:\Users\Idex\Documents\legal final\legal\legal\files")
OUTPUT_PATH = Path(r"C:\Users\Idex\Documents\legal final\legal\legal\backend\data\military_rules_structured.json")

# --- Helper functions ---
def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract full text from a PDF."""
    reader = PdfReader(str(pdf_path))
    full_text = ""
    for page in reader.pages:
        try:
            full_text += page.extract_text() + "\n"
        except Exception:
            continue
    return full_text


def parse_rules_from_text(text: str, pdf_name: str, existing_numbers: set) -> list:
    """Parse rule entries from extracted PDF text using heuristic patterns."""
    rules = []
    lines = text.split("\n")

    rule_patterns = [
        (r"Army Rule\s+(\d+)", "Army Rule"),
        (r"DSR\s+Para\s+(\d+)[A-D]?", "DSR Para"),
        (r"Section\s+(\d+)", "Section"),
        (r"Rule\s+(\d+)", "Rule"),
        (r"MML\s+vol\s+(\d+)(?:\([^)]*\))?", "MML"),
    ]

    current_rule_num = None
    current_rule_type = None
    current_line_idx = None

    def flush_rule():
        """Save the current rule if it has a valid number and isn't a duplicate."""
        nonlocal current_rule_num, current_rule_type, current_line_idx
        if current_rule_num and current_rule_num.lower() not in existing_numbers:
            # Collect surrounding context for summary/relevance
            ctx_start = max(0, current_line_idx - 3)
            ctx_end = min(len(lines), current_line_idx + 5)
            summary_parts = []
            for j in range(ctx_start, ctx_end):
                if j == current_line_idx:
                    continue
                lj = lines[j].strip()
                if lj and len(lj) > 10:
                    summary_parts.append(lj)
            # Deduplicate
            seen = set()
            unique_summary = []
            for s in summary_parts:
                key = s[:80].lower()
                if key not in seen:
                    seen.add(key)
                    unique_summary.append(s)
            relevance_text = " ".join(unique_summary[:3]) if unique_summary else ""

            rule_entry = {
                "rule_number": current_rule_num,
                "rule_or_section": f"{current_rule_type} {current_rule_num}",
                "title": f"{current_rule_type} {current_rule_num}: Extracted from {pdf_name}",
                "source_document": pdf_name,
                "section": current_rule_type,
                "topic": current_rule_type.lower(),
                "summary": relevance_text[:500] if relevance_text else "Extracted from " + pdf_name,
                "relevance": relevance_text[:300] if relevance_text else "Procedural rule for Court of Inquiry",
                "page_start": None,
                "page_end": None,
                "extract_method": "pdf_text",
                "keywords": [current_rule_type.lower(), current_rule_num.lower()],
            }
            rules.append(rule_entry)

    for i, line in enumerate(lines):
        line_stripped = line.strip()
        if not line_stripped:
            continue

        # Check if this line starts a new rule
        rule_match = None
        for pattern, rtype in rule_patterns:
            m = re.search(pattern, line_stripped, re.IGNORECASE)
            if m:
                rule_match = {"type": rtype, "number": m.group(1), "line": line_stripped}
                break

        if rule_match:
            # Save previous rule
            flush_rule()
            # Start new rule
            current_rule_type = rule_match["type"]
            current_rule_num = rule_match["number"]
            current_line_idx = i
        elif current_rule_num:
            # Continuation line — ignore for summary (kept simple)
            pass

    # Flush the last rule
    flush_rule()

    return rules


# --- Main Execution ---
def main():
    # Load existing catalog if present
    existing_catalog = []
    existing_numbers = set()
    if OUTPUT_PATH.exists():
        try:
            with open(OUTPUT_PATH, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
                existing_catalog = existing_data.get("rules", [])
                for r in existing_catalog:
                    num = r.get("rule_number") or r.get("rule_or_section", "").split()[-1] if r.get("rule_or_section") else ""
                    if num:
                        existing_numbers.add(num.lower())
        except Exception as e:
            print(f"Warning: Could not load existing catalog: {e}")

    # Extract rules from all 6 PDFs
    all_new_rules = []
    pdf_files = sorted(PDFS_DIR.glob("*.pdf"))
    print(f"Found {len(pdf_files)} PDFs in {PDFS_DIR}")

    for pdf_path in pdf_files:
        pdf_name = pdf_path.name
        print(f"  Processing: {pdf_name} ({pdf_path.stat().st_size // 1024} KB)")
        try:
            text = extract_text_from_pdf(pdf_path)
            rules = parse_rules_from_text(text, pdf_name, existing_numbers)
            print(f"    Extracted {len(rules)} rules")
            all_new_rules.extend(rules)
        except Exception as e:
            print(f"    ERROR: {e}")

    # Merge with existing catalog
    all_rules = existing_catalog + all_new_rules

    # Deduplicate by rule_number
    seen_numbers = set()
    deduped_rules = []
    for r in all_rules:
        num = r.get("rule_number", "").lower()
        if num and num not in seen_numbers:
            seen_numbers.add(num)
            deduped_rules.append(r)
        elif not num:
            deduped_rules.append(r)

    # Build final catalog WITH rules
    catalog_data = {
        "total_rules": len(deduped_rules),
        "sources": [pdf.name for pdf in PDFS_DIR.glob("*.pdf")],
        "generated_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "extraction_tool": "PyPDF2 + heuristic parsing (rule number + context detection)",
        "notes": "Rules extracted from 6 reference PDFs (DSR vol 1-2, MML vol 1-3). Heuristic parsing; page numbers may be approximate. "
        "Verify against original documents before relying on legal applicability. "
        "Each rule includes source_document, section, topic, summary, and relevance.",
        "rules": deduped_rules
    }

    # Ensure output directory exists
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(catalog_data, f, indent=2, ensure_ascii=False)

    print(f"\nCatalog written to {OUTPUT_PATH}")
    print(f"Total rules in catalog: {catalog_data['total_rules']}")
    print(f"New rules from PDFs: {len(all_new_rules)}")
    print(f"Duplicates avoided: {len(all_rules) - len(deduped_rules)}")


if __name__ == "__main__":
    main()