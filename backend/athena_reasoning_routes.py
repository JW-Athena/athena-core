from typing import Any, Dict

from fastapi import APIRouter, Body

from athena_reasoning_agent import AthenaReasoningAgent
from event_bus import event_bus


router = APIRouter(tags=["ATHENA Reasoning Agent"])
reasoning_agent = AthenaReasoningAgent()


@router.post("/athena/reasoning/summarize-file-request")
async def summarize_file_request(payload: Dict[str, Any] = Body(default_factory=dict)):
    result = reasoning_agent.summarize_file_request(payload.get("summary_request"))
    status = result.get("status", "blocked")
    summary = result.get("summary", {})

    if status == "success":
        event_bus.publish(
            "FileSummaryGenerated",
            "reasoning_agent",
            {
                "source_path": summary.get("source_path", ""),
                "source_name": summary.get("source_name", ""),
                "method": summary.get("method", "deterministic_preview_summary"),
                "result": "success",
            },
        )
    else:
        event_bus.publish(
            "DesktopActionFailed",
            "reasoning_agent",
            {
                "action": "summarize_file_request",
                "source_path": summary.get("source_path", ""),
                "result": "failed",
                "reason": result.get("reason", "reasoning_error"),
            },
        )

    response = {
        "engine": "reasoning_agent",
        "status": status,
        "summary": {
            "source_path": summary.get("source_path", ""),
            "source_name": summary.get("source_name", ""),
            "summary_text": summary.get("summary_text", ""),
            "method": summary.get("method", "deterministic_preview_summary"),
            "confidence": summary.get("confidence", "limited"),
        },
        "message": result.get("message", ""),
    }
    if status != "success":
        response["reason"] = result.get("reason", "reasoning_error")
    return response
