import re
from typing import Any, Dict, List, Optional

from bid_no_bid_engine import BidNoBidEngine
from business_memory_engine import BusinessMemoryEngine
from commercial_exposure_engine import CommercialExposureEngine
from executive_decision_brief_engine import ExecutiveDecisionBriefEngine
from executive_decision_engine import ExecutiveDecisionEngine
from risk_register_engine import RiskRegisterEngine
from timing_utils import cached_step, new_request_context, timed_step


class OpportunityScoringEngine:
    """
    Opportunity Scoring Intelligence

    Scores an opportunity by composing existing ATHENA intelligence outputs.
    The engine does not own document extraction logic.
    """

    def __init__(self):
        self.brief_engine = ExecutiveDecisionBriefEngine()
        self.bid_engine = BidNoBidEngine()
        self.commercial_engine = CommercialExposureEngine()
        self.risk_register_engine = RiskRegisterEngine()
        self.executive_decision_engine = ExecutiveDecisionEngine()
        self.business_memory_engine = BusinessMemoryEngine()

    def evaluate(
        self,
        text: str,
        document_type: Optional[str] = None,
        request_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        request_context = new_request_context(request_context)

        return cached_step(
            request_context=request_context,
            cache_key="opportunity_scoring.evaluate",
            engine="opportunity_scoring",
            step="evaluate",
            callback=lambda: self._evaluate_uncached(
                text=text,
                document_type=document_type,
                request_context=request_context,
            ),
        )

    def _evaluate_uncached(
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
        bid_result = self.bid_engine.evaluate(
            text=text,
            document_type=document_type,
            request_context=request_context,
        )
        commercial_result = self.commercial_engine.analyze(
            text=text,
            document_type=document_type,
            request_context=request_context,
        )
        risk_result = self.risk_register_engine.generate(
            text=text,
            document_type=document_type,
            request_context=request_context,
        )

        brief = brief_result.get("brief", {})
        source = brief_result.get("source_intelligence", {})
        business = source.get("business_intelligence", {})
        executive = source.get("executive_information", {})
        decision = bid_result.get("decision", {})
        commercial = commercial_result.get("commercial_exposure", {})
        risk_register = risk_result.get("risk_register", {})

        executive_decision_context = self._executive_decision_context(
            text=text,
            business=business,
        )
        memory_context = self._memory_context(
            document_type=document_type,
            business=business,
        )

        commercial_score = self._commercial_score(
            business=business,
            commercial=commercial,
            decision=decision,
        )
        technical_score = self._technical_score(
            business=business,
            brief=brief,
        )
        risk_score = self._risk_score(risk_register)
        financial_score = self._financial_score(
            business=business,
            commercial=commercial,
            brief=brief,
        )
        compliance_score = self._compliance_score(
            business=business,
            brief=brief,
            risk_register=risk_register,
        )
        readiness_score = self._readiness_score(
            business=business,
            decision=decision,
            executive_decision_context=executive_decision_context,
        )
        confidence = self._confidence(
            brief=brief,
            business=business,
            executive=executive,
            decision=decision,
            memory_context=memory_context,
        )
        strategic_fit = self._strategic_fit_score(
            business=business,
            brief=brief,
            memory_context=memory_context,
        )
        execution_readiness = self._execution_readiness_score(
            readiness_score=readiness_score,
            compliance_score=compliance_score,
            technical_score=technical_score,
        )
        decision_alignment = self._decision_alignment_score(
            decision=decision,
            confidence=confidence,
            executive_decision_context=executive_decision_context,
        )
        overall_score = self._overall_score(
            commercial_score=commercial_score,
            risk_score=risk_score,
            financial_score=financial_score,
            strategic_fit=strategic_fit,
            execution_readiness=execution_readiness,
            decision_alignment=decision_alignment,
        )
        opportunity_level = self._opportunity_level(overall_score)
        bid_recommendation = self._bid_recommendation(
            overall_score=overall_score,
            decision=decision,
            risk_register=risk_register,
        )
        key_strengths = self._key_strengths(
            commercial_score=commercial_score,
            risk_score=risk_score,
            strategic_fit=strategic_fit,
            execution_readiness=execution_readiness,
            decision_alignment=decision_alignment,
            commercial=commercial,
            decision=decision,
            business=business,
            source_text=text,
        )
        key_concerns = self._key_concerns(
            commercial_score=commercial_score,
            risk_score=risk_score,
            execution_readiness=execution_readiness,
            commercial=commercial,
            risk_register=risk_register,
            decision=decision,
            brief=brief,
            business=business,
        )
        recommended_next_action = self._recommended_next_action(
            bid_recommendation=bid_recommendation,
            commercial=commercial,
            risk_register=risk_register,
            brief=brief,
        )

        result = {
            "engine": "opportunity_scoring",
            "status": "success",
            "opportunity_score": {
                "overall_score": overall_score,
                "opportunity_level": opportunity_level,
                "bid_recommendation": bid_recommendation,
                "confidence": self._confidence_label(confidence),
                "score_breakdown": {
                    "commercial_attractiveness": commercial_score,
                    "risk_position": risk_score,
                    "strategic_fit": strategic_fit,
                    "execution_readiness": execution_readiness,
                    "decision_alignment": decision_alignment,
                },
                "key_strengths": key_strengths,
                "key_concerns": key_concerns,
                "executive_summary": self._executive_summary(
                    overall_score=overall_score,
                    opportunity_level=opportunity_level,
                    bid_recommendation=bid_recommendation,
                    commercial_score=commercial_score,
                    risk_score=risk_score,
                    strategic_fit=strategic_fit,
                    execution_readiness=execution_readiness,
                    decision_alignment=decision_alignment,
                    commercial=commercial,
                    risk_register=risk_register,
                    decision=decision,
                ),
                "recommended_next_action": recommended_next_action,
            },
        }
        timed_step(
            request_context=request_context,
            engine="opportunity_scoring",
            step="assemble",
            callback=lambda: None,
        )
        return result

    def _commercial_score(
        self,
        business: Dict[str, Any],
        commercial: Dict[str, Any],
        decision: Dict[str, Any],
    ) -> int:
        score = self._risk_level_score(
            commercial.get("overall_commercial_risk")
            or business.get("commercial_risk_level"),
        )

        payment_quality = str(commercial.get("payment_quality") or business.get("payment_quality") or "")
        score += {
            "Excellent": 8,
            "Good": 5,
            "Acceptable": 0,
            "Poor": -15,
            "Unknown": -10,
        }.get(payment_quality, 0)

        if commercial.get("contract_value") in ["", "Unknown"] or not commercial.get("currency"):
            score -= 8

        if commercial.get("penalty_exposure"):
            score -= 6
        if decision.get("recommendation") == "GO":
            score += 5
        if decision.get("recommendation") in ["NO GO", "INSUFFICIENT INFORMATION"]:
            score -= 4

        if commercial.get("overall_commercial_risk") == "Medium-High":
            score = max(score, 42)

        return self._clamp(score)

    def _technical_score(
        self,
        business: Dict[str, Any],
        brief: Dict[str, Any],
    ) -> int:
        score = self._risk_level_score(business.get("technical_risk_level"))

        technical_signal = self._combined_text(
            business.get("key_opportunities", []),
            business.get("key_risks", []),
            brief.get("required_actions", []),
        )

        if "technical" in technical_signal or "specification" in technical_signal:
            score += 5
        if "test report" in technical_signal or "compliance sheet" in technical_signal:
            score -= 6
        if "capacity" in technical_signal or "cannot comply" in technical_signal:
            score -= 10

        return self._clamp(score)

    def _risk_score(self, risk_register: Dict[str, Any]) -> int:
        score = self._risk_level_score(risk_register.get("overall_risk_level"))
        high_risks = int(risk_register.get("high_risks") or 0)
        medium_risks = int(risk_register.get("medium_risks") or 0)
        score -= min(high_risks * 4, 18)
        score -= min(medium_risks * 1, 6)

        if risk_register.get("overall_risk_level") == "Critical" and high_risks >= 4:
            return self._clamp(score)
        if risk_register.get("overall_risk_level") == "Critical":
            score = max(score, 22)
        else:
            score = max(score, 35)

        return self._clamp(score)

    def _financial_score(
        self,
        business: Dict[str, Any],
        commercial: Dict[str, Any],
        brief: Dict[str, Any],
    ) -> int:
        score = 75

        payment_quality = str(commercial.get("payment_quality") or business.get("payment_quality") or "")
        score += {
            "Excellent": 15,
            "Good": 10,
            "Acceptable": 0,
            "Poor": -20,
            "Unknown": -15,
        }.get(payment_quality, 0)

        if commercial.get("cash_flow_risk") == "Low":
            score += 8
        elif commercial.get("cash_flow_risk") == "High":
            score -= 18

        if not business.get("financial_exposure") and commercial.get("contract_value") in ["", "Unknown"]:
            score -= 15

        if commercial.get("penalty_exposure") or brief.get("penalties"):
            score -= 10
        if commercial.get("performance_bond") or commercial.get("bank_guarantee"):
            score -= 10

        return self._clamp(score)

    def _compliance_score(
        self,
        business: Dict[str, Any],
        brief: Dict[str, Any],
        risk_register: Dict[str, Any],
    ) -> int:
        score = self._risk_level_score(business.get("compliance_risk_level"))
        missing_count = self._number_or_default(
            business.get("missing_documents_count"),
            default=len(business.get("missing_documents", []) or []),
        )
        score -= min(missing_count * 5, 25)
        score -= min(len(brief.get("missing_information", []) or []) * 4, 20)

        compliance_high_risks = [
            risk
            for risk in risk_register.get("risks", []) or []
            if risk.get("category") == "Compliance"
            and risk.get("severity") in ["Critical", "High"]
        ]
        score -= min(len(compliance_high_risks) * 6, 18)

        return self._clamp(score)

    def _readiness_score(
        self,
        business: Dict[str, Any],
        decision: Dict[str, Any],
        executive_decision_context: Dict[str, Any],
    ) -> int:
        readiness = self._number_or_default(
            business.get("submission_readiness_percentage"),
            default=decision.get("score") or decision.get("confidence") or 50,
        )

        if decision.get("recommendation") == "GO":
            readiness += 8
        elif decision.get("recommendation") == "GO WITH CONDITIONS":
            readiness -= 4
        elif decision.get("recommendation") in ["NO GO", "INSUFFICIENT INFORMATION"]:
            readiness -= 15

        stored_score = executive_decision_context.get("score")
        if stored_score not in (None, ""):
            readiness = round((readiness + self._number_or_default(stored_score, readiness)) / 2)

        return self._clamp(readiness)

    def _confidence(
        self,
        brief: Dict[str, Any],
        business: Dict[str, Any],
        executive: Dict[str, Any],
        decision: Dict[str, Any],
        memory_context: Dict[str, Any],
    ) -> int:
        values = [
            brief.get("confidence"),
            business.get("confidence_score"),
            executive.get("confidence_score"),
            decision.get("confidence"),
        ]
        numeric_values = [
            self._number_or_default(value, default=None)
            for value in values
        ]
        numeric_values = [value for value in numeric_values if value is not None]

        if not numeric_values:
            confidence = 50
        else:
            confidence = round(sum(numeric_values) / len(numeric_values))

        if memory_context.get("count"):
            confidence += 3

        return self._clamp(confidence)

    def _overall_score(
        self,
        commercial_score: int,
        risk_score: int,
        financial_score: int,
        strategic_fit: int,
        execution_readiness: int,
        decision_alignment: int,
    ) -> int:
        commercial_attractiveness = round((commercial_score * 0.7) + (financial_score * 0.3))
        weighted = (
            commercial_attractiveness * 0.26
            + risk_score * 0.24
            + strategic_fit * 0.16
            + execution_readiness * 0.20
            + decision_alignment * 0.14
        )
        return self._clamp(round(weighted))

    def _strategic_fit_score(
        self,
        business: Dict[str, Any],
        brief: Dict[str, Any],
        memory_context: Dict[str, Any],
    ) -> int:
        score = 55

        opportunities = business.get("key_opportunities", []) or []
        if opportunities:
            score += min(len(opportunities) * 6, 18)

        combined = self._combined_text(
            opportunities,
            brief.get("delivery_terms", []),
            brief.get("warranty", []),
        )
        if any(word in combined for word in ["technical", "specification", "delivery scope", "capability"]):
            score += 8
        if memory_context.get("count"):
            score += 5
        if not opportunities and not combined:
            score -= 8

        return self._clamp(score)

    def _execution_readiness_score(
        self,
        readiness_score: int,
        compliance_score: int,
        technical_score: int,
    ) -> int:
        return self._clamp(
            readiness_score * 0.45
            + compliance_score * 0.35
            + technical_score * 0.20
        )

    def _decision_alignment_score(
        self,
        decision: Dict[str, Any],
        confidence: int,
        executive_decision_context: Dict[str, Any],
    ) -> int:
        recommendation = decision.get("recommendation")
        score = {
            "GO": 85,
            "GO WITH CONDITIONS": 65,
            "INSUFFICIENT INFORMATION": 50,
            "NO GO": 25,
        }.get(recommendation, 55)

        score = round((score * 0.75) + (confidence * 0.25))

        stored_recommendation = executive_decision_context.get("recommendation")
        if stored_recommendation == recommendation and stored_recommendation:
            score += 5

        return self._clamp(score)

    def _opportunity_level(self, score: int) -> str:
        if score >= 85:
            return "Strategic"
        if score >= 65:
            return "High"
        if score >= 40:
            return "Medium"
        return "Low"

    def _bid_recommendation(
        self,
        overall_score: int,
        decision: Dict[str, Any],
        risk_register: Dict[str, Any],
    ) -> str:
        bid_recommendation = decision.get("recommendation")
        risk_level = risk_register.get("overall_risk_level")

        if bid_recommendation == "NO GO":
            return "No-Bid"
        if bid_recommendation == "INSUFFICIENT INFORMATION":
            return "Conditional Bid"
        if overall_score >= 85 and risk_level not in ["Critical", "High"]:
            return "Strategic Bid"
        if overall_score >= 65 and bid_recommendation == "GO":
            return "Bid"
        if overall_score >= 40:
            return "Conditional Bid"
        return "No-Bid"

    def _confidence_label(self, confidence: int) -> str:
        if confidence >= 75:
            return "High"
        if confidence >= 50:
            return "Medium"
        return "Low"

    def _key_strengths(
        self,
        commercial_score: int,
        risk_score: int,
        strategic_fit: int,
        execution_readiness: int,
        decision_alignment: int,
        commercial: Dict[str, Any],
        decision: Dict[str, Any],
        business: Dict[str, Any],
        source_text: str,
    ) -> List[str]:
        strengths = []

        if commercial_score >= 60:
            strengths.append("Commercial terms are sufficiently visible for management review.")
        if commercial.get("payment_terms"):
            strengths.append("Payment terms are identifiable.")
        if risk_score >= 55:
            strengths.append("Risk position is manageable with controls.")
        if strategic_fit >= 65:
            strengths.append("Opportunity aligns with existing supply or execution capabilities.")
        if execution_readiness >= 60:
            strengths.append("Execution readiness is workable subject to final checks.")
        if decision_alignment >= 65 or decision.get("recommendation") == "GO":
            strengths.append("Bid decision signals support proceeding.")
        for item in business.get("key_opportunities", [])[:2]:
            strength = str(item)
            if self._is_supported_strength(strength, source_text):
                strengths.append(strength)

        return self._unique_text(strengths)[:5]

    def _key_concerns(
        self,
        commercial_score: int,
        risk_score: int,
        execution_readiness: int,
        commercial: Dict[str, Any],
        risk_register: Dict[str, Any],
        decision: Dict[str, Any],
        brief: Dict[str, Any],
        business: Dict[str, Any],
    ) -> List[str]:
        concerns = []

        if decision.get("recommendation") == "INSUFFICIENT INFORMATION":
            concerns.append("Bid decision has insufficient information and requires conditional approval only.")
        if commercial_score < 55:
            concerns.append("Commercial attractiveness is reduced by incomplete value, currency, payment, or exposure data.")
        if commercial.get("overall_commercial_risk") in ["Medium-High", "High"]:
            concerns.append(f"Commercial exposure is {commercial.get('overall_commercial_risk')}.")
        if risk_score < 45 or risk_register.get("overall_risk_level") in ["Critical", "High"]:
            concerns.append(f"Overall risk level is {risk_register.get('overall_risk_level', 'Unknown')}.")
        if execution_readiness < 55:
            concerns.append("Execution readiness depends on closing compliance, technical, and submission gaps.")
        if commercial.get("penalty_exposure"):
            concerns.append("Penalty exposure requires management review.")
        if commercial.get("contract_value") in ["", "Unknown"] or not commercial.get("currency"):
            concerns.append("Contract value or currency is not fully confirmed.")
        for item in (brief.get("missing_information", []) or [])[:2]:
            concerns.append(str(item))
        for item in (business.get("missing_documents", []) or [])[:2]:
            concerns.append(f"Missing document: {item}")

        return self._unique_text(concerns)[:6]

    def _recommended_next_action(
        self,
        bid_recommendation: str,
        commercial: Dict[str, Any],
        risk_register: Dict[str, Any],
        brief: Dict[str, Any],
    ) -> str:
        if bid_recommendation == "No-Bid":
            return "Do not proceed unless executive management accepts the confirmed risk exceptions."

        actions = []
        if commercial.get("contract_value") in ["", "Unknown"] or not commercial.get("currency"):
            actions.append("commercial")
        if brief.get("missing_information"):
            actions.append("missing information")
        if risk_register.get("overall_risk_level") in ["Critical", "High"]:
            actions.append("risk")

        if actions:
            action_text = ", ".join(actions)
            if len(actions) > 1:
                action_text = ", ".join(actions[:-1]) + f", and {actions[-1]}"

            return (
                "Proceed only after closing "
                + action_text
                + " items with assigned owners."
            )

        if bid_recommendation == "Strategic Bid":
            return "Proceed to executive bid approval and assign owners for final commercial and submission checks."

        return "Proceed with bid preparation subject to final commercial, compliance, and risk review."

    def _executive_summary(
        self,
        overall_score: int,
        opportunity_level: str,
        bid_recommendation: str,
        commercial_score: int,
        risk_score: int,
        strategic_fit: int,
        execution_readiness: int,
        decision_alignment: int,
        commercial: Dict[str, Any],
        risk_register: Dict[str, Any],
        decision: Dict[str, Any],
    ) -> str:
        weakest = sorted(
            [
                ("commercial attractiveness", commercial_score),
                ("risk position", risk_score),
                ("strategic fit", strategic_fit),
                ("execution readiness", execution_readiness),
                ("decision alignment", decision_alignment),
            ],
            key=lambda item: item[1],
        )[:2]
        weak_summary = " and ".join(
            f"{name} ({score})"
            for name, score in weakest
        )

        return (
            f"Opportunity scored {overall_score}/100 and is rated {opportunity_level}. "
            f"Recommended bid posture is {bid_recommendation}. "
            f"The weakest areas are {weak_summary}. "
            f"Commercial risk is {commercial.get('overall_commercial_risk', 'Unknown')}, "
            f"overall risk is {risk_register.get('overall_risk_level', 'Unknown')}, "
            f"and bid decision is {decision.get('recommendation', 'Needs review')}. "
            "Management should proceed only with clear owners for commercial, compliance, and risk closure."
        )

    def _executive_decision_context(
        self,
        text: str,
        business: Dict[str, Any],
    ) -> Dict[str, Any]:
        tender_reference = business.get("document_reference") or self._extract_tender_reference(text)
        if not tender_reference:
            return {}

        try:
            return self.executive_decision_engine.evaluate_tender(tender_reference)
        except Exception:
            return {}

    def _memory_context(
        self,
        document_type: Optional[str],
        business: Dict[str, Any],
    ) -> Dict[str, Any]:
        subjects = [
            business.get("document_reference"),
            document_type,
            business.get("document_type"),
        ]

        for subject in subjects:
            if not subject:
                continue

            try:
                memories = self.business_memory_engine.recall(str(subject))
            except Exception:
                memories = []

            if memories:
                return {
                    "count": len(memories),
                    "subject": subject,
                }

        return {
            "count": 0,
            "subject": "",
        }

    def _risk_level_score(self, value: Any) -> int:
        normalized = self._normalize_level(value)
        return {
            "Low": 88,
            "Medium": 70,
            "Medium-High": 56,
            "High": 44,
            "Critical": 34,
            "Information Incomplete": 55,
            "Unknown": 60,
        }.get(normalized, 60)

    def _normalize_level(self, value: Any) -> str:
        text = str(value or "").strip().lower()

        if text == "critical":
            return "Critical"
        if text == "high":
            return "High"
        if text in ["medium-high", "medium high"]:
            return "Medium-High"
        if text == "medium":
            return "Medium"
        if text == "low":
            return "Low"
        if text == "information incomplete":
            return "Information Incomplete"

        return "Unknown"

    def _extract_tender_reference(self, text: str) -> str:
        patterns = [
            r"(Tender\s*(?:No|Number|#)?[:\-]?\s*[A-Z0-9\-\/]+)",
            r"(RFQ\s*(?:No|Number|#)?[:\-]?\s*[A-Z0-9\-\/]+)",
            r"(RFP\s*(?:No|Number|#)?[:\-]?\s*[A-Z0-9\-\/]+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return ""

    def _combined_text(self, *groups) -> str:
        parts: List[str] = []

        for group in groups:
            if not group:
                continue

            items = group if isinstance(group, list) else [group]
            parts.extend(str(item) for item in items if item)

        return " ".join(parts).lower()

    def _number_or_default(self, value: Any, default: Any) -> Any:
        try:
            return int(value)
        except Exception:
            return default

    def _clamp(self, value: Any) -> int:
        return max(0, min(int(round(value)), 100))

    def _unique_text(self, values: List[str]) -> List[str]:
        results = []
        seen = set()

        for value in values:
            text = str(value or "").strip()
            if not text:
                continue

            key = text.lower()
            if key in seen:
                continue

            seen.add(key)
            results.append(text)

        return results

    def _is_supported_strength(self, value: str, source_text: str) -> bool:
        text = value.lower()
        source = source_text.lower()

        guarded_terms = [
            "market",
            "client",
            "customer",
            "abu dhabi",
            "dubai",
            "uae",
            "government",
            "authority",
            "future",
            "potential",
        ]

        for term in guarded_terms:
            if term in text and term not in source:
                return False

        if "entry into" in text or "expansion into" in text:
            return False

        return True
