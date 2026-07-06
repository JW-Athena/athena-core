from pathlib import Path
from typing import Any, Dict, List, Optional

from bid_no_bid_engine import BidNoBidEngine
from capability_004_executive_extraction import ExecutiveInformationExtractor
from commercial_exposure_engine import CommercialExposureEngine
from engine_013_learning_engine import execution_learning_engine
from engine_021_organization_impact import organization_impact_analysis
from engine_024_executive_reasoning_engine import executive_reasoning_engine
from event_bus import event_bus
from executive_action_plan_engine import ExecutiveActionPlanEngine
from executive_decision_brief_engine import ExecutiveDecisionBriefEngine
from opportunity_scoring_engine import OpportunityScoringEngine
from reader import AthenaReader
from risk_register_engine import RiskRegisterEngine
from timing_utils import new_request_context


class TenderExecutive:
    def __init__(self):
        self.reader = AthenaReader()
        self.executive_extractor = ExecutiveInformationExtractor()
        self.commercial_engine = CommercialExposureEngine()
        self.risk_register_engine = RiskRegisterEngine()
        self.opportunity_engine = OpportunityScoringEngine()
        self.bid_engine = BidNoBidEngine()
        self.brief_engine = ExecutiveDecisionBriefEngine()
        self.action_plan_engine = ExecutiveActionPlanEngine()

    def evaluate_tender(self, question: str, path: str) -> Dict[str, Any]:
        clean_question = str(question or "").strip()
        clean_path = str(path or "").strip()
        if not clean_question:
            return self._failure("question_required", "Tender executive question is required.")
        if not clean_path:
            return self._failure("path_required", "Tender document path is required.")

        event_bus.publish(
            "TenderExecutiveStarted",
            "tender_executive",
            {
                "question": clean_question,
                "path": clean_path,
                "result": "started",
            },
        )

        try:
            text = self._read_document(clean_path)
            request_context = new_request_context()
            executive_extraction = self.executive_extractor.extract(text, document_type="Tender")
            commercial_result = self.commercial_engine.analyze(
                text=text,
                document_type="Tender",
                request_context=request_context,
            )
            risk_result = self.risk_register_engine.generate(
                text=text,
                document_type="Tender",
                request_context=request_context,
            )
            opportunity_result = self.opportunity_engine.evaluate(
                text=text,
                document_type="Tender",
                request_context=request_context,
            )
            bid_result = self.bid_engine.evaluate(
                text=text,
                document_type="Tender",
                request_context=request_context,
            )
            brief_result = self.brief_engine.generate(
                text=text,
                document_type="Tender",
                request_context=request_context,
            )
            action_plan_result = self.action_plan_engine.generate(
                text=text,
                document_type="Tender",
                request_context=request_context,
            )
            organization_impact = organization_impact_analysis.analyze(
                mission=clean_question,
                context={"path": clean_path, "document_type": "Tender"},
            )
            learning = execution_learning_engine.find_similar_patterns(clean_question)
            executive_reasoning = executive_reasoning_engine.reason(
                clean_question,
                context={"path": clean_path, "document_type": "Tender"},
            )

            result = self._assemble_response(
                question=clean_question,
                path=clean_path,
                executive_extraction=executive_extraction,
                commercial_result=commercial_result,
                risk_result=risk_result,
                opportunity_result=opportunity_result,
                bid_result=bid_result,
                brief_result=brief_result,
                action_plan_result=action_plan_result,
                organization_impact=organization_impact,
                learning=learning,
                executive_reasoning=executive_reasoning,
            )
            event_bus.publish(
                "TenderExecutiveCompleted",
                "tender_executive",
                {
                    "question": clean_question,
                    "path": clean_path,
                    "bid_decision": result.get("bid_decision", ""),
                    "confidence": result.get("confidence", 0),
                    "result": "success",
                },
            )
            return result
        except Exception as exc:
            event_bus.publish(
                "TenderExecutiveCompleted",
                "tender_executive",
                {
                    "question": clean_question,
                    "path": clean_path,
                    "result": "failed",
                    "reason": "tender_executive_error",
                },
            )
            return self._failure("tender_executive_error", f"Tender executive assessment failed: {exc}")

    def _assemble_response(
        self,
        question: str,
        path: str,
        executive_extraction: Dict[str, Any],
        commercial_result: Dict[str, Any],
        risk_result: Dict[str, Any],
        opportunity_result: Dict[str, Any],
        bid_result: Dict[str, Any],
        brief_result: Dict[str, Any],
        action_plan_result: Dict[str, Any],
        organization_impact: Dict[str, Any],
        learning: Dict[str, Any],
        executive_reasoning: Dict[str, Any],
    ) -> Dict[str, Any]:
        brief = brief_result.get("brief", {})
        decision = bid_result.get("decision", {})
        commercial = commercial_result.get("commercial_exposure", {})
        risk_register = risk_result.get("risk_register", {})
        opportunity = opportunity_result.get("opportunity_score", {})
        action_plan = action_plan_result.get("action_plan", {})

        bid_decision = self._bid_decision(
            bid_recommendation=decision.get("recommendation", ""),
            opportunity_recommendation=opportunity.get("bid_recommendation", ""),
            blockers=decision.get("blockers", []),
        )
        key_blockers = self._key_blockers(
            decision=decision,
            brief=brief,
            opportunity=opportunity,
            risk_register=risk_register,
        )
        required_departments = organization_impact.get("impacted_departments", []) or [
            "Commercial",
            "Procurement",
            "Finance",
            "Operations",
            "Legal",
            "Management",
        ]
        recommended_next_actions = self._recommended_actions(
            action_plan=action_plan,
            opportunity=opportunity,
            decision=decision,
            key_blockers=key_blockers,
        )
        executive_summary = self._executive_summary(
            bid_decision=bid_decision,
            brief=brief,
            opportunity=opportunity,
            commercial=commercial,
            risk_register=risk_register,
            key_blockers=key_blockers,
        )
        executive_reasoning_text = self._executive_reasoning(
            bid_decision=bid_decision,
            key_blockers=key_blockers,
            executive_reasoning=executive_reasoning,
            organization_impact=organization_impact,
        )

        return {
            "engine": "tender_executive",
            "status": "success",
            "question": question,
            "path": path,
            "executive_summary": executive_summary,
            "bid_decision": bid_decision,
            "confidence": self._confidence(
                brief=brief,
                executive_reasoning=executive_reasoning,
                decision=decision,
                opportunity=opportunity,
                executive_extraction=executive_extraction,
            ),
            "commercial_risk": str(commercial.get("overall_commercial_risk") or "Unknown"),
            "technical_risk": self._technical_risk(brief, risk_register),
            "key_blockers": key_blockers,
            "required_departments": required_departments,
            "recommended_next_actions": recommended_next_actions,
            "executive_reasoning": executive_reasoning_text,
            "executive_brief": {
                "executive_extraction": executive_extraction,
                "commercial_exposure": commercial_result,
                "risk_register": risk_result,
                "opportunity_scoring": opportunity_result,
                "bid_no_bid": bid_result,
                "decision_brief": brief_result,
                "action_plan": action_plan_result,
                "organization_impact": organization_impact,
                "learning": learning,
                "executive_reasoning": executive_reasoning,
            },
        }

    def _read_document(self, path: str) -> str:
        document_path = Path(path)
        if document_path.suffix.lower() in {".txt", ".md", ".csv"}:
            return document_path.read_text(encoding="utf-8", errors="ignore")
        return self.reader.read(path)

    def _bid_decision(
        self,
        bid_recommendation: str,
        opportunity_recommendation: str,
        blockers: List[Any],
    ) -> str:
        signal = f"{bid_recommendation} {opportunity_recommendation}".lower()
        if blockers or "insufficient" in signal or "review" in signal or "condition" in signal:
            return "Review"
        if "no go" in signal or "no-bid" in signal or "do not" in signal:
            return "No Bid"
        if "go" in signal or "bid" in signal:
            return "Bid"
        return "Review"

    def _key_blockers(
        self,
        decision: Dict[str, Any],
        brief: Dict[str, Any],
        opportunity: Dict[str, Any],
        risk_register: Dict[str, Any],
    ) -> List[str]:
        blockers = self._unique_text(
            decision.get("blockers", []),
            decision.get("missing_information", []),
            brief.get("missing_information", []),
            opportunity.get("key_concerns", []),
        )
        high_risks = [
            risk.get("title") or risk.get("description")
            for risk in risk_register.get("risks", [])
            if str(risk.get("severity", "")).lower() in {"high", "critical"}
        ]
        return self._unique_text(blockers, high_risks)[:8]

    def _recommended_actions(
        self,
        action_plan: Dict[str, Any],
        opportunity: Dict[str, Any],
        decision: Dict[str, Any],
        key_blockers: List[str],
    ) -> List[str]:
        actions = [
            action.get("title") or action.get("description")
            for action in action_plan.get("actions", [])
            if action.get("title") or action.get("description")
        ]
        actions = self._unique_text(
            actions,
            [opportunity.get("recommended_next_action", "")],
            decision.get("required_actions", []),
        )
        if not actions and key_blockers:
            actions = [f"Resolve blocker: {key_blockers[0]}"]
        return actions[:6]

    def _executive_summary(
        self,
        bid_decision: str,
        brief: Dict[str, Any],
        opportunity: Dict[str, Any],
        commercial: Dict[str, Any],
        risk_register: Dict[str, Any],
        key_blockers: List[str],
    ) -> str:
        source_summary = (
            opportunity.get("executive_summary")
            or brief.get("executive_summary")
            or "ATHENA completed the tender assessment."
        )
        review_reason = ""
        if bid_decision == "Review":
            if key_blockers:
                review_reason = f" Review is required because {key_blockers[0]}."
            else:
                review_reason = " Review is required because the available tender evidence is not sufficient for unconditional bid approval."
        return (
            f"{source_summary} Bid direction is {bid_decision}. "
            f"Commercial risk is {commercial.get('overall_commercial_risk', 'Unknown')} "
            f"and overall risk is {risk_register.get('overall_risk_level', 'Unknown')}."
            f"{review_reason}"
        )

    def _executive_reasoning(
        self,
        bid_decision: str,
        key_blockers: List[str],
        executive_reasoning: Dict[str, Any],
        organization_impact: Dict[str, Any],
    ) -> str:
        if key_blockers:
            reason = key_blockers[0]
        else:
            reason = executive_reasoning.get("executive_explanation") or organization_impact.get("impact_summary", "")
        return f"ATHENA recommends {bid_decision} because {str(reason).rstrip('.')}."

    def _technical_risk(self, brief: Dict[str, Any], risk_register: Dict[str, Any]) -> str:
        risk_text = " ".join(str(item).lower() for item in brief.get("key_risks", []))
        if "technical" in risk_text and ("high" in risk_text or "critical" in risk_text):
            return "High"
        if "technical" in risk_text:
            return "Medium"
        return risk_register.get("overall_risk_level", "Unknown")

    def _confidence(
        self,
        brief: Dict[str, Any],
        executive_reasoning: Dict[str, Any],
        decision: Dict[str, Any],
        opportunity: Dict[str, Any],
        executive_extraction: Dict[str, Any],
    ) -> int:
        prioritized_values = [
            brief.get("confidence"),
            executive_reasoning.get("confidence"),
            decision.get("confidence"),
            decision.get("score"),
            opportunity.get("confidence"),
            executive_extraction.get("confidence_score"),
        ]
        values = [
            value
            for value in (self._confidence_value(item) for item in prioritized_values)
            if value is not None and value > 0
        ]
        if values:
            return max(1, min(round(sum(values) / len(values)), 100))

        evidence_exists = any(
            item not in (None, "", [], {})
            for item in [brief, executive_reasoning, decision, opportunity, executive_extraction]
        )
        return 50 if evidence_exists else 0

    def _confidence_value(self, value: Any) -> Optional[int]:
        if value in (None, "", [], {}):
            return None

        if isinstance(value, str):
            normalized = value.strip().lower()
            label_map = {
                "high": 85,
                "medium": 65,
                "low": 45,
                "very high": 92,
                "very low": 30,
            }
            if normalized in label_map:
                return label_map[normalized]
            if normalized.endswith("%"):
                normalized = normalized[:-1].strip()
            try:
                numeric = float(normalized)
            except ValueError:
                return None
        else:
            try:
                numeric = float(value)
            except (TypeError, ValueError):
                return None

        return max(0, min(round(numeric), 100))

    def _unique_text(self, *groups: Any) -> List[str]:
        values = []
        seen = set()
        for group in groups:
            if not group:
                continue
            items = group if isinstance(group, list) else [group]
            for item in items:
                text = str(item or "").strip()
                key = text.lower()
                if text and key not in seen:
                    values.append(text)
                    seen.add(key)
        return values

    def _failure(self, reason: str, message: str) -> Dict[str, Any]:
        return {
            "engine": "tender_executive",
            "status": "failed",
            "reason": reason,
            "message": message,
        }


tender_executive = TenderExecutive()


def evaluate_tender(question: str, path: str) -> Dict[str, Any]:
    return tender_executive.evaluate_tender(question=question, path=path)
