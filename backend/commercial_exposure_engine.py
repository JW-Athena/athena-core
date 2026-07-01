from typing import Any, Dict, Optional

from bid_no_bid_engine import BidNoBidEngine
from capability_005_obligation_extraction import ObligationExtractor
from capability_006_business_intelligence import BusinessIntelligenceEngine
from executive_decision_brief_engine import ExecutiveDecisionBriefEngine
from risk_register_engine import RiskRegisterEngine


class CommercialExposureEngine:
    """
    Commercial Exposure Intelligence

    Produces an executive commercial assessment by composing existing ATHENA
    intelligence outputs.
    """

    def __init__(self):
        self.brief_engine = ExecutiveDecisionBriefEngine()
        self.bid_engine = BidNoBidEngine()
        self.risk_register_engine = RiskRegisterEngine()
        self.business_engine = BusinessIntelligenceEngine()
        self.obligation_engine = ObligationExtractor()

    def analyze(
        self,
        text: str,
        document_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        brief_result = self.brief_engine.generate(
            text=text,
            document_type=document_type,
        )
        bid_result = self.bid_engine.evaluate(
            text=text,
            document_type=document_type,
        )
        risk_result = self.risk_register_engine.generate(
            text=text,
            document_type=document_type,
        )
        business = self.business_engine.analyze(
            text=text,
            document_type=document_type,
        )
        obligations = self.obligation_engine.extract(
            text=text,
            document_type=document_type,
        )

        brief = brief_result.get("brief", {})
        decision = bid_result.get("decision", {})
        risk_register = risk_result.get("risk_register", {})

        commercial_exposure = brief.get("commercial_exposure", {})
        missing_information = self._combined_text(
            brief.get("missing_information", []),
            decision.get("missing_information", []),
            decision.get("blockers", []),
        )

        contract_value = self._first_value(
            commercial_exposure.get("financial_exposure"),
            business.get("financial_exposure"),
        )
        contract_value = self._contract_value_or_unknown(contract_value)
        payment_terms = self._first_value(
            self._join_items(brief.get("payment_terms", [])),
            self._join_items(obligations.get("payment_obligations", [])),
        )
        payment_terms = self._complete_payment_terms(
            payment_terms=payment_terms,
            text=text,
        )
        payment_quality = self._payment_quality(
            payment_terms=payment_terms,
            existing_quality=self._first_value(
                commercial_exposure.get("payment_quality"),
                business.get("payment_quality"),
            ),
        )
        penalty_exposure = self._first_value(
            self._join_items(brief.get("penalties", [])),
            business.get("penalty_exposure"),
            self._join_items(obligations.get("penalties_or_liabilities", [])),
        )
        warranty_liability = self._first_value(
            self._join_items(brief.get("warranty", [])),
            business.get("warranty_exposure"),
            self._join_items(obligations.get("warranty_or_guarantee_terms", [])),
        )
        currency = self._currency_from_intelligence(
            text=missing_information,
            business=business,
            brief=brief,
        )

        return {
            "engine": "commercial_exposure",
            "name": "Commercial Exposure Intelligence",
            "status": "success",
            "commercial_exposure": {
                "contract_value": contract_value,
                "currency": currency,
                "payment_terms": payment_terms,
                "payment_quality": payment_quality,
                "cash_flow_risk": self._cash_flow_risk(
                    contract_value=contract_value,
                    payment_quality=payment_quality,
                    payment_terms=payment_terms,
                ),
                "penalty_exposure": penalty_exposure,
                "warranty_liability": warranty_liability,
                "retention": self._commercial_clause(obligations, "retention"),
                "performance_bond": self._commercial_clause(obligations, "performance bond"),
                "bank_guarantee": self._commercial_clause(obligations, "bank guarantee"),
                "overall_commercial_risk": self._overall_commercial_risk(
                    payment_quality=payment_quality,
                    payment_terms=payment_terms,
                    contract_value=contract_value,
                    currency=currency,
                    missing_information=missing_information,
                    penalty_exposure=penalty_exposure,
                    warranty_liability=warranty_liability,
                    delivery_terms=self._join_items(brief.get("delivery_terms", [])),
                    base_commercial_risk=business.get("commercial_risk_level"),
                    risk_register=risk_register,
                ),
                "executive_recommendation": self._executive_recommendation(
                    decision=decision,
                    contract_value=contract_value,
                    payment_terms=payment_terms,
                    penalty_exposure=penalty_exposure,
                    warranty_liability=warranty_liability,
                    missing_information=missing_information,
                ),
            },
        }

    def _first_value(self, *values):
        for value in values:
            if value not in (None, "", [], {}):
                return value
        return ""

    def _join_items(self, items) -> str:
        if not items:
            return ""

        if not isinstance(items, list):
            items = [items]

        cleaned = []
        seen = set()

        for item in items:
            if item in (None, "", [], {}):
                continue

            value = str(item).strip()
            key = value.lower()
            if key in seen:
                continue

            seen.add(key)
            cleaned.append(value)

        return "; ".join(cleaned)

    def _combined_text(self, *groups) -> str:
        parts = []

        for group in groups:
            if not group:
                continue

            items = group if isinstance(group, list) else [group]
            parts.extend(str(item) for item in items if item)

        return " ".join(parts).lower()

    def _contract_value_or_unknown(self, value: Any) -> str:
        text = str(value or "").strip()

        if not text:
            return "Unknown"

        lower = text.lower()
        if any(word in lower for word in ["payment", "delivery", "acceptance", "invoice", "days", "%", "penalty"]):
            return "Unknown"

        has_currency = any(marker in lower for marker in ["aed", "usd", "eur", "sar", "$"])
        digits = "".join(char for char in text if char.isdigit())

        if has_currency and digits:
            return text

        if digits and int(digits) >= 100:
            return text

        return "Unknown"

    def _complete_payment_terms(self, payment_terms: str, text: str) -> str:
        current = str(payment_terms or "").strip()

        if current and current.lower().strip() not in ["payment terms", "payment terms:"]:
            return current

        lines = [line.strip() for line in text.splitlines()]

        for index, line in enumerate(lines):
            if line.lower().rstrip(":") == "payment terms":
                for next_line in lines[index + 1:]:
                    if next_line:
                        return next_line

        return current

    def _currency_from_intelligence(
        self,
        text: str,
        business: Dict[str, Any],
        brief: Dict[str, Any],
    ) -> str:
        combined = " ".join(
            [
                str(business),
                str(brief),
                text,
            ]
        ).lower()

        if "aed" in combined or "dirham" in combined:
            return "AED"
        if "usd" in combined or "$" in combined:
            return "USD"
        if "eur" in combined:
            return "EUR"
        if "sar" in combined:
            return "SAR"

        return ""

    def _payment_quality(
        self,
        payment_terms: str,
        existing_quality: str,
    ) -> str:
        lower_terms = str(payment_terms).lower()

        if not lower_terms:
            return "Unknown"

        if "advance payment" in lower_terms or lower_terms.startswith("advance"):
            return "Excellent"

        days = self._max_days(payment_terms)
        if days and days > 60:
            return "Poor"
        if days == 30 and "delivery and acceptance" in lower_terms:
            return "Acceptable"
        if days and days <= 60:
            return "Acceptable"

        if existing_quality and existing_quality != "Unknown":
            return existing_quality

        return "Acceptable"

    def _cash_flow_risk(
        self,
        contract_value: str,
        payment_quality: str,
        payment_terms: str,
    ) -> str:
        lower_quality = str(payment_quality).lower()
        lower_terms = str(payment_terms).lower()

        if not lower_terms:
            return "High"
        if "advance payment" in lower_terms or "excellent" in lower_quality:
            return "Low"
        if contract_value == "Unknown":
            return "Medium"
        if "poor" in lower_quality:
            return "High"
        if "acceptable" in lower_quality:
            return "Medium"

        return "Medium"

    def _commercial_clause(self, obligations: Dict[str, Any], keyword: str) -> str:
        sources = []
        sources.extend(obligations.get("commercial_risks", []) or [])
        sources.extend(obligations.get("payment_obligations", []) or [])
        sources.extend(obligations.get("penalties_or_liabilities", []) or [])
        sources.extend(obligations.get("missing_or_unclear_information", []) or [])

        matches = [
            str(item)
            for item in sources
            if keyword in str(item).lower()
        ]

        return self._join_items(matches)

    def _overall_commercial_risk(
        self,
        payment_quality: str,
        payment_terms: str,
        contract_value: str,
        currency: str,
        missing_information: str,
        penalty_exposure: str,
        warranty_liability: str,
        delivery_terms: str,
        base_commercial_risk: str,
        risk_register: Dict[str, Any],
    ) -> str:
        risk_score = 0
        hard_blockers = 0
        information_incomplete = False

        if not payment_terms:
            hard_blockers += 1
        elif payment_quality == "Poor":
            hard_blockers += 1

        if contract_value == "Unknown":
            information_incomplete = True

        if not currency or "currency" in missing_information:
            information_incomplete = True

        if penalty_exposure:
            penalty_text = str(penalty_exposure).lower()
            if any(
                phrase in penalty_text
                for phrase in [
                    "critical",
                    "unlimited liability",
                    "liquidated damages",
                    "performance bond",
                    "bank guarantee",
                ]
            ):
                hard_blockers += 1
            else:
                risk_score += 2

        if warranty_liability:
            risk_score += 1

        if delivery_terms:
            risk_score += 1

        if any(word in missing_information for word in ["supplier", "customer", "signature"]):
            information_incomplete = True

        base = risk_register.get("overall_risk_level") or base_commercial_risk
        if base == "Critical":
            risk_score += 1
        elif base == "High":
            risk_score += 1

        if hard_blockers >= 1:
            return "High"
        if risk_score >= 3:
            return "Medium-High"
        if risk_score >= 1:
            return "Medium"
        if information_incomplete:
            return "Information Incomplete"
        return "Low"

    def _executive_recommendation(
        self,
        decision: Dict[str, Any],
        contract_value: str,
        payment_terms: str,
        penalty_exposure: str,
        warranty_liability: str,
        missing_information: str,
    ) -> str:
        recommendation = decision.get("recommendation", "INSUFFICIENT INFORMATION")

        if contract_value == "Unknown":
            return "Proceed only after confirming contract value and currency; payment terms alone are not contract value."

        if recommendation == "NO GO":
            return "Reject the opportunity unless management receives new evidence that changes the commercial risk."

        if recommendation == "GO":
            return "Commercially acceptable for approval, subject to final document verification."

        actions = []

        if not contract_value:
            actions.append("confirm contract value")
        if not payment_terms:
            actions.append("confirm payment terms")
        if penalty_exposure:
            actions.append("review penalty exposure")
        if warranty_liability:
            actions.append("price warranty liability")

        if actions:
            return f"{recommendation}: proceed only after management closes: {', '.join(actions)}."

        return f"{recommendation}: proceed with documented commercial conditions and management approval."

    def _max_days(self, value: str) -> int:
        import re

        matches = re.findall(r"\b(\d+)\s*days?\b", str(value), flags=re.IGNORECASE)
        if not matches:
            return 0

        return max(int(match) for match in matches)
