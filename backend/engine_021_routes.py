from typing import Any, Dict

from fastapi import APIRouter, Body, HTTPException

from engine_021_organization_impact import organization_impact_analysis


router = APIRouter(tags=["ATHENA Organization Impact Analysis"])


@router.post("/athena/organization/impact")
async def analyze_organization_impact(payload: Dict[str, Any] = Body(default_factory=dict)):
    context = payload.get("context", {})
    result = organization_impact_analysis.analyze(
        mission=str(payload.get("mission", "") or ""),
        context=context if isinstance(context, dict) else {},
    )
    if result.get("status") == "failed":
        raise HTTPException(status_code=400, detail=result)
    return result
