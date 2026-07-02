import re
from typing import Any, Dict, List, Optional

from bid_no_bid_engine import BidNoBidEngine
from commercial_exposure_engine import CommercialExposureEngine
from contract_intelligence_engine import ContractIntelligenceEngine
from executive_action_plan_engine import ExecutiveActionPlanEngine
from executive_dashboard_engine import ExecutiveDashboardEngine
from executive_decision_engine import ExecutiveDecisionEngine
from executive_report_engine import ExecutiveReportEngine
from opportunity_scoring_engine import OpportunityScoringEngine
from risk_register_engine import RiskRegisterEngine
from timing_utils import cached_step, new_request_context, timed_step


class ExecutiveScenariosEngine:
    """
    Executive Scenario Intelligence

    Compares realistic executive decision options using existing ATHENA
    intelligence. It does not extract documents or predict outcomes.
    """

    def __init__(self):
        self.dashboard_engine = ExecutiveDashboardEngine()
        self.report_engine = ExecutiveReportEngine()
        self.opportunity_engine = OpportunityScoringEngine()
        self.risk_register_engine = RiskRegisterEngine()
        self.commercial_engine = CommercialExposureEngine()
        self.executive_decision_engine = ExecutiveDecisionEngine()
        self.bid_engine = BidNoBidEngine()
        self.contract_engine = ContractIntelligenceEngine()
        self.action_plan_engine = ExecutiveActionPlanEngine()

    def analyze(
        self,
        text: str,
        document_type: Optional[str] = None,
        request_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        request_context = new_request_context(request_context)

        return cached_step(
            request_context=request_context,
            cache_key="executive_scenarios.analyze",
            engine="executive_scenarios",
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
        dashboard_result = self._safe_call(
            "executive_dashboard",
            lambda: self.dashboard_engine.analyze(
                text=text,
                document_type=document_type,
                request_context=request_context,
            ),
            request_context,
        )
        report_result = self._safe_call(
            "executive_report",
            lambda: self.report_engine.generate(
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
        bid_result = self._safe_call(
            "bid_no_bid",
            lambda: self.bid_engine.evaluate(
                text=text,
                document_type=document_type,
                request_context=request_context,
            ),
            request_context,
        )
        contract_result = self._safe_call(
            "contract_intelligence",
            lambda: self.contract_engine.analyze(
                text=text,
                document_type=document_type,
                request_context=request_context,
            ),
            request_context,
        )
        action_plan_result = self._safe_call(
            "executive_action_plan",
            lambda: self.action_plan_engine.generate(
                text=text,
                document_type=document_type,
                request_context=request_context,
            ),
            request_context,
        )
        decision_result = self._safe_executive_decision(text, request_context)

        dashboard = dashboard_result.get("executive_dashboard", {})
        report = report_result.get("executive_report", {})
        opportunity = opportunity_result.get("opportunity_score", {})
        risk_register = risk_result.get("risk_register", {})
        commercial = commercial_result.get("commercial_exposure", {})
        bid_decision = bid_result.get("decision", {})
        contract = contract_result.get("contract_intelligence", {})
        action_plan = action_plan_result.get("action_plan", {})

        context = self._scenario_context(
            dashboard=dashboard,
            report=report,
            opportunity=opportunity,
            risk_register=risk_register,
            commercial=commercial,
            bid_decision=bid_decision,
            contract=contract,
            action_plan=action_plan,
            executive_decision=decision_result,
        )

        scenarios = [
            self._proceed_immediately(context),
            self._proceed_after_risk_closure(context),
            self._do_not_proceed(context),
        ]
        recommended_scenario = self._recommended_scenario(context)

        return {
            "engine": "executive_scenarios",
            "status": "success",
            "scenario_analysis": {
                "current_position": self._current_position(context),
                "recommended_scenario": recommended_scenario,
                "confidence": context["confidence"],
                "scenarios": scenarios,
                "comparison_summary": self._comparison_summary(context),
                "best_business_outcome": (
                    f"{recommended_scenario} currently offers the strongest "
                    "balance between opportunity and risk."
                ),
                "executive_reasoning": self._executive_reasoning(context),
                "recommended_next_step": self._recommended_next_step(
                    context,
                    recommended_scenario,
                ),
            },
        }

    def _safe_call(self, name: str, callback, request_context: Dict[str, Any]) -> Dict[str, Any]:
        try:
            result = timed_step(
                request_context=request_context,
                engine="executive_scenarios",
                step=f"call_{name}",
                callback=callback,
            )
            return result if isinstance(result, dict) else {}
        except Exception as exc:
            print(f"[executive_scenarios] engine={name} status=skipped error={exc}")
            return {}

    def _safe_executive_decision(
        self,
        text: str,
        request_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        tender_reference = self._extract_tender_reference(text)
        if not tender_reference:
            return {}

        return self._safe_call(
            "executive_decision",
            lambda: self.executive_decision_engine.evaluate_tender(tender_reference),
            request_context,
        )

    def _scenario_context(
        self,
        dashboard: Dict[str, Any],
        report: Dict[str, Any],
        opportunity: Dict[str, Any],
        risk_register: Dict[str, Any],
        commercial: Dict[str, Any],
        bid_decision: Dict[str, Any],
        contract: Dict[str, Any],
        action_plan: Dict[str, Any],
        executive_decision: Dict[str, Any],
    ) -> Dict[str, Any]:
        kpis = dashboard.get("executive_kpis", {})
        report_opportunity = report.get("opportunity_assessment", {})
        report_risk = report.get("risk_assessment", {})
        report_commercial = report.get("commercial_assessment", {})
        report_readiness = report.get("readiness_assessment", {})

        opportunity_score = self._number_or_default(
            dashboard.get("opportunity_score"),
            default=self._number_or_default(
                opportunity.get("overall_score"),
                default=report_opportunity.get("score") or 0,
            ),
        )
        risk_level = self._normalize_level(
            self._first_value(
                kpis.get("risk_level"),
                report_risk.get("risk_level"),
                contract.get("overall_contract_risk"),
                risk_register.get("overall_risk_level"),
                "Unknown",
            )
        )
        commercial_exposure = self._normalize_exposure(
            self._first_value(
                kpis.get("commercial_exposure"),
                report_commercial.get("exposure_level"),
                commercial.get("overall_commercial_risk"),
                "Unknown",
            )
        )
        bid_posture = self._conservative_bid_posture(
            dashboard.get("bid_posture"),
            opportunity.get("bid_recommendation"),
            report_opportunity.get("bid_posture"),
            report.get("final_decision"),
            bid_decision.get("recommendation"),
            executive_decision.get("recommendation"),
        )
        critical_action_count = self._number_or_default(
            kpis.get("critical_action_count"),
            default=report_readiness.get("critical_action_count") or 0,
        )
        missing_count = len(contract.get("missing_contract_information") or [])
        major_risk_count = self._number_or_default(
            kpis.get("major_risk_count"),
            default=report_risk.get("major_risk_count") or risk_register.get("high_risks") or 0,
        )
        readiness_level = self._first_value(
            kpis.get("readiness_level"),
            report_readiness.get("readiness_level"),
            action_plan.get("overall_status"),
            "Unknown",
        )

        confidence = self._conservative_confidence(
            dashboard.get("confidence"),
            opportunity.get("confidence"),
            report_opportunity.get("confidence"),
            contract.get("confidence"),
            missing_count=missing_count,
            critical_action_count=critical_action_count,
        )

        priority_actions = self._list_values(
            dashboard.get("priority_actions"),
            report.get("priority_actions"),
            action_plan.get("actions"),
            contract.get("recommended_actions"),
        )
        strengths = self._list_values(
            dashboard.get("top_strengths"),
            opportunity.get("key_strengths"),
        )
        concerns = self._list_values(
            dashboard.get("top_concerns"),
            opportunity.get("key_concerns"),
            report.get("executive_recommendations"),
        )

        return {
            "opportunity_score": opportunity_score,
            "opportunity_level": self._first_value(
                dashboard.get("opportunity_level"),
                opportunity.get("opportunity_level"),
                report_opportunity.get("level"),
                self._opportunity_level(opportunity_score),
            ),
            "risk_level": risk_level,
            "commercial_exposure": commercial_exposure,
            "readiness_level": readiness_level,
            "bid_posture": bid_posture,
            "confidence": confidence,
            "critical_action_count": critical_action_count,
            "major_risk_count": major_risk_count,
            "missing_count": missing_count,
            "priority_actions": priority_actions,
            "strengths": strengths,
            "concerns": concerns,
            "dashboard_next_step": dashboard.get("recommended_next_step"),
            "report_next_step": report.get("next_step"),
            "action_plan_summary": action_plan.get("executive_summary"),
            "commercial_summary": report_commercial.get("summary"),
            "risk_summary": report_risk.get("summary"),
        }

    def _proceed_immediately(self, context: Dict[str, Any]) -> Dict[str, Any]:
        risk_level = context["risk_level"]
        commercial_exposure = context["commercial_exposure"]
        disadvantages = []

        if self._is_high_risk(risk_level):
            disadvantages.append("Exposes management to unresolved risk items.")
        if commercial_exposure in {"Medium-High", "High", "Critical"}:
            disadvantages.append("Leaves commercial exposure unresolved at decision point.")
        if context["missing_count"] or context["critical_action_count"]:
            disadvantages.append("Relies on incomplete information or open executive actions.")
        if not disadvantages:
            disadvantages.append("Requires management acceptance of the current evidence base.")

        if risk_level == "Critical":
            impact = (
                "Fastest decision path, but current intelligence shows elevated "
                "execution and commercial exposure."
            )
        else:
            impact = "Fastest decision path using the current available intelligence."

        return {
            "scenario": "Proceed Immediately",
            "risk_level": risk_level,
            "business_impact": impact,
            "advantages": [
                "Accelerates management decision and bid preparation.",
                "Uses current opportunity and commercial signals without further delay.",
            ],
            "disadvantages": disadvantages,
            "executive_summary": (
                "Proceeding immediately is only suitable if management accepts the "
                "current risk, commercial exposure, and readiness position."
            ),
        }

    def _proceed_after_risk_closure(self, context: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "scenario": "Proceed After Risk Closure",
            "risk_level": "Managed after closure",
            "business_impact": (
                "Keeps the opportunity under consideration while requiring closure "
                "of major commercial, legal, compliance, or operational gaps before approval."
            ),
            "advantages": [
                "Improves decision quality by closing priority actions.",
                "Allows management to quantify unresolved exposure before commitment.",
                "Preserves the option to bid if open conditions are resolved.",
            ],
            "disadvantages": [
                "Requires accountable owners and additional review time.",
                "Submission readiness remains dependent on closing open actions.",
            ],
            "executive_summary": (
                "This is the balanced option when the opportunity remains viable but "
                "current risk or information gaps are not ready for immediate approval."
            ),
        }

    def _do_not_proceed(self, context: Dict[str, Any]) -> Dict[str, Any]:
        supported_opportunity = (
            context["opportunity_score"] >= 40
            or context["opportunity_level"] in {"Medium", "High", "Strategic"}
            or bool(context["strengths"])
        )
        impact = "Avoids current risk exposure and stops further bid effort."
        disadvantages = ["May reduce optionality if missing information is later resolved."]

        if supported_opportunity:
            impact = (
                "Avoids current risk exposure, but may forgo the commercial "
                "opportunity identified by the existing analysis."
            )
            disadvantages = ["May forgo a viable commercial opportunity."]

        return {
            "scenario": "Do Not Proceed",
            "risk_level": "Avoided exposure",
            "business_impact": impact,
            "advantages": [
                "Avoids unresolved commercial, legal, or execution exposure.",
                "Prevents commitment with incomplete information.",
            ],
            "disadvantages": disadvantages,
            "executive_summary": (
                "Do not proceed is appropriate when unresolved exposure outweighs "
                "the currently supported business value."
            ),
        }

    def _recommended_scenario(self, context: Dict[str, Any]) -> str:
        if (
            context["bid_posture"] == "No-Bid"
            and context["opportunity_score"] < 40
        ):
            return "Do Not Proceed"

        if (
            self._is_high_risk(context["risk_level"])
            or context["commercial_exposure"] in {"Medium-High", "High", "Critical"}
            or context["critical_action_count"] > 0
            or context["missing_count"] > 0
            or context["bid_posture"] == "Conditional Bid"
        ):
            return "Proceed After Risk Closure"

        if context["opportunity_score"] >= 65 and context["bid_posture"] in {
            "Bid",
            "Strategic Bid",
        }:
            return "Proceed Immediately"

        return "Proceed After Risk Closure"

    def _current_position(self, context: Dict[str, Any]) -> str:
        return (
            f"Current position is {context['bid_posture']} with "
            f"{context['risk_level']} risk, {context['commercial_exposure']} "
            f"commercial exposure, {context['readiness_level']} readiness, and "
            f"an opportunity score of {context['opportunity_score']}/100."
        )

    def _comparison_summary(self, context: Dict[str, Any]) -> str:
        return (
            "Proceed Immediately prioritizes speed, Proceed After Risk Closure "
            "keeps the opportunity viable while closing open exposure, and Do Not "
            "Proceed avoids current exposure but may stop a supported opportunity."
        )

    def _executive_reasoning(self, context: Dict[str, Any]) -> str:
        concerns = []
        if self._is_high_risk(context["risk_level"]):
            concerns.append(f"{context['risk_level']} risk")
        if context["commercial_exposure"] in {"Medium-High", "High", "Critical"}:
            concerns.append(f"{context['commercial_exposure']} commercial exposure")
        if context["critical_action_count"] > 0:
            concerns.append(f"{context['critical_action_count']} critical open action(s)")
        if context["missing_count"] > 0:
            concerns.append("missing contract information")

        concern_text = ", ".join(concerns) if concerns else "no critical blockers identified"
        return (
            f"The recommendation reflects a {context['opportunity_score']}/100 "
            f"opportunity score, {context['bid_posture']} bid posture, and "
            f"{concern_text} in the existing intelligence."
        )

    def _recommended_next_step(
        self,
        context: Dict[str, Any],
        recommended_scenario: str,
    ) -> str:
        if recommended_scenario == "Proceed Immediately":
            return "Proceed to executive approval review and assign owners for final submission checks."
        if recommended_scenario == "Do Not Proceed":
            return "Record the no-proceed decision and document the risk basis for management review."

        first_action = self._first_value(*context["priority_actions"])
        if first_action:
            return self._clean_sentence(first_action)

        return "Assign accountable owners to close commercial, compliance, contract, and risk gaps before executive approval."

    def _conservative_bid_posture(self, *values: Any) -> str:
        rank = {
            "No-Bid": 0,
            "Conditional Bid": 1,
            "Bid": 2,
            "Strategic Bid": 3,
        }
        postures = [self._map_bid_posture(value) for value in values]
        postures = [posture for posture in postures if posture in rank]
        if not postures:
            return "Conditional Bid"
        return min(postures, key=lambda posture: rank[posture])

    def _map_bid_posture(self, value: Any) -> str:
        text = str(value or "").strip()
        upper = text.upper()
        if not text:
            return ""
        if "NO-BID" in upper or "NO BID" in upper or upper in {"NO GO", "NO-GO"}:
            return "No-Bid"
        if "INSUFFICIENT" in upper or "CONDITION" in upper:
            return "Conditional Bid"
        if "STRATEGIC" in upper:
            return "Strategic Bid"
        if upper in {"GO", "BID", "PROCEED"} or " BID" in upper:
            return "Bid"
        return text

    def _conservative_confidence(
        self,
        *values: Any,
        missing_count: int,
        critical_action_count: int,
    ) -> str:
        rank = {"Low": 0, "Medium": 1, "High": 2}
        labels = [self._confidence_label(value) for value in values]
        labels = [label for label in labels if label in rank]
        confidence = min(labels, key=lambda label: rank[label]) if labels else "Medium"
        if missing_count >= 3 or critical_action_count >= 2:
            return "Low"
        if missing_count or critical_action_count:
            return "Low" if confidence == "Low" else "Medium"
        return confidence

    def _confidence_label(self, value: Any) -> str:
        if isinstance(value, (int, float)):
            if value >= 70:
                return "High"
            if value >= 40:
                return "Medium"
            return "Low"
        text = str(value or "").strip().title()
        if text in {"Low", "Medium", "High"}:
            return text
        return ""

    def _list_values(self, *values: Any) -> List[str]:
        items = []
        for value in values:
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        candidate = self._first_value(
                            item.get("action"),
                            item.get("title"),
                            item.get("summary"),
                            item.get("recommendation"),
                        )
                    else:
                        candidate = str(item or "")
                    candidate = self._clean_sentence(candidate)
                    if candidate and candidate not in items:
                        items.append(candidate)
            elif value:
                candidate = self._clean_sentence(value)
                if candidate and candidate not in items:
                    items.append(candidate)
        return items[:8]

    def _extract_tender_reference(self, text: str) -> Optional[str]:
        patterns = [
            r"(Tender\s*(?:No|Number|#)?[:\-]?\s*[A-Z0-9\-\/]+)",
            r"(RFQ\s*(?:No|Number|#)?[:\-]?\s*[A-Z0-9\-\/]+)",
            r"(RFP\s*(?:No|Number|#)?[:\-]?\s*[A-Z0-9\-\/]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text or "", flags=re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None

    def _first_value(self, *values: Any) -> str:
        for value in values:
            if value is None:
                continue
            text = str(value).strip()
            if text:
                return text
        return ""

    def _number_or_default(self, value: Any, default: Any = 0) -> int:
        try:
            if value is None or value == "":
                value = default
            return max(0, min(100, round(float(value))))
        except (TypeError, ValueError):
            return self._number_or_default(default, default=0)

    def _normalize_level(self, value: Any) -> str:
        text = str(value or "").strip().title()
        mapping = {
            "Medium-High": "High",
            "Medium High": "High",
            "Severe": "Critical",
            "Watch": "Medium",
        }
        return mapping.get(text, text or "Unknown")

    def _normalize_exposure(self, value: Any) -> str:
        text = str(value or "").strip()
        if not text:
            return "Unknown"
        title = text.title().replace("Medium High", "Medium-High")
        return title

    def _is_high_risk(self, risk_level: str) -> bool:
        return risk_level in {"High", "Critical"}

    def _opportunity_level(self, score: int) -> str:
        if score >= 85:
            return "Strategic"
        if score >= 65:
            return "High"
        if score >= 40:
            return "Medium"
        return "Low"

    def _clean_sentence(self, value: Any) -> str:
        text = re.sub(r"\s+", " ", str(value or "")).strip(" ;")
        if not text:
            return ""
        if text[-1] not in ".!?":
            text += "."
        return text
