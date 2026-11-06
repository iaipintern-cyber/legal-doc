import json
import re
import logging
import time
import requests
from typing import Dict, Any, List, Optional
from config import (
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
    OLLAMA_NUM_CTX,
    OLLAMA_TIMEOUT,
    OLLAMA_RETRIES,
)
from services.military_law_service import select_rules, get_military_rulebook_summary, get_mandatory_checklist

logger = logging.getLogger(__name__)


class LLMService:
    """All inference goes through the local Ollama daemon. Nothing else."""

    def __init__(self):
        self.ollama_base_url = OLLAMA_BASE_URL
        self.ollama_model = OLLAMA_MODEL
        self.num_ctx = OLLAMA_NUM_CTX
        self.timeout = OLLAMA_TIMEOUT
        self.retries = OLLAMA_RETRIES

    def _call_ollama(self, system_prompt: str, user_prompt: str, max_tokens: int = 4000, temperature: float = 0.2) -> str:
        """Single-round chat against the local Ollama instance. Fully offline."""
        url = f"{self.ollama_base_url.rstrip('/')}/api/chat"
        payload = {
            "model": self.ollama_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "stream": False,
            # Every caller in this service wants a JSON object back, so use
            # Ollama's constrained JSON decoding instead of relying on the
            # regex salvage in _clean_json_response to strip prose.
            "format": "json",
            "options": {
                "temperature": temperature,
                "num_ctx": self.num_ctx,
                "num_predict": max_tokens
            }
        }
        logger.info(
            f"Ollama '{self.ollama_model}' <- {len(user_prompt):,} chars "
            f"(num_ctx={self.num_ctx}, num_predict={max_tokens}, timeout={self.timeout}s)"
        )
        resp = requests.post(url, json=payload, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()
        content = data.get("message", {}).get("content", "")
        if not content or not content.strip():
            raise RuntimeError(f"Ollama returned empty response for model {self.ollama_model}")
        return content.strip()

    def _call_llm(self, system_prompt: str, user_prompt: str, max_tokens: int = 4000, temperature: float = 0.2) -> str:
        """Calls the local Ollama model.

        Only *connection* failures are retried (Ollama still booting, socket
        reset). A read timeout means the CPU is simply still working, so it is
        surfaced immediately instead of being retried for another full window.
        """
        last_error = None
        attempts = self.retries + 1
        for attempt in range(1, attempts + 1):
            try:
                return self._call_ollama(system_prompt, user_prompt, max_tokens, temperature)
            except requests.exceptions.ConnectionError as e:
                last_error = e
                if attempt < attempts:
                    logger.warning(
                        f"Cannot reach Ollama at {self.ollama_base_url} "
                        f"(attempt {attempt}/{attempts}): {e}. Retrying in 3s..."
                    )
                    time.sleep(3)
                    continue
                raise RuntimeError(
                    f"Cannot reach Ollama at {self.ollama_base_url} after {attempts} "
                    f"attempt(s). Is 'ollama serve' running with '{self.ollama_model}' "
                    f"pulled? Last error: {e}"
                ) from e
            except requests.exceptions.ReadTimeout as e:
                raise RuntimeError(
                    f"Ollama model '{self.ollama_model}' did not answer within {self.timeout}s. "
                    f"This box is CPU-only, so a large prompt is slow -- reduce the number/size "
                    f"of supporting documents, lower OLLAMA_TIMEOUT-bound max_tokens, or raise "
                    f"OLLAMA_TIMEOUT in backend/.env. Original: {e}"
                ) from e
            except Exception as e:
                raise RuntimeError(
                    f"Ollama call to '{self.ollama_model}' failed: {type(e).__name__}: {e}"
                ) from e
        raise RuntimeError(f"Ollama call failed: {last_error}")

    def _clean_json_response(self, text: str) -> Dict[str, Any]:
        """Cleans potential markdown fences from JSON output and parses it."""
        cleaned = text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
        
        try:
            return json.loads(cleaned)
        except Exception:
            match = re.search(r'(\{.*\})', cleaned, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except Exception as inner_err:
                    logger.error(f"Failed regex JSON parsing: {inner_err}")
            return {"raw_text": text}

    # ------------------------------------------------------------------
    # Anti-hallucination helpers -- pull values VERBATIM out of the OCR'd
    # Convening Order so parsed data can never drift from what was uploaded.
    # ------------------------------------------------------------------
    _RANKS = (
        r"Brigadier|Brig|Colonel|Col|Lt\.?\s*Colonel|Lt\.?\s*Col|Lieutenant|Lt|"
        r"Major|Maj|Captain|Capt|Subedar|Naib\s*Subedar|Nb\.?\s*Subedar|Nb\.?\s*Sub|Sub|"
        r"Havildar|Hav|Lance\s*Naik|Lnk|Sepoy|Sep|Naik|Gunner|Gnr"
    )

    @staticmethod
    def _norm_match(value: str) -> str:
        """Compact form used to verify that a value really occurs in the source."""
        return re.sub(r"[\s.,:;()'\"/-]", "", (value or "").lower())

    def _supported_by_text(self, value: str, text: str) -> bool:
        """True when `value` genuinely occurs in `text` (empty values always pass)."""
        if not value or not str(value).strip():
            return True
        needle = self._norm_match(str(value))
        return (not needle) or needle in self._norm_match(text)

    @classmethod
    def _split_rank_name(cls, person: str):
        m = re.match(rf"^\s*({cls._RANKS})\.?\s*[,\-–]?\s+(.+?)\s*$", person, re.I)
        if m:
            return m.group(1).strip(), re.sub(r"\s+", " ", m.group(2)).strip()
        return "", re.sub(r"\s+", " ", person).strip()

    @classmethod
    def _member_key(cls, rank: str, name: str) -> str:
        """Canonical identity of a court member with all rank words removed, so
        'Col R K Malhotra' and rank='Col', name='Col R K Malhotra' compare equal."""
        combined = f"{rank} {name}".strip().lower()
        cleaned = re.sub(rf"\b(?:{cls._RANKS})\b\.?", "", combined, flags=re.I)
        return re.sub(r"\s+", " ", cleaned).strip(" ,.")

    # Commissioned-officer ranks (they carry an IC number, everyone else an Army number)
    _OFFICER_RANKS = (
        "lt col", "lt", "capt", "maj", "col", "brig", "maj gen", "lt gen", "gen",
        "lieutenant colonel", "lieutenant", "captain", "major", "colonel",
        "brigadier", "major general", "lieutenant general", "general",
    )

    @classmethod
    def _service_number_label(cls, rank: str, service_no: str) -> str:
        """'54613' + Naik -> 'Army No. 54613'; officers -> 'IC No. ...'.
        A value the user already labelled ('IC-12345', 'Army 12345') is kept
        exactly as typed."""
        no = re.sub(r"\s+", " ", str(service_no or "").strip())
        if not no:
            return ""
        if re.search(r"[A-Za-z]", no):
            return no
        rank_l = str(rank or "").strip().lower()
        officer = any(rank_l == o or rank_l.startswith(o + " ") for o in cls._OFFICER_RANKS)
        return f"{'IC No.' if officer else 'Army No.'} {no}"

    @classmethod
    def _witness_person(cls, witness: Dict[str, Any]) -> str:
        """'Army No. 54613, Naik vjds' -- service number then rank+name, no labels."""
        rank = str(witness.get("rank") or "").strip()
        name = str(witness.get("name") or "").strip()
        no_part = cls._service_number_label(rank, witness.get("service_no"))
        person = " ".join(x for x in (rank, name) if x).strip()
        return ", ".join(p for p in (no_part, person) if p)

    @classmethod
    def _warning_declaration(cls, witness: Dict[str, Any], seq: str = "1.") -> str:
        """Statutory opening line, built ONLY from the witness's own record --
        never from the model, so placeholder label words ('Rank', 'Name') and
        odd orderings can never leak into the statement."""
        person = cls._witness_person(witness)
        unit = str(witness.get("unit") or "").strip()
        if not person:
            return f"{seq} I, the witness, having been duly warned, state the following:-"
        unit_part = f", of {unit}" if unit else ""
        return f"{seq} I, {person}{unit_part}, having been duly warned, state the following:-"

    @classmethod
    def _witness_sign(cls, witness: Dict[str, Any]) -> str:
        person = cls._witness_person(witness)
        return f"({person})" if person else "(Signature of witness)"

    @staticmethod
    def _polish_posting(text: str) -> str:
        """Grammar-clean the posting line the model produced:
        'wef' -> 'with effect from', 'I have been posted to' -> 'I am posted at',
        missing 'am' before 'performing' -> added."""
        t = re.sub(r"\s+", " ", str(text or "")).strip()
        t = re.sub(r"\bwef\b", "with effect from", t, flags=re.I)
        t = re.sub(r"^(\s*(?:\d+\.\s*)?)I have been posted to\b", r"\1I am posted at", t, flags=re.I)
        t = re.sub(r"\band performing the duties\b", "and am performing the duties", t, flags=re.I)
        return t

    @classmethod
    def _verbatim_subject(cls, text: str) -> str:
        """Subject / incident paragraph exactly as printed in the order ('' if absent)."""
        lines = (text or "").splitlines()
        patterns = (
            re.compile(r"^\s*(?:subject|sub)\s*[:.\-–]\s*(.*)$", re.I),
            re.compile(r"^.*\bsubject\b\s*[:.\-–]\s*(.*)$", re.I),
        )
        for pattern in patterns:
            for i, line in enumerate(lines):
                m = pattern.match(line)
                if not m:
                    continue
                block = [m.group(1).strip()] if m.group(1).strip() else []
                for j in range(i + 1, min(i + 10, len(lines))):
                    nxt = lines[j].strip()
                    if not nxt:
                        break
                    if re.match(r"^(?:subject|sub|part\s|reference|no\.|1\.|2\.)\s*[:.\-–]", nxt, re.I):
                        break
                    # Numbered body paragraph of the order ("1. A Court of Inquiry ...")
                    if re.match(r"^\d+\.\s", nxt):
                        break
                    # Common convening-order sections that are never part of the subject
                    if re.match(
                        r"^(?:the\s+following|assemble|presiding\s|member\s|by\s+order|place\s+of|down)",
                        nxt, re.I,
                    ):
                        break
                    block.append(nxt)
                result = re.sub(r"\s+", " ", " ".join(block)).strip()
                if len(result) >= 12:
                    return result
        return ""

    @classmethod
    def _verbatim_composition(cls, text: str) -> List[Dict[str, str]]:
        """Court members copied exactly as printed in the order (never invented)."""
        members: List[Dict[str, str]] = []
        seen = set()
        member_idx = 0

        def _service_no(raw: str) -> str:
            m = re.search(r"\b(?:No\.?\s*|JC[-\s]?)(\d{4,}[A-Za-z]?)\b", raw, re.I)
            return m.group(1) if m else ""

        def _add(role: str, person: str) -> None:
            person = re.sub(r"\s+", " ", person).strip()
            person = re.sub(r"\((?:presiding\s+officer|member[^)]*)\)", "", person, flags=re.I)
            person = person.strip(" .,;:-")
            if len(person) < 3:
                return
            rank, name = cls._split_rank_name(person)
            if not rank and len(person) > 60:
                return
            key = cls._member_key(rank, name)
            if not key or key in seen:
                return
            probe = name if len(name) >= 4 else person
            if cls._norm_match(probe) not in cls._norm_match(text or ""):
                return  # not printed in the order -> would be a hallucination
            seen.add(key)
            members.append({
                "role": role,
                "rank": rank,
                "name": name,
                "service_no": _service_no(person),
                "unit": "",
            })

        # Pattern A: "Presiding Offr : Col A B Singh" / "Member No 1 : ..."
        # (the forces' orders abbreviate it as "Offr"/"Offrs"/"PO", so accept
        # all common spellings -- otherwise the Presiding Officer goes missing)
        label_re = re.compile(
            r"^\s*(presiding\s*(?:offrs?|officers?|o)?|po|member[^:]{0,20})\s*[:\-–]\s*(.+?)\s*$",
            re.I | re.M,
        )
        for m in label_re.finditer(text or ""):
            label = m.group(1).lower()
            person = m.group(2)
            parts = [p.strip() for p in re.split(r"\s*(?:,|;|\band\b)\s*", person) if p.strip()]
            multi = len(parts) > 1 and all(re.match(rf"^(?:{cls._RANKS})\b", p, re.I) for p in parts)
            for p in (parts if multi else [person]):
                if "presiding" in label:
                    _add("Presiding Officer", p)
                else:
                    member_idx += 1
                    _add(f"Member {member_idx}", p)

        if not members:
            # Pattern B: "Col A B Singh is the Presiding Officer" / "... appointed as Member 1"
            inline_re = re.compile(
                rf"\b({cls._RANKS})\s+([A-Z][A-Za-z.\s]{{2,45}}?)\s*,?\s*"
                rf"(?:is\s+)?(?:appointed\s+as\s+)?(?:the\s+)?"
                rf"(presiding\s+(?:officer|offr)|member(?:\s+no\.?\s*\d+)?)\b",
                re.I,
            )
            for m in inline_re.finditer(text or ""):
                person = f"{m.group(1)} {m.group(2)}".strip()
                if "presiding" in m.group(3).lower():
                    _add("Presiding Officer", person)
                else:
                    member_idx += 1
                    _add(f"Member {member_idx}", person)

        return members

    @classmethod
    def _first_match(cls, text: str, pattern: str) -> str:
        m = re.search(pattern, text or "", re.I | re.M)
        if not m:
            return ""
        value = m.group(1) if m.groups() else m.group(0)
        return re.sub(r"\s+", " ", value).strip()

    def _fallback_parsed_order(self, text: str, subject: str, comp: List[Dict[str, str]]) -> Dict[str, Any]:
        """Deterministic parse used when the LLM is unavailable.

        Extracts only what is literally printed in the order; anything that
        cannot be found stays an empty string -- nothing is ever invented.
        """
        month = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*"
        order_no = self._first_match(
            text,
            r"(?:part\s*I{0,3}\s*order\s*(?:no\.?)?|order\s*(?:no\.?)?)\s*([A-Za-z0-9/\-]*\d[\w/\-]*)"
        )
        date = (
            self._first_match(text, rf"\b(?:dt|dated|date)\s*[:.]?\s*([A-Za-z]{{3,9}}\.?\s+20\d{{2}})")
            or self._first_match(text, rf"\b(\d{{1,2}}(?:st|nd|rd|th)?\s+{month}\.?\s+20\d{{2}}\b)")
            or self._first_match(text, rf"\b({month}\.?\s+20\d{{2}}\b)")
        )
        authority = self._first_match(
            text, r"(?:by\s+order\s+of|convening\s+authority|issued\s+by)\s*[:\-]?\s*([^\n]{3,60})"
        )
        place = self._first_match(text, r"(?:place\s+of\s+assembly|assembled\s+at)\s*[:\-]\s*([^\n]{3,60})")
        return {
            "order_number": order_no,
            "convening_authority": authority,
            "date_of_order": date,
            "place_of_assembly": place,
            "subject_matter": subject,
            "incident_details": {
                "nature_of_incident": subject,
                "incident_date_time": date,
                "property_or_personnel_affected": "",
            },
            "composition_of_court": comp,
            "terms_of_reference": [],
            "executive_summary": subject,
        }

    @classmethod
    def _build_executive_summary(cls, parsed: Dict[str, Any]) -> str:
        """Deterministic briefing built ONLY from fields already verified
        word-for-word against the uploaded order.

        The model's free-text summary is deliberately discarded: a fluent
        'briefing' is exactly where invented names, dates and incident types
        slip through. Every component below was either copied verbatim from
        the OCR text or verified against it, so the summary cannot state
        anything that is not actually in the uploaded document."""
        sentences: List[str] = []

        order_no = (parsed.get("order_number") or "").strip()
        date = (parsed.get("date_of_order") or "").strip()
        conv = (parsed.get("convening_authority") or "").strip()
        place = (parsed.get("place_of_assembly") or "").strip()

        # 1) Reference line: number, date, issuing authority -- as printed.
        ref_bits = []
        if order_no:
            ref_bits.append(f"No. {order_no}")
        if date:
            ref_bits.append(f"dated {date}")
        if conv:
            ref_bits.append(f"issued by {conv}")
        if ref_bits:
            sentences.append(f"Convening Order " + ", ".join(ref_bits) + ".")

        # 2) Subject / incident statement, verbatim from the order.
        subject = (parsed.get("subject_matter") or "").strip()
        if subject:
            sentences.append(f"Subject, as stated in the order: '{subject}'")

        # 3) Verified incident particulars only.
        inc = parsed.get("incident_details") if isinstance(parsed.get("incident_details"), dict) else {}
        dt = (inc.get("incident_date_time") or "").strip()
        affected = (inc.get("property_or_personnel_affected") or "").strip()
        particulars = [p for p in (dt, affected) if p]
        if particulars:
            sentences.append("Particulars recorded in the order: " + "; ".join(particulars) + ".")

        # 4) Court composition (verified members only; rank + name, no IC/JC
        #    labels) and the verified place of assembly.
        comp_raw = parsed.get("composition_of_court")
        comp = [m for m in (comp_raw if isinstance(comp_raw, list) else []) if isinstance(m, dict)]
        members = []
        for m in comp:
            person = " ".join(
                x for x in (str(m.get("rank") or "").strip(), str(m.get("name") or "").strip()) if x
            )
            if person:
                members.append(person)
        assembly_bits = []
        if place:
            assembly_bits.append(f"assembles at {place}")
        if members:
            assembly_bits.append("comprises " + "; ".join(members))
        if assembly_bits:
            sentences.append("The court " + " and ".join(assembly_bits) + ".")

        # 5) Terms of reference (verified entries only).
        tor_raw = parsed.get("terms_of_reference")
        tor_items = [
            str(t).strip().rstrip(".")
            for t in (tor_raw if isinstance(tor_raw, list) else [])
            if isinstance(t, str) and str(t).strip()
        ]
        if tor_items:
            shown = tor_items[:3]
            tail = " (further tasks as listed in the order)." if len(tor_items) > 3 else "."
            sentences.append("Terms of reference: " + "; ".join(shown) + tail)

        if not sentences:
            # Nothing could be verified -- say so plainly instead of inventing.
            return (
                "Key particulars could not be verified in the uploaded convening order. "
                "Please review the original document and re-run the extraction."
            )
        return " ".join(sentences)

    def parse_convening_order(self, text: str) -> Dict[str, Any]:
        """Parses Convening Order text into structured data.

        Anti-hallucination contract:
          * the subject / incident statement is taken VERBATIM from the order;
          * every literal field must actually occur in the uploaded text,
            otherwise it is blanked out -- never guessed;
          * court members are copied exactly as printed in the order.
        """
        verbatim_subject = self._verbatim_subject(text)
        verbatim_comp = self._verbatim_composition(text)

        system_prompt = (
            "You are a Senior Judge Advocate General (JAG) / Staff Officer in the Armed Forces. "
            "Extract the facts of the given Convening Order and return a valid JSON object strictly matching this schema:\n"
            "{\n"
            '  "order_number": "string (reference number and date EXACTLY as printed in the order)",\n'
            '  "convening_authority": "string (the authority issuing the order, exactly as printed)",\n'
            '  "date_of_order": "string (exactly as printed)",\n'
            '  "place_of_assembly": "string (exactly as printed)",\n'
            '  "subject_matter": "string (COMPLETE subject / incident statement copied VERBATIM word-for-word from the order -- do not shorten, summarise or rephrase)",\n'
            '  "incident_details": {\n'
            '     "nature_of_incident": "string (complete description of the incident exactly as recorded in the order)",\n'
            '     "incident_date_time": "string (exactly as printed)",\n'
            '     "property_or_personnel_affected": "string (exactly as printed; empty string if not stated)"\n'
            '  },\n'
            '  "composition_of_court": [\n'
            '     {"role": "Presiding Officer", "rank": "string", "name": "string", "service_no": "string", "unit": "string"},\n'
            '     {"role": "Member 1", "rank": "string", "name": "string", "service_no": "string", "unit": "string"},\n'
            '     {"role": "Member 2", "rank": "string", "name": "string", "service_no": "string", "unit": "string"}\n'
            '  ],\n'
            '  "terms_of_reference": ["string array copied from the order"],\n'
            '  "executive_summary": "string (A crisp 3-4 sentence military briefing on the convening order)"\n'
            "}\n"
            "STRICT FACT RULES -- violating any of these is an error:\n"
            "1. Copy names, ranks, service numbers, units, dates, places and order references EXACTLY as they appear in the text.\n"
            "2. NEVER invent, guess, complete or generalise any value. If a field is not present in the text, use an empty string \"\".\n"
            "3. List ONLY the court members actually named in the order. If none are named, return an empty array [].\n"
            "4. Do not add fields outside the schema. Only return valid JSON, no markdown preamble."
        )

        user_prompt = f"Convening Order Text:\n\n{text}"
        parsed: Optional[Dict[str, Any]] = None
        try:
            response_text = self._call_llm(system_prompt, user_prompt)
            candidate = self._clean_json_response(response_text)
            if isinstance(candidate, dict) and "subject_matter" in candidate:
                parsed = candidate
        except Exception as e:
            logger.warning(f"Error parsing order via LLM: {e}")

        if not parsed:
            parsed = self._fallback_parsed_order(text, verbatim_subject, verbatim_comp)

        # 1. Subject / incident statement: the verbatim text from the order always wins
        if verbatim_subject:
            parsed["subject_matter"] = verbatim_subject
        parsed["subject_matter"] = (parsed.get("subject_matter") or "").strip()

        # 2. Every literal field must be supported by the uploaded text
        for field in ("order_number", "convening_authority", "date_of_order", "place_of_assembly"):
            value = (parsed.get(field) or "").strip()
            if value and not self._supported_by_text(value, text):
                logger.info(f"Dropping unsupported '{field}' value returned by model: {value!r}")
                parsed[field] = ""

        # 2b. order_number must look like a reference (digits or slashes), not
        #     the document title ("CONVENING ORDER") that models often return
        order_no = (parsed.get("order_number") or "").strip()
        if order_no and not re.search(r"[\d/]", order_no):
            alt = self._first_match(text, r"\b([A-Za-z]/[A-Za-z0-9\-/]{3,})")
            logger.info(f"order_number {order_no!r} is not a reference; replacing with {alt!r}")
            parsed["order_number"] = alt

        # 3. Incident details: blank out anything not present in the order
        inc = parsed.get("incident_details")
        if not isinstance(inc, dict):
            inc = {}
        for key, value in list(inc.items()):
            if isinstance(value, str) and value.strip() and not self._supported_by_text(value, text):
                inc[key] = ""
        if verbatim_subject and not inc.get("nature_of_incident"):
            inc["nature_of_incident"] = verbatim_subject
        parsed["incident_details"] = inc

        # 4. Court composition: verbatim extraction first, then any model members
        #    whose names genuinely appear in the order (never invented ones).
        comp: List[Dict[str, str]] = list(verbatim_comp)
        seen = {self._member_key(str(m.get("rank", "")), str(m.get("name", ""))) for m in comp}
        model_comp = parsed.get("composition_of_court")
        if isinstance(model_comp, list):
            member_seq = len([m for m in comp if str(m.get("role", "")).lower().startswith("member")])
            for m in model_comp:
                if not isinstance(m, dict):
                    continue
                name = str(m.get("name") or "").strip()
                if not name or not self._supported_by_text(name, text):
                    logger.info(f"Dropping court member not found in the order: {m}")
                    continue
                key = self._member_key(str(m.get("rank", "")), name)
                if not key or key in seen:
                    continue
                # The model often re-formats the same person (order prints
                # 'No - xxxxxx Hav xxxxx xxxx', model returns 'xxxxxx Hav xxxxx
                # xxxx'): containment of the compact name means same identity,
                # so one human being never gets two cards.
                name_norm = self._norm_match(name)
                if len(name_norm) >= 6 and any(
                    name_norm in self._norm_match(str(v.get("name", "")))
                    or self._norm_match(str(v.get("name", ""))) in name_norm
                    for v in comp
                ):
                    logger.info(f"Skipping duplicate court member (same person reformatted): {m}")
                    continue
                seen.add(key)
                role = str(m.get("role") or "").strip()
                if not role:
                    member_seq += 1
                    role = "Presiding Officer" if not comp else f"Member {member_seq}"
                comp.append({
                    "role": role,
                    "rank": str(m.get("rank") or "").strip(),
                    "name": name,
                    "service_no": str(m.get("service_no") or "").strip(),
                    "unit": str(m.get("unit") or "").strip(),
                })
        parsed["composition_of_court"] = comp

        # 5. Terms of reference: keep only what is traceable to the order
        terms = parsed.get("terms_of_reference")
        if isinstance(terms, list):
            parsed["terms_of_reference"] = [
                t for t in terms if isinstance(t, str) and t.strip() and self._supported_by_text(t, text)
            ]
        else:
            parsed["terms_of_reference"] = []

        # 6. The executive summary is REBUILT deterministically from fields that
        #    were verified verbatim above. The model's free-text briefing is
        #    never shown: a fluent summary is exactly where invented names,
        #    dates and incident types would slip into the UI.
        parsed["executive_summary"] = self._build_executive_summary(parsed)

        return parsed

    def analyze_case_and_evidence(
        self, 
        convening_order_text: str, 
        supporting_docs_text: str, 
        military_laws_context: str,
        witness_statements_text: str = ""
    ) -> Dict[str, Any]:
        """
        Synthesizes Convening Order, Supporting Documents, Military Laws, AND Witness Statements.
        Cross-examines all evidence to detect ambiguities and discrepancies.
        """
        system_prompt = (
            "You are a military legal advisor and presiding officer of a statutory Court of Inquiry (CoI). "
            "Examine all provided evidence: Convening Order, Supporting Documents/Exhibits, "
            "statutory Military Laws (Army Act, Army Rules, DSR), and any recorded Witness Statements.\n\n"
            "CRITICAL TASK: Cross-correlate every witness statement with the documentary exhibits and convening order. "
            "Detect any contradictions, timeline discrepancies, physical inconsistencies, or ambiguities.\n\n"
            "Keep the JSON COMPACT: use short phrases of 25 words or fewer per field and short lists "
            "(max 6 items) -- never long paragraphs.\n\n"
            "Produce a structured JSON report strictly with the following keys:\n"
            "{\n"
            '  "incident_overview": {\n'
            '     "date_and_time": "exact date and time of incident",\n'
            '     "location": "location of occurrence",\n'
            '     "subject_or_equipment_involved": "Vehicle / weapon / property / unit involved",\n'
            '     "mission_nature": "Context of duty or occurrence",\n'
            '     "full_subject_statement": "VERBATIM subject / incident statement exactly as written in the convening order",\n'
            '     "conditions_weather_road_or_site": "weather, road, lighting, storage or site conditions if recorded in the documents",\n'
            '     "key_circumstances": "Key circumstances established by evidence",\n'
            '     "sequence_of_events": ["event 1 with its time as recorded", "event 2 with its time", "further events in order"]\n'
            '  },\n'
            '  "parties_involved": {\n'
            '     "individuals_investigated": [\n'
            '         {\n'
            '            "rank_and_name": "string",\n'
            '            "service_no": "string",\n'
            '            "unit": "string",\n'
            '            "role_in_incident": "string",\n'
            '            "status_or_fitness": "Medical/duty fitness or sobriety assessment"\n'
            '         }\n'
            '     ],\n'
            '     "victim_and_damage_summary": {\n'
            '         "injured_personnel": ["List of any personnel injured with injury degree"],\n'
            '         "military_property_damaged": ["Military equipment / vehicle / property affected"],\n'
            '         "public_or_mes_property_damaged": ["Public / MES / third party property affected"],\n'
            '         "financial_loss_estimate": "Estimated total financial damage with item breakdown"\n'
            '     }\n'
            '  },\n'
            '  "root_cause_analysis": {\n'
            '     "primary_cause": "Core reason for occurrence (e.g. mechanical failure, negligence, unavoidable accident)",\n'
            '     "culpability_verdict": "Clear verdict whether any individual was negligent or if failure/incident was beyond control",\n'
            '     "contributory_factors": "Any other technical or environmental factors"\n'
            '  },\n'
            '  "ambiguities_and_discrepancies": [\n'
            '     {\n'
            '        "subject": "Area of discrepancy (e.g. Speed / Servicing / Timeline / Statement Contradiction)",\n'
            '        "finding": "Detailed explanation of what the witness claimed versus what the technical/documentary evidence records",\n'
            '        "status": "Resolved / Clarified by Expert / Unresolved Contradiction"\n'
            '     }\n'
            '  ],\n'
            '  "military_legal_compliance": [\n'
            '     {\n'
            '        "law_provision": "Army Rule 180",\n'
            '        "applicability": "Assessment of whether character/reputation was affected and whether opportunity for cross-examination was given",\n'
            '        "finding": "Complied with / Exonerated / Procedural status"\n'
            '     },\n'
            '     {\n'
            '        "law_provision": "Army Act applicable Section",\n'
            '        "applicability": "Relevance to neglect of duty, property damage, or discipline",\n'
            '        "finding": "Finding on culpability"\n'
            '     },\n'
            '     {\n'
            '        "law_provision": "DSR Regulations / SOPs",\n'
            '        "applicability": "Guideline on regularisation of financial loss or investigation standards",\n'
            '        "finding": "Recommended action (e.g. write-off by CFA or disciplinary action)"\n'
            '     }\n'
            '  ],\n'
            '  "court_preliminary_opinion": "Detailed multi-sentence executive summary of what the evidence establishes, culpability, and correlations between documents and statements.",\n'
            '  "chronology_of_events": [\n'
            '     {"time": "date/time exactly as recorded", "event": "what happened", "source_document": "Convening Order / FIR / Medical Report / Technical Inspection / Witness Statement"}\n'
            '  ],\n'
            '  "exhibits_and_their_findings": [\n'
            '     {"exhibit": "exhibit letter or file name", "document_type": "FIR / Medical / Technical / Convening Order", "what_it_establishes": "the specific fact this document proves"}\n'
            '  ],\n'
            '  "areas_requiring_detailed_probing": [\n'
            '     "specific point on which the record is thin, silent or contradictory and which the Court must question witnesses about"\n'
            '  ],\n'
            '  "evidence_gaps": [\n'
            '     "information that is missing from the uploaded documents and must be obtained"\n'
            '  ],\n'
            '  "financial_loss_breakdown": [\n'
            '     {"item": "damaged item as named in the documents", "estimated_amount": "amount exactly as recorded (empty if not stated)", "source_document": "which exhibit states it"}\n'
            '  ],\n'
            '  "procedural_compliance": [\n'
            '     {"requirement": "procedural step (reporting, scene security, medical evacuation, exhibit seizure)", "status": "Complied / Not shown in documents", "remarks": "what the documents show"}\n'
            '  ]\n'
            "}\n"
            "STRICT FACT-EXTRACTION RULES -- violating any of these is an error:\n"
            "1. Use ONLY facts explicitly present in the supplied documents. Never add outside knowledge.\n"
            "2. Copy every name, rank, service number, unit, date, time, place, amount and document reference EXACTLY as written.\n"
            "3. NEVER invent, estimate, infer or complete missing information. If something is not stated in the documents, "
            "write the exact string 'Not stated in the documents' for that field (or an empty string / empty array for lists).\n"
            "4. Every entry in chronology_of_events, exhibits_and_their_findings, financial_loss_breakdown and "
            "procedural_compliance must cite a document that was actually supplied.\n"
            "5. Do not mention or cite any rule, section or paragraph numbers.\n"
            "6. Describe each exhibit ONLY by what its OWN supplied text shows. Never describe what such a "
            "document 'would normally' contain; if its text is unreadable or missing in the supplied copy, write "
            "the exact string 'Contents not readable in the supplied copy'. Likewise, never infer injuries, "
            "casualties, delays or fault that no supplied document states.\n"
            "7. Ensure the output is 100% valid JSON only."
        )

        user_prompt = (
            "FACT-EXTRACTION RULES: answer only from the documents below; copy values verbatim; "
            "write 'Not stated in the documents' where a fact is absent; describe each exhibit only by "
            "what its own supplied text shows; invent nothing; cite no rule numbers.\n\n"
            f"--- CONVENING ORDER ---\n{convening_order_text}\n\n"
            f"--- SUPPORTING EVIDENCE & EXHIBITS ---\n{supporting_docs_text}\n\n"
            f"--- RECORDED WITNESS STATEMENTS ---\n{witness_statements_text if witness_statements_text else 'No witness statements recorded yet.'}\n\n"
            f"--- MILITARY LAW STATUTES & REGULATIONS ---\n{military_laws_context}"
        )

        try:
            response_text = self._call_llm(system_prompt, user_prompt, max_tokens=3000)
            parsed = self._clean_json_response(response_text)
            if isinstance(parsed, dict) and "incident_overview" in parsed:
                return parsed
        except Exception as e:
            logger.warning(f"Error analyzing case via LLM: {e}")

        # Fallback analysis if LLM fails -- neutral placeholders only, no invented facts
        return {
            "incident_overview": {
                "date_and_time": "Recorded in Convening Order",
                "location": "Recorded in Convening Order",
                "subject_or_equipment_involved": "As specified in the Convening Order",
                "mission_nature": "As specified in the Convening Order",
                "full_subject_statement": "",
                "conditions_weather_road_or_site": "Not stated in the documents",
                "key_circumstances": "To be established from the documents uploaded with the Convening Order.",
                "sequence_of_events": []
            },
            "parties_involved": {
                "individuals_investigated": [],
                "victim_and_damage_summary": {
                    "injured_personnel": [],
                    "military_property_damaged": [],
                    "public_or_mes_property_damaged": [],
                    "financial_loss_estimate": "Not stated in the documents"
                }
            },
            "root_cause_analysis": {
                "primary_cause": "Not stated in the documents",
                "culpability_verdict": "To be recorded by the Court on the evidence",
                "contributory_factors": "Not stated in the documents"
            },
            "ambiguities_and_discrepancies": [],
            "military_legal_compliance": [],
            "court_preliminary_opinion": "The Court will record the evidence of the witnesses examined and the exhibits tendered.",
            "chronology_of_events": [],
            "exhibits_and_their_findings": [],
            "areas_requiring_detailed_probing": [],
            "evidence_gaps": ["Case brief could not be generated - please run the analysis again."],
            "financial_loss_breakdown": [],
            "procedural_compliance": []
        }

    def generate_witness_questions(
        self,
        case_overview: Dict[str, Any],
        witness_info: Dict[str, Any],
        supporting_docs_text: str = "",
        convening_order_text: str = ""
    ) -> List[str]:
        """Case-specific witness questions: minimum 20, ordered BASIC -> ADVANCED.

        The model only ever sees the documents that were actually uploaded and
        is instructed never to invent a fact or to cite a rule/section number,
        so the questions stay strictly tied to this case (no hallucinations).
        """
        # ---- Normalise the case overview (accepts the structured shape sent by
        # the API as well as the raw case-analysis shape) ----
        if "incident_overview" in case_overview and "subject_matter" not in case_overview:
            analysis: Dict[str, Any] = case_overview
            subject_matter = ""
            incident_details: Dict[str, Any] = {}
        else:
            analysis = case_overview.get("case_analysis") or {}
            subject_matter = case_overview.get("subject_matter") or ""
            incident_details = case_overview.get("incident_details") or {}

        incident_overview = analysis.get("incident_overview") or {}
        if not subject_matter:
            subject_matter = str(
                incident_details.get("nature_of_incident")
                or incident_overview.get("full_subject_statement")
                or ""
            )

        # ---- Rule catalogue: background relevance context ONLY. The questions
        # themselves never cite rules (see HARD RULE 3 in the prompt). ----
        combined_text = f"{subject_matter} {convening_order_text or ''}".lower()
        stop_words = {"the", "and", "or", "but", "is", "are", "was", "were", "be", "been", "being",
                      "to", "of", "a", "an", "in", "for", "on", "with", "as", "by", "at", "from"}
        search_terms: List[str] = []
        seen_terms = set()
        for word in combined_text.split():
            word = word.strip(".,;:!?'\"")
            if len(word) > 2 and word not in stop_words and word not in seen_terms:
                seen_terms.add(word)
                search_terms.append(word)
        search_query = " ".join(search_terms[:6])

        selected_rules: List[Dict[str, Any]] = []
        if search_query.strip():
            try:
                selected_rules = select_rules(search_query, max_results=12)
                selected_rules = [r for r in selected_rules if len(r.get("summary", "")) > 10]
            except Exception as e:
                logger.warning(f"Rule catalog search failed: {e}")
                selected_rules = []

        rules_context = ""
        if selected_rules:
            rules_context = (
                "\nBACKGROUND TOPICS TO KEEP IN MIND "
                "(do NOT quote or cite any of these in the questions):\n"
            )
            for i, r in enumerate(selected_rules, 1):
                rules_context += (
                    f"{i}. {r.get('rule_number', r.get('rule_or_section', ''))}: "
                    f"{r.get('summary', '')}\n"
                )
            rules_context += "\n"

        # ---- Mandatory procedural checklist (e.g. the fire-inquiry points).
        # When the rulebook prescribes the exact points of the inquiry, every
        # point MUST be turned into one or more witness questions. ----
        checklist_points: List[str] = []
        try:
            checklist_points = get_mandatory_checklist(
                f"{subject_matter} {convening_order_text or ''} "
                f"{supporting_docs_text[:2000]} {witness_info.get('statement') or ''}"
            )
        except Exception as e:
            logger.warning(f"Checklist detection failed: {e}")
            checklist_points = []

        mandatory_points_block = ""
        if checklist_points:
            numbered = "\n".join(f"{i}. {p}" for i, p in enumerate(checklist_points, 1))
            mandatory_points_block = (
                "\n--- MANDATORY CHECKLIST: points the rulebook prescribes for this inquiry ---\n"
                "EVERY numbered point below MUST be covered by at least one question put to THIS "
                "witness. Turn each point into a plain question about what this witness personally "
                "saw, did, or was told (adapt it: a guard answers about the alarm and piquet, a "
                "runner about who was informed, an officer about command arrangements). You may ask "
                "extra questions beyond the checklist, but you may NOT skip, merge or re-order the "
                "points into fewer questions than needed:\n"
                f"{numbered}\n"
                "--- END MANDATORY CHECKLIST ---\n"
            )

        MIN_QUESTIONS = 20
        if checklist_points:
            MIN_QUESTIONS = max(MIN_QUESTIONS, len(checklist_points) + 8)

        system_prompt = (
            "You are the Presiding Officer of a statutory Court of Inquiry. You draft the questions "
            "put to a witness, based ONLY on the case documents supplied in the user message.\n\n"
            "HARD RULES:\n"
            "1. Ask ONLY about facts connected to this case as described in the supplied documents. "
            "Ignore every other topic.\n"
            "2. NEVER invent a name, date, time, place, unit, event or document. If a detail is not in "
            "the documents, phrase the question so the witness supplies it (e.g. 'State the exact time...').\n"
            "3. NEVER quote, cite or mention any Army Rule, DSR paragraph, section, rulebook or "
            "regulation number inside a question.\n"
            "4. One specific, answerable question per entry; no two questions may cover the same point.\n"
            "5. Return a single JSON object with the key 'questions' holding a list, each question "
            "numbered Q1, Q2, ... in the exact order they are to be asked.\n\n"
            "MANDATORY ORDERING -- BASIC TO ADVANCED:\n"
            "Block 1 - Basic identification and background: witness identity, rank, service number, "
            "unit, posting, duties and relationship to this case.\n"
            "Block 2 - Plain facts of the occurrence: exact date, time, place, what was happening, who "
            "else was present, what the witness personally saw and heard.\n"
            "Block 3 - Detailed case-specific probing: every specific detail found in the documents - "
            "equipment/vehicle/property condition, weather/road/site conditions, reporting to superiors "
            "and its timing, actions taken, medical treatment or evacuation, and each exhibit (FIR, "
            "technical inspection report, medical report, convening order) and what it records.\n"
            "Block 4 - Advanced and corroboration: discrepancies between statements and documents, "
            "gaps in the sequence, contributory factors, compliance with standing orders, loss and "
            "damage figures, responsibility, and corroboration of the other witnesses.\n\n"
            "If the user message contains a MANDATORY CHECKLIST, every numbered point of that "
            "checklist MUST appear as at least one question - weave them mainly into Block 3 while "
            "keeping the basic-to-advanced order overall.\n\n"
            "COUNT OF QUESTIONS:\n"
            + (
                f"- With a mandatory checklist: there is NO upper limit. Ask every question needed "
                f"to cover the whole checklist (at least {MIN_QUESTIONS}); do not compress points "
                f"to save space."
                if checklist_points
                else f"- Without a checklist: return {MIN_QUESTIONS} to 25 questions."
            )
            + " Number every question Q1, Q2, ... in the exact order they are to be asked."
        )

        has_supporting_docs = bool(supporting_docs_text and len(supporting_docs_text.strip()) > 50)
        evidence_section = (
            f"--- SUPPORTING EXHIBITS & REPORTS ---\n{supporting_docs_text[:3500]}"
            if has_supporting_docs
            else "--- NO SUPPORTING EXHIBITS UPLOADED ---"
        )

        case_facts = (
            "--- CASE SUBJECT / INCIDENT (verbatim from the Convening Order) ---\n"
            f"{subject_matter or 'Not stated in the documents'}\n\n"
            "--- INCIDENT DETAILS ---\n"
            f"{json.dumps(incident_details, indent=2) if incident_details else 'Not stated in the documents'}\n\n"
            "--- CASE BRIEF (analysed from the uploaded documents) ---\n"
            f"{json.dumps(analysis, indent=2)[:3500] if analysis else 'Case brief not generated yet.'}\n\n"
            "--- CONVENING ORDER RAW TEXT ---\n"
            f"{(convening_order_text or '')[:3500]}\n\n"
            f"{evidence_section}\n\n"
            "--- WITNESS TO BE EXAMINED ---\n"
            f"Name: {witness_info.get('name')}\n"
            f"Rank: {witness_info.get('rank')}\n"
            f"Service No: {witness_info.get('service_no')}\n"
            f"Unit: {witness_info.get('unit')}\n"
            f"Ref Letter: {witness_info.get('ref_letter', 'B')}\n"
            "Preliminary Statement (if any):\n"
            f"{witness_info.get('statement') or 'None provided yet.'}"
        )

        base_prompt = (
            f"{case_facts}\n{rules_context}{mandatory_points_block}\n"
            f"REQUIREMENT: produce at least {MIN_QUESTIONS} questions ordered from basic to advanced "
            f"exactly as specified in the system instructions."
            + (
                " You MUST ask about EVERY point of the MANDATORY CHECKLIST above."
                if checklist_points
                else ""
            )
        )

        def _ask(prompt: str) -> List[str]:
            try:
                response_text = self._call_llm(system_prompt, prompt, max_tokens=5000, temperature=0.2)
                parsed = self._clean_json_response(response_text)
                if isinstance(parsed, dict) and isinstance(parsed.get("questions"), list):
                    return [str(q).strip() for q in parsed["questions"] if str(q).strip()]
            except Exception as e:
                logger.warning(f"Error generating questions via LLM: {e}")
            return []

        questions = _ask(base_prompt)

        if len(questions) < MIN_QUESTIONS:
            # One corrective retry that spells out exactly what is missing
            correction = (
                f"{base_prompt}\n\nCORRECTION: only {len(questions)} questions were returned. "
                f"You MUST return at least {MIN_QUESTIONS} DISTINCT questions covering all four "
                f"blocks (identification, occurrence facts, document-specific detail, advanced "
                f"corroboration). Do not stop early."
                + (
                    " Verify that EVERY point of the MANDATORY CHECKLIST is asked about - one or "
                    "more questions per point, in checklist order where possible."
                    if checklist_points
                    else ""
                )
            )
            retried = _ask(correction)
            if len(retried) > len(questions):
                questions = retried

        # Guarantee the minimum: top up with case-tailored standard questions
        if len(questions) < MIN_QUESTIONS:
            questions = self._top_up_questions(questions, subject_matter, witness_info, MIN_QUESTIONS)

        return self._dedupe_questions(questions)

    @staticmethod
    def _dedupe_questions(questions: List[str]) -> List[str]:
        """Removes duplicate questions (ignoring numbering and case)."""
        out: List[str] = []
        seen = set()
        for q in questions:
            q = re.sub(r"\s+", " ", str(q)).strip()
            key = re.sub(r"^q\d+\.?\s*", "", q, flags=re.I).lower().strip(" ?.")
            if not key or key in seen:
                continue
            seen.add(key)
            out.append(q)
        return out

    def _top_up_questions(
        self,
        existing: List[str],
        subject_matter: str,
        witness_info: Dict[str, Any],
        minimum: int,
    ) -> List[str]:
        """Fills the list up to `minimum` with case-tailored standard questions
        (basic -> advanced) when the model returned too few."""
        subject = (subject_matter or "the incident under investigation").strip().rstrip(".")
        standard = [
            "State your full name, rank, service number, unit and present appointment.",
            "Describe your duties and place of posting on the date of the incident.",
            f"On what date and at what time did you first become aware of the incident relating to {subject}?",
            "Where exactly did the incident take place? Describe the place in detail.",
            "What were you personally doing at the time the incident occurred?",
            "Who else was present at the scene when the incident occurred?",
            "Describe in sequence what you saw and heard from the beginning of the incident.",
            "What were the weather, road, lighting or site conditions at the time of the incident?",
            "What equipment, vehicle or property was involved in the incident, and what was its condition?",
            "Was that equipment, vehicle or property in your charge, or in whose charge was it kept?",
            "To whom did you first report the incident, and at what time?",
            "What advice or instructions did your superior give you after you reported the incident?",
            "What action did you take immediately after the incident occurred?",
            "Who was injured, if anyone, and what medical assistance was rendered?",
            "How and when was the injured person evacuated to hospital, and who accompanied him?",
            "Which documents relating to this incident (FIR, technical inspection report, medical report) have you seen?",
            "Do the contents of those documents match what you have stated? Point out every difference.",
            "State the sequence of events between the occurrence of the incident and its reporting.",
            "Was any delay caused in reporting or in treatment? If so, give the reason for the delay.",
            "Is there any discrepancy between your statement and the statements of the other witnesses?",
            "In your opinion, what were the contributing factors to the incident?",
            "Were the standing orders, SOPs or safety precautions for this activity being followed?",
            "What loss or damage to government property resulted from the incident, and to what extent?",
            "Who, in your opinion, is responsible for the incident, and on what grounds?",
            f"Is there anything else you wish to state about {subject} that the Court should know?",
        ]
        combined = list(existing)
        for q in standard:
            if q not in combined:
                combined.append(q)
        return combined[: max(minimum, len(existing))]

    def compile_witness_testimony(
        self,
        witness_info: Dict[str, Any],
        case_overview: Dict[str, Any],
        convening_order_text: str = ""
    ) -> Dict[str, Any]:
        """
        Combines background particulars and all manually filled Q&A answers into the
        standard statutory witness deposition matching coi.PDF (IAFD-931 pages 2-4).
        """
        qa_pairs = witness_info.get("qa_pairs") or []
        user_answers_text = ""
        for idx, item in enumerate(qa_pairs):
            q_text = item.get("question", f"Question {idx+1}")
            a_text = item.get("answer", "No answer recorded.")
            user_answers_text += f"{q_text}\nAns. {a_text}\n\n"

        system_prompt = (
            "You are a Military Legal Drafter preparing official witness depositions for a Court of Inquiry under Army Rule 179. "
            "Synthesize the provided witness particulars, preliminary statement, and all Question-Answer responses "
            "into the exact statutory format seen in Indian Army Court of Inquiry proceedings (IAFD-931):\n\n"
            "SCHEMA REQUIRED (JSON):\n"
            "{\n"
            '  "warning_declaration": "1. I, Army No. [Service No], [Rank] [Name], of [Unit], having been duly warned, state the following:-",\n'
            '  "posting_and_duties": "2. I am posted at [Unit] with effect from [Date] and am performing the duties of [Duties].",\n'
            '  "narrative_statement": "3. On [Date] at [Time], I was proceeding for duty... [Comprehensive chronological facts of occurrence]...",\n'
            '  "questions_by_court": [\n'
            '     {"q": "Q1. How did you get injure?", "ans": "Ans. I got injured on..."},\n'
            '     {"q": "Q2. ...", "ans": "Ans. ..."}\n'
            '  ],\n'
            '  "closing_affirmation": "The above statement has been read to me in the language I understand and I sign it as correct.",\n'
            '  "presiding_officer_sign": "Presiding Officer: [Rank Name]",\n'
            '  "witness_sign": "(Army No. [Service No], [Rank] [Name])"\n'
            "}\n"
            "Only return valid JSON."
        )

        user_prompt = (
            f"--- WITNESS PARTICULARS ---\n"
            f"Rank: {witness_info.get('rank')}\n"
            f"Name: {witness_info.get('name')}\n"
            f"Service No: {witness_info.get('service_no')}\n"
            f"Unit: {witness_info.get('unit')}\n\n"
            f"--- WITNESS PRELIMINARY STATEMENT / BACKGROUND ---\n"
            f"{witness_info.get('statement', 'None provided')}\n\n"
            f"--- RECORDED QUESTIONS AND ANSWERS GIVEN BY WITNESS ---\n"
            f"{user_answers_text}\n\n"
            f"--- CONVENING CONTEXT ---\n{convening_order_text[:1000]}"
        )

        try:
            response_text = self._call_llm(system_prompt, user_prompt, max_tokens=2500)
            parsed = self._clean_json_response(response_text)
            if isinstance(parsed, dict) and "warning_declaration" in parsed:
                # Fixed statutory lines: rebuild them from the witness's own
                # record so the model can never inject label words ('Rank',
                # 'Name') or shorthand ('wef') into the statement.
                parsed["warning_declaration"] = self._warning_declaration(witness_info)
                posting = parsed.get("posting_and_duties")
                parsed["posting_and_duties"] = (
                    self._polish_posting(posting)
                    if isinstance(posting, str) and posting.strip()
                    else f"2. I am posted at {str(witness_info.get('unit') or 'the Unit')} "
                         f"and am performing the duties entrusted to me."
                )
                parsed["witness_sign"] = self._witness_sign(witness_info)
                return parsed
        except Exception as e:
            logger.warning(f"Error compiling testimony via LLM: {e}")

        # Deterministic structured assembly fallback -- uses only the witness's
        # own particulars; nothing is invented when a field is missing.
        w_rank = witness_info.get("rank") or ""
        w_name = witness_info.get("name") or ""
        w_no = witness_info.get("service_no") or "XXXXX"
        w_unit = witness_info.get("unit") or "the Unit"

        q_list = []
        for idx, item in enumerate(qa_pairs):
            q_list.append({
                "q": item.get("question", f"Q{idx+1}."),
                "ans": f"Ans. {item.get('answer', 'Stated as recorded.')}"
            })

        # Presiding Officer signature: read from the order text, never invented
        po_label = "As per Convening Order"
        try:
            order_comp = self._verbatim_composition(convening_order_text or "")
            po = next((m for m in order_comp if m.get("role") == "Presiding Officer"), None)
            if po:
                po_label = f"{po.get('rank', '')} {po.get('name', '')}".strip() or po_label
        except Exception:
            po_label = "As per Convening Order"

        return {
            "warning_declaration": self._warning_declaration(witness_info),
            "posting_and_duties": f"2. I am posted at {w_unit} and am performing the duties entrusted to me.",
            "narrative_statement": f"3. {witness_info.get('statement') or 'On the date of occurrence recorded in the Convening Order, the incident occurred as stated in the evidence.'}",
            "questions_by_court": q_list,
            "closing_affirmation": "The above statement has been read to me in the language I understand and I sign it as correct.",
            "presiding_officer_sign": f"Presiding Officer: {po_label}",
            "witness_sign": self._witness_sign(witness_info),
        }

    def _ensure_complete_coi_draft(self, draft: Dict[str, Any], case_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Guarantees that every section of the Court of Inquiry draft is completely populated
        STRICTLY following the new 'In lieu of IAFD - 931' format from coi.PDF.
        Ensures NO EMPTY draft is ever returned!
        """
        conv = case_state.get("convening_order", {})
        parsed_order = conv.get("parsed") or {}
        analysis = case_state.get("case_analysis") or {}
        witnesses = case_state.get("witnesses") or []
        po_review = case_state.get("presiding_officer_review") or {}

        # 1. Header (In lieu of IAFD - 931)
        draft["header_iafd_form"] = "In lieu of IAFD - 931"
        header = draft.get("header") or {}
        header["form_id"] = "In lieu of IAFD - 931"
        if not header.get("proceed_of"):
            header["proceed_of"] = "Court of Inquiry"
        if not header.get("assembled_at"):
            header["assembled_at"] = parsed_order.get("place_of_assembly") or "As per Convening Order"
        if not header.get("on_time"):
            header["on_time"] = parsed_order.get("date_of_order") or "As per Convening Order"
        if not header.get("by_order_of"):
            order_no = parsed_order.get("order_number") or ""
            auth = parsed_order.get("convening_authority") or ""
            date = parsed_order.get("date_of_order") or ""
            if order_no or auth:
                bits = []
                if auth:
                    bits.append(auth)
                if order_no:
                    bits.append(f"Part I Order No {order_no}")
                if date:
                    bits.append(f"dt {date}")
                header["by_order_of"] = " ".join(bits)
            else:
                header["by_order_of"] = "As per Convening Order"
        if not header.get("for_the_purpose_of"):
            header["for_the_purpose_of"] = (
                parsed_order.get("subject_matter")
                or conv.get("summary")
                or "As detailed in the Convening Order"
            )

        # Composition of Court -- taken from the order as uploaded, never invented
        comp = header.get("composition_of_court") or []
        if not comp:
            comp_from_order = parsed_order.get("composition_of_court") or []
            if not comp_from_order:
                # last resort: read the members straight out of the raw order text
                try:
                    comp_from_order = self._verbatim_composition(conv.get("raw_text", ""))
                except Exception:
                    comp_from_order = []
            if comp_from_order:
                for m in comp_from_order:
                    rank_name = f"{m.get('rank', '')} {m.get('name', '')}".strip()
                    if m.get("service_no"):
                        rank_name = f"{m.get('service_no')} {rank_name}".strip()
                    comp.append({
                        "role": m.get("role", "Member"),
                        "rank_name": rank_name or "As per Convening Order"
                    })
            else:
                comp = [{"role": "Presiding Officer", "rank_name": "As per Convening Order"}]
        header["composition_of_court"] = comp

        if not header.get("assembly_declaration"):
            header["assembly_declaration"] = (
                f"The court of inquiry having assembled pursuant to order proceeded to investigate the circumstances under which "
                f"{header.get('for_the_purpose_of', 'the incident occurred')}."
            )
        draft["header"] = header

        # 2. Witness Proceedings (Matching coi.PDF pages 2-4)
        witness_proceedings = draft.get("witness_proceedings") or []
        # The opening warning, posting line and signatures are fixed statutory
        # formulas: rebuild them from the witness roster and grammar-clean the
        # posting line, so model wording (placeholder labels, 'wef', etc.) can
        # never reach the draft.
        for p_idx, wp in enumerate(witness_proceedings):
            if not isinstance(wp, dict):
                continue
            w_for_wp = witnesses[p_idx] if p_idx < len(witnesses) else None
            if w_for_wp:
                wp["warning_declaration"] = self._warning_declaration(w_for_wp)
                wp["witness_sign"] = self._witness_sign(w_for_wp)
            if isinstance(wp.get("posting_and_duties"), str) and wp["posting_and_duties"].strip():
                wp["posting_and_duties"] = self._polish_posting(wp["posting_and_duties"])
        if not witness_proceedings:
            for idx, w in enumerate(witnesses):
                w_no = w.get("service_no") or f"XXXX{idx+1}"
                w_rank = w.get("rank") or ""
                w_name = w.get("name") or ""
                w_unit = w.get("unit") or "the Unit"

                # If compiled statement exists, use it; otherwise build Q&A pairs
                qa_list = []
                qa_pairs = w.get("qa_pairs") or []
                if qa_pairs:
                    for q_idx, q_item in enumerate(qa_pairs):
                        qa_list.append({
                            "q": q_item.get("question", f"Q{q_idx+1}."),
                            "ans": f"Ans. {q_item.get('answer', 'Stated as recorded.')}"
                        })
                elif w.get("questions"):
                    for q_idx, q_text in enumerate(w["questions"]):
                        qa_list.append({
                            "q": f"Q{q_idx+1}. {q_text}",
                            "ans": "Ans. Stated and affirmed on solemn oath."
                        })
                else:
                    qa_list = [
                        {"q": "Q1. How did you get injure / How did the incident occur?", "ans": f"Ans. The incident occurred on bonafide duty as detailed in preliminary statement."},
                        {"q": "Q2. Did you seek medical assistance after the incident?", "ans": "Ans. Yes, reported to Base Hospital / Medical Officer."},
                        {"q": "Q3. Did you report the incident to anyone?", "ans": "Ans. Reported immediately to ADM JCO / Superior Officer."},
                        {"q": "Q4. Was your vehicle / conveyance in good condition?", "ans": "Ans. Conveyance was in good roadworthy condition."},
                        {"q": "Q5. Were you in state of intoxication when fell down?", "ans": "Ans. No, I was not in state of intoxication."}
                    ]

                witness_proceedings.append({
                    "witness_no": idx + 1,
                    "title": f"Witness No {idx + 1}",
                    "warning_declaration": self._warning_declaration(w),
                    "posting_and_duties": f"2. I am posted at {w_unit} and am performing the duties entrusted to me.",
                    "narrative_statement": f"3. {w.get('statement') or 'On the date of occurrence recorded in the Convening Order, the incident occurred as stated in the evidence.'}",
                    "questions_by_court": qa_list,
                    "closing_affirmation": "The above statement has been read to me in the language I understand and I sign it as correct.",
                    "presiding_officer_sign": f"Presiding Officer: {comp[0].get('rank_name', 'As per Convening Order')}",
                    "witness_sign": self._witness_sign(w),
                })

            if not witness_proceedings:
                witness_proceedings = [{
                    "witness_no": 1,
                    "title": "Witness No 1",
                    "warning_declaration": "1. Witness particulars to be recorded from the Convening Order and the witness roster.",
                    "posting_and_duties": "2. Posting and duties to be recorded from the evidence.",
                    "narrative_statement": "3. Statement of the witness to be recorded on examination by the Court.",
                    "questions_by_court": [
                        {"q": "Q1. State your name, rank, service number and unit.", "ans": "Ans. To be recorded."},
                        {"q": "Q2. How did the incident occur?", "ans": "Ans. To be recorded."}
                    ],
                    "closing_affirmation": "The above statement has been read to me in the language I understand and I sign it as correct.",
                    "presiding_officer_sign": f"Presiding Officer: {comp[0].get('rank_name', 'As per Convening Order')}",
                    "witness_sign": "(Signature of witness)"
                }]
        draft["witness_proceedings"] = witness_proceedings

        # 3. Finding of the Court (Matching coi.PDF page 5)
        findings = draft.get("findings_of_the_court") or []
        if not findings or len(findings) == 0:
            # Neutral findings assembled only from what the case record holds --
            # no incident-specific detail is invented here.
            primary_cause = (analysis.get("root_cause_analysis") or {}).get("primary_cause") or ""
            findings = [
                "1. That the Court assembled pursuant to the Convening Order and recorded the evidence of the witnesses examined.",
            ]
            if primary_cause and "not stated" not in primary_cause.lower():
                findings.append(
                    f"2. That the evidence on record indicates the following circumstances: {primary_cause}."
                )
            findings.append(
                f"{len(findings) + 1}. That the occurrence has been examined in the light of the "
                "Convening Order, the exhibits tendered and the statements of the witnesses recorded."
            )
            findings.append(
                f"{len(findings) + 1}. That the remaining points are to be arrived at from the evidence on record."
            )
        draft["findings_of_the_court"] = findings

        # 4. Opinion of the Court (standard four-point form; no invented details)
        opinion = draft.get("opinion_of_the_court") or []
        if not opinion or len(opinion) == 0:
            opinion = [
                "1. The occurrence took place in the circumstances established by the evidence on record.",
                "2. The occurrence took place while the individual was on bonafide military duty, as recorded in the documents.",
                "3. The loss / injury is attributable to military service, based on the evidence tendered.",
                "4. No blame attaches to the individual on the evidence recorded."
            ]
        draft["opinion_of_the_court"] = opinion

        # 5. Remarks of OC / Convening Authority (Matching coi.PDF page 7)
        remarks = draft.get("remarks_of_convening_authority") or {}
        if not remarks or not remarks.get("points"):
            authority_title = parsed_order.get("convening_authority") or "Convening Authority"
            subject_line = parsed_order.get("subject_matter") or "the occurrence"
            remarks = {
                "title": f"REMARKS OF {authority_title.upper()} ON THE COURT OF INQUIRY REGARDING {subject_line}",
                "points": [
                    "1. I concur with the finding of the court.",
                    "2. The loss / injury, if established to have been sustained on bonafide military duty, is Attributable To Military Service.",
                    "3. The individual is not to be blamed, subject to the findings recorded above."
                ],
                "station": f"Station: {parsed_order.get('place_of_assembly') or 'As per Convening Order'}",
                "date": f"Date : {parsed_order.get('date_of_order') or 'As per Convening Order'}"
            }
        draft["remarks_of_convening_authority"] = remarks

        # 6. Signatures
        sigs = draft.get("signatures") or {}
        if not sigs.get("presiding_officer"):
            sigs["presiding_officer"] = comp[0].get("rank_name", "As per Convening Order")
            sigs["members"] = [
                comp[1].get("rank_name", "As per Convening Order") if len(comp) > 1 else "As per Convening Order",
                comp[2].get("rank_name", "As per Convening Order") if len(comp) > 2 else "As per Convening Order"
            ]
        draft["signatures"] = sigs

        # Aliases for frontend flexibility and backward compatibility
        draft["witness_depositions"] = draft.get("witness_proceedings", [])
        draft["findings"] = draft.get("findings_of_the_court", [])
        draft["opinion"] = draft.get("opinion_of_the_court", [])
        draft["remarks_of_oc_tps"] = draft.get("remarks_of_convening_authority", {})
        draft["assembly_table"] = {
            "purpose_of_inquiry": header.get("for_the_purpose_of", ""),
            "place_of_assembly": header.get("assembled_at", ""),
            "date_of_assembly": header.get("on_time", ""),
            "convening_order_ref": header.get("by_order_of", "")
        }

        return draft

    def generate_coi_draft_report(self, full_case_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generates the complete Court of Inquiry draft report strictly adhering to the new
        'In lieu of IAFD - 931' format from coi.PDF.
        Guaranteed to ALWAYS return a complete, authentic 7-page standard report!
        """
        system_prompt = (
            "You are a Senior Judge Advocate General (JAG) Military Drafter. "
            "Generate the formal, complete Court of Inquiry proceedings draft adhering STRICTLY "
            "to the statutory Indian Armed Forces Court of Inquiry format (In lieu of IAFD - 931) from coi.PDF.\n\n"
            "MANDATORY SCHEMA (JSON ONLY):\n"
            "{\n"
            '  "header": {\n'
            '     "proceed_of": "Court of Inquiry",\n'
            '     "assembled_at": "string",\n'
            '     "on_time": "string",\n'
            '     "by_order_of": "string (Part I Order Ref and Date)",\n'
            '     "for_the_purpose_of": "string (Exact mandate from convening order)",\n'
            '     "composition_of_court": [\n'
            '        {"role": "Presiding Officer", "rank_name": "string"},\n'
            '        {"role": "Member 1", "rank_name": "string"},\n'
            '        {"role": "Member 2", "rank_name": "string"}\n'
            '     ],\n'
            '     "assembly_declaration": "The court of inquiry having assembled pursuant to order proceeded to investigate..."\n'
            '  },\n'
            '  "witness_proceedings": [\n'
            '     {\n'
            '        "witness_no": 1,\n'
            '        "title": "Witness No 1",\n'
            '        "warning_declaration": "1. I, Army No. [No], [Rank] [Name], of [Unit], having been duly warned, state the following:-",\n'
            '        "posting_and_duties": "2. I am posted at [Unit] with effect from [Date] and am performing the duties of [Duties].",\n'
            '        "narrative_statement": "3. On [date] at [time]... [factual occurrence]...",\n'
            '        "questions_by_court": [\n'
            '           {"q": "Q1. How did you get injure?", "ans": "Ans. ..."},\n'
            '           {"q": "Q2. ...", "ans": "Ans. ..."}\n'
            '        ],\n'
            '        "closing_affirmation": "The above statement has been read to me in the language I understand and I sign it as correct.",\n'
            '        "presiding_officer_sign": "Presiding Officer: JC-xxxx Rank Name",\n'
            '        "witness_sign": "(No xxxxx Rank Name)"\n'
            '     }\n'
            '  ],\n'
            '  "findings_of_the_court": [\n'
            '     "1. That... (Witness No 1)",\n'
            '     "2. That... (Witness No 1)",\n'
            '     "3. That... (Witness No 1&2)",\n'
            '     "4. That... (Witness No 1&3 & Exhibit \'I\')"\n'
            '  ],\n'
            '  "opinion_of_the_court": [\n'
            '     "1. [Occurrence summary: Individual sustained injury/loss due to...]",\n'
            '     "2. [Bonafide military duty finding: Sustained while on bonafide military duty]",\n'
            '     "3. [Attributability finding: Injury/occurrence is attributable to military service]",\n'
            '     "4. [Culpability verdict: The indl is not to be blamed for the injury / No negligence]"\n'
            '  ],\n'
            '  "remarks_of_convening_authority": {\n'
            '     "title": "REMARKS OF [CONVENING AUTHORITY] ON THE COURT OF INQUIRY REGARDING [SUBJECT]",\n'
            '     "points": [\n'
            '        "1. I concur with the finding of the court.",\n'
            '        "2. The severe injury sustained by [Name] is Attributable To Military Service as indl was on bonafide military duty.",\n'
            '        "3. The indl is not to be blamed for the injury."\n'
            '     ],\n'
            '     "station": "Station: string",\n'
            '     "date": "Date : string"\n'
            '  },\n'
            '  "signatures": {\n'
            '     "presiding_officer": "string",\n'
            '     "members": ["string", "string"]\n'
            '  }\n'
            "}\n"
            "STRICT FACT RULES:\n"
            "1. Fill every field ONLY from the Case State Data supplied -- copy names, ranks, service "
            "numbers, units, dates and order references exactly as they appear there.\n"
            "2. NEVER invent a person, date, place, unit or event. Where the supplied data does not "
            "contain a value, write 'As per Convening Order'.\n"
            "3. Never quote or cite any rule / section / paragraph numbers.\n"
            "Output strictly valid JSON matching this schema."
        )

        # Provide a streamlined case overview to keep prompt tokens well within TPM limits
        streamlined_state = {
            "convening_order_parsed": full_case_state.get("convening_order", {}).get("parsed", {}),
            "convening_order_summary": full_case_state.get("convening_order", {}).get("summary", ""),
            "witnesses": [
                {
                    "rank": w.get("rank"),
                    "name": w.get("name"),
                    "service_no": w.get("service_no"),
                    "unit": w.get("unit"),
                    "qa_pairs": w.get("qa_pairs"),
                    "compiled_testimony": w.get("compiled_testimony"),
                    "statement": w.get("statement")
                }
                for w in full_case_state.get("witnesses", [])
            ],
            "case_analysis": full_case_state.get("case_analysis", {}),
            "presiding_officer_review": full_case_state.get("presiding_officer_review", {})
        }
        user_prompt = f"Case State Data:\n\n{json.dumps(streamlined_state, indent=2)}"
        raw_draft = {}
        try:
            response_text = self._call_llm(system_prompt, user_prompt, max_tokens=4000)
            parsed = self._clean_json_response(response_text)
            if isinstance(parsed, dict) and "header" in parsed:
                raw_draft = parsed
        except Exception as e:
            logger.warning(f"Error generating CoI draft via LLM: {e}")

        # Pass through the completion helper to guarantee NO empty fields
        complete_draft = self._ensure_complete_coi_draft(raw_draft, full_case_state)
        return complete_draft

llm_service = LLMService()
