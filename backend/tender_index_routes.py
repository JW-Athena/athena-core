from fastapi import APIRouter

from tender_index_engine import TenderIndexEngine


router = APIRouter(
    prefix="/tenders",
    tags=["Tender Index"],
)

engine = TenderIndexEngine()


@router.get("/")
async def list_tenders():

    return {
        "engine": "tender_index",
        "status": "success",
        "count": len(engine.list_tenders()),
        "tenders": engine.list_tenders(),
    }