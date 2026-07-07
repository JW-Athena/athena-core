from typing import Any, Dict

from fastapi import APIRouter, Body, HTTPException

from engine_027_contract_executive import evaluate_contract


router = APIRouter(tags=["ATHENA Contract Executive"])


@router.post("/athena/executive/contract")
async def contract_executive(payload: Dict[str, Any] = Body(default_factory=dict)):
    result = evaluate_contract(
        question=str(payload.get("question", "") or ""),
        path=str(payload.get("path", "") or ""),
    )
    if result.get("status") == "failed":
        raise HTTPException(status_code=400, detail=result)
    return result
