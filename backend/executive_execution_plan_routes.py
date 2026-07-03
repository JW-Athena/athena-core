from typing import Any, Dict, List

from fastapi import APIRouter, Body

from agent_registry import agent_registry
from capability_marketplace import capability_marketplace
from event_bus import event_bus


router = APIRouter(tags=["ATHENA Executive Brain"])

DOCUMENT_KEYWORDS = {
    "tender",
    "document",
    "risk",
    "risks",
    "obligation",
    "obligations",
    "action plan",
    "decision brief",
}

FILE_KEYWORDS = {
    "file",
    "understand",
    "remember",
    "search",
    "search memory",
}


@router.post("/athena/brain/execution-plan")
async def build_execution_plan(payload: Dict[str, Any] = Body(default_factory=dict)):
    objective = str(payload.get("objective", "") or "").strip()
    path = str(payload.get("path", "") or "").strip()

    if not objective:
        return _failed_response(
            status="failed",
            objective=objective,
            selected_plan="",
            reason="missing_objective",
            message="Objective is required.",
        )

    try:
        discovery = _discover_capabilities()
    except Exception as exc:
        return _failed_response(
            status="failed",
            objective=objective,
            selected_plan="",
            reason="capability_discovery_error",
            message=f"Capability discovery failed: {exc}",
        )

    try:
        selected_plan = _selected_plan(objective, discovery)
        if not selected_plan:
            return _failed_response(
                status="needs_clarification",
                objective=objective,
                selected_plan="",
                reason="unsupported_objective",
                message="ATHENA needs a clearer executive objective before building an execution plan.",
                clarification_question=(
                    "Should ATHENA analyze a document, understand a file, or search file memory?"
                ),
            )

        if not path:
            return _failed_response(
                status="failed",
                objective=objective,
                selected_plan=selected_plan,
                reason="missing_path",
                message="Path is required for the selected execution plan.",
            )

        execution_plan = _build_plan(selected_plan)
    except Exception as exc:
        return _failed_response(
            status="failed",
            objective=objective,
            selected_plan="",
            reason="planning_error",
            message=f"Executive execution planning failed: {exc}",
        )

    event_bus.publish(
        "ExecutiveExecutionPlanBuilt",
        "executive_brain",
        {
            "objective": objective,
            "selected_plan": selected_plan,
            "path": path,
            "step_count": len(execution_plan.get("steps", [])),
            "result": "success",
        },
    )

    return {
        "engine": "executive_brain",
        "status": "success",
        "objective": objective,
        "selected_plan": selected_plan,
        "execution_plan": execution_plan,
        "message": "Executive execution plan built.",
    }


def _discover_capabilities() -> Dict[str, Any]:
    capabilities = capability_marketplace.enabled_capabilities()
    agents = [
        agent
        for agent in agent_registry.list_agents()
        if agent.get("enabled")
    ]
    capability_ids = {
        str(capability.get("id", ""))
        for capability in capabilities
        if capability.get("id")
    }
    agent_ids = {
        str(agent.get("id", ""))
        for agent in agents
        if agent.get("id")
    }

    return {
        "capabilities": capabilities,
        "agents": agents,
        "capability_ids": capability_ids,
        "agent_ids": agent_ids,
    }


def _selected_plan(objective: str, discovery: Dict[str, Any]) -> str:
    signal = objective.lower()
    capability_ids = discovery.get("capability_ids", set())
    agent_ids = discovery.get("agent_ids", set())

    document_supported = (
        "executive_analysis" in capability_ids
        and "risk_intelligence" in capability_ids
        and "contract_intelligence" in capability_ids
        and "memory_agent" in agent_ids
        and "workflow_agent" in agent_ids
    )
    file_supported = (
        "memory" in capability_ids
        and "desktop_agent" in agent_ids
        and "workflow_agent" in agent_ids
    )

    if document_supported and any(keyword in signal for keyword in DOCUMENT_KEYWORDS):
        return "document_intelligence_plan"
    if file_supported and any(keyword in signal for keyword in FILE_KEYWORDS):
        return "file_intelligence_plan"
    return ""


def _build_plan(selected_plan: str) -> Dict[str, Any]:
    if selected_plan == "document_intelligence_plan":
        return {
            "steps": [
                _step(
                    1,
                    "file_understanding_with_memory",
                    "Prepare document context and store memory.",
                    "low",
                    output_key="file_understanding_with_memory",
                ),
                _step(
                    2,
                    "executive_extraction",
                    "Extract executive business information.",
                    "low",
                    required_inputs=["text"],
                    output_key="executive_extraction",
                    depends_on=["file_understanding_with_memory"],
                ),
                _step(
                    3,
                    "obligation_extraction",
                    "Identify obligations, requirements, and management actions.",
                    "medium",
                    required_inputs=["text"],
                    output_key="obligation_extraction",
                    depends_on=["file_understanding_with_memory"],
                ),
                _step(
                    4,
                    "risk_register",
                    "Build a consolidated executive risk register.",
                    "medium",
                    required_inputs=["text"],
                    output_key="risk_register",
                    depends_on=["file_understanding_with_memory"],
                ),
                _step(
                    5,
                    "executive_decision_brief",
                    "Prepare decision-ready executive brief.",
                    "medium",
                    required_inputs=["text"],
                    output_key="executive_decision_brief",
                    depends_on=["file_understanding_with_memory"],
                ),
                _step(
                    6,
                    "executive_action_plan",
                    "Convert intelligence into a prioritized executive action plan.",
                    "medium",
                    required_inputs=["text"],
                    output_key="executive_action_plan",
                    depends_on=["file_understanding_with_memory"],
                ),
            ]
        }

    if selected_plan == "file_intelligence_plan":
        return {
            "steps": [
                _step(
                    1,
                    "file_intelligence_loop",
                    "Understand the file, remember it, search memory, plan, and evaluate.",
                    "low",
                    output_key="file_intelligence_loop",
                ),
            ]
        }

    raise ValueError(f"Unsupported selected plan: {selected_plan}")


def _step(
    order: int,
    capability: str,
    reason: str,
    risk: str,
    required_inputs: List[str] = None,
    output_key: str = "",
    depends_on: List[str] = None,
) -> Dict[str, Any]:
    return {
        "order": order,
        "capability": capability,
        "purpose": reason,
        "reason": reason,
        "required_inputs": list(required_inputs or []),
        "output_key": output_key or capability,
        "depends_on": list(depends_on or []),
        "requires_approval": False,
        "risk": risk,
    }


def _failed_response(
    status: str,
    objective: str,
    selected_plan: str,
    reason: str,
    message: str,
    clarification_question: str = "",
) -> Dict[str, Any]:
    event_bus.publish(
        "ExecutiveExecutionPlanFailed",
        "executive_brain",
        {
            "objective": objective,
            "selected_plan": selected_plan,
            "reason": reason,
            "result": "failed",
        },
    )

    response = {
        "engine": "executive_brain",
        "status": status,
        "objective": objective,
        "selected_plan": selected_plan,
        "reason": reason,
        "message": message,
    }
    if clarification_question:
        response["clarification_question"] = clarification_question
    return response
