from typing import Any, Dict

from fastapi import APIRouter, Body, HTTPException

from engine_019_strategic_objective_manager import strategic_objective_manager


router = APIRouter(tags=["ATHENA Strategic Objective Manager"])


@router.post("/athena/strategic-objectives")
async def create_strategic_objective(payload: Dict[str, Any] = Body(default_factory=dict)):
    result = strategic_objective_manager.create_strategic_objective(
        title=str(payload.get("title", "") or ""),
        description=str(payload.get("description", "") or ""),
        priority=str(payload.get("priority", "medium") or "medium"),
    )
    return _raise_on_failure(result)


@router.get("/athena/strategic-objectives")
async def list_strategic_objectives():
    return strategic_objective_manager.list_strategic_objectives()


@router.get("/athena/strategic-objectives/{strategic_objective_id}")
async def get_strategic_objective(strategic_objective_id: str):
    result = strategic_objective_manager.get_strategic_objective(strategic_objective_id)
    return _raise_on_failure(result)


@router.post("/athena/strategic-objectives/{strategic_objective_id}/attach-mission")
async def attach_mission(
    strategic_objective_id: str,
    payload: Dict[str, Any] = Body(default_factory=dict),
):
    mission_payload = payload.get("mission_result", payload)
    result = strategic_objective_manager.attach_mission(
        strategic_objective_id=strategic_objective_id,
        mission=mission_payload if isinstance(mission_payload, dict) else {},
    )
    return _raise_on_failure(result)


@router.post("/athena/strategic-objectives/{strategic_objective_id}/status")
async def update_strategic_objective_status(
    strategic_objective_id: str,
    payload: Dict[str, Any] = Body(default_factory=dict),
):
    result = strategic_objective_manager.update_status(
        strategic_objective_id=strategic_objective_id,
        status=str(payload.get("status", "") or ""),
    )
    return _raise_on_failure(result)


@router.get("/athena/strategic-objectives/{strategic_objective_id}/next-mission")
async def recommend_next_mission(strategic_objective_id: str):
    result = strategic_objective_manager.recommend_next_mission(strategic_objective_id)
    return _raise_on_failure(result)


def _raise_on_failure(result: Dict[str, Any]) -> Dict[str, Any]:
    if result.get("status") != "failed":
        return result

    reason = result.get("reason", "")
    status_code = 404 if reason == "strategic_objective_not_found" else 400
    raise HTTPException(status_code=status_code, detail=result)
