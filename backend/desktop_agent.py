import os
import subprocess
from datetime import datetime
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

    def open_folder(self, path: str) -> Dict[str, Any]:
        validation = self._validate_folder_path(path)
        if not validation["valid"]:
            return {
                "status": "failed",
                "path": validation["path"],
                "executed": False,
                "message": validation["message"],
            }

        safe_path = validation["path"]
        try:
            subprocess.Popen(["explorer.exe", safe_path])
        except Exception as exc:
            return {
                "status": "failed",
                "path": safe_path,
                "executed": False,
                "message": f"Failed to open folder: {exc}",
            }

        return {
            "status": "success",
            "path": safe_path,
            "executed": True,
            "message": "Folder opened successfully.",
        }

    def list_folder(self, path: str) -> Dict[str, Any]:
        validation = self._validate_folder_path(path)
        if not validation["valid"]:
            return {
                "status": "failed",
                "folder": validation["path"],
                "exists": False,
                "item_count": 0,
                "folders": [],
                "files": [],
                "message": validation["message"],
            }

        safe_path = validation["path"]
        folders = []
        files = []

        try:
            with os.scandir(safe_path) as entries:
                for entry in entries:
                    try:
                        stat = entry.stat(follow_symlinks=False)
                    except OSError:
                        continue

                    if entry.is_dir(follow_symlinks=False):
                        folders.append(entry.name)
                    elif entry.is_file(follow_symlinks=False):
                        _, extension = os.path.splitext(entry.name)
                        files.append(
                            {
                                "name": entry.name,
                                "extension": extension,
                                "size_bytes": int(stat.st_size),
                                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                            }
                        )
        except Exception as exc:
            return {
                "status": "failed",
                "folder": safe_path,
                "exists": True,
                "item_count": 0,
                "folders": [],
                "files": [],
                "message": f"Failed to list folder: {exc}",
            }

        folders.sort(key=str.lower)
        files.sort(key=lambda item: item["name"].lower())

        return {
            "status": "success",
            "folder": safe_path,
            "exists": True,
            "item_count": len(folders) + len(files),
            "folders": folders,
            "files": files,
            "message": "",
        }

    def file_info(self, path: str) -> Dict[str, Any]:
        validation = self._validate_file_path(path)
        if not validation["valid"]:
            return {
                "status": "failed",
                "file": self._empty_file_info(validation["path"]),
                "message": validation["message"],
            }

        safe_path = validation["path"]
        try:
            stat = os.stat(safe_path, follow_symlinks=False)
        except Exception as exc:
            return {
                "status": "failed",
                "file": self._empty_file_info(safe_path),
                "message": f"Failed to inspect file metadata: {exc}",
            }

        name = os.path.basename(safe_path)
        _, extension = os.path.splitext(name)

        return {
            "status": "success",
            "file": {
                "path": safe_path,
                "exists": True,
                "name": name,
                "extension": extension,
                "size_bytes": int(stat.st_size),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "is_file": True,
            },
            "message": "File metadata inspected successfully.",
        }

    def _validate_folder_path(self, path: str) -> Dict[str, Any]:
        requested_path = str(path or "").strip().strip('"')
        if not requested_path:
            return self._folder_validation(False, "", "Folder path is required.")

        lowered = requested_path.lower()
        if requested_path.startswith(("\\\\", "//")):
            return self._folder_validation(False, requested_path, "Network and UNC paths are not allowed.")
        if any(token in lowered for token in ["shell:", "control panel", "::{", "registry", "regedit"]):
            return self._folder_validation(False, requested_path, "Shell, registry, and Control Panel paths are not allowed.")
        if not os.path.isabs(requested_path) or not os.path.splitdrive(requested_path)[0]:
            return self._folder_validation(False, requested_path, "Only absolute local drive folders are allowed.")

        absolute_path = os.path.abspath(requested_path)
        if not os.path.isdir(absolute_path):
            return self._folder_validation(False, absolute_path, "Folder does not exist.")
        if self._is_admin_folder(absolute_path):
            return self._folder_validation(False, absolute_path, "Administrative and system folders are not allowed.")

        return self._folder_validation(True, absolute_path, "")

    def _validate_file_path(self, path: str) -> Dict[str, Any]:
        requested_path = str(path or "").strip().strip('"')
        if not requested_path:
            return self._folder_validation(False, "", "File path is required.")

        lowered = requested_path.lower()
        if requested_path.startswith(("\\\\", "//")):
            return self._folder_validation(False, requested_path, "Network and UNC paths are not allowed.")
        if any(token in lowered for token in ["shell:", "control panel", "::{", "registry", "regedit"]):
            return self._folder_validation(False, requested_path, "Shell, registry, and Control Panel paths are not allowed.")
        if not os.path.isabs(requested_path) or not os.path.splitdrive(requested_path)[0]:
            return self._folder_validation(False, requested_path, "Only absolute local file paths are allowed.")

        absolute_path = os.path.abspath(requested_path)
        if self._is_admin_folder(absolute_path):
            return self._folder_validation(False, absolute_path, "Administrative and system paths are not allowed.")
        if not os.path.exists(absolute_path):
            return self._folder_validation(False, absolute_path, "File does not exist.")
        if os.path.isdir(absolute_path):
            return self._folder_validation(False, absolute_path, "Folders are not valid for file metadata inspection.")
        if not os.path.isfile(absolute_path):
            return self._folder_validation(False, absolute_path, "Path is not a regular file.")

        return self._folder_validation(True, absolute_path, "")

    def _is_admin_folder(self, path: str) -> bool:
        normalized = os.path.normcase(os.path.abspath(path))
        protected_roots = [
            os.environ.get("SystemRoot", r"C:\Windows"),
            os.environ.get("ProgramFiles", r"C:\Program Files"),
            os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
            os.environ.get("ProgramData", r"C:\ProgramData"),
        ]

        for root in protected_roots:
            if not root:
                continue
            protected = os.path.normcase(os.path.abspath(root))
            if normalized == protected or normalized.startswith(protected + os.sep):
                return True

        return False

    def _folder_validation(self, valid: bool, path: str, message: str) -> Dict[str, Any]:
        return {
            "valid": valid,
            "path": path,
            "message": message,
        }

    def _empty_file_info(self, path: str) -> Dict[str, Any]:
        name = os.path.basename(path) if path else ""
        _, extension = os.path.splitext(name)
        return {
            "path": path,
            "exists": False,
            "name": name,
            "extension": extension,
            "size_bytes": 0,
            "modified": "",
            "created": "",
            "is_file": False,
        }


desktop_agent = AthenaDesktopAgent()
