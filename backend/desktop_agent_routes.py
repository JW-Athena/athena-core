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
