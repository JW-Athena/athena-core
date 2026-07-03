from typing import Any, Dict

from fastapi import APIRouter, Body

from engine_011_execution_runtime import ExecutionContext, ExecutiveExecutionRuntime
from engine_014_adaptive_planner import build_adaptive_plan
from event_bus import event_bus
from executive_execution_plan_routes import build_execution_plan


router = APIRouter(tags=["ATHENA Executive Brain Runtime"])
runtime = ExecutiveExecutionRuntime()


@router.post("/athena/brain/execute-objective")
async def execute_objective(payload: Dict[str, Any] = Body(default_factory=dict)):
    objective = str(payload.get("objective", "") or "").strip()
    path = str(payload.get("path", "") or "").strip()

    plan_result = payload.get("execution_plan_result")
    adaptive_planning = None
    if not isinstance(plan_result, dict):
        adaptive_planning = await build_adaptive_plan(objective=objective, path=path)
        if isinstance(adaptive_planning, dict) and adaptive_planning.get("status") == "success":
            plan_result = adaptive_planning.get("plan", {})
        else:
            plan_result = await build_execution_plan(payload)

    if not isinstance(plan_result, dict) or plan_result.get("status") != "success":
        reason = plan_result.get("reason", "planning_error") if isinstance(plan_result, dict) else "planning_error"
        event_bus.publish(
            "BrainObjectiveExecutionFailed",
            "executive_brain",
            {
                "objective": objective,
                "selected_plan": plan_result.get("selected_plan", "") if isinstance(plan_result, dict) else "",
                "reason": reason,
                "result": "failed",
            },
        )
        return {
            "engine": "executive_brain",
            "status": "failed" if not isinstance(plan_result, dict) else plan_result.get("status", "failed"),
            "objective": objective,
            "selected_plan": plan_result.get("selected_plan", "") if isinstance(plan_result, dict) else "",
            "execution_status": "not_started",
            "capabilities_executed": [],
            "results": {},
            "executive_response": {
                "summary": plan_result.get("message", "Executive execution could not start.") if isinstance(plan_result, dict) else "Executive execution could not start.",
                "recommended_next_action": "Clarify the objective or provide a valid path, then retry.",
                "requires_approval": False,
            },
            "reason": reason,
        }

    context = ExecutionContext(
        objective=plan_result.get("objective", objective),
        path=path,
        selected_plan=plan_result.get("selected_plan", ""),
        execution_plan=plan_result.get("execution_plan", {}),
        document_type=str(payload.get("document_type", "") or ""),
        query=str(payload.get("query", "") or ""),
        mission_context=payload.get("mission_context"),
        objective_id=str(payload.get("objective_id", "") or ""),
    )

    response = await runtime.execute_plan(context)
    if adaptive_planning is not None and isinstance(response, dict):
        response["adaptive_planning"] = adaptive_planning
    return response
