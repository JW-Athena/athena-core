from typing import Any, Dict

from fastapi import APIRouter, Body

from athena_decision_engine import AthenaDecisionEngine
from event_bus import event_bus


router = APIRouter(tags=["ATHENA Decision Engine"])
decision_engine = AthenaDecisionEngine()


@router.post("/athena/decision/evaluate-recommendation")
async def evaluate_recommendation(payload: Dict[str, Any] = Body(default_factory=dict)):
    result = decision_engine.evaluate_recommendation(payload.get("recommendation"))
    status = result.get("status", "blocked")
    decision = result.get("decision", {})

    if status == "success":
        event_bus.publish(
            "DecisionRecommendationEvaluated",
            "decision_engine",
            {
                "outcome": decision.get("outcome", ""),
                "next_step": decision.get("next_step", ""),
                "risk": decision.get("risk", ""),
                "requires_approval": bool(decision.get("requires_approval", False)),
                "result": "success",
            },
        )
    else:
        event_bus.publish(
            "DesktopActionFailed",
            "decision_engine",
            {
                "action": "evaluate_recommendation",
                "result": "failed",
                "reason": result.get("reason", "decision_error"),
            },
        )

    response = {
        "engine": "decision_engine",
        "status": status,
        "decision": {
            "outcome": decision.get("outcome", ""),
            "next_step": decision.get("next_step", ""),
            "reason": decision.get("reason", ""),
            "risk": decision.get("risk", ""),
            "requires_approval": bool(decision.get("requires_approval", False)),
        } if decision else {},
        "message": result.get("message", ""),
    }
    if status != "success":
        response["reason"] = result.get("reason", "decision_error")
    return response
