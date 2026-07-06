from typing import Any, Dict

from fastapi import APIRouter, Body, HTTPException

from engine_024_executive_reasoning_engine import executive_reasoning_engine


router = APIRouter(tags=["ATHENA Executive Reasoning Engine"])


@router.post("/athena/reasoning/executive")
async def executive_reasoning(payload: Dict[str, Any] = Body(default_factory=dict)):
    context = payload.get("context", {})
    result = executive_reasoning_engine.reason(
        question=str(payload.get("question", "") or ""),
        context=context if isinstance(context, dict) else {},
    )
    if result.get("status") == "failed":
        raise HTTPException(status_code=400, detail=result)
    return result
