from typing import Any, Dict

from fastapi import APIRouter, Body

from event_bus import event_bus
from executive_document_intelligence_loop_routes import document_intelligence_loop
from executive_file_intelligence_loop_routes import file_intelligence_loop


router = APIRouter(tags=["ATHENA Executive Brain"])

DOCUMENT_KEYWORDS = {
    "tender",
    "document",
    "action plan",
    "obligations",
    "risks",
    "decision brief",
}

FILE_KEYWORDS = {
    "file",
    "understand",
    "remember",
    "search memory",
}


@router.post("/athena/brain/objective")
async def route_objective(payload: Dict[str, Any] = Body(default_factory=dict)):
    objective = str(payload.get("objective", "") or "").strip()
    path = str(payload.get("path", "") or "").strip()

    if not objective:
        return _failed_response(
            status="failed",
            objective=objective,
            selected_capability="",
            reason="missing_objective",
            message="Objective is required.",
        )

    selected_capability = _selected_capability(objective)
    if not selected_capability:
        return _failed_response(
            status="needs_clarification",
            objective=objective,
            selected_capability="",
            reason="unsupported_objective",
            message="ATHENA needs a clearer executive objective before routing.",
        )

    if not path:
        return _failed_response(
            status="failed",
            objective=objective,
            selected_capability=selected_capability,
            reason="missing_path",
            message="Path is required for the selected capability.",
        )

    try:
        if selected_capability == "document_intelligence_loop":
            result = await document_intelligence_loop(
                {
                    "path": path,
                    "document_type": payload.get("document_type", ""),
                }
            )
        else:
            result = await file_intelligence_loop(
                {
                    "path": path,
                    "query": payload.get("query") or objective,
                }
            )
    except Exception as exc:
        return _failed_response(
            status="failed",
            objective=objective,
            selected_capability=selected_capability,
            reason="routing_error",
            message=f"Executive objective routing failed: {exc}",
        )

    if not isinstance(result, dict):
        return _failed_response(
            status="failed",
            objective=objective,
            selected_capability=selected_capability,
            reason="routing_error",
            message="Selected capability returned an invalid result.",
        )

    if result.get("status") not in {"success"}:
        return _failed_response(
            status="failed",
            objective=objective,
            selected_capability=selected_capability,
            reason=result.get("reason", "routing_error"),
            message=result.get("message", "Selected capability failed."),
            result=result,
        )

    event_bus.publish(
        "ExecutiveObjectiveRouted",
        "executive_brain",
        {
            "objective": objective,
            "selected_capability": selected_capability,
            "path": path,
            "result": "success",
        },
    )

    return {
        "engine": "executive_brain",
        "status": "success",
        "objective": objective,
        "selected_capability": selected_capability,
        "result": result,
        "message": "Executive objective routed and completed.",
    }


def _selected_capability(objective: str) -> str:
    signal = objective.lower()

    if any(keyword in signal for keyword in DOCUMENT_KEYWORDS):
        return "document_intelligence_loop"
    if any(keyword in signal for keyword in FILE_KEYWORDS):
        return "file_intelligence_loop"
    return ""


def _failed_response(
    status: str,
    objective: str,
    selected_capability: str,
    reason: str,
    message: str,
    result: Dict[str, Any] = None,
) -> Dict[str, Any]:
    event_bus.publish(
        "ExecutiveObjectiveRoutingFailed",
        "executive_brain",
        {
            "objective": objective,
            "selected_capability": selected_capability,
            "reason": reason,
            "result": "failed",
        },
    )

    response = {
        "engine": "executive_brain",
        "status": status,
        "objective": objective,
        "selected_capability": selected_capability,
        "reason": reason,
        "message": message,
    }
    if result is not None:
        response["result"] = result
    return response
