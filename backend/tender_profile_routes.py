from fastapi import APIRouter

from tender_profile_engine import TenderProfileEngine


router = APIRouter(
    prefix="/tender-profiles",
    tags=["Tender Profile Engine"],
)

engine = TenderProfileEngine()


@router.get("/{tender_reference}")
async def get_tender_profile(tender_reference: str):

    result = engine.get_profile(
        tender_reference=tender_reference,
    )

    return {
        "engine": "tender_profile_engine",
        "name": "Tender Profile Engine",
        "status": "success",
        "result": result,
    }