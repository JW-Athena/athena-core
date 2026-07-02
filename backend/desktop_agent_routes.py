from fastapi import APIRouter

from desktop_agent import desktop_agent


router = APIRouter(tags=["ATHENA Desktop Agent"])


@router.get("/athena/desktop/status")
async def desktop_status():
    return {
        "engine": "desktop_agent",
        "status": "success",
        "desktop": desktop_agent.status(),
    }
