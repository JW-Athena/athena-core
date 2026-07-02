import re
from typing import Any, Dict, List, Optional

from bid_no_bid_engine import BidNoBidEngine
from business_memory_engine import BusinessMemoryEngine
from commercial_exposure_engine import CommercialExposureEngine
from executive_action_plan_engine import ExecutiveActionPlanEngine
from executive_decision_brief_engine import ExecutiveDecisionBriefEngine
from executive_decision_engine import ExecutiveDecisionEngine
from opportunity_scoring_engine import OpportunityScoringEngine
from risk_register_engine import RiskRegisterEngine
from timing_utils import cached_step, new_request_context, timed_step


class ExecutiveDashboardEngine:
    """
    Executive Dashboard Intelligence

    Orchestrates existing ATHENA intelligence into a single executive-ready
    dashboard payload. It does not own document extraction logic.
    """

    def __init__(self):
        self.brief_engine = ExecutiveDecisionBriefEngine()
        self.opportunity_engine = OpportunityScoringEngine()
        self.bid_engine = BidNoBidEngine()
        self.risk_register_engine = RiskRegisterEngine()
        self.commercial_engine = CommercialExposureEngine()
        self.action_plan_engine = ExecutiveActionPlanEngine()
        self.executive_decision_engine = ExecutiveDecisionEngine()
        self.business_memory_engine = BusinessMemoryEngine()

    def analyze(
        self,
        text: str,
        document_type: Optional[str] = None,
        request_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        request_context = new_request_context(request_context)

        return cached_step(
            request_context=request_context,
            cache_key="executive_dashboard.analyze",
            engine="executive_dashboard",
            step="analyze",
            callback=lambda: self._analyze_uncached(
                text=text,
                document_type=document_type,
                request_context=request_context,
            ),
        )

    def _analyze_uncached(
        self,
        text: str,
        document_type: Optional[str],
        request_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        brief_result = self._safe_call(
            "executive_decision_brief",
            lambda: self.brief_engine.generate(
                text=text,
                document_type=document_type,
                request_context=request_context,
            ),
            request_context,
        )
        opportunity_result = self._safe_call(
            "opportunity_scoring",
            lambda: self.opportunity_engine.evaluate(
                text=text,
                document_type=document_type,
                request_context=request_context,
            ),
            request_context,
        )
        bid_result = self._safe_call(
            "bid_no_bid",
            lambda: self.bid_engine.evaluate(
                text=text,
                document_type=document_type,
                request_context=request_context,
            ),
            request_context,
        )
        risk_result = self._safe_call(
            "risk_register",
            lambda: self.risk_register_engine.generate(
                text=text,
                document_type=document_type,
                request_context=request_context,
            ),
            request_context,
        )
        commercial_result = self._safe_call(
            "commercial_exposure",
            lambda: self.commercial_engine.analyze(
                text=text,
                document_type=document_type,
                request_context=request_context,
            ),
            request_context,
        )
        action_result = self._safe_call(
            "executive_action_plan",
            lambda: self.action_plan_engine.generate(
                text=text,
                document_type=document_type,
                request_context=request_context,
            ),
            request_context,
        )

        brief = brief_result.get("brief", {})
        opportunity = opportunity_result.get("opportunity_score", {})
        decision = bid_result.get("decision", {})
        risk_register = risk_result.get("risk_register", {})
        commercial = commercial_result.get("commercial_exposure", {})
        action_plan = action_result.get("action_plan", {})
        executive_decision = self._executive_decision_context(text, brief)
        memory_count = self._business_memory_count(text, document_type, brief)

        opportunity_score = self._number_or_default(
            opportunity.get("overall_score"),
            default=0,
        )
        risk_level = str(risk_register.get("overall_risk_level") or "Unknown")
        commercial_exposure = str(commercial.get("overall_commercial_risk") or "Unknown")
        bid_posture = self._conservative_bid_posture(
            opportunity_posture=opportunity.get("bid_recommendation"),
            bid_decision=decision.get("recommendation"),
            risk_level=risk_level,
            commercial_exposure=commercial_exposure,
        )
        overall_health = self._overall_health(
            score=opportunity_score,
            risk_level=risk_level,
            commercial_exposure=commercial_exposure,
        )
        confidence = self._conservative_confidence(
            opportunity_confidence=opportunity.get("confidence"),
            brief_confidence=brief.get("confidence"),
            decision_confidence=decision.get("confidence"),
            missing_count=len(brief.get("missing_information", []) or []),
        )
        priority_actions = self._priority_actions(
            action_plan=action_plan,
            brief=brief,
            text=text,
        )
        critical_action_count = self._critical_action_count(action_plan)
        major_risk_count = self._major_risk_count(risk_register)
        readiness_level = self._readiness_level(
            action_plan=action_plan,
            opportunity=opportunity,
            critical_action_count=critical_action_count,
        )
        top_strengths = self._top_items(
            opportunity.get("key_strengths", []),
            limit=5,
        )
        top_concerns = self._top_items(
            self._merge_lists(
                opportunity.get("key_concerns", []),
                self._risk_concerns(risk_register),
                self._commercial_concerns(commercial),
            ),
            limit=6,
        )
        executive_verdict = self._executive_verdict(
            bid_posture=bid_posture,
            overall_health=overall_health,
            risk_level=risk_level,
            commercial_exposure=commercial_exposure,
            executive_decision=executive_decision,
        )
        recommended_next_step = self._recommended_next_step(
            bid_posture=bid_posture,
            opportunity=opportunity,
            priority_actions=priority_actions,
            critical_action_count=critical_action_count,
            risk_level=risk_level,
            commercial_exposure=commercial_exposure,
        )

        result = {
            "engine": "executive_dashboard",
            "status": "success",
            "executive_dashboard": {
                "overall_health": overall_health,
                "executive_verdict": executive_verdict,
                "bid_posture": bid_posture,
                "opportunity_score": opportunity_score,
                "opportunity_level": opportunity.get("opportunity_level", "Low"),
                "confidence": confidence,
                "executive_kpis": {
                    "risk_level": risk_level,
                    "commercial_exposure": commercial_exposure,
                    "readiness_level": readiness_level,
                    "critical_action_count": critical_action_count,
                    "major_risk_count": major_risk_count,
                },
                "top_strengths": top_strengths,
                "top_concerns": top_concerns,
                "priority_actions": priority_actions,
                "management_summary": self._management_summary(
                    overall_health=overall_health,
                    bid_posture=bid_posture,
                    opportunity_score=opportunity_score,
                    risk_level=risk_level,
                    commercial_exposure=commercial_exposure,
                    readiness_level=readiness_level,
                    brief=brief,
                    action_plan=action_plan,
                    memory_count=memory_count,
                ),
                "recommended_next_step": recommended_next_step,
            },
        }
        timed_step(
            request_context=request_context,
            engine="executive_dashboard",
            step="assemble",
            callback=lambda: None,
        )
        return result

    def _safe_call(self, name: str, callback, request_context: Dict[str, Any]) -> Dict[str, Any]:
        try:
            result = timed_step(
                request_context=request_context,
                engine="executive_dashboard",
                step=f"call_{name}",
                callback=callback,
            )
            return result if isinstance(result, dict) else {}
        except Exception as exc:
            print(f"[executive_dashboard] engine={name} status=skipped error={exc}")
            return {}

    def _conservative_bid_posture(
        self,
        opportunity_posture: Any,
        bid_decision: Any,
        risk_level: str,
        commercial_exposure: str,
    ) -> str:
        postures = [
            str(opportunity_posture or "Conditional Bid"),
            self._bid_decision_to_posture(bid_decision),
        ]

        if risk_level == "Critical":
            postures.append("Conditional Bid")
        if commercial_exposure in ["Medium-High", "High"]:
            postures.append("Conditional Bid")

        return sorted(postures, key=self._posture_rank)[0]

    def _bid_decision_to_posture(self, value: Any) -> str:
        decision = str(value or "").upper()

        if decision == "NO GO":
            return "No-Bid"
        if decision in ["INSUFFICIENT INFORMATION", "GO WITH CONDITIONS"]:
            return "Conditional Bid"
        if decision == "GO":
            return "Bid"

        return "Conditional Bid"

    def _posture_rank(self, value: str) -> int:
        return {
            "No-Bid": 0,
            "Conditional Bid": 1,
            "Bid": 2,
            "Strategic Bid": 3,
        }.get(str(value), 1)

    def _overall_health(
        self,
        score: int,
        risk_level: str,
        commercial_exposure: str,
    ) -> str:
        if score <= 39 or risk_level == "Critical":
            return "Poor"
        if score <= 64 or commercial_exposure == "Medium-High":
            return "Watch"
        if score <= 84:
            return "Stable"
        return "Strong"

    def _conservative_confidence(
        self,
        opportunity_confidence: Any,
        brief_confidence: Any,
        decision_confidence: Any,
        missing_count: int,
    ) -> str:
        values = [
            self._confidence_rank(opportunity_confidence),
            self._confidence_rank_from_number(brief_confidence),
            self._confidence_rank_from_number(decision_confidence),
        ]
        values = [value for value in values if value is not None]
        rank = min(values) if values else 1

        if missing_count:
            rank = min(rank, 1)

        return {
            0: "Low",
            1: "Medium",
            2: "High",
        }.get(rank, "Medium")

    def _confidence_rank(self, value: Any) -> Optional[int]:
        text = str(value or "").strip()
        if text == "High":
            return 2
        if text == "Medium":
            return 1
        if text == "Low":
            return 0
        return self._confidence_rank_from_number(value)

    def _confidence_rank_from_number(self, value: Any) -> Optional[int]:
        number = self._number_or_default(value, default=None)
        if number is None:
            return None
        if number >= 75:
            return 2
        if number >= 50:
            return 1
        return 0

    def _priority_actions(
        self,
        action_plan: Dict[str, Any],
        brief: Dict[str, Any],
        text: str,
    ) -> List[Dict[str, Any]]:
        actions = action_plan.get("actions", []) or []
        cleaned = []

        for action in actions:
            if self._is_unsupported_customer_action(action, brief, text):
                continue

            cleaned.append(
                {
                    "priority": action.get("priority", "Medium"),
                    "department": action.get("department", "Management"),
                    "title": action.get("title", "Review management action"),
                    "description": action.get("description", ""),
                }
            )

            if len(cleaned) >= 5:
                break

        return cleaned

    def _is_unsupported_customer_action(
        self,
        action: Dict[str, Any],
        brief: Dict[str, Any],
        text: str,
    ) -> bool:
        action_text = self._combined_text(
            action.get("title"),
            action.get("description"),
            action.get("reason"),
        )

        if not any(word in action_text for word in ["customer", "buyer", "client"]):
            return False

        source_text = str(text or "").lower()

        explicit_blank_customer_field = any(
            re.search(pattern, source_text, flags=re.IGNORECASE)
            for pattern in [
                r"\b(customer|buyer|client)\s*:\s*$",
                r"\b(customer|buyer|client)\s*:\s*(n/?a|none|not provided|missing|unknown)\b",
            ]
        )

        explicit_document_requirement = any(
            phrase in source_text
            for phrase in [
                "customer information required",
                "buyer information required",
                "client information required",
                "provide customer details",
                "provide buyer details",
                "provide client details",
            ]
        )

        return not (explicit_blank_customer_field or explicit_document_requirement)

    def _critical_action_count(self, action_plan: Dict[str, Any]) -> int:
        return len(
            [
                action
                for action in action_plan.get("actions", []) or []
                if action.get("priority") == "Critical"
            ]
        )

    def _major_risk_count(self, risk_register: Dict[str, Any]) -> int:
        if "high_risks" in risk_register:
            return int(risk_register.get("high_risks") or 0)

        return len(
            [
                risk
                for risk in risk_register.get("risks", []) or []
                if risk.get("severity") in ["Critical", "High"]
            ]
        )

    def _readiness_level(
        self,
        action_plan: Dict[str, Any],
        opportunity: Dict[str, Any],
        critical_action_count: int,
    ) -> str:
        if critical_action_count:
            return "Blocked"

        status = action_plan.get("overall_status")
        if status:
            return str(status)

        readiness = (
            opportunity.get("score_breakdown", {}) or {}
        ).get("execution_readiness")
        readiness = self._number_or_default(readiness, default=0)

        if readiness >= 75:
            return "Ready"
        if readiness >= 50:
            return "Needs Review"
        return "Blocked"

    def _risk_concerns(self, risk_register: Dict[str, Any]) -> List[str]:
        concerns = []
        for risk in risk_register.get("risks", []) or []:
            if risk.get("severity") in ["Critical", "High"]:
                title = risk.get("title") or risk.get("category") or "Major risk"
                concerns.append(str(title))
        return concerns

    def _commercial_concerns(self, commercial: Dict[str, Any]) -> List[str]:
        concerns = []
        if commercial.get("contract_value") in ["", "Unknown"] or not commercial.get("currency"):
            concerns.append("Confirm contract value and currency.")
        if commercial.get("penalty_exposure"):
            concerns.append("Review penalty exposure.")
        if commercial.get("cash_flow_risk") == "High":
            concerns.append("Review cash-flow exposure.")
        return concerns

    def _executive_verdict(
        self,
        bid_posture: str,
        overall_health: str,
        risk_level: str,
        commercial_exposure: str,
        executive_decision: Dict[str, Any],
    ) -> str:
        stored_recommendation = executive_decision.get("recommendation")

        if bid_posture == "No-Bid":
            return "Do not proceed unless executive management accepts the identified exceptions."
        if overall_health == "Poor":
            return "Hold executive approval until critical risk and information gaps are closed."
        if bid_posture == "Conditional Bid":
            return "Proceed only under conditions with accountable owners for commercial, risk, and submission closure."
        if stored_recommendation:
            return f"Proceed with bid preparation; stored decision context indicates {stored_recommendation}."
        if risk_level in ["High", "Critical"] or commercial_exposure in ["Medium-High", "High"]:
            return "Proceed only with executive review of risk and commercial exposure."
        return "Proceed with bid preparation subject to final management review."

    def _recommended_next_step(
        self,
        bid_posture: str,
        opportunity: Dict[str, Any],
        priority_actions: List[Dict[str, Any]],
        critical_action_count: int,
        risk_level: str,
        commercial_exposure: str,
    ) -> str:
        if opportunity.get("recommended_next_action"):
            return str(opportunity.get("recommended_next_action"))
        if critical_action_count:
            return "Close critical actions before executive bid approval."
        if priority_actions:
            return "Assign owners to the priority actions and hold a management review before submission."
        if bid_posture == "No-Bid":
            return "Do not bid unless the executive team approves the documented exceptions."
        if risk_level in ["Critical", "High"] or commercial_exposure in ["Medium-High", "High"]:
            return "Proceed only after commercial and risk exposure are reviewed by management."
        return "Proceed with bid preparation and complete final commercial, compliance, and risk checks."

    def _management_summary(
        self,
        overall_health: str,
        bid_posture: str,
        opportunity_score: int,
        risk_level: str,
        commercial_exposure: str,
        readiness_level: str,
        brief: Dict[str, Any],
        action_plan: Dict[str, Any],
        memory_count: int,
    ) -> str:
        brief_summary = str(brief.get("executive_summary") or "").strip()
        action_summary = str(action_plan.get("executive_summary") or "").strip()
        summary = (
            f"Health is {overall_health}; bid posture is {bid_posture}; "
            f"score is {opportunity_score}/100. Risk is {risk_level}, "
            f"commercial exposure is {commercial_exposure}, and readiness is {readiness_level}."
        )

        if overall_health == "Poor":
            return (
                f"{summary} Executive approval should remain on hold until "
                "commercial value, compliance documents, and risk exposure are closed."
            )
        if bid_posture == "Conditional Bid":
            return (
                f"{summary} Management should proceed only after priority actions "
                "have owners and closure evidence."
            )
        if action_summary:
            return self._short_sentence(f"{summary} {action_summary}", max_words=42)
        if brief_summary:
            return self._short_sentence(f"{summary} {brief_summary}", max_words=42)
        return summary

    def _executive_decision_context(
        self,
        text: str,
        brief: Dict[str, Any],
    ) -> Dict[str, Any]:
        tender_reference = self._extract_tender_reference(text)
        if not tender_reference:
            return {}

        try:
            return self.executive_decision_engine.evaluate_tender(tender_reference)
        except Exception:
            return {}

    def _business_memory_count(
        self,
        text: str,
        document_type: Optional[str],
        brief: Dict[str, Any],
    ) -> int:
        subjects = [
            self._extract_tender_reference(text),
            document_type,
            brief.get("document_type"),
        ]

        for subject in subjects:
            if not subject:
                continue

            try:
                return len(self.business_memory_engine.recall(str(subject)))
            except Exception:
                continue

        return 0

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

    def _top_items(self, values: List[Any], limit: int) -> List[str]:
        return self._merge_lists(values)[:limit]

    def _merge_lists(self, *groups) -> List[str]:
        results = []
        seen = set()

        for group in groups:
            if not group:
                continue

            items = group if isinstance(group, list) else [group]
            for item in items:
                text = str(item or "").strip()
                if not text:
                    continue

                key = text.lower()
                if key in seen:
                    continue

                seen.add(key)
                results.append(text)

        return results

    def _combined_text(self, *values) -> str:
        parts = []

        for value in values:
            if not value:
                continue

            items = value if isinstance(value, list) else [value]
            parts.extend(str(item) for item in items if item)

        return " ".join(parts).lower()

    def _number_or_default(self, value: Any, default: Any) -> Any:
        try:
            return int(value)
        except Exception:
            return default

    def _short_sentence(self, value: str, max_words: int) -> str:
        words = str(value or "").split()
        if len(words) <= max_words:
            return str(value or "").strip()
        return " ".join(words[:max_words]).strip(" .") + "."
