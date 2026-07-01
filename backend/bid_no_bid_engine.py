from typing import Any, Dict, List, Optional

from executive_decision_brief_engine import ExecutiveDecisionBriefEngine


class BidNoBidEngine:
    """
    Bid / No-Bid Intelligence

    Converts an executive decision brief into an executive-ready bid decision.
    """

    def __init__(self):
        self.brief_engine = ExecutiveDecisionBriefEngine()

    def evaluate(
        self,
        text: str,
        document_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        brief_result = self.brief_engine.generate(
            text=text,
            document_type=document_type,
        )
        brief = brief_result.get("brief", {})

        confidence = self._number_or_default(
            brief.get("confidence"),
            default=50,
        )
        score = confidence
        reasons = []
        risks = list(brief.get("key_risks", []))
        blockers = []

        missing_information = list(brief.get("missing_information", []))
        required_actions = list(brief.get("required_actions", []))
        commercial_exposure = brief.get("commercial_exposure", {})

        score = self._apply_blockers(
            score=score,
            blockers=blockers,
            missing_information=missing_information,
            commercial_exposure=commercial_exposure,
        )

        score = self._apply_risk_adjustments(
            score=score,
            risks=risks,
            penalties=brief.get("penalties", []),
        )

        score = self._apply_positive_signals(
            score=score,
            reasons=reasons,
            payment_terms=brief.get("payment_terms", []),
            delivery_terms=brief.get("delivery_terms", []),
            warranty=brief.get("warranty", []),
        )

        score = max(0, min(int(score), 100))

        recommendation = self._recommendation(
            score=score,
            blockers=blockers,
            risks=risks,
        )

        if blockers:
            required_actions = self._unique_list(
                [
                    f"Resolve blocker: {blocker}"
                    for blocker in blockers
                ],
                required_actions,
            )

        return {
            "engine": "bid_no_bid",
            "name": "Bid / No-Bid Intelligence",
            "status": "success",
            "decision": {
                "recommendation": recommendation,
                "confidence": score,
                "score": score,
                "reasons": reasons,
                "risks": risks,
                "blockers": blockers,
                "required_actions": required_actions,
                "missing_information": missing_information,
                "commercial_exposure": commercial_exposure,
            },
            "executive_brief": brief,
        }

    def _apply_blockers(
        self,
        score: int,
        blockers: List[str],
        missing_information: List[Any],
        commercial_exposure: Dict[str, Any],
    ) -> int:
        missing_text = " ".join(str(item).lower() for item in missing_information)
        financial_exposure = str(commercial_exposure.get("financial_exposure", "")).strip()

        if (
            not financial_exposure
            or "price" in missing_text
            or "pricing" in missing_text
            or "amount" in missing_text
        ):
            blockers.append("Missing essential commercial information: pricing")
            score -= 25

        for field in ["supplier", "customer", "signature", "currency"]:
            if field in missing_text:
                blockers.append(f"Missing essential commercial information: {field}")
                score -= 10

        if (
            "certificate" in missing_text
            or "required documents" in missing_text
            or "document" in missing_text
        ):
            blockers.append("Missing certificates or required documents")
            score -= 20

        return score

    def _apply_risk_adjustments(
        self,
        score: int,
        risks: List[Any],
        penalties: List[Any],
    ) -> int:
        risk_text = " ".join(str(item).lower() for item in risks)

        if "critical" in risk_text:
            score -= 25
        if "high" in risk_text:
            score -= 15
        if "penalty" in risk_text or "liquidated damages" in risk_text:
            score -= 10
        if penalties:
            score -= min(len(penalties) * 8, 20)
            if "Penalty exposure detected" not in risks:
                risks.append("Penalty exposure detected")

        return score

    def _apply_positive_signals(
        self,
        score: int,
        reasons: List[str],
        payment_terms: List[Any],
        delivery_terms: List[Any],
        warranty: List[Any],
    ) -> int:
        if payment_terms:
            score += 8
            reasons.append("Payment terms are identifiable")

        if delivery_terms:
            score += 8
            reasons.append("Delivery terms are identifiable")

        if warranty:
            score += 5
            reasons.append("Warranty terms are identifiable")

        return score

    def _recommendation(
        self,
        score: int,
        blockers: List[str],
        risks: List[Any],
    ) -> str:
        risk_text = " ".join(str(item).lower() for item in risks)
        essential_missing = any(
            str(blocker).startswith("Missing essential commercial information")
            for blocker in blockers
        )

        if essential_missing:
            return "INSUFFICIENT INFORMATION"

        if (
            "reject" in risk_text
            or "do not proceed" in risk_text
            or "unacceptable" in risk_text
            or "cannot comply" in risk_text
            or "critical" in risk_text and score < 45
        ):
            return "NO GO"

        if score >= 80 and not blockers and "critical" not in risk_text and "high" not in risk_text:
            return "GO"

        if score >= 50:
            return "GO WITH CONDITIONS"

        if blockers:
            return "INSUFFICIENT INFORMATION"

        return "GO WITH CONDITIONS"

    def _number_or_default(self, value: Any, default: int) -> int:
        try:
            return int(value)
        except Exception:
            return default

    def _unique_list(self, *groups) -> List[Any]:
        results = []
        seen = set()

        for group in groups:
            if not group:
                continue

            items = group if isinstance(group, list) else [group]

            for item in items:
                if item in (None, "", [], {}):
                    continue

                key = str(item)
                if key in seen:
                    continue

                seen.add(key)
                results.append(item)

        return results
