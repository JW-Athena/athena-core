from typing import Any, Dict, List


class AthenaActionPlanner:
    """
    ATHENA Action Planner

    Converts a planning-only execution plan into an ordered future execution
    sequence. It never executes actions.
    """

    def plan(
        self,
        execution: Dict[str, Any],
        decision: Dict[str, Any],
        tasks: Dict[str, Any],
        notifications: Dict[str, Any],
        approval: Dict[str, Any],
    ) -> Dict[str, Any]:
        steps = []

        self._add_internal_steps(steps, execution, tasks)
        self._add_notification_steps(steps, notifications)
        self._add_external_communication_steps(steps, execution, approval)
        self._add_business_system_steps(steps, execution, approval)
        self._add_external_portal_steps(steps, execution, approval, decision)

        for index, step in enumerate(steps, start=1):
            step["step"] = index

        return {
            "ready": False,
            "steps": steps,
            "execution_mode": "planned",
            "estimated_sequence": self._estimated_sequence(steps),
            "summary": self._summary(steps=steps, approval=approval),
        }

    def _add_internal_steps(
        self,
        steps: List[Dict[str, Any]],
        execution: Dict[str, Any],
        tasks: Dict[str, Any],
    ) -> None:
        allowed = execution.get("allowed_actions", []) or []

        if "Prepare executive briefing" in allowed:
            self._add_step(
                steps,
                action="Prepare executive briefing",
                agent="future_email_agent",
                approval_required=False,
            )

        if tasks.get("generated") or "Create task list" in allowed:
            self._add_step(
                steps,
                action="Create task list",
                agent="future_desktop_agent",
                approval_required=False,
            )

        if "Prepare document checklist" in allowed:
            self._add_step(
                steps,
                action="Prepare document checklist",
                agent="future_desktop_agent",
                approval_required=False,
            )

        if "Prepare calendar follow-up" in allowed:
            self._add_step(
                steps,
                action="Prepare calendar follow-up",
                agent="future_calendar_agent",
                approval_required=False,
            )

    def _add_notification_steps(
        self,
        steps: List[Dict[str, Any]],
        notifications: Dict[str, Any],
    ) -> None:
        if notifications.get("generated"):
            self._add_step(
                steps,
                action="Prepare notification plan",
                agent="future_email_agent",
                approval_required=False,
            )

    def _add_external_communication_steps(
        self,
        steps: List[Dict[str, Any]],
        execution: Dict[str, Any],
        approval: Dict[str, Any],
    ) -> None:
        allowed = execution.get("allowed_actions", []) or []
        if "Prepare email draft" in allowed:
            self._add_step(
                steps,
                action="Prepare email draft",
                agent="future_email_agent",
                approval_required=False,
            )

        if self._approval_item_present(approval, "Sending external communications"):
            self._add_step(
                steps,
                action="Send external communication",
                agent="future_email_agent",
                approval_required=True,
            )

    def _add_business_system_steps(
        self,
        steps: List[Dict[str, Any]],
        execution: Dict[str, Any],
        approval: Dict[str, Any],
    ) -> None:
        if self._approval_item_present(approval, "Updating business systems"):
            self._add_step(
                steps,
                action="Update business system",
                agent="future_erp_agent",
                approval_required=True,
            )

    def _add_external_portal_steps(
        self,
        steps: List[Dict[str, Any]],
        execution: Dict[str, Any],
        approval: Dict[str, Any],
        decision: Dict[str, Any],
    ) -> None:
        if self._approval_item_present(approval, "Logging into external portals"):
            self._add_step(
                steps,
                action="Login to external portal",
                agent="future_tender_agent",
                approval_required=True,
            )

        if self._approval_item_present(approval, "Submitting tender documents"):
            self._add_step(
                steps,
                action="Submit tender",
                agent="future_tender_agent",
                approval_required=True,
            )

        if self._approval_item_present(approval, "Approving bid decision") or decision.get("status") == "approved":
            self._add_step(
                steps,
                action="Approve bid decision",
                agent="future_crm_agent",
                approval_required=True,
            )

    def _add_step(
        self,
        steps: List[Dict[str, Any]],
        action: str,
        agent: str,
        approval_required: bool,
    ) -> None:
        key = (action.lower(), agent)
        for step in steps:
            if (step["action"].lower(), step["agent"]) == key:
                return

        steps.append(
            {
                "step": 0,
                "action": action,
                "agent": agent,
                "approval_required": approval_required,
            }
        )

    def _approval_item_present(self, approval: Dict[str, Any], item: str) -> bool:
        return item in (approval.get("approval_items", []) or [])

    def _estimated_sequence(self, steps: List[Dict[str, Any]]) -> str:
        if not steps:
            return "No execution steps are currently planned."

        return "Internal planning, notifications, external communication, business systems, external portals."

    def _summary(self, steps: List[Dict[str, Any]], approval: Dict[str, Any]) -> str:
        if not steps:
            return "ATHENA did not prepare an execution sequence. No actions have been executed."

        approval_text = (
            "Management approval is required before external execution."
            if approval.get("required")
            else "No approval is required for internal planning outputs."
        )
        return (
            f"ATHENA prepared a {len(steps)}-step execution plan. "
            f"No actions have been executed. {approval_text}"
        )
