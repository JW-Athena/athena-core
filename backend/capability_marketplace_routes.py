from fastapi import APIRouter

from capability_marketplace import capability_marketplace


router = APIRouter(tags=["ATHENA Capability Marketplace"])


@router.get("/athena/capabilities")
async def list_capabilities():
    return {
        "engine": "capability_marketplace",
        "status": "success",
        "capabilities": capability_marketplace.list_capabilities(),
    }
