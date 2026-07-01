from fastapi import APIRouter

from module_registry import registry


router = APIRouter(
    prefix="/modules",
    tags=["ATHENA Modules"],
)


@router.get("/")
async def modules():

    return {
        "status": "success",
        "count": registry.module_count(),
        "modules": registry.list_modules(),
    }