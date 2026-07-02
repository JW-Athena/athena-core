from typing import Any, Dict

from fastapi import APIRouter, Body

from desktop_agent import desktop_agent
from event_bus import event_bus


router = APIRouter(tags=["ATHENA Desktop Agent"])


@router.get("/athena/desktop/status")
async def desktop_status():
    return {
        "engine": "desktop_agent",
        "status": "success",
        "desktop": desktop_agent.status(),
    }


@router.post("/athena/desktop/open-notepad")
async def open_notepad():
    result = desktop_agent.open_notepad()
    status = result.get("status", "failed")
    executed = bool(result.get("executed", False))
    event_type = "DesktopActionExecuted" if executed else "DesktopActionFailed"

    event_bus.publish(
        event_type,
        "desktop_agent",
        {
            "action": "open_notepad",
            "result": status,
        },
    )

    return {
        "engine": "desktop_agent",
        "status": status,
        "action": "open_notepad",
        "executed": executed,
        "message": result.get("message", ""),
    }


@router.post("/athena/desktop/open-explorer")
async def open_explorer():
    result = desktop_agent.open_explorer()
    status = result.get("status", "failed")
    executed = bool(result.get("executed", False))
    event_type = "DesktopActionExecuted" if executed else "DesktopActionFailed"

    event_bus.publish(
        event_type,
        "desktop_agent",
        {
            "action": "open_explorer",
            "result": status,
        },
    )

    return {
        "engine": "desktop_agent",
        "status": status,
        "action": "open_explorer",
        "executed": executed,
        "message": result.get("message", ""),
    }


@router.post("/athena/desktop/open-folder")
async def open_folder(payload: Dict[str, Any] = Body(default_factory=dict)):
    result = desktop_agent.open_folder(payload.get("path", ""))
    status = result.get("status", "failed")
    executed = bool(result.get("executed", False))
    path = result.get("path", "")
    event_type = "DesktopActionExecuted" if executed else "DesktopActionFailed"

    event_bus.publish(
        event_type,
        "desktop_agent",
        {
            "action": "open_folder",
            "path": path,
            "result": status,
        },
    )

    return {
        "engine": "desktop_agent",
        "status": status,
        "action": "open_folder",
        "path": path,
        "executed": executed,
        "message": result.get("message", ""),
    }


@router.post("/athena/desktop/list-folder")
async def list_folder(payload: Dict[str, Any] = Body(default_factory=dict)):
    result = desktop_agent.list_folder(payload.get("path", ""))
    status = result.get("status", "failed")

    if status == "success":
        event_bus.publish(
            "DesktopFolderRead",
            "desktop_agent",
            {
                "path": result.get("folder", ""),
                "items": result.get("item_count", 0),
            },
        )

    return {
        "engine": "desktop_agent",
        "status": status,
        "folder": result.get("folder", ""),
        "exists": bool(result.get("exists", False)),
        "item_count": int(result.get("item_count", 0) or 0),
        "folders": result.get("folders", []),
        "files": result.get("files", []),
    }


@router.post("/athena/desktop/file-info")
async def file_info(payload: Dict[str, Any] = Body(default_factory=dict)):
    result = desktop_agent.file_info(payload.get("path", ""))
    status = result.get("status", "failed")
    file_data = result.get("file", {})
    event_type = "DesktopFileInspected" if status == "success" else "DesktopActionFailed"

    event_bus.publish(
        event_type,
        "desktop_agent",
        {
            "action": "file_info",
            "path": file_data.get("path", ""),
            "result": status,
        },
    )

    return {
        "engine": "desktop_agent",
        "status": status,
        "file": {
            "path": file_data.get("path", ""),
            "exists": bool(file_data.get("exists", False)),
            "name": file_data.get("name", ""),
            "extension": file_data.get("extension", ""),
            "size_bytes": int(file_data.get("size_bytes", 0) or 0),
            "modified": file_data.get("modified", ""),
            "created": file_data.get("created", ""),
            "is_file": bool(file_data.get("is_file", False)),
        },
        "message": result.get("message", ""),
    }


@router.post("/athena/desktop/read-file")
async def read_file(payload: Dict[str, Any] = Body(default_factory=dict)):
    result = desktop_agent.read_file(payload.get("path", ""))
    status = result.get("status", "blocked")
    file_data = result.get("file", {})

    if status == "success":
        event_bus.publish(
            "DesktopFileRead",
            "desktop_agent",
            {
                "action": "read_file",
                "path": file_data.get("path", ""),
                "result": "success",
            },
        )
    else:
        event_bus.publish(
            "DesktopActionFailed",
            "desktop_agent",
            {
                "action": "read_file",
                "path": file_data.get("path", ""),
                "result": "failed",
                "reason": result.get("reason", "read_error"),
            },
        )

    response = {
        "engine": "desktop_agent",
        "status": status,
        "file": {
            "path": file_data.get("path", ""),
            "exists": bool(file_data.get("exists", False)),
            "name": file_data.get("name", ""),
            "extension": file_data.get("extension", ""),
            "size_bytes": int(file_data.get("size_bytes", 0) or 0),
            "content": file_data.get("content", ""),
            "truncated": bool(file_data.get("truncated", False)),
        },
    }
    if status != "success":
        response["reason"] = result.get("reason", "read_error")
    if result.get("message"):
        response["message"] = result.get("message", "")
    return response


@router.post("/athena/desktop/search-files")
async def search_files(payload: Dict[str, Any] = Body(default_factory=dict)):
    result = desktop_agent.search_files(
        folder=payload.get("folder", ""),
        pattern=payload.get("pattern", "*"),
        recursive=bool(payload.get("recursive", False)),
        max_results=payload.get("max_results", 100),
    )
    status = result.get("status", "failed")

    event_bus.publish(
        "DesktopFilesSearched",
        "desktop_agent",
        {
            "folder": result.get("folder", ""),
            "pattern": result.get("pattern", "*"),
            "recursive": bool(result.get("recursive", False)),
            "result_count": int(result.get("result_count", 0) or 0),
            "result": status,
        },
    )

    return {
        "engine": "desktop_agent",
        "status": status,
        "folder": result.get("folder", ""),
        "pattern": result.get("pattern", "*"),
        "recursive": bool(result.get("recursive", False)),
        "max_results": int(result.get("max_results", 100) or 100),
        "result_count": int(result.get("result_count", 0) or 0),
        "results": result.get("results", []),
        "message": result.get("message", ""),
    }


@router.post("/athena/desktop/open-file-location")
async def open_file_location(payload: Dict[str, Any] = Body(default_factory=dict)):
    result = desktop_agent.open_file_location(payload.get("path", ""))
    status = result.get("status", "failed")

    if status == "success":
        event_bus.publish(
            "DesktopFileLocationOpened",
            "desktop_agent",
            {
                "action": "open_file_location",
                "path": result.get("path", ""),
                "folder": result.get("folder", ""),
                "result": "success",
            },
        )
    else:
        event_bus.publish(
            "DesktopActionFailed",
            "desktop_agent",
            {
                "action": "open_file_location",
                "path": result.get("path", ""),
                "result": "failed",
                "reason": result.get("reason", "open_error"),
            },
        )

    response = {
        "engine": "desktop_agent",
        "status": status,
        "path": result.get("path", ""),
        "folder": result.get("folder", ""),
        "name": result.get("name", ""),
        "message": result.get("message", ""),
    }
    if status != "success":
        response["reason"] = result.get("reason", "open_error")
    return response


@router.post("/athena/desktop/recommend-file-actions")
async def recommend_file_actions(payload: Dict[str, Any] = Body(default_factory=dict)):
    result = desktop_agent.recommend_file_actions(payload.get("path", ""))
    file_data = result.get("file", {})
    actions = result.get("recommended_actions", [])

    event_bus.publish(
        "DesktopFileActionsRecommended",
        "desktop_agent",
        {
            "action": "recommend_file_actions",
            "path": file_data.get("path", ""),
            "exists": bool(file_data.get("exists", False)),
            "recommended_count": len(actions),
            "result": result.get("status", "success"),
        },
    )

    response = {
        "engine": "desktop_agent",
        "status": result.get("status", "success"),
        "file": {
            "path": file_data.get("path", ""),
            "exists": bool(file_data.get("exists", False)),
            "name": file_data.get("name", ""),
            "extension": file_data.get("extension", ""),
            "size_bytes": int(file_data.get("size_bytes", 0) or 0),
        },
        "recommended_actions": actions,
    }
    if result.get("reason"):
        response["reason"] = result.get("reason")
    if result.get("message"):
        response["message"] = result.get("message")
    return response
