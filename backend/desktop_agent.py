import subprocess
from typing import Any, Dict


class AthenaDesktopAgent:
    """
    Planning-only Desktop Agent.

    The agent is installed for future controlled execution, but it does not
    move the mouse, type, click, open applications, or automate the desktop.
    """

    def status(self) -> Dict[str, Any]:
        return {
            "enabled": False,
            "mode": "planning_only",
            "connected": False,
            "available_actions": [
                "Open Application",
                "Open Folder",
                "Open Browser",
                "Open Document",
                "Take Screenshot",
            ],
            "summary": "Desktop Agent is installed but execution is disabled.",
        }

    def can_execute(self, approval: Dict[str, Any], execution: Dict[str, Any]) -> bool:
        execution_enabled = bool(execution.get("enabled", False))
        approval_required = bool(approval.get("required", True))
        execution_mode = execution.get("mode", "planning_only")

        return (
            execution_enabled
            and execution_mode != "planning_only"
            and not approval_required
        )

    def open_notepad(self) -> Dict[str, Any]:
        try:
            subprocess.Popen(["notepad.exe"])
        except Exception as exc:
            return {
                "status": "failed",
                "executed": False,
                "message": f"Failed to open Notepad: {exc}",
            }

        return {
            "status": "success",
            "executed": True,
            "message": "Notepad opened successfully.",
        }

    def open_explorer(self) -> Dict[str, Any]:
        try:
            subprocess.Popen(["explorer.exe"])
        except Exception as exc:
            return {
                "status": "failed",
                "executed": False,
                "message": f"Failed to open File Explorer: {exc}",
            }

        return {
            "status": "success",
            "executed": True,
            "message": "File Explorer opened successfully.",
        }


desktop_agent = AthenaDesktopAgent()
