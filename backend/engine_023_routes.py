from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from engine_023_reasoning_graph import executive_reasoning_graph


router = APIRouter(tags=["ATHENA Executive Reasoning Graph"])


@router.get("/athena/reasoning/trace/{node_id}")
async def trace_reasoning(node_id: str):
    result = executive_reasoning_graph.trace_reasoning(node_id)
    return _raise_on_failure(result)


@router.get("/athena/reasoning/impact/{node_id}")
async def find_business_impact(node_id: str):
    result = executive_reasoning_graph.find_business_impact(node_id)
    return _raise_on_failure(result)


def _raise_on_failure(result: Dict[str, Any]) -> Dict[str, Any]:
    if result.get("status") != "failed":
        return result

    reason = result.get("reason", "")
    status_code = 404 if reason.endswith("_not_found") else 400
    raise HTTPException(status_code=status_code, detail=result)
