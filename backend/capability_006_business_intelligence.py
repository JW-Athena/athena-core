import os
import re
import json
from typing import Any, Dict, List, Optional

try:
    from openai import OpenAI
except Exception:
    OpenAI = None


class BusinessIntelligenceEngine:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=self.api_key) if OpenAI and self.api_key else None

    def analyze(self, text: str, document_type: Optional[str] = None) -> Dict[str, Any]:
        clean_text = self._clean_text(text)

        if self.client:
            return self._analyze_with_ai(clean_text, document_type)

        return self._analyze_basic(clean_text, document_type)

    def _clean_text(self, text: str) -> str:
        text = text.replace("\x00", " ")
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def _analyze_with_ai(self, text: str, document_type: Optional[str]) -> Dict[str, Any]:
        prompt = f"""
You are ATHENA Capability 006: Business Intelligence Engine.

Your job is to produce an executive decision report from a tender, contract,
quotation, purchase order, invoice, or technical document.

Return ONLY valid JSON.

Required JSON format:
{{
  "document_type": "",
  "document_reference": "",
  "executive_title": "",
  "executive_summary": "",
  "should_bid_or_proceed": "Yes / No / Proceed with Caution / Not Applicable",
  "overall_recommendation": "",
  "overall_risk_level": "Low / Medium / High / Critical",
  "commercial_risk_level": "Low / Medium / High / Critical",
  "technical_risk_level": "Low / Medium / High / Critical",
  "compliance_risk_level": "Low / Medium / High / Critical",
  "delivery_risk_level": "Low / Medium / High / Critical",
  "payment_quality": "Poor / Acceptable / Good / Excellent / Unknown",
  "submission_readiness_percentage": 0,
  "missing_documents_count": 0,
  "missing_documents": [],
  "mandatory_certificates": [],
  "important_deadlines": [],
  "financial_exposure": "",
  "penalty_exposure": "",
  "warranty_exposure": "",
  "key_opportunities": [],
  "key_risks": [],
  "management_action_plan": [],
  "decision_summary_for_ceo": "",
  "confidence_score": 0
}}

Rules:
- Think like a CEO, COO, tender manager, and commercial manager.
- Do not invent information.
- If the document does not contain enough information, say so clearly.
- submission_readiness_percentage should estimate how ready the company is to act.
- should_bid_or_proceed must be practical.
- management_action_plan must contain numbered practical actions.
- decision_summary_for_ceo must be short, direct, and executive.
- confidence_score must be 0 to 100.

Document Type:
{document_type or "Unknown"}

Document Text:
{text[:16000]}
"""

        response = self.client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are ATHENA, an executive business intelligence engine for tenders, contracts, and commercial documents.",
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
                "document_reference": "",
                "executive_title": "Executive Decision Report",
                "executive_summary": raw,
                "should_bid_or_proceed": "Proceed with Caution",
                "overall_recommendation": "Manual review required because AI response was not valid JSON.",
                "overall_risk_level": "Medium",
                "commercial_risk_level": "Medium",
                "technical_risk_level": "Medium",
                "compliance_risk_level": "Medium",
                "delivery_risk_level": "Medium",
                "payment_quality": "Unknown",
                "submission_readiness_percentage": 50,
                "missing_documents_count": 0,
                "missing_documents": [],
                "mandatory_certificates": [],
                "important_deadlines": [],
                "financial_exposure": "",
                "penalty_exposure": "",
                "warranty_exposure": "",
                "key_opportunities": [],
                "key_risks": ["AI response was not valid JSON"],
                "management_action_plan": ["Review the document manually before making a decision"],
                "decision_summary_for_ceo": "Manual review required before decision.",
                "confidence_score": 50,
            }

    def _analyze_basic(self, text: str, document_type: Optional[str]) -> Dict[str, Any]:
        lower = text.lower()

        missing_documents = self._missing_documents(text)
        certificates = self._certificates(text)
        deadlines = self._deadlines(text)

        overall_risk = self._risk_level(text)
        readiness = self._readiness_score(text, missing_documents, deadlines)

        return {
            "document_type": document_type or self._detect_document_type(text),
            "document_reference": self._document_reference(text),
            "executive_title": "ATHENA Executive Decision Report",
            "executive_summary": self._summary(text),
            "should_bid_or_proceed": self._recommendation(overall_risk, readiness),
            "overall_recommendation": self._overall_recommendation(overall_risk, readiness),
            "overall_risk_level": overall_risk,
            "commercial_risk_level": self._commercial_risk(text),
            "technical_risk_level": self._technical_risk(text),
            "compliance_risk_level": self._compliance_risk(text),
            "delivery_risk_level": self._delivery_risk(text),
            "payment_quality": self._payment_quality(text),
            "submission_readiness_percentage": readiness,
            "missing_documents_count": len(missing_documents),
            "missing_documents": missing_documents,
            "mandatory_certificates": certificates,
            "important_deadlines": deadlines,
            "financial_exposure": self._financial_exposure(text),
            "penalty_exposure": self._penalty_exposure(text),
            "warranty_exposure": self._warranty_exposure(text),
            "key_opportunities": self._opportunities(text),
            "key_risks": self._risks(text),
            "management_action_plan": self._actions(text, missing_documents),
            "decision_summary_for_ceo": self._ceo_summary(overall_risk, readiness),
            "confidence_score": 65,
        }

    def _detect_document_type(self, text: str) -> str:
        lower = text.lower()
        if "tender" in lower:
            return "Tender"
        if "contract" in lower or "agreement" in lower:
            return "Contract"
        if "quotation" in lower or "quote" in lower:
            return "Quotation"
        if "purchase order" in lower:
            return "Purchase Order"
        if "invoice" in lower:
            return "Invoice"
        return "Unknown"

    def _document_reference(self, text: str) -> str:
        patterns = [
            r"(?:tender|quotation|quote|invoice|contract|po|purchase order)\s*(?:no|number|#)?[:\-]?\s*([A-Z0-9\-\/]+)",
            r"(?:ref|reference)\s*(?:no|number)?[:\-]?\s*([A-Z0-9\-\/]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return ""

    def _summary(self, text: str) -> str:
        lines = [line.strip() for line in text.splitlines() if len(line.strip()) > 25]
        return " ".join(lines[:5])[:1000]

    def _missing_documents(self, text: str) -> List[str]:
        lower = text.lower()
        expected = {
            "Trade license": ["trade license"],
            "VAT certificate": ["vat certificate", "tax registration"],
            "ISO certificate": ["iso certificate", "iso"],
            "Technical compliance sheet": ["technical compliance"],
            "Product test report": ["test report"],
            "Warranty letter": ["warranty"],
            "Bank guarantee or performance bond": ["bank guarantee", "performance bond"],
        }

        missing = []
        for doc, keywords in expected.items():
            if not any(k in lower for k in keywords):
                missing.append(doc)

        return missing

    def _certificates(self, text: str) -> List[str]:
        results = []
        for line in text.splitlines():
            clean = line.strip()
            lower = clean.lower()
            if any(k in lower for k in ["certificate", "iso", "compliance", "test report"]):
                results.append(clean)
        return results[:20]

    def _deadlines(self, text: str) -> List[str]:
        results = []
        date_pattern = r"\b\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}\b|\b\d{4}[\/\-\.]\d{1,2}[\/\-\.]\d{1,2}\b"

        for line in text.splitlines():
            clean = line.strip()
            lower = clean.lower()
            if re.search(date_pattern, clean) or any(k in lower for k in ["deadline", "closing date", "submission", "validity", "expiry"]):
                results.append(clean)

        return results[:20]

    def _risk_level(self, text: str) -> str:
        lower = text.lower()

        if any(k in lower for k in ["liquidated damages", "performance bond", "bank guarantee", "delay penalty"]):
            return "Critical"
        if any(k in lower for k in ["penalty", "warranty", "guarantee", "closing date", "deadline"]):
            return "High"
        if any(k in lower for k in ["delivery", "payment", "certificate", "submission"]):
            return "Medium"
        return "Low"

    def _commercial_risk(self, text: str) -> str:
        lower = text.lower()
        if any(k in lower for k in ["penalty", "liquidated damages", "bank guarantee", "performance bond"]):
            return "High"
        if any(k in lower for k in ["payment", "retention", "advance"]):
            return "Medium"
        return "Low"

    def _technical_risk(self, text: str) -> str:
        lower = text.lower()
        if any(k in lower for k in ["technical specification", "test report", "compliance", "standard"]):
            return "Medium"
        return "Low"

    def _compliance_risk(self, text: str) -> str:
        lower = text.lower()
        if any(k in lower for k in ["required documents", "certificate", "submit", "submission"]):
            return "Medium"
        return "Low"

    def _delivery_risk(self, text: str) -> str:
        lower = text.lower()
        if any(k in lower for k in ["within 30 days", "urgent", "immediate"]):
            return "High"
        if any(k in lower for k in ["delivery", "lead time", "within 60 days"]):
            return "Medium"
        return "Low"

    def _payment_quality(self, text: str) -> str:
        lower = text.lower()
        if "advance payment" in lower:
            return "Excellent"
        if "30 days" in lower and "payment" in lower:
            return "Good"
        if "60 days" in lower and "payment" in lower:
            return "Acceptable"
        if "90 days" in lower and "payment" in lower:
            return "Poor"
        return "Unknown"

    def _readiness_score(self, text: str, missing_documents: List[str], deadlines: List[str]) -> int:
        score = 85

        score -= min(len(missing_documents) * 7, 35)

        lower = text.lower()
        if "penalty" in lower:
            score -= 10
        if "bank guarantee" in lower or "performance bond" in lower:
            score -= 10
        if not deadlines:
            score -= 10
        if "payment" not in lower:
            score -= 10
        if "delivery" not in lower:
            score -= 10

        return max(0, min(score, 100))

    def _recommendation(self, risk: str, readiness: int) -> str:
        if risk == "Critical" and readiness < 60:
            return "Proceed with Caution"
        if readiness >= 75:
            return "Yes"
        if readiness >= 50:
            return "Proceed with Caution"
        return "No"

    def _overall_recommendation(self, risk: str, readiness: int) -> str:
        if readiness >= 75 and risk in ["Low", "Medium"]:
            return "Proceed. Document appears commercially and operationally acceptable."
        if readiness >= 60:
            return "Proceed with caution after resolving missing documents and risk items."
        return "Do not proceed until missing information and commercial risks are resolved."

    def _financial_exposure(self, text: str) -> str:
        amounts = re.findall(r"(?:AED|USD|EUR|SAR|\$|€)?\s?\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?", text, re.IGNORECASE)
        return amounts[-1] if amounts else ""

    def _penalty_exposure(self, text: str) -> str:
        for line in text.splitlines():
            if any(k in line.lower() for k in ["penalty", "liquidated damages", "delay damages"]):
                return line.strip()
        return ""

    def _warranty_exposure(self, text: str) -> str:
        for line in text.splitlines():
            if any(k in line.lower() for k in ["warranty", "guarantee"]):
                return line.strip()
        return ""

    def _opportunities(self, text: str) -> List[str]:
        opportunities = []
        lower = text.lower()

        if "payment" in lower:
            opportunities.append("Payment terms are available for review")
        if "delivery" in lower:
            opportunities.append("Delivery scope is identifiable")
        if "technical" in lower or "specification" in lower:
            opportunities.append("Technical requirements can be checked against company capability")
        if "warranty" in lower:
            opportunities.append("Warranty can be priced into the offer")

        return opportunities

    def _risks(self, text: str) -> List[str]:
        risks = []
        lower = text.lower()

        if "penalty" in lower:
            risks.append("Penalty clause detected")
        if "warranty" in lower or "guarantee" in lower:
            risks.append("Warranty or guarantee exposure detected")
        if "submission" in lower or "closing date" in lower:
            risks.append("Submission deadline must be managed carefully")
        if "certificate" in lower:
            risks.append("Certificate requirements must be verified")
        if "delivery" in lower:
            risks.append("Delivery capability must be confirmed")

        return risks

    def _actions(self, text: str, missing_documents: List[str]) -> List[str]:
        actions = [
            "Review executive summary and confirm bid interest",
            "Assign responsible manager for tender submission",
            "Verify delivery timeline with operations or supplier",
            "Review payment terms and commercial exposure",
            "Review penalties, warranty, and guarantee obligations",
        ]

        for doc in missing_documents[:5]:
            actions.append(f"Confirm availability of {doc}")

        return actions

    def _ceo_summary(self, risk: str, readiness: int) -> str:
        return f"ATHENA assessment: readiness is {readiness}%, overall risk is {risk}. Management should proceed only after reviewing missing documents, penalties, delivery capability, and payment terms."