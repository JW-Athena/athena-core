from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def write_file(relative_path: str, content: str) -> None:
    path = BASE_DIR / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")
    print(f"Updated: {path}")


ENTITY_INTELLIGENCE_ENGINE = r'''
import re
from typing import Dict, List, Optional


class EntityIntelligenceEngine:
    """
    Entity Intelligence Engine

    Converts document text into clean reusable business entities.
    """

    def extract(self, text: str, document_type: Optional[str] = None) -> Dict:
        clean_text = self._clean_text(text)

        return {
            "document_type": document_type or self._detect_document_type(clean_text),
            "entities": {
                "companies": self._extract_companies(clean_text),
                "products": self._extract_products(clean_text),
                "tenders": self._extract_tenders(clean_text),
                "certificates": self._extract_certificates(clean_text),
                "warranties": self._extract_warranties(clean_text),
                "payment_terms": self._extract_payment_terms(clean_text),
                "delivery_terms": self._extract_delivery_terms(clean_text),
                "penalties": self._extract_penalties(clean_text),
                "locations": self._extract_locations(clean_text),
                "deadlines": self._extract_deadlines(clean_text),
            },
            "relationships": self._build_relationships(clean_text),
            "executive_summary": self._executive_summary(clean_text),
            "confidence_score": 80,
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
        if "quotation" in lower or "quote" in lower:
            return "Quotation"
        if "purchase order" in lower:
            return "Purchase Order"
        if "invoice" in lower:
            return "Invoice"
        if "contract" in lower or "agreement" in lower:
            return "Contract"

        return "Unknown"

    def _extract_companies(self, text: str) -> List[Dict]:
        companies = []

        for line in text.splitlines():
            clean = line.strip()
            lower = clean.lower()

            if self._is_reference_line(lower):
                continue

            if lower.startswith("from:") or lower.startswith("to:"):
                companies.append({
                    "type": "company_or_party",
                    "value": clean.split(":", 1)[-1].strip(),
                    "source_line": clean,
                })
                continue

            government_keywords = [
                "ministry",
                "department",
                "authority",
                "police",
                "municipality",
                "armed forces",
                "civil defence",
                "civil defense",
            ]

            if any(k in lower for k in government_keywords):
                companies.append({
                    "type": "government_entity",
                    "value": clean,
                    "source_line": clean,
                })

        return self._deduplicate(companies)

    def _extract_products(self, text: str) -> List[Dict]:
        products = []

        for line in text.splitlines():
            clean = line.strip()
            lower = clean.lower()

            product_name = None
            category = None

            if "tactical boots" in lower:
                product_name = "Tactical Boots"
                category = "Footwear"
            elif "boots" in lower:
                product_name = "Boots"
                category = "Footwear"
            elif "shoes" in lower or "footwear" in lower:
                product_name = "Footwear"
                category = "Footwear"
            elif "fabric" in lower:
                product_name = "Fabric"
                category = "Fabric"
            elif "uniform" in lower:
                product_name = "Uniform"
                category = "Uniform / Accessories"
            elif "helmet" in lower:
                product_name = "Helmet"
                category = "Tactical Equipment"
            elif "vest" in lower:
                product_name = "Vest"
                category = "Tactical Equipment"

            if product_name:
                products.append({
                    "type": "product",
                    "value": product_name,
                    "category": category,
                    "quantity": self._extract_quantity(clean),
                    "source_line": clean,
                })

        return self._deduplicate(products)

    def _extract_tenders(self, text: str) -> List[Dict]:
        tenders = []
        patterns = [
            r"(Tender\s*(?:No|Number|#)?[:\-]?\s*[A-Z0-9\-\/]+)",
            r"(RFQ\s*(?:No|Number|#)?[:\-]?\s*[A-Z0-9\-\/]+)",
            r"(RFP\s*(?:No|Number|#)?[:\-]?\s*[A-Z0-9\-\/]+)",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text, flags=re.IGNORECASE)
            for match in matches:
                tenders.append({
                    "type": "tender_reference",
                    "value": match.strip(),
                    "source_line": match.strip(),
                })

        return self._deduplicate(tenders)

    def _extract_certificates(self, text: str) -> List[Dict]:
        certificates = []
        certificate_keywords = [
            "trade license",
            "vat certificate",
            "iso certificate",
            "iso",
            "test report",
            "technical compliance sheet",
            "certificate",
        ]

        for line in text.splitlines():
            clean = line.strip()
            lower = clean.lower()

            if any(keyword in lower for keyword in certificate_keywords):
                certificates.append({
                    "type": "certificate_or_required_document",
                    "value": clean.lstrip("-").strip(),
                    "source_line": clean,
                })

        return self._deduplicate(certificates)

    def _extract_warranties(self, text: str) -> List[Dict]:
        warranties = []

        for line in text.splitlines():
            clean = line.strip()
            lower = clean.lower()

            if any(k in lower for k in ["warranty", "guarantee", "defect", "replacement"]):
                warranties.append({
                    "type": "warranty",
                    "value": clean,
                    "years": self._extract_years(clean),
                    "coverage": "manufacturing defects" if "defect" in lower else None,
                    "source_line": clean,
                })

        return self._deduplicate(warranties)

    def _extract_payment_terms(self, text: str) -> List[Dict]:
        terms = []
        capture_next = False

        for line in text.splitlines():
            clean = line.strip()
            lower = clean.lower()

            if capture_next and clean:
                if not self._is_heading_only(lower):
                    terms.append({
                        "type": "payment_term",
                        "value": clean,
                        "days": self._extract_days(clean),
                        "trigger": "after delivery and acceptance" if "delivery and acceptance" in lower else None,
                        "source_line": clean,
                    })
                capture_next = False

            if any(k in lower for k in ["payment terms", "payment:", "invoice", "advance payment", "retention"]):
                if not self._is_heading_only(lower):
                    terms.append({
                        "type": "payment_term",
                        "value": clean,
                        "days": self._extract_days(clean),
                        "trigger": None,
                        "source_line": clean,
                    })
                capture_next = True

        return self._deduplicate(terms)

    def _extract_delivery_terms(self, text: str) -> List[Dict]:
        terms = []

        for line in text.splitlines():
            clean = line.strip()
            lower = clean.lower()

            if self._is_payment_context(lower):
                continue

            if any(k in lower for k in ["delivery terms", "delivery location", "deliver ", " shall deliver", "lead time"]):
                terms.append({
                    "type": "delivery_term",
                    "value": f"{self._extract_days(clean)} days" if self._extract_days(clean) else clean,
                    "days": self._extract_days(clean),
                    "source_line": clean,
                })

        return self._deduplicate(terms)

    def _extract_penalties(self, text: str) -> List[Dict]:
        penalties = []
        lines = [line.strip() for line in text.splitlines()]

        for index, clean in enumerate(lines):
            if not clean:
                continue

            lower = clean.lower()

            if any(k in lower for k in ["penalty", "liquidated damages", "fine", "liability"]):
                if not self._is_heading_only(lower):
                    penalties.append({
                        "type": "penalty",
                        "value": clean,
                        "percentage": self._extract_percentage(clean),
                        "frequency": "per week" if "week" in lower else None,
                        "source_line": clean,
                    })

                next_index = index + 1

                if next_index < len(lines):
                    next_line = lines[next_index].strip()
                    next_lower = next_line.lower()

                    if (
                        next_line
                        and not self._is_heading_only(next_lower)
                        and any(k in next_lower for k in ["penalty", "%", "delay", "damages", "fine"])
                    ):
                        penalties.append({
                            "type": "penalty",
                            "value": next_line,
                            "percentage": self._extract_percentage(next_line),
                            "frequency": "per week" if "week" in next_lower else None,
                            "source_line": next_line,
                        })

        return self._deduplicate(penalties)

    def _extract_locations(self, text: str) -> List[Dict]:
        locations = []
        known_locations = {
            "abu dhabi": "Abu Dhabi",
            "dubai": "Dubai",
            "sharjah": "Sharjah",
            "uae": "United Arab Emirates",
            "united arab emirates": "United Arab Emirates",
        }

        for line in text.splitlines():
            clean = line.strip()
            lower = clean.lower()

            for key, normalized in known_locations.items():
                if key in lower:
                    locations.append({
                        "type": "location",
                        "value": normalized,
                        "source_line": clean,
                    })

        return self._deduplicate(locations)

    def _extract_deadlines(self, text: str) -> List[Dict]:
        deadlines = []
        date_pattern = r"\b\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}\b|\b\d{4}[\/\-\.]\d{1,2}[\/\-\.]\d{1,2}\b"

        for line in text.splitlines():
            clean = line.strip()
            lower = clean.lower()

            if re.search(date_pattern, clean) or any(k in lower for k in ["deadline", "closing date", "submission date"]):
                deadlines.append({
                    "type": "deadline_or_date",
                    "value": clean,
                    "source_line": clean,
                })

        return self._deduplicate(deadlines)

    def _build_relationships(self, text: str) -> List[Dict]:
        relationships = []
        lower = text.lower()

        if "boots" in lower and ("warranty" in lower or "guarantee" in lower):
            relationships.append({
                "relationship": "product_has_warranty",
                "from": "Tactical Boots",
                "to": "Warranty / Guarantee",
            })

        if "boots" in lower and "deliver" in lower:
            relationships.append({
                "relationship": "product_has_delivery_obligation",
                "from": "Tactical Boots",
                "to": "Delivery Requirement",
            })

        if "penalty" in lower and "delivery" in lower:
            relationships.append({
                "relationship": "delivery_has_penalty_risk",
                "from": "Delivery Requirement",
                "to": "Penalty Clause",
            })

        if "certificate" in lower or "iso" in lower:
            relationships.append({
                "relationship": "document_requires_certificate",
                "from": "Tender / Document",
                "to": "Certificate Requirement",
            })

        return relationships

    def _executive_summary(self, text: str) -> str:
        lower = text.lower()
        parts = []

        if "tender" in lower:
            parts.append("Tender-related document detected.")
        if "boots" in lower or "footwear" in lower:
            parts.append("Footwear product requirement detected.")
        if "warranty" in lower or "guarantee" in lower:
            parts.append("Warranty obligation detected.")
        if "penalty" in lower:
            parts.append("Penalty exposure detected.")
        if "certificate" in lower or "iso" in lower:
            parts.append("Certificate or document requirement detected.")

        return " ".join(parts) if parts else "Business entities extracted from document."

    def _extract_quantity(self, value: str):
        match = re.search(r"\b\d{2,}\b", value)
        if match:
            return int(match.group(0))
        return None

    def _extract_days(self, value: str):
        match = re.search(r"\b(\d+)\s*days?\b", value, re.IGNORECASE)
        if match:
            return int(match.group(1))
        return None

    def _extract_years(self, value: str):
        match = re.search(r"\b(\d+)\s*years?\b|\b(\d+)\s*year\b", value, re.IGNORECASE)
        if match:
            return int(match.group(1) or match.group(2))
        return None

    def _extract_percentage(self, value: str):
        match = re.search(r"(\d+(?:\.\d+)?)\s*%", value)
        if match:
            return float(match.group(1))
        return None

    def _is_reference_line(self, lower_text: str) -> bool:
        return any(
            lower_text.startswith(prefix)
            for prefix in [
                "tender no",
                "tender number",
                "rfq no",
                "rfq number",
                "rfp no",
                "rfp number",
                "quotation no",
                "invoice no",
                "purchase order",
            ]
        )

    def _is_payment_context(self, lower_text: str) -> bool:
        return any(
            k in lower_text
            for k in [
                "payment terms",
                "payment:",
                "after delivery and acceptance",
                "invoice",
                "advance payment",
                "retention",
            ]
        )

    def _is_heading_only(self, lower_text: str) -> bool:
        stripped = lower_text.strip().rstrip(":")
        headings = {
            "payment terms",
            "penalty",
            "submission",
            "required documents",
            "technical specifications",
            "delivery terms",
            "warranty",
            "guarantee",
        }
        return stripped in headings

    def _deduplicate(self, items: List[Dict]) -> List[Dict]:
        seen = set()
        result = []

        for item in items:
            key = (
                item.get("type"),
                item.get("value"),
                item.get("source_line"),
            )

            if key not in seen:
                seen.add(key)
                result.append(item)

        return result
'''


def main():
    write_file("entity_intelligence_engine.py", ENTITY_INTELLIGENCE_ENGINE)
    print("Done.")


if __name__ == "__main__":
    main()