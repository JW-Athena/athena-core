from fastapi import APIRouter

from executive_decision_engine import ExecutiveDecisionEngine


router = APIRouter(
    prefix="/executive-decision",
    tags=["Executive Decision Engine"],
)

engine = ExecutiveDecisionEngine()


@router.get("/evaluate/{tender_reference}")
async def evaluate_tender(
    tender_reference: str,
):
    result = engine.evaluate_tender(
        tender_reference=tender_reference,
    )

    return {
        "engine": "executive_decision_engine",
        "name": "Executive Decision Engine",
        "status": "success",
        "result": result,
    }