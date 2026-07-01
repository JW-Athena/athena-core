from fastapi import APIRouter

from tender_comparison_engine import TenderComparisonEngine


router = APIRouter(
    prefix="/tender-comparison",
    tags=["Tender Comparison Engine"],
)

engine = TenderComparisonEngine()


@router.get("/compare")
async def compare_all_tenders():

    result = engine.compare_all()

    return {
        "engine": "tender_comparison",
        "name": "Tender Comparison Engine",
        "status": "success",
        "result": result,
    }