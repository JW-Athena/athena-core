from typing import Any, Dict

from fastapi import APIRouter, Body

from athena_reasoning_agent import AthenaReasoningAgent
from athena_workflow_agent import AthenaWorkflowAgent
from desktop_agent import desktop_agent
from event_bus import event_bus


router = APIRouter(tags=["ATHENA Workflow Agent"])
workflow_agent = AthenaWorkflowAgent()
reasoning_agent = AthenaReasoningAgent()


@router.post("/athena/workflow/file-understanding")
async def file_understanding(payload: Dict[str, Any] = Body(default_factory=dict)):
    result = workflow_agent.file_understanding(
        desktop_agent=desktop_agent,
        reasoning_agent=reasoning_agent,
        path=payload.get("path", ""),
    )
    status = result.get("status", "blocked")
    workflow = result.get("workflow", {})

    if status == "success":
        file_data = workflow.get("file", {})
        summary = workflow.get("summary", {})
        event_bus.publish(
            "FileUnderstandingWorkflowCompleted",
            "workflow_agent",
            {
                "path": file_data.get("path", ""),
                "name": file_data.get("name", ""),
                "steps_completed": workflow.get("steps_completed", []),
                "summary_method": summary.get("method", ""),
                "result": "success",
            },
        )
    else:
        event_bus.publish(
            "DesktopActionFailed",
            "workflow_agent",
            {
                "action": "file_understanding",
                "step": result.get("step", "workflow"),
                "reason": result.get("reason", "workflow_error"),
                "result": "failed",
            },
        )

    response = {
        "engine": "workflow_agent",
        "status": status,
        "workflow": {
            "name": workflow.get("name", "file_understanding"),
            "steps_completed": workflow.get("steps_completed", []),
            "file": workflow.get("file", {}),
            "summary": workflow.get("summary", {}),
        },
        "message": result.get("message", ""),
    }
    if status != "success":
        response["step"] = result.get("step", "workflow")
        response["reason"] = result.get("reason", "workflow_error")
    return response
