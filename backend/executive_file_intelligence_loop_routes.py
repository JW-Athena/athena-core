from typing import Any, Dict

from fastapi import APIRouter, Body

from athena_decision_engine import AthenaDecisionEngine
from athena_memory_agent import AthenaMemoryAgent
from athena_planner import AthenaPlanner
from athena_reasoning_agent import AthenaReasoningAgent
from athena_workflow_agent import AthenaWorkflowAgent
from desktop_agent import desktop_agent
from event_bus import event_bus


router = APIRouter(tags=["ATHENA Executive OS"])

workflow_agent = AthenaWorkflowAgent()
reasoning_agent = AthenaReasoningAgent()
memory_agent = AthenaMemoryAgent()
planner_agent = AthenaPlanner()
decision_engine = AthenaDecisionEngine()


@router.post("/athena/executive/file-intelligence-loop")
async def file_intelligence_loop(payload: Dict[str, Any] = Body(default_factory=dict)):
    path = str(payload.get("path", "") or "")
    query = str(payload.get("query", "") or "")
    steps_completed = []

    file_result = workflow_agent.file_understanding_with_memory(
        desktop_agent=desktop_agent,
        reasoning_agent=reasoning_agent,
        memory_agent=memory_agent,
        path=path,
    )
    if file_result.get("status") != "success":
        return _failed_response(
            failed_step="file_understanding_with_memory",
            reason=file_result.get("reason", "workflow_error"),
            message=file_result.get("message", "File understanding with memory failed."),
            steps_completed=steps_completed,
        )
    steps_completed.append("file_understanding_with_memory")
    workflow = file_result.get("workflow", {})

    memory_result = memory_agent.search_file_understandings(
        query=query,
        limit=20,
    )
    if memory_result.get("status") != "success":
        return _failed_response(
            failed_step="search_file_understandings",
            reason=memory_result.get("reason", "memory_search_error"),
            message=memory_result.get("message", "File understanding search failed."),
            steps_completed=steps_completed,
            file_data=workflow.get("file", {}),
        )
    steps_completed.append("search_file_understandings")

    planner_result = planner_agent.recommend_from_file_memory(
        query=query,
        memory_agent=memory_agent,
    )
    if planner_result.get("status") != "success":
        return _failed_response(
            failed_step="planner_recommendation",
            reason=planner_result.get("reason", "planner_error"),
            message=planner_result.get("message", "Planner recommendation failed."),
            steps_completed=steps_completed,
            file_data=workflow.get("file", {}),
            memory_matches=_memory_matches(memory_result, query),
        )
    steps_completed.append("planner_recommendation")
    recommendation = planner_result.get("recommendation", {})

    decision_result = decision_engine.evaluate_recommendation(recommendation)
    if decision_result.get("status") != "success":
        return _failed_response(
            failed_step="decision_evaluation",
            reason=decision_result.get("reason", "decision_error"),
            message=decision_result.get("message", "Decision evaluation failed."),
            steps_completed=steps_completed,
            file_data=workflow.get("file", {}),
            memory_matches=_memory_matches(memory_result, query),
            recommendation=recommendation,
        )
    steps_completed.append("decision_evaluation")
    decision = decision_result.get("decision", {})

    event_bus.publish(
        "ExecutiveFileIntelligenceLoopCompleted",
        "executive_os",
        {
            "path": workflow.get("file", {}).get("path", ""),
            "query": memory_result.get("query", query),
            "steps_completed": steps_completed,
            "matches_found": memory_result.get("count", 0),
            "recommendation_next_step": recommendation.get("next_step", ""),
            "decision_outcome": decision.get("outcome", ""),
            "result": "success",
        },
    )

    return {
        "engine": "executive_os",
        "status": "success",
        "capability": "file_intelligence_loop",
        "steps_completed": steps_completed,
        "file": workflow.get("file", {}),
        "memory_matches": _memory_matches(memory_result, query),
        "recommendation": recommendation,
        "decision": {
            "outcome": decision.get("outcome", ""),
            "next_step": decision.get("next_step", ""),
            "reason": decision.get("reason", ""),
            "risk": decision.get("risk", ""),
            "requires_approval": bool(decision.get("requires_approval", False)),
        },
        "message": "Executive file intelligence loop completed.",
    }


def _memory_matches(result: Dict[str, Any], query: str) -> Dict[str, Any]:
    return {
        "query": result.get("query", query),
        "count": int(result.get("count", 0) or 0),
        "records": result.get("records", []),
    }


def _failed_response(
    failed_step: str,
    reason: str,
    message: str,
    steps_completed: list,
    file_data: Dict[str, Any] = None,
    memory_matches: Dict[str, Any] = None,
    recommendation: Dict[str, Any] = None,
) -> Dict[str, Any]:
    event_bus.publish(
        "DesktopActionFailed",
        "executive_os",
        {
            "action": "file_intelligence_loop",
            "failed_step": failed_step,
            "reason": reason,
            "result": "failed",
        },
    )

    response = {
        "engine": "executive_os",
        "status": "failed",
        "capability": "file_intelligence_loop",
        "steps_completed": list(steps_completed),
        "failed_step": failed_step,
        "reason": reason,
        "message": message,
    }
    if file_data is not None:
        response["file"] = file_data
    if memory_matches is not None:
        response["memory_matches"] = memory_matches
    if recommendation is not None:
        response["recommendation"] = recommendation
    return response
