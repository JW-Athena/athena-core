from typing import Any, Dict, Optional

from fastapi import APIRouter, Body

from organization_awareness import organization_awareness


router = APIRouter(tags=["ATHENA Organizational Awareness"])


@router.post("/athena/organization/state")
async def organization_state(payload: Optional[Dict[str, Any]] = Body(default=None)):
    state = organization_awareness.update_from_input(payload)

    return {
        "engine": "organization_awareness",
        "status": "success",
        "organization_state": state,
    }
