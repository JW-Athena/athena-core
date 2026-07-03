from fastapi import APIRouter, Query

from engine_018_operations_center import operations_center


router = APIRouter(tags=["ATHENA Operations Center"])


@router.get("/athena/operations/overview")
async def operations_overview():
    return operations_center.overview()


@router.get("/athena/operations/health")
async def operations_health():
    return operations_center.health()


@router.get("/athena/operations/live-missions")
async def operations_live_missions():
    return operations_center.live_missions()


@router.get("/athena/operations/live-events")
async def operations_live_events(limit: int = Query(default=100, ge=1, le=250)):
    return operations_center.live_events(limit=limit)


@router.get("/athena/operations/timeline")
async def operations_timeline(limit: int = Query(default=50, ge=1, le=250)):
    return operations_center.get_operations_timeline(limit=limit)
