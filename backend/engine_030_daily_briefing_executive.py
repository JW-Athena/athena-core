from typing import Any, Dict, List

from engine_017_approval_workflow import approval_workflow
from engine_018_operations_center import operations_center
from engine_019_strategic_objective_manager import strategic_objective_manager
from engine_020_organization_model import organization_model
from event_bus import event_bus


class DailyBriefingExecutive:
    def generate_briefing(self) -> Dict[str, Any]:
        operations = operations_center.overview()
        missions = operations_center.live_missions()
        approvals = approval_workflow.list_pending_approvals()
        objectives = strategic_objective_manager.list_strategic_objectives()
        organization = organization_model.organization_summary()

        result = self._assemble_response(operations, missions, approvals, objectives, organization)
        event_bus.publish(
            "DailyBriefingGenerated",
            "daily_briefing_executive",
            {"priorities": len(result.get("priorities", [])), "pending_approvals": len(result.get("pending_approvals", [])), "result": "success"},
        )
        return result

    def _assemble_response(
        self,
        operations: Dict[str, Any],
        missions: Dict[str, Any],
        approvals: Dict[str, Any],
        objectives: Dict[str, Any],
        organization: Dict[str, Any],
    ) -> Dict[str, Any]:
        pending_approvals = approvals.get("approvals", [])
        active_missions = missions.get("current_missions", [])
        active_objectives = [
            item for item in objectives.get("strategic_objectives", [])
            if item.get("status") == "active"
        ]
        risks = self._risks(operations, pending_approvals, active_objectives, organization)
        priorities = self._priorities(pending_approvals, active_missions, active_objectives, risks)

        return {
            "engine": "daily_briefing_executive",
            "status": "success",
            "greeting": "Good morning, Wassim.",
            "executive_summary": self._executive_summary(operations, pending_approvals, active_missions, active_objectives, risks),
            "priorities": priorities,
            "pending_approvals": pending_approvals[:6],
            "active_missions": active_missions[:6],
            "strategic_objectives": active_objectives[:6],
            "risks": risks,
            "recommended_focus": self._recommended_focus(priorities, risks),
        }

    def _priorities(
        self,
        approvals: List[Dict[str, Any]],
        missions: List[Dict[str, Any]],
        objectives: List[Dict[str, Any]],
        risks: List[str],
    ) -> List[str]:
        priorities = []
        if approvals:
            priorities.append(f"Resolve {len(approvals)} pending approval(s).")
        if missions:
            priorities.append(f"Review {len(missions)} active mission(s) and unblock execution.")
        critical_objectives = [item for item in objectives if item.get("priority") == "critical"]
        if critical_objectives:
            priorities.append(f"Advance critical objective: {critical_objectives[0].get('title', '')}.")
        elif objectives:
            priorities.append(f"Advance strategic objective: {objectives[0].get('title', '')}.")
        if risks:
            priorities.append(f"Address top risk: {risks[0]}")
        if not priorities:
            priorities.append("Set one executive objective for today and assign the next mission.")
        return priorities[:6]

    def _risks(
        self,
        operations: Dict[str, Any],
        approvals: List[Dict[str, Any]],
        objectives: List[Dict[str, Any]],
        organization: Dict[str, Any],
    ) -> List[str]:
        risks = []
        timeline = operations.get("timeline", {})
        if timeline.get("errors", 0):
            risks.append(f"{timeline.get('errors')} operational error(s) require attention.")
        if approvals:
            risks.append("Pending approvals may delay execution.")
        high_risk_suppliers = organization.get("statistics", {}).get("high_risk_suppliers", 0)
        if high_risk_suppliers:
            risks.append(f"{high_risk_suppliers} high-risk supplier(s) are recorded in the organization model.")
        stalled = [item for item in objectives if int(item.get("progress", 0) or 0) == 0]
        if stalled:
            risks.append(f"{len(stalled)} active strategic objective(s) have no recorded progress.")
        return risks[:6]

    def _executive_summary(
        self,
        operations: Dict[str, Any],
        approvals: List[Dict[str, Any]],
        missions: List[Dict[str, Any]],
        objectives: List[Dict[str, Any]],
        risks: List[str],
    ) -> str:
        return (
            f"ATHENA is online and operations are {operations.get('system_status', 'unknown')}. "
            f"There are {len(approvals)} pending approval(s), {len(missions)} active mission(s), "
            f"and {len(objectives)} active strategic objective(s). "
            f"Top risk: {risks[0] if risks else 'no critical risk is visible from current operating data'}."
        )

    def _recommended_focus(self, priorities: List[str], risks: List[str]) -> str:
        if priorities:
            return priorities[0]
        if risks:
            return f"Resolve {risks[0]}"
        return "Define today's executive decision and start one focused mission."


daily_briefing_executive = DailyBriefingExecutive()


def generate_daily_briefing() -> Dict[str, Any]:
    return daily_briefing_executive.generate_briefing()
