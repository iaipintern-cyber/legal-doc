import json
import os
import re
import shutil
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from config import BASE_DIR, WORKSPACE_DIR

CASE_STORE_FILE = BASE_DIR / "uploads" / "active_case_state.json"
CASES_DIR = BASE_DIR / "uploads" / "cases"
CASES_DIR.mkdir(parents=True, exist_ok=True)

def sanitize_case_id(raw_id: str) -> str:
    """Sanitizes case ID for filesystem safety on Windows/Linux."""
    if not raw_id:
        return f"COI-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    # Replace slashes, colons, and illegal characters with dashes/underscores
    cleaned = re.sub(r'[<>:"/\\|?*]+', '-', raw_id)
    cleaned = re.sub(r'[\s_]+', '_', cleaned).strip('.-_')
    return cleaned[:45] if cleaned else f"COI-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

class CaseService:
    def __init__(self):
        self.state = self._load_or_init_state()
        self._archive_case()

    def _default_state(self) -> Dict[str, Any]:
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        return {
            "case_id": f"COI-{ts}",
            "order_reference": "",
            "created_at": now_str,
            "updated_at": now_str,
            "status": "PENDING",
            "status_label": "Pending",
            "convening_order": {
                "file_name": "",
                "raw_text": "",
                "parsed": None,
                "summary": ""
            },
            "supporting_docs": [],
            "case_analysis": None,
            "witnesses": [],
            "presiding_officer_review": {
                "verified": False,
                "reviewed_by": "Admin",
                "service_no": "",
                "checklist": {
                    "convening_order_authenticated": False,
                    "exhibits_catalogued": False,
                    "army_rule_180_complied": False,
                    "witness_testimonies_recorded_under_oath": False,
                    "technical_inspection_attached": False,
                    "damage_assessment_verified": False
                },
                "comments": "",
                "forwarded_to_draft": False
            },
            "coi_draft": None,
            "drafted_at": None
        }

    def _load_or_init_state(self) -> Dict[str, Any]:
        if CASE_STORE_FILE.exists():
            try:
                with open(CASE_STORE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Ensure case_id is sanitized
                    data["case_id"] = sanitize_case_id(data.get("case_id"))
                    return data
            except Exception:
                pass
        return self._default_state()

    def _calculate_status(self):
        """Calculates accurate status ('DRAFTED' or 'PENDING' with sub-stage)."""
        if self.state.get("coi_draft"):
            self.state["status"] = "DRAFTED"
            self.state["status_label"] = "Drafted"
            return

        # Check sub-stages for Pending
        po = self.state.get("presiding_officer_review") or {}
        if po.get("verified") or po.get("forwarded_to_draft"):
            self.state["status"] = "PENDING"
            self.state["status_label"] = "Pending (PO Reviewed)"
            return

        witnesses = self.state.get("witnesses") or []
        has_stmts = any(bool(w.get("statement")) for w in witnesses)
        if has_stmts:
            self.state["status"] = "PENDING"
            self.state["status_label"] = "Pending (Witnesses Examined)"
            return

        if self.state.get("case_analysis"):
            self.state["status"] = "PENDING"
            self.state["status_label"] = "Pending (Evidence Correlated)"
            return

        docs = self.state.get("supporting_docs") or []
        if docs:
            self.state["status"] = "PENDING"
            self.state["status_label"] = "Pending (Exhibits Attached)"
            return

        conv = self.state.get("convening_order") or {}
        if conv.get("parsed") or conv.get("file_name"):
            self.state["status"] = "PENDING"
            self.state["status_label"] = "Pending (Order Uploaded)"
            return

        self.state["status"] = "PENDING"
        self.state["status_label"] = "Pending"

    def save_state(self):
        """Saves active case state and continuously mirrors it in the archive."""
        CASE_STORE_FILE.parent.mkdir(parents=True, exist_ok=True)
        self.state["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        self._calculate_status()

        safe_id = sanitize_case_id(self.state.get("case_id"))
        self.state["case_id"] = safe_id

        with open(CASE_STORE_FILE, "w", encoding="utf-8") as f:
            json.dump(self.state, f, indent=2)

        self._archive_case()

    def _archive_case(self):
        """Archives current case to cases/ directory using sanitized filename."""
        safe_id = sanitize_case_id(self.state.get("case_id"))
        archive_file = CASES_DIR / f"{safe_id}.json"
        try:
            with open(archive_file, "w", encoding="utf-8") as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            print(f"Error archiving case {safe_id}: {e}")

    def get_state(self) -> Dict[str, Any]:
        return self.state

    def start_new_case(self) -> Dict[str, Any]:
        """
        Safely archives current case if it has content, 
        and initializes a completely clean, empty case session.
        """
        if self.state.get("convening_order", {}).get("file_name") or self.state.get("coi_draft") or self.state.get("supporting_docs"):
            self._archive_case()

        self.state = self._default_state()
        self.save_state()
        return self.state

    def reset_state(self) -> Dict[str, Any]:
        return self.start_new_case()

    def list_all_cases(self) -> List[Dict[str, Any]]:
        """Returns metadata list of all monitored cases with accurate DRAFTED / PENDING status."""
        cases_map = {}

        # 1. Read all files in CASES_DIR
        if CASES_DIR.exists():
            for p in CASES_DIR.glob("*.json"):
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        c = json.load(f)
                        cid = c.get("case_id") or p.stem
                        conv = c.get("convening_order", {})
                        parsed = conv.get("parsed") or {}

                        # Determine status
                        status = c.get("status", "PENDING")
                        status_label = c.get("status_label", "Pending")
                        if c.get("coi_draft"):
                            status = "DRAFTED"
                            status_label = "Drafted"

                        cases_map[cid] = {
                            "case_id": cid,
                            "order_reference": c.get("order_reference") or parsed.get("order_number", ""),
                            "created_at": c.get("created_at", "Recent"),
                            "updated_at": c.get("updated_at", c.get("created_at", "Recent")),
                            "status": status,
                            "status_label": status_label,
                            "subject": parsed.get("subject_matter") or conv.get("summary") or "New Inquiry (Pending Order)",
                            "authority": parsed.get("convening_authority") or "Pending Upload",
                            "file_name": conv.get("file_name", ""),
                            "docs_count": len(c.get("supporting_docs", [])),
                            "witnesses_count": len(c.get("witnesses", [])),
                            "has_draft": bool(c.get("coi_draft")),
                            "is_active": (cid == self.state.get("case_id"))
                        }
                except Exception:
                    continue

        # 2. Ensure current active case is included with latest status
        active_id = self.state.get("case_id")
        if active_id:
            active_conv = self.state.get("convening_order", {})
            active_parsed = active_conv.get("parsed") or {}
            cases_map[active_id] = {
                "case_id": active_id,
                "order_reference": self.state.get("order_reference") or active_parsed.get("order_number", ""),
                "created_at": self.state.get("created_at", "Recent"),
                "updated_at": self.state.get("updated_at", "Recent"),
                "status": self.state.get("status", "PENDING"),
                "status_label": self.state.get("status_label", "Pending"),
                "subject": active_parsed.get("subject_matter") or active_conv.get("summary") or "New Inquiry (Pending Order)",
                "authority": active_parsed.get("convening_authority") or "Pending Upload",
                "file_name": active_conv.get("file_name", ""),
                "docs_count": len(self.state.get("supporting_docs", [])),
                "witnesses_count": len(self.state.get("witnesses", [])),
                "has_draft": bool(self.state.get("coi_draft")),
                "is_active": True
            }

        cases = list(cases_map.values())
        # Sort with most recent updated/created first
        cases.sort(key=lambda x: x.get("updated_at", x.get("created_at", "")), reverse=True)
        return cases

    def load_case_by_id(self, case_id: str) -> Dict[str, Any]:
        safe_id = sanitize_case_id(case_id)
        target_file = CASES_DIR / f"{safe_id}.json"
        if not target_file.exists():
            raise FileNotFoundError(f"Case {case_id} not found")
        with open(target_file, "r", encoding="utf-8") as f:
            self.state = json.load(f)
        self.state["case_id"] = safe_id
        self.save_state()
        return self.state

    def delete_case_by_id(self, case_id: str) -> bool:
        safe_id = sanitize_case_id(case_id)
        target_file = CASES_DIR / f"{safe_id}.json"
        if target_file.exists():
            target_file.unlink()
        if self.state.get("case_id") == safe_id:
            self.start_new_case()
        return True

case_service = CaseService()
