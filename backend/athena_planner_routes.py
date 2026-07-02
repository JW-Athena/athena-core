from typing import Any, Dict

from fastapi import APIRouter, Body

from athena_memory_agent import AthenaMemoryAgent
from athena_planner import AthenaPlanner
from event_bus import event_bus


router = APIRouter(tags=["ATHENA Planner Agent"])
planner_agent = AthenaPlanner()
memory_agent = AthenaMemoryAgent()


@router.post("/athena/planner/recommend-from-file-memory")
async def recommend_from_file_memory(payload: Dict[str, Any] = Body(default_factory=dict)):
    result = planner_agent.recommend_from_file_memory(
        query=payload.get("query", ""),
        memory_agent=memory_agent,
    )
    status = result.get("status", "blocked")

    if status == "success":
        recommendation = result.get("recommendation", {})
        event_bus.publish(
            "PlannerRecommendationGenerated",
            "planner_agent",
            {
                "query": result.get("query", ""),
                "matches_found": result.get("matches_found", 0),
                "next_step": recommendation.get("next_step", ""),
                "result": "success",
            },
        )
    else:
        event_bus.publish(
            "DesktopActionFailed",
            "planner_agent",
            {
                "action": "recommend_from_file_memory",
                "query": result.get("query", payload.get("query", "")),
                "result": "failed",
                "reason": result.get("reason", "planner_error"),
            },
        )

    response = {
        "engine": "planner_agent",
        "status": status,
        "query": result.get("query", payload.get("query", "")),
        "matches_found": int(result.get("matches_found", 0) or 0),
        "recommendation": result.get("recommendation", {}),
        "message": result.get("message", ""),
    }
    if status != "success":
        response["reason"] = result.get("reason", "planner_error")
    return response
