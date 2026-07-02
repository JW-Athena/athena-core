from fastapi import APIRouter, Query

from event_bus import event_bus


router = APIRouter(tags=["ATHENA Event Bus"])


@router.get("/athena/events")
async def latest_events(limit: int = Query(default=100, ge=1, le=250)):
    return {
        "engine": "event_bus",
        "status": "success",
        "events": event_bus.latest(limit=limit),
    }
