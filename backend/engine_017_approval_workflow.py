from datetime import datetime
from typing import Any, Dict, List
from uuid import uuid4
import builtins

from event_bus import event_bus


class ApprovalWorkflow:
    def __init__(self):
        if not hasattr(builtins, "_ATHENA_MISSION_APPROVALS"):
            builtins._ATHENA_MISSION_APPROVALS = []
        self._approvals: List[Dict[str, Any]] = builtins._ATHENA_MISSION_APPROVALS

    def create_approval_request(
        self,
        mission_id: str,
        mission: str,
        reason: str,
        required_action: str,
        approval_payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        approval = {
            "approval_id": str(uuid4()),
            "mission_id": mission_id,
            "mission": mission,
            "status": "pending",
            "reason": reason,
            "required_action": required_action,
            "approval_payload": approval_payload,
            "created_at": datetime.utcnow().isoformat(),
            "resolved_at": None,
        }
        self._approvals.append(approval)

        event_bus.publish(
            "MissionApprovalRequired",
            "approval_workflow",
            {
                "approval_id": approval["approval_id"],
                "mission_id": mission_id,
                "mission": mission,
                "status": "pending",
                "result": "success",
            },
        )
        return dict(approval)

    def list_pending_approvals(self) -> Dict[str, Any]:
        records = [
            dict(approval)
            for approval in self._approvals
            if approval.get("status") == "pending"
        ]
        return {
            "engine": "approval_workflow",
            "status": "success",
            "count": len(records),
            "approvals": records,
        }

    def approve(self, approval_id: str, approved_by: str = "", note: str = "") -> Dict[str, Any]:
        approval = self._find_approval(approval_id)
        if not approval:
            return self._failure(approval_id, "approval_not_found", "Approval request was not found.")
        if approval.get("status") != "pending":
            return self._failure(approval_id, "approval_not_pending", "Approval request is not pending.")

        approval["status"] = "approved"
        approval["approved_by"] = str(approved_by or "")
        approval["note"] = str(note or "")
        approval["resolved_at"] = datetime.utcnow().isoformat()

        event_bus.publish(
            "MissionApproved",
            "approval_workflow",
            self._event_payload(approval, result="success"),
        )
        self.resume_mission(approval)

        return {
            "engine": "approval_workflow",
            "status": "success",
            "approval_id": approval_id,
            "approval_status": "approved",
            "message": "Mission approved.",
        }

    def reject(self, approval_id: str, rejected_by: str = "", reason: str = "") -> Dict[str, Any]:
        approval = self._find_approval(approval_id)
        if not approval:
            return self._failure(approval_id, "approval_not_found", "Approval request was not found.")
        if approval.get("status") != "pending":
            return self._failure(approval_id, "approval_not_pending", "Approval request is not pending.")

        approval["status"] = "rejected"
        approval["rejected_by"] = str(rejected_by or "")
        approval["rejection_reason"] = str(reason or "")
        approval["resolved_at"] = datetime.utcnow().isoformat()

        event_bus.publish(
            "MissionRejected",
            "approval_workflow",
            self._event_payload(approval, result="success"),
        )

        return {
            "engine": "approval_workflow",
            "status": "success",
            "approval_id": approval_id,
            "approval_status": "rejected",
            "message": "Mission rejected.",
        }

    def resume_mission(self, approval: Dict[str, Any]) -> Dict[str, Any]:
        approval["status"] = "resumed"
        event_bus.publish(
            "MissionResumed",
            "approval_workflow",
            self._event_payload(approval, result="success"),
        )
        return {
            "engine": "approval_workflow",
            "status": "success",
            "approval_id": approval.get("approval_id", ""),
            "approval_status": "resumed",
            "message": "Mission resumed.",
        }

    def _find_approval(self, approval_id: str) -> Dict[str, Any]:
        clean_id = str(approval_id or "").strip()
        for approval in self._approvals:
            if approval.get("approval_id") == clean_id:
                return approval
        return {}

    def _event_payload(self, approval: Dict[str, Any], result: str) -> Dict[str, Any]:
        return {
            "approval_id": approval.get("approval_id", ""),
            "mission_id": approval.get("mission_id", ""),
            "mission": approval.get("mission", ""),
            "status": approval.get("status", ""),
            "result": result,
        }

    def _failure(self, approval_id: str, reason: str, message: str) -> Dict[str, Any]:
        return {
            "engine": "approval_workflow",
            "status": "failed",
            "approval_id": approval_id,
            "reason": reason,
            "message": message,
        }


approval_workflow = ApprovalWorkflow()
