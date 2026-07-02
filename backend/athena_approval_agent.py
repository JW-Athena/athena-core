from typing import Any, Dict, List


class AthenaApprovalAgent:
    """
    ATHENA Approval Agent

    Determines whether future execution actions require executive approval.
    It never grants approval and never executes actions.
    """

    APPROVAL_ACTIONS = {
        "Send email": "Sending external communications",
        "Submit tender": "Submitting tender documents",
        "Modify ERP": "Updating business systems",
        "Login to external portal": "Logging into external portals",
        "Delete files": "Deleting business data",
        "Approve bid": "Approving bid decision",
        "Financial commitment": "Making a financial commitment",
    }

    def evaluate(
        self,
        decision: Dict[str, Any],
        tasks: Dict[str, Any],
        notifications: Dict[str, Any],
        execution: Dict[str, Any],
    ) -> Dict[str, Any]:
        approval_items = self._approval_items(
            decision=decision,
            tasks=tasks,
            notifications=notifications,
            execution=execution,
        )
        required = bool(approval_items)

        return {
            "required": required,
            "status": "waiting" if required else "not_required",
            "approver_role": "Management",
            "approval_reason": self._approval_reason(
                required=required,
                decision=decision,
                approval_items=approval_items,
            ),
            "approval_items": approval_items,
            "auto_approvable": False,
            "approval_summary": self._approval_summary(
                required=required,
                approval_items=approval_items,
            ),
        }

    def _approval_items(
        self,
        decision: Dict[str, Any],
        tasks: Dict[str, Any],
        notifications: Dict[str, Any],
        execution: Dict[str, Any],
    ) -> List[str]:
        items = []

        for action in execution.get("blocked_actions", []) or []:
            mapped = self.APPROVAL_ACTIONS.get(action)
            if mapped:
                items.append(mapped)

        for item in execution.get("approval_required_for", []) or []:
            items.append(str(item))

        for task in tasks.get("items", []) or []:
            title = str(task.get("title") or "").lower()
            if any(term in title for term in ["submit tender", "approve bid", "financial commitment", "external"]):
                items.append(task.get("title", "Approving external action"))

        return self._dedupe(items)

    def _approval_reason(
        self,
        required: bool,
        decision: Dict[str, Any],
        approval_items: List[str],
    ) -> str:
        if not required:
            return "Only internal planning actions are proposed."

        if decision.get("status") in {"conditional", "blocked", "rejected"}:
            return "Management approval is required before any external or binding action."

        if approval_items:
            return "Future execution includes actions that require management authorization."

        return "Management approval is required before execution."

    def _approval_summary(self, required: bool, approval_items: List[str]) -> str:
        if not required:
            return "No approval is required for internal planning outputs."

        return "Approval is required before any external communication, system update, tender submission, or binding commitment."

    def _dedupe(self, values: List[str]) -> List[str]:
        deduped = []
        for value in values:
            text = str(value or "").strip()
            if text and text not in deduped:
                deduped.append(text)
        return deduped
