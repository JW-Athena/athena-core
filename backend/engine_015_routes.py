from typing import Any, Dict

from fastapi import APIRouter, Body

from engine_015_mission_controller import mission_controller


router = APIRouter(tags=["ATHENA Executive Mission Controller"])


@router.post("/athena/brain/execute-mission")
async def execute_mission(payload: Dict[str, Any] = Body(default_factory=dict)):
    return await mission_controller.execute_mission(
        mission=str(payload.get("mission", "") or ""),
        path=str(payload.get("path", "") or ""),
    )
