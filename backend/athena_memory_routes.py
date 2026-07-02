from typing import Any, Dict

from fastapi import APIRouter, Body, Query

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


@router.get("/athena/memory/file-understandings")
async def list_file_understandings(limit: int = Query(default=20)):
    result = memory_agent.list_file_understandings(limit=limit)
    status = result.get("status", "blocked")

    if status == "success":
        event_bus.publish(
            "FileUnderstandingsListed",
            "memory_agent",
            {
                "count": result.get("count", 0),
                "limit": min(int(limit), 100) if isinstance(limit, int) else 20,
                "result": "success",
            },
        )
    else:
        event_bus.publish(
            "DesktopActionFailed",
            "memory_agent",
            {
                "action": "list_file_understandings",
                "result": "failed",
                "reason": result.get("reason", "memory_read_error"),
            },
        )

    response = {
        "engine": "memory_agent",
        "status": status,
        "count": int(result.get("count", 0) or 0),
        "records": result.get("records", []),
        "message": result.get("message", ""),
    }
    if status != "success":
        response["reason"] = result.get("reason", "memory_read_error")
    return response


@router.get("/athena/memory/search-file-understandings")
async def search_file_understandings(
    query: str = Query(default=""),
    limit: int = Query(default=20),
):
    result = memory_agent.search_file_understandings(query=query, limit=limit)
    status = result.get("status", "blocked")

    if status == "success":
        event_bus.publish(
            "FileUnderstandingsSearched",
            "memory_agent",
            {
                "query": result.get("query", ""),
                "count": result.get("count", 0),
                "limit": min(int(limit), 100) if isinstance(limit, int) else 20,
                "result": "success",
            },
        )
    else:
        event_bus.publish(
            "DesktopActionFailed",
            "memory_agent",
            {
                "action": "search_file_understandings",
                "query": query,
                "result": "failed",
                "reason": result.get("reason", "memory_search_error"),
            },
        )

    response = {
        "engine": "memory_agent",
        "status": status,
        "query": result.get("query", query),
        "count": int(result.get("count", 0) or 0),
        "records": result.get("records", []),
        "message": result.get("message", ""),
    }
    if status != "success":
        response["reason"] = result.get("reason", "memory_search_error")
    return response
