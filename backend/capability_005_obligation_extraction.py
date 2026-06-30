import os
import re
import json
from typing import Any, Dict, List, Optional

try:
    from openai import OpenAI
except Exception:
    OpenAI = None


class ObligationExtractor:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=self.api_key) if OpenAI and self.api_key else None

    def extract(self, text: str, document_type: Optional[str] = None) -> Dict[str, Any]:
        clean_text = self._clean_text(text)

        if self.client:
            return self._extract_with_ai(clean_text, document_type)

        return self._extract_basic(clean_text, document_type)

    def _clean_text(self, text: str) -> str:
        text = text.replace("\x00", " ")
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def _extract_with_ai(self, text: str, document_type: Optional[str]) -> Dict[str, Any]:
        prompt = f"""
You are ATHENA Capability 005: Contract and Tender Obligation Extraction.

Your job is to extract obligations, risks, deadlines, penalties, required documents,
technical requirements, and management actions from a tender, contract, quotation,
purchase order, invoice, or business document.

Return ONLY valid JSON.

Required JSON format:
{{
  "document_type": "",
  "executive_summary": "",
  "supplier_obligations": [],
  "buyer_or_client_obligations": [],
  "delivery_obligations": [],
  "payment_obligations": [],
  "technical_specifications": [],
  "required_documents": [],
  "certificates_required": [],
  "submission_requirements": [],
  "important_dates": [],
  "penalties_or_liabilities": [],
  "warranty_or_guarantee_terms": [],
  "commercial_risks": [],
  "missing_or_unclear_information": [],
  "management_action_list": [],
  "priority_level": "Low / Medium / High / Critical",
  "confidence_score": 0
}}

Rules:
- Do not invent information.
- If something is missing, add it to missing_or_unclear_information.
- management_action_list must be practical and written for company management.
- priority_level depends on deadline risk, penalty risk, missing documents, unclear scope, or financial exposure.
- confidence_score must be from 0 to 100.

Document Type:
{document_type or "Unknown"}

Document text:
{text[:14000]}
"""

        response = self.client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You extract contractual, tender, commercial, and operational obligations from business documents.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0,
        )

        raw = response.choices[0].message.content.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()

        try:
            return json.loads(raw)
        except Exception:
            return {
                "document_type": document_type or "",
                "executive_summary": raw,
                "supplier_obligations": [],
                "buyer_or_client_obligations": [],
                "delivery_obligations": [],
                "payment_obligations": [],
                "technical_specifications": [],
                "required_documents": [],
                "certificates_required": [],
                "submission_requirements": [],
                "important_dates": [],
                "penalties_or_liabilities": [],
                "warranty_or_guarantee_terms": [],
                "commercial_risks": ["AI response was not valid JSON"],
                "missing_or_unclear_information": ["Manual review required"],
                "management_action_list": ["Review document manually before decision"],
                "priority_level": "Medium",
                "confidence_score": 50,
            }

    def _extract_basic(self, text: str, document_type: Optional[str]) -> Dict[str, Any]:
        return {
            "document_type": document_type or self._detect_document_type(text),
            "executive_summary": self._basic_summary(text),
            "supplier_obligations": self._find_lines(text, ["supplier shall", "contractor shall", "vendor shall", "seller shall"]),
            "buyer_or_client_obligations": self._find_lines(text, ["buyer shall", "client shall", "customer shall", "authority shall"]),
            "delivery_obligations": self._find_lines(text, ["delivery", "deliver", "lead time", "location"]),
            "payment_obligations": self._find_lines(text, ["payment", "invoice", "advance", "retention"]),
            "technical_specifications": self._find_lines(text, ["specification", "gsm", "fabric", "leather", "sole", "material", "standard"]),
            "required_documents": self._find_lines(text, ["required documents", "documents required", "submit", "submission"]),
            "certificates_required": self._find_lines(text, ["certificate", "iso", "test report", "compliance"]),
            "submission_requirements": self._find_lines(text, ["submission", "submit", "closing date", "deadline"]),
            "important_dates": self._find_dates_and_deadlines(text),
            "penalties_or_liabilities": self._find_lines(text, ["penalty", "liability", "liquidated damages", "delay damages", "fine"]),
            "warranty_or_guarantee_terms": self._find_lines(text, ["warranty", "guarantee", "defect", "replacement"]),
            "commercial_risks": self._basic_risks(text),
            "missing_or_unclear_information": self._missing_info(text),
            "management_action_list": [
                "Confirm delivery obligations",
                "Confirm payment terms",
                "Confirm required documents before submission",
                "Review penalties and warranty exposure",
                "Assign responsible person for each obligation",
            ],
            "priority_level": self._priority_level(text),
            "confidence_score": 60,
        }

    def _detect_document_type(self, text: str) -> str:
        lower = text.lower()
        if "tender" in lower:
            return "Tender"
        if "contract" in lower or "agreement" in lower:
            return "Contract"
        if "quotation" in lower or "quote" in lower:
            return "Quotation"
        if "purchase order" in lower or " po " in lower:
            return "Purchase Order"
        if "invoice" in lower:
            return "Invoice"
        return "Unknown"

    def _basic_summary(self, text: str) -> str:
        lines = [line.strip() for line in text.splitlines() if len(line.strip()) > 25]
        return " ".join(lines[:4])[:900]

    def _find_lines(self, text: str, keywords: List[str]) -> List[str]:
        results = []
        for line in text.splitlines():
            clean = line.strip()
            lower = clean.lower()
            if clean and any(keyword in lower for keyword in keywords):
                if clean not in results:
                    results.append(clean)
        return results[:20]

    def _find_dates_and_deadlines(self, text: str) -> List[str]:
        results = []
        date_pattern = r"\b\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}\b|\b\d{4}[\/\-\.]\d{1,2}[\/\-\.]\d{1,2}\b"

        for line in text.splitlines():
            clean = line.strip()
            lower = clean.lower()
            if re.search(date_pattern, clean) or any(k in lower for k in ["deadline", "closing date", "submission", "valid until", "expiry"]):
                if clean not in results:
                    results.append(clean)

        return results[:20]

    def _basic_risks(self, text: str) -> List[str]:
        lower = text.lower()
        risks = []

        if "penalty" in lower or "liquidated damages" in lower:
            risks.append("Penalty or liquidated damages clause detected")
        if "warranty" in lower or "guarantee" in lower:
            risks.append("Warranty or guarantee obligation detected")
        if "deadline" in lower or "closing date" in lower:
            risks.append("Deadline-sensitive document")
        if "submit" in lower or "submission" in lower:
            risks.append("Submission requirements must be checked carefully")
        if "delivery" in lower and "payment" not in lower:
            risks.append("Delivery obligation detected but payment terms may be unclear")

        return risks

    def _missing_info(self, text: str) -> List[str]:
        lower = text.lower()
        missing = []

        checks = {
            "Payment terms not clearly detected": ["payment"],
            "Delivery terms not clearly detected": ["delivery"],
            "Deadline or closing date not clearly detected": ["deadline", "closing date", "submission date"],
            "Penalty terms not clearly detected": ["penalty", "liquidated damages"],
            "Warranty or guarantee terms not clearly detected": ["warranty", "guarantee"],
            "Required documents not clearly detected": ["required documents", "documents required", "certificate"],
        }

        for message, keywords in checks.items():
            if not any(keyword in lower for keyword in keywords):
                missing.append(message)

        return missing

    def _priority_level(self, text: str) -> str:
        lower = text.lower()

        critical_words = ["penalty", "liquidated damages", "bank guarantee", "performance bond"]
        high_words = ["deadline", "closing date", "submission", "warranty", "guarantee"]
        medium_words = ["delivery", "payment", "certificate", "technical"]

        if any(word in lower for word in critical_words):
            return "Critical"
        if any(word in lower for word in high_words):
            return "High"
        if any(word in lower for word in medium_words):
            return "Medium"
        return "Low"