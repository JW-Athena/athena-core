import re
from typing import Dict, List, Optional


class EntityIntelligenceEngine:
    """
    Entity Intelligence Engine

    Converts document text into reusable business entities.
    This is the first step toward ATHENA's company knowledge graph.
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
                companies.append(
                    {
                        "type": "company_or_party",
                        "value": clean,
                        "source_line": clean,
                    }
                )
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
                companies.append(
                    {
                        "type": "government_entity",
                        "value": clean,
                        "source_line": clean,
                    }
                )

        return self._deduplicate(companies)

    def _extract_products(self, text: str) -> List[Dict]:
        products = []
        product_keywords = [
            "boots",
            "shoes",
            "footwear",
            "fabric",
            "uniform",
            "shirt",
            "trousers",
            "cap",
            "belt",
            "helmet",
            "vest",
        ]

        for line in text.splitlines():
            clean = line.strip()
            lower = clean.lower()

            if any(keyword in lower for keyword in product_keywords):
                products.append(
                    {
                        "type": "product",
                        "value": clean,
                        "category": self._product_category(lower),
                        "source_line": clean,
                    }
                )

        return self._deduplicate(products)

    def _product_category(self, lower_text: str) -> str:
        if any(k in lower_text for k in ["boots", "shoes", "footwear"]):
            return "Footwear"
        if any(k in lower_text for k in ["fabric", "textile"]):
            return "Fabric"
        if any(k in lower_text for k in ["uniform", "shirt", "trousers", "cap", "belt"]):
            return "Uniform / Accessories"
        if any(k in lower_text for k in ["helmet", "vest"]):
            return "Tactical Equipment"
        return "General Product"

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
                tenders.append(
                    {
                        "type": "tender_reference",
                        "value": match.strip(),
                        "source_line": match.strip(),
                    }
                )

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
                certificates.append(
                    {
                        "type": "certificate_or_required_document",
                        "value": clean,
                        "source_line": clean,
                    }
                )

        return self._deduplicate(certificates)

    def _extract_warranties(self, text: str) -> List[Dict]:
        warranties = []

        for line in text.splitlines():
            clean = line.strip()
            lower = clean.lower()

            if any(k in lower for k in ["warranty", "guarantee", "defect", "replacement"]):
                warranties.append(
                    {
                        "type": "warranty",
                        "value": clean,
                        "source_line": clean,
                    }
                )

        return self._deduplicate(warranties)

    def _extract_payment_terms(self, text: str) -> List[Dict]:
        terms = []
        capture_next = False

        for line in text.splitlines():
            clean = line.strip()
            lower = clean.lower()

            if capture_next and clean:
                if not self._is_heading_only(lower):
                    terms.append(
                        {
                            "type": "payment_term",
                            "value": clean,
                            "source_line": clean,
                        }
                    )
                capture_next = False

            if any(
                k in lower
                for k in [
                    "payment terms",
                    "payment:",
                    "invoice",
                    "advance payment",
                    "retention",
                ]
            ):
                terms.append(
                    {
                        "type": "payment_term",
                        "value": clean,
                        "source_line": clean,
                    }
                )
                capture_next = True

        return self._deduplicate(terms)

    def _extract_delivery_terms(self, text: str) -> List[Dict]:
        terms = []

        for line in text.splitlines():
            clean = line.strip()
            lower = clean.lower()

            if self._is_payment_context(lower):
                continue

            if any(
                k in lower
                for k in [
                    "delivery terms",
                    "delivery location",
                    "deliver ",
                    " shall deliver",
                    "lead time",
                ]
            ):
                terms.append(
                    {
                        "type": "delivery_term",
                        "value": clean,
                        "source_line": clean,
                    }
                )

        return self._deduplicate(terms)

    def _extract_penalties(self, text: str) -> List[Dict]:
        penalties = []
        lines = [line.strip() for line in text.splitlines()]

        for index, clean in enumerate(lines):
            if not clean:
                continue

            lower = clean.lower()

            if any(k in lower for k in ["penalty", "liquidated damages", "fine", "liability"]):
                penalties.append(
                    {
                        "type": "penalty",
                        "value": clean,
                        "source_line": clean,
                    }
                )

                next_index = index + 1

                if next_index < len(lines):
                    next_line = lines[next_index].strip()
                    next_lower = next_line.lower()

                    if (
                        next_line
                        and not self._is_heading_only(next_lower)
                        and any(k in next_lower for k in ["penalty", "%", "delay", "damages", "fine"])
                    ):
                        penalties.append(
                            {
                                "type": "penalty",
                                "value": next_line,
                                "source_line": next_line,
                            }
                        )

        return self._deduplicate(penalties)

    def _extract_locations(self, text: str) -> List[Dict]:
        locations = []
        known_locations = [
            "abu dhabi",
            "dubai",
            "sharjah",
            "uae",
            "united arab emirates",
        ]

        for line in text.splitlines():
            clean = line.strip()
            lower = clean.lower()

            if any(location in lower for location in known_locations):
                locations.append(
                    {
                        "type": "location",
                        "value": clean,
                        "source_line": clean,
                    }
                )

        return self._deduplicate(locations)

    def _extract_deadlines(self, text: str) -> List[Dict]:
        deadlines = []
        date_pattern = r"\b\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}\b|\b\d{4}[\/\-\.]\d{1,2}[\/\-\.]\d{1,2}\b"

        for line in text.splitlines():
            clean = line.strip()
            lower = clean.lower()

            if re.search(date_pattern, clean) or any(
                k in lower for k in ["deadline", "closing date", "submission date"]
            ):
                deadlines.append(
                    {
                        "type": "deadline_or_date",
                        "value": clean,
                        "source_line": clean,
                    }
                )

        return self._deduplicate(deadlines)

    def _build_relationships(self, text: str) -> List[Dict]:
        relationships = []
        lower = text.lower()

        if "boots" in lower and ("warranty" in lower or "guarantee" in lower):
            relationships.append(
                {
                    "relationship": "product_has_warranty",
                    "from": "Tactical Boots / Footwear",
                    "to": "Warranty / Guarantee",
                }
            )

        if "boots" in lower and "deliver" in lower:
            relationships.append(
                {
                    "relationship": "product_has_delivery_obligation",
                    "from": "Tactical Boots / Footwear",
                    "to": "Delivery Requirement",
                }
            )

        if "penalty" in lower and "delivery" in lower:
            relationships.append(
                {
                    "relationship": "delivery_has_penalty_risk",
                    "from": "Delivery Requirement",
                    "to": "Penalty Clause",
                }
            )

        if "certificate" in lower or "iso" in lower:
            relationships.append(
                {
                    "relationship": "document_requires_certificate",
                    "from": "Tender / Document",
                    "to": "Certificate Requirement",
                }
            )

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