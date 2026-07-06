from typing import Any, Dict

from fastapi import APIRouter, Body, HTTPException

from engine_025_tender_executive import evaluate_tender


router = APIRouter(tags=["ATHENA Tender Executive"])


@router.post("/athena/executive/tender")
async def tender_executive(payload: Dict[str, Any] = Body(default_factory=dict)):
    result = evaluate_tender(
        question=str(payload.get("question", "") or ""),
        path=str(payload.get("path", "") or ""),
    )
    if result.get("status") == "failed":
        raise HTTPException(status_code=400, detail=result)
    return result
