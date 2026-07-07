from typing import Any, Dict

from fastapi import APIRouter, Body, HTTPException

from engine_028_procurement_executive import evaluate_procurement


router = APIRouter(tags=["ATHENA Procurement Executive"])


@router.post("/athena/executive/procurement")
async def procurement_executive(payload: Dict[str, Any] = Body(default_factory=dict)):
    result = evaluate_procurement(
        question=str(payload.get("question", "") or ""),
        item=str(payload.get("item", "") or ""),
        supplier=str(payload.get("supplier", "") or ""),
    )
    if result.get("status") == "failed":
        raise HTTPException(status_code=400, detail=result)
    return result
