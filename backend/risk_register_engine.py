from typing import Any, Dict, List, Optional

from capability_005_obligation_extraction import ObligationExtractor
from capability_006_business_intelligence import BusinessIntelligenceEngine
from document_intelligence_engine import DocumentIntelligenceEngine
from entity_intelligence_engine import EntityIntelligenceEngine
from executive_decision_brief_engine import ExecutiveDecisionBriefEngine
from timing_utils import cached_step, new_request_context, timed_step


class RiskRegisterEngine:
    """
    Risk Register Intelligence

    Builds an executive risk register from existing ATHENA intelligence outputs.
    It does not duplicate document extraction logic.
    """

    def __init__(self):
        self.brief_engine = ExecutiveDecisionBriefEngine()
        self.business_engine = BusinessIntelligenceEngine()
        self.obligation_engine = ObligationExtractor()
        self.document_engine = DocumentIntelligenceEngine()
        self.entity_engine = EntityIntelligenceEngine()

    def generate(
        self,
        text: str,
        document_type: Optional[str] = None,
        request_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        request_context = new_request_context(request_context)

        return cached_step(
            request_context=request_context,
            cache_key="risk_register.generate",
            engine="risk_register",
            step="generate",
            callback=lambda: self._generate_uncached(
                text=text,
                document_type=document_type,
                request_context=request_context,
            ),
        )

    def _generate_uncached(
        self,
        text: str,
        document_type: Optional[str],
        request_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        brief_result = self.brief_engine.generate(
            text=text,
            document_type=document_type,
            request_context=request_context,
        )
        source = brief_result.get("source_intelligence", {})
        business = source.get("business_intelligence") or cached_step(
            request_context=request_context,
            cache_key="business_intelligence.analyze",
            engine="business_intelligence",
            step="analyze",
            callback=lambda: self.business_engine.analyze(
                text=text,
                document_type=document_type,
            ),
        )
        obligations = source.get("obligation_extraction") or cached_step(
            request_context=request_context,
            cache_key="obligation_extraction.extract",
            engine="obligation_extraction",
            step="extract",
            callback=lambda: self.obligation_engine.extract(
                text=text,
                document_type=document_type,
            ),
        )
        document = cached_step(
            request_context=request_context,
            cache_key="document_intelligence.analyze",
            engine="document_intelligence",
            step="analyze",
            callback=lambda: self.document_engine.analyze(
                text=text,
                document_type=document_type,
            ),
        )
        entities = cached_step(
            request_context=request_context,
            cache_key="entity_intelligence.extract",
            engine="entity_intelligence",
            step="extract",
            callback=lambda: self.entity_engine.extract(
                text=text,
                document_type=document_type,
            ),
        )

        risks = []
        brief = brief_result.get("brief", {})

        self._add_business_risks(risks, business)
        self._add_obligation_risks(risks, obligations)
        self._add_document_risks(risks, document)
        self._add_brief_risks(risks, brief)
        self._add_entity_risks(risks, entities)

        risks = self._consolidate_risks(risks)
        risks = self._sort_risks(risks)[:15]

        for index, risk in enumerate(risks, start=1):
            risk["id"] = f"RISK-{index:03d}"

        counts = self._severity_counts(risks)

        result = {
            "engine": "risk_register",
            "name": "Risk Register Intelligence",
            "status": "success",
            "risk_register": {
                "overall_risk_level": self._overall_risk_level(risks),
                "total_risks": len(risks),
                "high_risks": counts["high"],
                "medium_risks": counts["medium"],
                "low_risks": counts["low"],
                "risks": risks,
            },
        }
        timed_step(
            request_context=request_context,
            engine="risk_register",
            step="assemble",
            callback=lambda: None,
        )
        return result

    def _add_business_risks(self, risks: List[Dict], business: Dict[str, Any]) -> None:
        for item in business.get("key_risks", []):
            self._add_risk(
                risks=risks,
                category=self._category_for_text(item),
                title=self._title_from_text(item),
                description=str(item),
                severity=self._severity_from_text(
                    item,
                    default=business.get("overall_risk_level", "Medium"),
                ),
                probability="Medium",
                impact=self._impact_from_severity(
                    business.get("overall_risk_level", "Medium")
                ),
                mitigation=self._mitigation_for_text(item),
                source="Business Intelligence Engine",
            )

        exposure_map = [
            ("Commercial", "Commercial risk level", business.get("commercial_risk_level")),
            ("Financial", "Financial exposure", business.get("financial_exposure")),
            ("Delivery", "Delivery risk level", business.get("delivery_risk_level")),
            ("Compliance", "Compliance risk level", business.get("compliance_risk_level")),
            ("Warranty", "Warranty exposure", business.get("warranty_exposure")),
            ("Legal", "Penalty exposure", business.get("penalty_exposure")),
        ]

        for category, title, value in exposure_map:
            if value and str(value).lower() not in ["low", ""]:
                severity = self._severity_from_text(value, default="Medium")
                self._add_risk(
                    risks=risks,
                    category=category,
                    title=title,
                    description=str(value),
                    severity=severity,
                    probability="Medium",
                    impact=self._impact_from_severity(severity),
                    mitigation=self._mitigation_for_text(f"{title}: {value}"),
                    source="Business Intelligence Engine",
                )

    def _add_obligation_risks(self, risks: List[Dict], obligations: Dict[str, Any]) -> None:
        risk_fields = [
            ("Commercial", "Commercial risk", obligations.get("commercial_risks", [])),
            ("Legal", "Penalty or liability", obligations.get("penalties_or_liabilities", [])),
            ("Warranty", "Warranty or guarantee obligation", obligations.get("warranty_or_guarantee_terms", [])),
            ("Compliance", "Missing or unclear information", obligations.get("missing_or_unclear_information", [])),
            ("Delivery", "Delivery obligation", obligations.get("delivery_obligations", [])),
        ]

        priority = obligations.get("priority_level", "Medium")

        for category, title, items in risk_fields:
            for item in items or []:
                severity = self._severity_from_text(item, default=priority)
                self._add_risk(
                    risks=risks,
                    category=category,
                    title=title,
                    description=str(item),
                    severity=severity,
                    probability=self._probability_for_text(item),
                    impact=self._impact_from_severity(severity),
                    mitigation=self._mitigation_for_text(item),
                    source="Obligation Extraction",
                )

    def _add_document_risks(self, risks: List[Dict], document: Dict[str, Any]) -> None:
        for item in document.get("detected_risks", []):
            severity = self._severity_from_text(item, default="Medium")
            self._add_risk(
                risks=risks,
                category=self._category_for_text(item),
                title=self._title_from_text(item),
                description=str(item),
                severity=severity,
                probability=self._probability_for_text(item),
                impact=self._impact_from_severity(severity),
                mitigation=self._mitigation_for_text(item),
                source="Document Intelligence Engine",
            )

    def _add_brief_risks(self, risks: List[Dict], brief: Dict[str, Any]) -> None:
        for item in brief.get("key_risks", []):
            severity = self._severity_from_text(item, default="Medium")
            self._add_risk(
                risks=risks,
                category=self._category_for_text(item),
                title=self._title_from_text(item),
                description=str(item),
                severity=severity,
                probability=self._probability_for_text(item),
                impact=self._impact_from_severity(severity),
                mitigation=self._mitigation_for_text(item),
                source="Executive Decision Brief Engine",
            )

        for item in brief.get("missing_information", []):
            self._add_risk(
                risks=risks,
                category="Compliance",
                title="Missing information",
                description=str(item),
                severity="High",
                probability="High",
                impact="High",
                mitigation="Resolve the missing information before executive approval.",
                source="Executive Decision Brief Engine",
            )

    def _add_entity_risks(self, risks: List[Dict], entities: Dict[str, Any]) -> None:
        entity_groups = entities.get("entities", {})

        for item in entity_groups.get("penalties", []):
            self._add_risk(
                risks=risks,
                category="Legal",
                title="Penalty exposure",
                description=str(item.get("value", "")),
                severity="High",
                probability="Medium",
                impact="High",
                mitigation="Review penalty clause, delivery capability, and commercial pricing before commitment.",
                source="Entity Intelligence Engine",
            )

        for item in entity_groups.get("warranties", []):
            self._add_risk(
                risks=risks,
                category="Warranty",
                title="Warranty exposure",
                description=str(item.get("value", "")),
                severity="Medium",
                probability="Medium",
                impact="Medium",
                mitigation="Confirm warranty responsibility, cost, supplier back-to-back support, and defect handling.",
                source="Entity Intelligence Engine",
            )

        for item in entity_groups.get("certificates", []):
            self._add_risk(
                risks=risks,
                category="Compliance",
                title="Certificate requirement",
                description=str(item.get("value", "")),
                severity="Medium",
                probability="Medium",
                impact="High",
                mitigation="Verify certificate availability and validity before submission.",
                source="Entity Intelligence Engine",
            )

    def _add_risk(
        self,
        risks: List[Dict],
        category: str,
        title: str,
        description: str,
        severity: str,
        probability: str,
        impact: str,
        mitigation: str,
        source: str,
    ) -> None:
        if not description:
            return

        risks.append(
            {
                "id": "",
                "category": category,
                "title": title,
                "description": description,
                "executive_explanation": self._executive_explanation(
                    category=category,
                    severity=severity,
                    description=description,
                ),
                "severity": self._normalize_level(severity, default="Medium"),
                "probability": self._normalize_level(probability, default="Medium"),
                "impact": self._normalize_level(impact, default="Medium"),
                "mitigation": mitigation,
                "source": source,
            }
        )

    def _category_for_text(self, value: Any) -> str:
        text = str(value).lower()

        if any(word in text for word in ["payment", "price", "amount", "commercial"]):
            return "Commercial"
        if any(word in text for word in ["financial", "bank guarantee", "performance bond", "vat"]):
            return "Financial"
        if any(word in text for word in ["delivery", "deadline", "closing date", "lead time"]):
            return "Delivery"
        if any(word in text for word in ["warranty", "guarantee", "defect", "replacement"]):
            return "Warranty"
        if any(word in text for word in ["certificate", "document", "submission", "compliance", "iso"]):
            return "Compliance"
        if any(word in text for word in ["penalty", "liability", "damages", "fine"]):
            return "Legal"

        return "Operational"

    def _title_from_text(self, value: Any) -> str:
        text = str(value).strip()
        if not text:
            return "Business risk"
        return text[:80]

    def _severity_from_text(self, value: Any, default: str = "Medium") -> str:
        text = str(value).lower()

        if any(word in text for word in ["critical", "liquidated damages", "bank guarantee", "performance bond"]):
            return "Critical"
        if any(word in text for word in ["high", "penalty", "liability", "missing", "deadline", "closing date"]):
            return "High"
        if any(word in text for word in ["medium", "warranty", "certificate", "delivery", "payment"]):
            return "Medium"
        if "low" in text:
            return "Low"

        return self._normalize_level(default, default="Medium")

    def _probability_for_text(self, value: Any) -> str:
        text = str(value).lower()

        if any(word in text for word in ["missing", "detected", "required", "must", "shall"]):
            return "High"
        if any(word in text for word in ["may", "unclear", "review", "confirm"]):
            return "Medium"

        return "Medium"

    def _impact_from_severity(self, severity: str) -> str:
        severity = self._normalize_level(severity, default="Medium")

        if severity in ["Critical", "High"]:
            return "High"
        if severity == "Medium":
            return "Medium"
        return "Low"

    def _mitigation_for_text(self, value: Any) -> str:
        text = str(value).lower()

        if any(word in text for word in ["penalty", "liability", "damages", "fine"]):
            return "Review legal and commercial exposure before approval; price or negotiate the clause."
        if any(word in text for word in ["payment", "price", "amount"]):
            return "Confirm commercial terms, payment timing, currency, and total exposure before decision."
        if any(word in text for word in ["delivery", "deadline", "closing date", "lead time"]):
            return "Confirm delivery capability, timeline ownership, and submission deadline responsibility."
        if any(word in text for word in ["warranty", "guarantee", "defect", "replacement"]):
            return "Confirm warranty duration, supplier support, and replacement cost responsibility."
        if any(word in text for word in ["certificate", "document", "submission", "compliance", "iso"]):
            return "Verify required documents and certificates are available before submission."

        return "Assign an owner to review and close this risk before executive approval."

    def _executive_explanation(self, category: str, severity: str, description: str) -> str:
        return (
            f"{category} risk rated {self._normalize_level(severity, default='Medium')}: "
            f"{description}"
        )

    def _normalize_level(self, value: Any, default: str) -> str:
        text = str(value).strip().lower()

        if text == "critical":
            return "Critical"
        if text == "high":
            return "High"
        if text == "medium":
            return "Medium"
        if text == "low":
            return "Low"

        return default

    def _deduplicate_risks(self, risks: List[Dict]) -> List[Dict]:
        deduplicated = []
        seen = set()

        for risk in risks:
            key = (
                risk.get("category"),
                risk.get("title"),
                risk.get("description"),
                risk.get("source"),
            )

            if key in seen:
                continue

            seen.add(key)
            deduplicated.append(risk)

        return deduplicated

    def _consolidate_risks(self, risks: List[Dict]) -> List[Dict]:
        grouped: Dict[str, List[Dict]] = {}

        for risk in self._deduplicate_risks(risks):
            group_key = self._risk_group_key(risk)
            grouped.setdefault(group_key, []).append(risk)

        consolidated = []

        for group_key, group in grouped.items():
            primary = self._primary_risk_for_group(group_key, group)
            mitigations = self._merge_text_values(
                risk.get("mitigation")
                for risk in group
            )
            explanations = self._merge_text_values(
                risk.get("executive_explanation")
                for risk in group
            )
            sources = self._merge_text_values(
                risk.get("source")
                for risk in group
            )
            descriptions = self._merge_text_values(
                risk.get("description")
                for risk in group
            )

            primary["description"] = self._executive_description(
                group_key=group_key,
                descriptions=descriptions,
                fallback=primary.get("description", ""),
            )
            primary["severity"] = self._highest_severity(group)
            primary["probability"] = self._highest_probability(group)
            primary["impact"] = self._highest_impact(group)
            primary["mitigation"] = "; ".join(mitigations)
            primary["executive_explanation"] = "; ".join(explanations)
            primary["source"] = ", ".join(sources)

            consolidated.append(primary)

        return consolidated

    def _risk_group_key(self, risk: Dict) -> str:
        text = " ".join(
            str(risk.get(field, "")).lower()
            for field in ["category", "title", "description"]
        )

        if any(word in text for word in ["supplier", "vendor"]):
            return "missing_supplier_information"
        if any(word in text for word in ["customer", "client", "buyer"]):
            return "missing_customer_information"
        if any(word in text for word in ["price", "pricing", "amount", "financial exposure", "currency"]):
            return "missing_commercial_information"
        if any(word in text for word in ["signature", "signed", "stamp", "seal"]):
            return "missing_authorization_information"
        if any(
            word in text
            for word in [
                "trade license",
                "vat certificate",
                "iso",
                "technical compliance",
                "test report",
                "certificate",
                "required document",
                "mandatory document",
            ]
        ):
            return "missing_mandatory_documents"
        if any(word in text for word in ["delay penalty", "penalty", "liquidated damages", "1%", "fine"]):
            return "delay_penalty_exposure"
        if any(word in text for word in ["warranty", "guarantee", "defect", "replacement"]):
            return "warranty_liability"
        if any(word in text for word in ["delivery", "deadline", "closing date", "lead time"]):
            return "delivery_deadline_risk"
        if any(word in text for word in ["payment", "invoice", "retention", "advance"]):
            return "payment_terms_risk"
        if any(word in text for word in ["submission", "submit", "compliance"]):
            return "submission_compliance_risk"

        normalized = " ".join(text.split())
        return normalized[:80] or "general_business_risk"

    def _primary_risk_for_group(self, group_key: str, group: List[Dict]) -> Dict:
        highest = sorted(
            group,
            key=lambda risk: self._level_rank(risk.get("severity")),
            reverse=True,
        )[0].copy()

        title_map = {
            "missing_supplier_information": ("Commercial", "Missing Supplier Information"),
            "missing_customer_information": ("Commercial", "Missing Customer Information"),
            "missing_commercial_information": ("Financial", "Missing Essential Commercial Information"),
            "missing_authorization_information": ("Legal", "Missing Authorization Evidence"),
            "missing_mandatory_documents": ("Compliance", "Missing Mandatory Documents"),
            "delay_penalty_exposure": ("Legal", "Delay Penalty Exposure"),
            "warranty_liability": ("Warranty", "Warranty Liability"),
            "delivery_deadline_risk": ("Delivery", "Delivery and Deadline Risk"),
            "payment_terms_risk": ("Commercial", "Payment Terms Risk"),
            "submission_compliance_risk": ("Compliance", "Submission Compliance Risk"),
        }

        if group_key in title_map:
            category, title = title_map[group_key]
            highest["category"] = category
            highest["title"] = title

        return highest

    def _executive_description(
        self,
        group_key: str,
        descriptions: List[str],
        fallback: str,
    ) -> str:
        description_map = {
            "missing_supplier_information": "Supplier identity or supplier details are not clear enough for executive approval.",
            "missing_customer_information": "Customer or buyer information is not clear enough to confirm the business context.",
            "missing_commercial_information": "Essential commercial information such as pricing, currency, value, or exposure is incomplete.",
            "missing_authorization_information": "The document does not clearly show required authorization evidence such as signature, stamp, or approval.",
            "missing_mandatory_documents": "Mandatory compliance documents or certificates must be confirmed before submission or commitment.",
            "delay_penalty_exposure": "The opportunity includes potential delay penalty, liquidated damages, or liability exposure.",
            "warranty_liability": "Warranty or guarantee obligations may create after-sales liability and cost exposure.",
            "delivery_deadline_risk": "Delivery obligations, deadlines, or lead times require management confirmation.",
            "payment_terms_risk": "Payment terms may affect cash flow, collection timing, or commercial acceptability.",
            "submission_compliance_risk": "Submission requirements or compliance obligations must be closed before proceeding.",
        }

        if group_key in description_map:
            return description_map[group_key]

        if descriptions:
            return descriptions[0]

        return fallback

    def _merge_text_values(self, values) -> List[str]:
        merged = []
        seen = set()

        for value in values:
            if not value:
                continue

            text = str(value).strip()
            if not text:
                continue

            key = text.lower()
            if key in seen:
                continue

            seen.add(key)
            merged.append(text)

        return merged

    def _highest_severity(self, risks: List[Dict]) -> str:
        return self._highest_level(
            risks=risks,
            field="severity",
            default="Medium",
        )

    def _highest_probability(self, risks: List[Dict]) -> str:
        return self._highest_level(
            risks=risks,
            field="probability",
            default="Medium",
        )

    def _highest_impact(self, risks: List[Dict]) -> str:
        return self._highest_level(
            risks=risks,
            field="impact",
            default="Medium",
        )

    def _highest_level(self, risks: List[Dict], field: str, default: str) -> str:
        if not risks:
            return default

        return sorted(
            (
                self._normalize_level(risk.get(field), default=default)
                for risk in risks
            ),
            key=self._level_rank,
            reverse=True,
        )[0]

    def _sort_risks(self, risks: List[Dict]) -> List[Dict]:
        return sorted(
            risks,
            key=lambda risk: (
                self._level_rank(risk.get("severity")),
                self._level_rank(risk.get("impact")),
                self._level_rank(risk.get("probability")),
            ),
            reverse=True,
        )

    def _level_rank(self, value: Any) -> int:
        return {
            "Critical": 4,
            "High": 3,
            "Medium": 2,
            "Low": 1,
        }.get(self._normalize_level(value, default="Medium"), 2)

    def _severity_counts(self, risks: List[Dict]) -> Dict[str, int]:
        return {
            "high": len([risk for risk in risks if risk.get("severity") in ["Critical", "High"]]),
            "medium": len([risk for risk in risks if risk.get("severity") == "Medium"]),
            "low": len([risk for risk in risks if risk.get("severity") == "Low"]),
        }

    def _overall_risk_level(self, risks: List[Dict]) -> str:
        severities = [risk.get("severity") for risk in risks]

        if "Critical" in severities:
            return "Critical"
        if "High" in severities:
            return "High"
        if "Medium" in severities:
            return "Medium"
        if "Low" in severities:
            return "Low"

        return "Low"
