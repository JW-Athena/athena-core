from fastapi import APIRouter

from dashboard_engine import DashboardEngine


router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"],
)

engine = DashboardEngine()


@router.get("/summary")
async def dashboard_summary():
    return {
        "engine": "dashboard",
        "status": "success",
        "summary": engine.get_summary(),
    }