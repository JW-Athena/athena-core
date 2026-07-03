from fastapi import APIRouter, Query

from engine_014_adaptive_planner import adaptive_summary, objective_history


router = APIRouter(tags=["ATHENA Executive Brain Adaptive Planning"])


@router.get("/athena/brain/adaptive-summary")
async def get_adaptive_summary():
    return adaptive_summary()


@router.get("/athena/brain/objective-history")
async def get_objective_history(objective_type: str = Query(default="")):
    return objective_history(objective_type=objective_type)
