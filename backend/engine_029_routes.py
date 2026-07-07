from typing import Any, Dict

from fastapi import APIRouter, Body, HTTPException

from engine_029_meeting_executive import prepare_meeting


router = APIRouter(tags=["ATHENA Meeting Executive"])


@router.post("/athena/executive/meeting-prep")
async def meeting_executive(payload: Dict[str, Any] = Body(default_factory=dict)):
    context = payload.get("context", {})
    result = prepare_meeting(
        meeting=str(payload.get("meeting", "") or ""),
        context=context if isinstance(context, dict) else {},
    )
    if result.get("status") == "failed":
        raise HTTPException(status_code=400, detail=result)
    return result
