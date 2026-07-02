from fastapi import APIRouter

from athena_runtime_manager import athena_runtime_manager


router = APIRouter(tags=["ATHENA Runtime Manager"])


@router.get("/athena/runtime/status")
async def runtime_status():
    return {
        "engine": "athena_runtime",
        "status": "success",
        "runtime": athena_runtime_manager.status(),
    }
