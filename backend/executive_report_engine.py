import re
from typing import Any, Dict, List, Optional

from bid_no_bid_engine import BidNoBidEngine
from commercial_exposure_engine import CommercialExposureEngine
from executive_action_plan_engine import ExecutiveActionPlanEngine
from executive_dashboard_engine import ExecutiveDashboardEngine
from executive_decision_brief_engine import ExecutiveDecisionBriefEngine
from executive_decision_engine import ExecutiveDecisionEngine
from opportunity_scoring_engine import OpportunityScoringEngine
from risk_register_engine import RiskRegisterEngine
from timing_utils import cached_step, new_request_context, timed_step


class ExecutiveReportEngine:
    """
    Executive Report Generator

    Converts existing ATHENA intelligence into a structured executive report.
    It does not generate files and does not own extraction logic.
    """

    def __init__(self):
        self.dashboard_engine = ExecutiveDashboardEngine()
        self.opportunity_engine = OpportunityScoringEngine()
        self.brief_engine = ExecutiveDecisionBriefEngine()
        self.bid_engine = BidNoBidEngine()
        self.risk_register_engine = RiskRegisterEngine()
        self.commercial_engine = CommercialExposureEngine()
        self.action_plan_engine = ExecutiveActionPlanEngine()
        self.executive_decision_engine = ExecutiveDecisionEngine()

    def generate(
        self,
        text: str,
        document_type: Optional[str] = None,
        request_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        request_context = new_request_context(request_context)

        return cached_step(
            request_context=request_context,
            cache_key="executive_report.generate",
            engine="executive_report",
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
        dashboard_result = self._safe_call(
            "executive_dashboard",
            lambda: self.dashboard_engine.analyze(
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
        brief_result = self._safe_call(
            "executive_decision_brief",
            lambda: self.brief_engine.generate(
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

        dashboard = dashboard_result.get("executive_dashboard", {})
        opportunity = opportunity_result.get("opportunity_score", {})
        brief = brief_result.get("brief", {})
        decision = bid_result.get("decision", {})
        risk_register = risk_result.get("risk_register", {})
        commercial = commercial_result.get("commercial_exposure", {})
        action_plan = action_result.get("action_plan", {})
        executive_decision = self._executive_decision_context(text)

        risk_level = self._first_value(
            dashboard.get("executive_kpis", {}).get("risk_level"),
            risk_register.get("overall_risk_level"),
            "Unknown",
        )
        exposure_level = self._first_value(
            dashboard.get("executive_kpis", {}).get("commercial_exposure"),
            commercial.get("overall_commercial_risk"),
            "Unknown",
        )
        readiness_level = self._first_value(
            dashboard.get("executive_kpis", {}).get("readiness_level"),
            action_plan.get("overall_status"),
            "Needs Review",
        )
        critical_action_count = self._number_or_default(
            dashboard.get("executive_kpis", {}).get("critical_action_count"),
            default=self._critical_action_count(action_plan),
        )
        major_risk_count = self._number_or_default(
            dashboard.get("executive_kpis", {}).get("major_risk_count"),
            default=self._major_risk_count(risk_register),
        )
        opportunity_score = self._number_or_default(
            dashboard.get("opportunity_score"),
            default=opportunity.get("overall_score") or 0,
        )
        bid_posture = self._first_value(
            dashboard.get("bid_posture"),
            opportunity.get("bid_recommendation"),
            self._bid_decision_to_posture(decision.get("recommendation")),
        )
        confidence = self._first_value(
            dashboard.get("confidence"),
            opportunity.get("confidence"),
            "Low" if brief.get("missing_information") else "Medium",
        )
        final_decision = self._final_decision(
            bid_posture=bid_posture,
            risk_level=risk_level,
            missing_information=brief.get("missing_information", []),
            dashboard=dashboard,
            executive_decision=executive_decision,
        )
        priority_actions = self._priority_actions(
            dashboard=dashboard,
            action_plan=action_plan,
        )
        recommendations = self._executive_recommendations(
            final_decision=final_decision,
            dashboard=dashboard,
            commercial=commercial,
            risk_register=risk_register,
            brief=brief,
            priority_actions=priority_actions,
        )
        next_step = self._next_step(
            dashboard=dashboard,
            final_decision=final_decision,
            priority_actions=priority_actions,
            risk_level=risk_level,
            exposure_level=exposure_level,
        )

        result = {
            "engine": "executive_report",
            "status": "success",
            "executive_report": {
                "report_title": self._report_title(document_type, brief),
                "document_type": self._first_value(
                    brief_result.get("document_type"),
                    brief.get("document_type"),
                    document_type,
                    "Unknown",
                ),
                "overall_verdict": self._overall_verdict(
                    final_decision=final_decision,
                    dashboard=dashboard,
                    risk_level=risk_level,
                    exposure_level=exposure_level,
                ),
                "executive_summary": self._executive_summary(
                    dashboard=dashboard,
                    final_decision=final_decision,
                    opportunity_score=opportunity_score,
                    risk_level=risk_level,
                    exposure_level=exposure_level,
                    readiness_level=readiness_level,
                ),
                "opportunity_assessment": {
                    "score": opportunity_score,
                    "level": self._first_value(
                        dashboard.get("opportunity_level"),
                        opportunity.get("opportunity_level"),
                        "Low",
                    ),
                    "bid_posture": bid_posture,
                    "confidence": confidence,
                },
                "risk_assessment": {
                    "risk_level": risk_level,
                    "major_risk_count": major_risk_count,
                    "summary": self._risk_summary(
                        risk_level=risk_level,
                        major_risk_count=major_risk_count,
                        risk_register=risk_register,
                    ),
                    "top_risks": self._top_risks(risk_register),
                },
                "commercial_assessment": {
                    "exposure_level": exposure_level,
                    "summary": self._commercial_summary(commercial),
                    "key_commercial_concerns": self._commercial_concerns(commercial),
                },
                "readiness_assessment": {
                    "readiness_level": readiness_level,
                    "critical_action_count": critical_action_count,
                    "summary": self._readiness_summary(
                        readiness_level=readiness_level,
                        critical_action_count=critical_action_count,
                        action_plan=action_plan,
                    ),
                },
                "priority_actions": priority_actions,
                "executive_recommendations": recommendations,
                "final_decision": final_decision,
                "next_step": next_step,
            },
        }
        timed_step(
            request_context=request_context,
            engine="executive_report",
            step="assemble",
            callback=lambda: None,
        )
        return result

    def _safe_call(self, name: str, callback, request_context: Dict[str, Any]) -> Dict[str, Any]:
        try:
            result = timed_step(
                request_context=request_context,
                engine="executive_report",
                step=f"call_{name}",
                callback=callback,
            )
            return result if isinstance(result, dict) else {}
        except Exception as exc:
            print(f"[executive_report] engine={name} status=skipped error={exc}")
            return {}

    def _report_title(self, document_type: Optional[str], brief: Dict[str, Any]) -> str:
        detected_type = self._first_value(
            brief.get("document_type"),
            document_type,
            "Business Document",
        )
        return f"Executive {detected_type} Report"

    def _overall_verdict(
        self,
        final_decision: str,
        dashboard: Dict[str, Any],
        risk_level: str,
        exposure_level: str,
    ) -> str:
        if final_decision == "Hold":
            return "Executive approval should remain on hold until critical gaps are closed."
        if final_decision == "No-Bid":
            return "Do not bid unless management accepts the documented exceptions."
        if final_decision == "Conditional Bid":
            return "Proceed only as a conditional bid with clear owners and closure evidence."
        if risk_level in ["Critical", "High"] or exposure_level in ["Medium-High", "High"]:
            return "Proceed only after management reviews risk and commercial exposure."
        return dashboard.get("executive_verdict") or "Proceed with final management review."

    def _executive_summary(
        self,
        dashboard: Dict[str, Any],
        final_decision: str,
        opportunity_score: int,
        risk_level: str,
        exposure_level: str,
        readiness_level: str,
    ) -> str:
        return (
            f"The opportunity is assessed at {opportunity_score}/100 with final decision "
            f"{final_decision}. Risk is {risk_level}, commercial exposure is {exposure_level}, "
            f"and readiness is {readiness_level}. Executive focus should remain on closing "
            "commercial value, compliance requirements, and major risk exposure before approval."
        ).strip()

    def _risk_summary(
        self,
        risk_level: str,
        major_risk_count: int,
        risk_register: Dict[str, Any],
    ) -> str:
        if major_risk_count:
            return (
                f"Risk level is {risk_level} with {major_risk_count} major risk items "
                "requiring management review."
            )
        return f"Risk level is {risk_level}; no major risk count was identified by the risk register."

    def _top_risks(self, risk_register: Dict[str, Any]) -> List[Dict[str, Any]]:
        risks = risk_register.get("risks", []) or []
        top_risks = []

        for risk in risks[:5]:
            top_risks.append(
                {
                    "severity": risk.get("severity", "Medium"),
                    "category": risk.get("category", "Operational"),
                    "title": risk.get("title", "Business risk"),
                    "mitigation": self._clean_mitigation(risk.get("mitigation", "")),
                }
            )

        return top_risks

    def _commercial_summary(self, commercial: Dict[str, Any]) -> str:
        exposure = commercial.get("overall_commercial_risk", "Unknown")
        payment_quality = commercial.get("payment_quality", "Unknown")
        contract_value = commercial.get("contract_value", "Unknown")
        return (
            f"Commercial exposure is {exposure}. Payment quality is {payment_quality}; "
            f"contract value is {contract_value}."
        )

    def _commercial_concerns(self, commercial: Dict[str, Any]) -> List[str]:
        concerns = []

        if commercial.get("contract_value") in ["", "Unknown"] or not commercial.get("currency"):
            concerns.append("Confirm contract value and currency.")
        if commercial.get("payment_quality") in ["Poor", "Unknown"]:
            concerns.append("Review payment terms and cash-flow impact.")
        if commercial.get("penalty_exposure"):
            concerns.append("Review penalty exposure before approval.")
        if commercial.get("warranty_liability"):
            concerns.append("Confirm warranty liability and support model.")
        if commercial.get("overall_commercial_risk") in ["Medium-High", "High"]:
            concerns.append("Escalate commercial exposure for management review.")

        return self._unique_text(concerns)[:6]

    def _readiness_summary(
        self,
        readiness_level: str,
        critical_action_count: int,
        action_plan: Dict[str, Any],
    ) -> str:
        if critical_action_count:
            return (
                f"Readiness is {readiness_level}; {critical_action_count} critical action(s) "
                "must close before approval."
            )

        estimated = action_plan.get("estimated_readiness")
        if estimated not in (None, ""):
            return f"Readiness is {readiness_level} with estimated readiness of {estimated}%."

        return f"Readiness is {readiness_level}; final action ownership should be confirmed."

    def _priority_actions(
        self,
        dashboard: Dict[str, Any],
        action_plan: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        dashboard_actions = dashboard.get("priority_actions", []) or []
        if dashboard_actions:
            return dashboard_actions[:8]

        actions = []
        for action in (action_plan.get("actions", []) or [])[:8]:
            actions.append(
                {
                    "priority": action.get("priority", "Medium"),
                    "department": action.get("department", "Management"),
                    "title": action.get("title", "Review management action"),
                    "description": action.get("description", ""),
                }
            )
        return actions

    def _executive_recommendations(
        self,
        final_decision: str,
        dashboard: Dict[str, Any],
        commercial: Dict[str, Any],
        risk_register: Dict[str, Any],
        brief: Dict[str, Any],
        priority_actions: List[Dict[str, Any]],
    ) -> List[str]:
        recommendations = []

        if final_decision == "Hold":
            recommendations.append("Keep executive approval on hold until critical risk and missing information are closed.")
        elif final_decision == "No-Bid":
            recommendations.append("Do not bid unless management approves the documented exceptions.")
        elif final_decision == "Conditional Bid":
            recommendations.append("Proceed only as a conditional bid with named owners for each open issue.")
        else:
            recommendations.append("Proceed with bid preparation subject to final management review.")

        if commercial.get("contract_value") in ["", "Unknown"] or not commercial.get("currency"):
            recommendations.append("Confirm contract value, pricing basis, and currency.")
        if risk_register.get("overall_risk_level") in ["Critical", "High"]:
            recommendations.append("Complete management review of major risks before commitment.")
        if brief.get("missing_information"):
            recommendations.append("Close missing information before final approval.")
        if priority_actions:
            recommendations.append("Assign accountable owners and deadlines for priority actions.")
        if dashboard.get("recommended_next_step"):
            recommendations.append(str(dashboard.get("recommended_next_step")))

        return self._unique_text(recommendations)[:6]

    def _final_decision(
        self,
        bid_posture: str,
        risk_level: str,
        missing_information: List[Any],
        dashboard: Dict[str, Any],
        executive_decision: Dict[str, Any],
    ) -> str:
        if risk_level == "Critical" or missing_information:
            return "Hold"
        if bid_posture == "No-Bid":
            return "No-Bid"
        if bid_posture == "Conditional Bid":
            return "Conditional Bid"
        if executive_decision.get("recommendation") == "NO GO":
            return "No-Bid"
        if dashboard.get("overall_health") == "Poor":
            return "Hold"
        return bid_posture or "Conditional Bid"

    def _next_step(
        self,
        dashboard: Dict[str, Any],
        final_decision: str,
        priority_actions: List[Dict[str, Any]],
        risk_level: str,
        exposure_level: str,
    ) -> str:
        if final_decision == "Hold":
            return "Hold executive approval and close commercial value, compliance, and risk exposure items."
        if final_decision == "No-Bid":
            return "Record the no-bid decision unless management approves an exception."
        if priority_actions:
            return "Assign owners to priority actions and reconvene management review before submission."
        if risk_level in ["Critical", "High"] or exposure_level in ["Medium-High", "High"]:
            return "Complete management review of risk and commercial exposure before bid approval."
        return dashboard.get("recommended_next_step") or "Proceed with final bid preparation and management approval."

    def _executive_decision_context(self, text: str) -> Dict[str, Any]:
        tender_reference = self._extract_tender_reference(text)
        if not tender_reference:
            return {}

        try:
            return self.executive_decision_engine.evaluate_tender(tender_reference)
        except Exception:
            return {}

    def _bid_decision_to_posture(self, value: Any) -> str:
        decision = str(value or "").upper()
        if decision == "NO GO":
            return "No-Bid"
        if decision in ["INSUFFICIENT INFORMATION", "GO WITH CONDITIONS"]:
            return "Conditional Bid"
        if decision == "GO":
            return "Bid"
        return "Conditional Bid"

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

    def _first_value(self, *values):
        for value in values:
            if value not in (None, "", [], {}):
                return value
        return ""

    def _number_or_default(self, value: Any, default: Any) -> Any:
        try:
            return int(value)
        except Exception:
            return default

    def _short_sentence(self, value: str, max_words: int) -> str:
        text = str(value or "").strip()
        words = text.split()

        if len(words) <= max_words:
            return text

        return " ".join(words[:max_words]).strip(" .") + "."

    def _clean_mitigation(self, value: Any) -> str:
        fallback = "Assign an owner to review, quantify, and close this risk before executive approval."
        text = str(value or "").strip()

        if not text:
            return fallback

        fragments = re.split(r"[.;]\s*", text)
        cleaned = []
        seen = set()

        for fragment in fragments:
            item = " ".join(str(fragment or "").split()).strip(" ,;:.")
            if not item:
                continue

            if self._is_weak_mitigation_fragment(item):
                continue

            key = item.lower()
            if key in seen:
                continue

            seen.add(key)
            cleaned.append(item)

        if not cleaned:
            return fallback

        selected = cleaned[0]
        words = selected.split()
        if len(words) > 22:
            selected = " ".join(words[:22]).strip(" ,;:.")

        if self._is_weak_mitigation_fragment(selected):
            return fallback

        return selected + "."

    def _is_weak_mitigation_fragment(self, value: str) -> bool:
        text = str(value or "").strip()
        lower = text.lower()

        if len(text.split()) < 6:
            return True

        weak_endings = [
            ",",
            " and",
            " or",
            " the",
            " missing",
            " duration",
            " confirm",
            " resolve",
            " review",
            " quantify",
        ]

        if any(lower.endswith(ending) for ending in weak_endings):
            return True

        broken_phrases = [
            "resolve the missing",
            "confirm warranty duration",
            "confirm warranty duration,",
        ]

        return any(phrase == lower or lower.endswith(phrase) for phrase in broken_phrases)

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
