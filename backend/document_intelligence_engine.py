import re
from typing import Dict, List, Optional


class DocumentIntelligenceEngine:
    """
    Document Intelligence Engine

    Turns raw document text into structured document understanding.
    This is the foundation for large tender analysis.
    """

    def analyze(self, text: str, document_type: Optional[str] = None) -> Dict:
        clean_text = self._clean_text(text)
        sections = self._split_into_sections(clean_text)

        return {
            "document_type": document_type or self._detect_document_type(clean_text),
            "document_length_characters": len(clean_text),
            "section_count": len(sections),
            "sections": sections,
            "document_map": self._build_document_map(sections),
            "executive_summary": self._executive_summary(sections),
            "detected_requirements": self._detect_requirements(clean_text),
            "detected_risks": self._detect_risks(clean_text),
            "management_actions": self._management_actions(clean_text),
            "confidence_score": 75,
        }

    def _clean_text(self, text: str) -> str:
        text = text.replace("\x00", " ")
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

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

    def _split_into_sections(self, text: str) -> List[Dict]:
        raw_blocks = re.split(r"\n\s*\n", text)
        sections = []

        for block in raw_blocks:
            clean_block = block.strip()

            if len(clean_block) < 10:
                continue

            section_type = self._classify_section(clean_block)

            sections.append(
                {
                    "section_number": len(sections) + 1,
                    "section_type": section_type,
                    "title": self._section_title(clean_block),
                    "content": clean_block[:2000],
                    "important_terms": self._important_terms(clean_block),
                }
            )

        return sections

    def _section_title(self, text: str) -> str:
        first_line = text.splitlines()[0].strip()
        return first_line[:120]

    def _classify_section(self, text: str) -> str:
        lower = text.lower()
        first_line = text.splitlines()[0].strip().lower()

        if any(k in first_line for k in ["required documents", "documents required", "document requirements"]):
            return "Certificates / Documents"

        if any(k in first_line for k in ["certificates", "certificate requirements"]):
            return "Certificates / Documents"

        if any(k in lower for k in ["trade license", "vat certificate", "iso certificate", "test report"]):
            if "technical specifications" not in first_line:
                return "Certificates / Documents"

        if any(k in first_line for k in ["technical specifications", "technical specification", "specifications"]):
            return "Technical"

        if any(k in first_line for k in ["payment terms", "commercial terms"]):
            return "Commercial / Payment"

        if any(k in first_line for k in ["delivery terms", "delivery location", "lead time"]):
            return "Delivery"

        if any(k in first_line for k in ["warranty", "guarantee"]):
            return "Warranty / Guarantee"

        if any(k in first_line for k in ["penalty", "liquidated damages", "liability"]):
            return "Risk / Penalty"

        if any(k in first_line for k in ["submission", "closing date", "deadline"]):
            return "Submission"

        if any(k in lower for k in ["payment terms", "invoice", "advance", "retention"]):
            return "Commercial / Payment"

        if any(k in lower for k in ["delivery", "lead time", "deliver", "delivery location"]):
            return "Delivery"

        if any(k in lower for k in ["warranty", "guarantee", "defect", "replacement"]):
            return "Warranty / Guarantee"

        if any(k in lower for k in ["penalty", "liquidated damages", "liability", "fine"]):
            return "Risk / Penalty"

        if any(k in lower for k in ["certificate", "iso", "test report", "trade license", "vat"]):
            return "Certificates / Documents"

        if any(k in lower for k in ["technical", "specification", "material", "fabric", "leather", "sole", "standard"]):
            return "Technical"

        if any(k in lower for k in ["submission", "closing date", "deadline", "submit"]):
            return "Submission"

        return "General"

    def _important_terms(self, text: str) -> List[str]:
        terms = []

        keyword_groups = [
            "payment",
            "delivery",
            "warranty",
            "guarantee",
            "penalty",
            "deadline",
            "submission",
            "certificate",
            "technical",
            "specification",
            "invoice",
            "acceptance",
            "defect",
            "replacement",
            "iso",
            "vat",
            "trade license",
            "test report",
        ]

        lower = text.lower()

        for keyword in keyword_groups:
            if keyword in lower:
                terms.append(keyword)

        return terms

    def _build_document_map(self, sections: List[Dict]) -> Dict:
        document_map = {
            "commercial_sections": [],
            "technical_sections": [],
            "delivery_sections": [],
            "warranty_sections": [],
            "risk_sections": [],
            "submission_sections": [],
            "certificate_sections": [],
            "general_sections": [],
        }

        for section in sections:
            section_type = section.get("section_type")

            if section_type == "Commercial / Payment":
                document_map["commercial_sections"].append(section)
            elif section_type == "Technical":
                document_map["technical_sections"].append(section)
            elif section_type == "Delivery":
                document_map["delivery_sections"].append(section)
            elif section_type == "Warranty / Guarantee":
                document_map["warranty_sections"].append(section)
            elif section_type == "Risk / Penalty":
                document_map["risk_sections"].append(section)
            elif section_type == "Submission":
                document_map["submission_sections"].append(section)
            elif section_type == "Certificates / Documents":
                document_map["certificate_sections"].append(section)
            else:
                document_map["general_sections"].append(section)

        return document_map

    def _executive_summary(self, sections: List[Dict]) -> str:
        if not sections:
            return "No readable sections detected."

        section_types = {}

        for section in sections:
            section_type = section.get("section_type", "General")
            section_types[section_type] = section_types.get(section_type, 0) + 1

        parts = [f"Document contains {len(sections)} detected sections."]

        for section_type, count in section_types.items():
            parts.append(f"{count} section(s) classified as {section_type}.")

        return " ".join(parts)

    def _detect_requirements(self, text: str) -> Dict:
        lower = text.lower()

        return {
            "has_payment_terms": "payment" in lower,
            "has_delivery_terms": "delivery" in lower,
            "has_warranty_terms": "warranty" in lower or "guarantee" in lower,
            "has_penalty_terms": "penalty" in lower or "liquidated damages" in lower,
            "has_submission_requirements": "submission" in lower or "submit" in lower,
            "has_certificate_requirements": "certificate" in lower or "iso" in lower or "test report" in lower,
            "has_technical_specifications": "technical" in lower or "specification" in lower,
        }

    def _detect_risks(self, text: str) -> List[str]:
        lower = text.lower()
        risks = []

        if "penalty" in lower or "liquidated damages" in lower:
            risks.append("Penalty or liquidated damages risk detected")

        if "warranty" in lower or "guarantee" in lower:
            risks.append("Warranty or guarantee obligation detected")

        if "closing date" in lower or "deadline" in lower:
            risks.append("Deadline-sensitive document")

        if "delivery" in lower:
            risks.append("Delivery obligation must be verified")

        if "certificate" in lower or "iso" in lower:
            risks.append("Certificate or compliance requirement detected")

        return risks

    def _management_actions(self, text: str) -> List[str]:
        actions = [
            "Review document map section by section",
            "Confirm commercial terms",
            "Confirm delivery obligations",
            "Confirm technical compliance",
            "Confirm submission requirements",
        ]

        lower = text.lower()

        if "penalty" in lower:
            actions.append("Review penalty clause before approval")

        if "warranty" in lower or "guarantee" in lower:
            actions.append("Confirm warranty exposure with supplier")

        if "certificate" in lower or "iso" in lower:
            actions.append("Verify required certificates are available")

        return actions