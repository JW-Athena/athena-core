from typing import Any, Dict, List

from engine_018_operations_center import operations_center
from engine_019_strategic_objective_manager import strategic_objective_manager
from engine_020_organization_model import organization_model
from engine_021_organization_impact import organization_impact_analysis
from engine_024_executive_reasoning_engine import executive_reasoning_engine
from event_bus import event_bus


class MeetingExecutive:
    def prepare_meeting(self, meeting: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        clean_meeting = str(meeting or "").strip()
        if not clean_meeting:
            return self._failure("meeting_required", "Meeting description is required.")
        safe_context = context if isinstance(context, dict) else {}

        event_bus.publish(
            "MeetingExecutiveStarted",
            "meeting_executive",
            {"meeting": clean_meeting, "result": "started"},
        )

        try:
            organization = organization_model.organization_summary()
            objectives = strategic_objective_manager.list_strategic_objectives()
            operations = operations_center.overview()
            impact = organization_impact_analysis.analyze(clean_meeting, context=safe_context)
            reasoning = executive_reasoning_engine.reason(clean_meeting, context=safe_context)
            result = self._assemble_response(clean_meeting, safe_context, organization, objectives, operations, impact, reasoning)
            event_bus.publish(
                "MeetingExecutiveCompleted",
                "meeting_executive",
                {"meeting": clean_meeting, "recommended_position": result.get("recommended_position", ""), "result": "success"},
            )
            return result
        except Exception as exc:
            event_bus.publish(
                "MeetingExecutiveCompleted",
                "meeting_executive",
                {"meeting": clean_meeting, "reason": "meeting_executive_error", "result": "failed"},
            )
            return self._failure("meeting_executive_error", f"Meeting executive preparation failed: {exc}")

    def _assemble_response(
        self,
        meeting: str,
        context: Dict[str, Any],
        organization: Dict[str, Any],
        objectives: Dict[str, Any],
        operations: Dict[str, Any],
        impact: Dict[str, Any],
        reasoning: Dict[str, Any],
    ) -> Dict[str, Any]:
        departments = impact.get("impacted_departments", []) or [item.get("name", "") for item in organization.get("departments", [])[:3]]
        risks = self._risks_to_raise(impact, operations, reasoning)
        objective = self._meeting_objective(meeting, reasoning)
        return {
            "engine": "meeting_executive",
            "status": "success",
            "executive_summary": f"ATHENA prepared the meeting around one objective: {objective}",
            "meeting_objective": objective,
            "agenda": self._agenda(meeting, departments, objectives),
            "key_talking_points": self._talking_points(reasoning, objectives, impact),
            "risks_to_raise": risks,
            "questions_to_ask": self._questions_to_ask(meeting, risks, context),
            "documents_to_prepare": self._documents_to_prepare(meeting, departments),
            "recommended_position": self._recommended_position(reasoning, risks),
        }

    def _meeting_objective(self, meeting: str, reasoning: Dict[str, Any]) -> str:
        recommendation = str(reasoning.get("recommended_next_action") or reasoning.get("executive_recommendation") or "").strip()
        if recommendation:
            return recommendation.rstrip(".")
        return f"Align decision, risks, owners, and next action for {meeting}"

    def _agenda(self, meeting: str, departments: List[str], objectives: Dict[str, Any]) -> List[str]:
        active_objectives = [item.get("title", "") for item in objectives.get("strategic_objectives", []) if item.get("status") == "active"]
        agenda = [
            f"Confirm desired outcome for {meeting}.",
            "Review current facts, constraints, and decision deadline.",
            f"Confirm department ownership: {self._human_join(departments)}.",
        ]
        if active_objectives:
            agenda.append(f"Check alignment with strategic objective: {active_objectives[0]}.")
        agenda.append("Agree decision, owner, and immediate next action.")
        return agenda

    def _talking_points(self, reasoning: Dict[str, Any], objectives: Dict[str, Any], impact: Dict[str, Any]) -> List[str]:
        points = self._unique_text(reasoning.get("key_findings", []), [impact.get("impact_summary", "")])
        active = [item.get("title", "") for item in objectives.get("strategic_objectives", []) if item.get("status") == "active"]
        if active:
            points.append(f"Keep discussion aligned to {active[0]}.")
        return self._unique_text(points)[:6]

    def _risks_to_raise(self, impact: Dict[str, Any], operations: Dict[str, Any], reasoning: Dict[str, Any]) -> List[str]:
        risks = []
        if impact.get("requires_management_attention"):
            risks.append(impact.get("impact_summary") or "Meeting subject requires management attention.")
        approvals = operations.get("approvals", {})
        if approvals.get("pending", 0):
            risks.append(f"{approvals.get('pending')} pending approval(s) may affect execution.")
        risks.extend([item for item in reasoning.get("key_findings", []) if "limited" in item.lower() or "no " in item.lower()])
        return self._unique_text(risks)[:6]

    def _questions_to_ask(self, meeting: str, risks: List[str], context: Dict[str, Any]) -> List[str]:
        questions = [
            "What decision must be made in this meeting?",
            "Who owns execution after the meeting?",
            "What evidence would change the decision?",
        ]
        if risks:
            questions.append(f"How should we resolve this risk: {risks[0]}")
        if context:
            questions.append("Which context item is mandatory for the final decision?")
        return questions[:6]

    def _documents_to_prepare(self, meeting: str, departments: List[str]) -> List[str]:
        docs = ["One-page executive brief", "Decision log with owner and deadline", "Risk and dependency list"]
        if "contract" in meeting.lower():
            docs.append("Contract terms and obligations summary")
        if "procure" in meeting.lower() or "supplier" in meeting.lower():
            docs.append("Supplier and procurement evidence summary")
        if departments:
            docs.append(f"Department input from {departments[0]}")
        return self._unique_text(docs)[:6]

    def _recommended_position(self, reasoning: Dict[str, Any], risks: List[str]) -> str:
        if risks:
            return f"Enter the meeting with a review position until the primary risk is resolved: {risks[0]}"
        return reasoning.get("executive_recommendation") or "Enter the meeting seeking a clear decision, named owner, and immediate next action."

    def _human_join(self, values: List[Any]) -> str:
        clean = [str(value or "").strip() for value in values if str(value or "").strip()]
        if not clean:
            return "relevant owners"
        if len(clean) == 1:
            return clean[0]
        if len(clean) == 2:
            return f"{clean[0]} and {clean[1]}"
        return f"{', '.join(clean[:-1])}, and {clean[-1]}"

    def _unique_text(self, *groups: Any) -> List[str]:
        values = []
        seen = set()
        for group in groups:
            items = group if isinstance(group, list) else [group]
            for item in items:
                text = str(item or "").strip()
                key = text.lower()
                if text and key not in seen:
                    values.append(text)
                    seen.add(key)
        return values

    def _failure(self, reason: str, message: str) -> Dict[str, Any]:
        return {"engine": "meeting_executive", "status": "failed", "reason": reason, "message": message}


meeting_executive = MeetingExecutive()


def prepare_meeting(meeting: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
    return meeting_executive.prepare_meeting(meeting=meeting, context=context)
