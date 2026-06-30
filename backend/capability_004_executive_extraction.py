import os
import re
import json
from typing import Any, Dict, List, Optional


try:
    from openai import OpenAI
except Exception:
    OpenAI = None


class ExecutiveInformationExtractor:
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
You are ATHENA Executive Information Extraction Engine.

Extract executive business information from this document.

Document Type:
{document_type or "Unknown"}

Return ONLY valid JSON.

Required JSON format:
{{
  "document_type": "",
  "executive_summary": "",
  "supplier_or_sender": "",
  "customer_or_receiver": "",
  "document_number": "",
  "document_date": "",
  "expiry_or_validity_date": "",
  "currency": "",
  "subtotal": "",
  "vat_amount": "",
  "total_amount": "",
  "payment_terms": "",
  "delivery_terms": "",
  "delivery_location": "",
  "important_deadlines": [],
  "key_items": [
    {{
      "description": "",
      "quantity": "",
      "unit_price": "",
      "total_price": ""
    }}
  ],
  "risks_or_missing_information": [],
  "required_actions": [],
  "confidence_score": 0
}}

Rules:
- Be accurate.
- Do not invent information.
- If information is missing, use empty string or empty list.
- risks_or_missing_information should include missing price, missing date, unclear payment terms, unclear delivery, missing signature, missing stamp, unclear scope, or deadline risk.
- required_actions should be practical executive actions.
- confidence_score must be from 0 to 100.

Document text:
{text[:12000]}
"""

        response = self.client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": "You extract structured executive business information from documents."},
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
                "supplier_or_sender": "",
                "customer_or_receiver": "",
                "document_number": "",
                "document_date": "",
                "expiry_or_validity_date": "",
                "currency": "",
                "subtotal": "",
                "vat_amount": "",
                "total_amount": "",
                "payment_terms": "",
                "delivery_terms": "",
                "delivery_location": "",
                "important_deadlines": [],
                "key_items": [],
                "risks_or_missing_information": ["AI returned unclean JSON"],
                "required_actions": ["Review extracted summary manually"],
                "confidence_score": 50,
            }

    def _extract_basic(self, text: str, document_type: Optional[str]) -> Dict[str, Any]:
        currency = self._detect_currency(text)
        amounts = self._extract_amounts(text)

        return {
            "document_type": document_type or self._detect_document_type(text),
            "executive_summary": self._basic_summary(text),
            "supplier_or_sender": self._find_party(text, ["supplier", "vendor", "from", "seller"]),
            "customer_or_receiver": self._find_party(text, ["customer", "client", "to", "buyer"]),
            "document_number": self._find_document_number(text),
            "document_date": self._find_date(text),
            "expiry_or_validity_date": self._find_validity_date(text),
            "currency": currency,
            "subtotal": "",
            "vat_amount": self._find_vat(text),
            "total_amount": amounts[-1] if amounts else "",
            "payment_terms": self._find_line_containing(text, ["payment terms", "payment", "terms of payment"]),
            "delivery_terms": self._find_line_containing(text, ["delivery terms", "delivery", "lead time"]),
            "delivery_location": self._find_line_containing(text, ["delivery location", "location", "deliver to"]),
            "important_deadlines": self._extract_deadlines(text),
            "key_items": [],
            "risks_or_missing_information": self._basic_risks(text, amounts),
            "required_actions": [
                "Review extracted values",
                "Confirm total amount and currency",
                "Confirm payment and delivery terms",
            ],
            "confidence_score": 60,
        }

    def _detect_document_type(self, text: str) -> str:
        lower = text.lower()
        if "quotation" in lower or "quote" in lower:
            return "Quotation"
        if "tender" in lower:
            return "Tender"
        if "invoice" in lower:
            return "Invoice"
        if "purchase order" in lower or " po " in lower:
            return "Purchase Order"
        return "Unknown"

    def _detect_currency(self, text: str) -> str:
        lower = text.lower()
        if "aed" in lower or "dirham" in lower:
            return "AED"
        if "usd" in lower or "$" in text:
            return "USD"
        if "eur" in lower or "€" in text:
            return "EUR"
        if "sar" in lower:
            return "SAR"
        return ""

    def _extract_amounts(self, text: str) -> List[str]:
        pattern = r"(?:AED|USD|EUR|SAR|\$|€)?\s?\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?"
        return re.findall(pattern, text, flags=re.IGNORECASE)

    def _find_document_number(self, text: str) -> str:
        patterns = [
            r"(?:quotation|quote|invoice|tender|po|purchase order)\s*(?:no|number|#)?[:\-]?\s*([A-Z0-9\-\/]+)",
            r"(?:ref|reference)\s*(?:no|number)?[:\-]?\s*([A-Z0-9\-\/]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return ""

    def _find_date(self, text: str) -> str:
        patterns = [
            r"\b\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}\b",
            r"\b\d{4}[\/\-\.]\d{1,2}[\/\-\.]\d{1,2}\b",
            r"\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}\b",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)
        return ""

    def _find_validity_date(self, text: str) -> str:
        line = self._find_line_containing(text, ["validity", "valid until", "expiry", "expires"])
        return self._find_date(line) if line else ""

    def _find_vat(self, text: str) -> str:
        lines = text.splitlines()
        for line in lines:
            if "vat" in line.lower() or "tax" in line.lower():
                amounts = self._extract_amounts(line)
                if amounts:
                    return amounts[-1]
        return ""

    def _extract_deadlines(self, text: str) -> List[str]:
        deadlines = []
        for line in text.splitlines():
            lower = line.lower()
            if any(k in lower for k in ["deadline", "closing date", "submission", "valid until", "expiry"]):
                deadlines.append(line.strip())
        return deadlines[:10]

    def _find_party(self, text: str, keywords: List[str]) -> str:
        for line in text.splitlines():
            lower = line.lower()
            if any(k in lower for k in keywords):
                cleaned = line.strip()
                if 3 <= len(cleaned) <= 150:
                    return cleaned
        return ""

    def _find_line_containing(self, text: str, keywords: List[str]) -> str:
        for line in text.splitlines():
            lower = line.lower()
            if any(k in lower for k in keywords):
                return line.strip()
        return ""

    def _basic_summary(self, text: str) -> str:
        lines = [line.strip() for line in text.splitlines() if len(line.strip()) > 20]
        return " ".join(lines[:3])[:700]

    def _basic_risks(self, text: str, amounts: List[str]) -> List[str]:
        risks = []
        lower = text.lower()

        if not amounts:
            risks.append("No clear amount detected")
        if "payment" not in lower:
            risks.append("Payment terms not clearly detected")
        if "delivery" not in lower:
            risks.append("Delivery terms not clearly detected")
        if "signature" not in lower and "signed" not in lower:
            risks.append("Signature not clearly detected")
        if "stamp" not in lower and "seal" not in lower:
            risks.append("Company stamp not clearly detected")

        return risks