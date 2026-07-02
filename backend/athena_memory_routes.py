from typing import Any, Dict

from fastapi import APIRouter, Body

from athena_memory_agent import AthenaMemoryAgent
from event_bus import event_bus


router = APIRouter(tags=["ATHENA Memory Agent"])
memory_agent = AthenaMemoryAgent()


@router.post("/athena/memory/store-file-understanding")
async def store_file_understanding(payload: Dict[str, Any] = Body(default_factory=dict)):
    result = memory_agent.store_file_understanding(payload.get("workflow"))
    status = result.get("status", "blocked")
    memory_record = result.get("memory_record", {})

    if status == "success":
        event_bus.publish(
            "FileUnderstandingStored",
            "memory_agent",
            {
                "type": memory_record.get("type", "file_understanding"),
                "source_path": memory_record.get("source_path", ""),
                "source_name": memory_record.get("source_name", ""),
                "result": "success",
            },
        )
    else:
        event_bus.publish(
            "DesktopActionFailed",
            "memory_agent",
            {
                "action": "store_file_understanding",
                "result": "failed",
                "reason": result.get("reason", "memory_store_error"),
            },
        )

    response = {
        "engine": "memory_agent",
        "status": status,
        "memory_record": {
            "type": memory_record.get("type", ""),
            "source_path": memory_record.get("source_path", ""),
            "source_name": memory_record.get("source_name", ""),
            "summary_text": memory_record.get("summary_text", ""),
            "confidence": memory_record.get("confidence", ""),
        },
        "message": result.get("message", ""),
    }
    if status != "success":
        response["reason"] = result.get("reason", "memory_store_error")
    return response
