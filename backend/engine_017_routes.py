from typing import Any, Dict

from fastapi import APIRouter, Body

from engine_017_approval_workflow import approval_workflow


router = APIRouter(tags=["ATHENA Mission Approval Workflow"])


@router.get("/athena/brain/pending-approvals")
async def pending_approvals():
    return approval_workflow.list_pending_approvals()


@router.post("/athena/brain/approve-mission")
async def approve_mission(payload: Dict[str, Any] = Body(default_factory=dict)):
    return approval_workflow.approve(
        approval_id=str(payload.get("approval_id", "") or ""),
        approved_by=str(payload.get("approved_by", "") or ""),
        note=str(payload.get("note", "") or ""),
    )


@router.post("/athena/brain/reject-mission")
async def reject_mission(payload: Dict[str, Any] = Body(default_factory=dict)):
    return approval_workflow.reject(
        approval_id=str(payload.get("approval_id", "") or ""),
        rejected_by=str(payload.get("rejected_by", "") or ""),
        reason=str(payload.get("reason", "") or ""),
    )
