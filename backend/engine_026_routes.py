from typing import Any, Dict

from fastapi import APIRouter, Body, HTTPException

from engine_026_supplier_executive import evaluate_supplier


router = APIRouter(tags=["ATHENA Supplier Executive"])


@router.post("/athena/executive/supplier")
async def supplier_executive(payload: Dict[str, Any] = Body(default_factory=dict)):
    result = evaluate_supplier(
        question=str(payload.get("question", "") or ""),
        supplier=str(payload.get("supplier", "") or ""),
    )
    if result.get("status") == "failed":
        raise HTTPException(status_code=400, detail=result)
    return result
