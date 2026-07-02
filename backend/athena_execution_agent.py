from typing import Any, Dict, List


class AthenaExecutionAgent:
    """
    ATHENA Execution Agent

    Converts decisions, tasks, and notifications into a planning-only execution
    plan. It never performs real-world actions.
    """

    BLOCKED_ACTIONS = [
        "Send email",
        "Submit tender",
        "Modify ERP",
        "Login to external portal",
        "Delete files",
        "Approve bid",
        "Financial commitment",
    ]

    APPROVAL_REQUIRED_FOR = [
        "Sending external communications",
        "Submitting tender documents",
        "Updating business systems",
        "Approving bid decision",
        "Logging into external portals",
    ]

    def plan(
        self,
        decision: Dict[str, Any],
        tasks: Dict[str, Any],
        notifications: Dict[str, Any],
        reasoning: Dict[str, Any],
        clarification: Dict[str, Any],
    ) -> Dict[str, Any]:
        execution_status = self._execution_status(decision)
        allowed_actions = self._allowed_actions(
            decision=decision,
            tasks=tasks,
            notifications=notifications,
            reasoning=reasoning,
            clarification=clarification,
        )

        return {
            "enabled": False,
            "mode": "planning_only",
            "authorization_required": True,
            "execution_status": execution_status,
            "allowed_actions": allowed_actions,
            "blocked_actions": list(self.BLOCKED_ACTIONS),
            "approval_required_for": list(self.APPROVAL_REQUIRED_FOR),
            "execution_summary": self._execution_summary(
                decision=decision,
                execution_status=execution_status,
            ),
            "next_execution_step": self._next_execution_step(
                decision=decision,
                execution_status=execution_status,
                clarification=clarification,
            ),
        }

    def _execution_status(self, decision: Dict[str, Any]) -> str:
        status = str(decision.get("status") or "").lower()
        if status == "approved":
            return "ready_for_automation"
        if status == "conditional":
            return "pending_approval"
        if status in {"blocked", "rejected"}:
            return "blocked"
        return "pending_approval"

    def _allowed_actions(
        self,
        decision: Dict[str, Any],
        tasks: Dict[str, Any],
        notifications: Dict[str, Any],
        reasoning: Dict[str, Any],
        clarification: Dict[str, Any],
    ) -> List[str]:
        actions = [
            "Prepare executive briefing",
        ]

        if tasks.get("generated"):
            actions.append("Create task list")

        if notifications.get("generated"):
            actions.append("Prepare notification plan")

        if decision.get("status") in {"approved", "conditional"}:
            actions.append("Prepare email draft")
            actions.append("Prepare calendar follow-up")

        if reasoning.get("missing_information") or clarification.get("needed"):
            actions.append("Prepare document checklist")

        return self._dedupe(actions)

    def _execution_summary(
        self,
        decision: Dict[str, Any],
        execution_status: str,
    ) -> str:
        status = str(decision.get("status") or "unknown").lower()
        if execution_status == "ready_for_automation":
            return "Execution is planning-only; the decision is approved but automation remains disabled pending authorization."
        if execution_status == "pending_approval":
            return "Execution is planning-only; management approval is required before any real-world action."
        return f"Execution is planning-only and blocked because the decision status is {status}."

    def _next_execution_step(
        self,
        decision: Dict[str, Any],
        execution_status: str,
        clarification: Dict[str, Any],
    ) -> str:
        if clarification.get("needed"):
            return "Resolve the clarification before execution planning advances."
        if execution_status == "ready_for_automation":
            return "Review and authorize any future automation before execution."
        if execution_status == "pending_approval":
            return "Obtain management approval before any external action."
        if decision.get("status") == "rejected":
            return "Record the rejection decision and take no external action."
        return "Resolve blocking factors before any execution step."

    def _dedupe(self, values: List[str]) -> List[str]:
        deduped = []
        for value in values:
            if value not in deduped:
                deduped.append(value)
        return deduped
