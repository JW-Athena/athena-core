import os
import subprocess
from fnmatch import fnmatch
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

    SAFE_TEXT_EXTENSIONS = {".txt", ".md", ".json", ".log", ".csv"}
    MAX_SAFE_TEXT_BYTES = 1024 * 1024

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

    def read_file(self, path: str) -> Dict[str, Any]:
        validation = self._validate_readable_text_file(path)
        if not validation["valid"]:
            return {
                "status": "blocked",
                "reason": validation["reason"],
                "file": self._empty_read_file_info(validation["path"]),
                "message": validation["message"],
            }

        safe_path = validation["path"]
        try:
            with open(safe_path, "rb") as handle:
                raw_content = handle.read(self.MAX_SAFE_TEXT_BYTES + 1)
        except Exception as exc:
            return {
                "status": "blocked",
                "reason": "read_error",
                "file": self._empty_read_file_info(safe_path),
                "message": f"Failed to read file safely: {exc}",
            }

        if self._is_binary_content(raw_content):
            return {
                "status": "blocked",
                "reason": "binary_file_detected",
                "file": self._empty_read_file_info(safe_path),
                "message": "Binary file content was detected.",
            }

        try:
            content = self._decode_text(raw_content)
        except UnicodeDecodeError:
            return {
                "status": "blocked",
                "reason": "binary_file_detected",
                "file": self._empty_read_file_info(safe_path),
                "message": "File could not be decoded as safe text.",
            }
        except Exception as exc:
            return {
                "status": "blocked",
                "reason": "read_error",
                "file": self._empty_read_file_info(safe_path),
                "message": f"Failed to decode file safely: {exc}",
            }

        stat = os.stat(safe_path, follow_symlinks=False)
        name = os.path.basename(safe_path)
        _, extension = os.path.splitext(name)

        return {
            "status": "success",
            "file": {
                "path": safe_path,
                "exists": True,
                "name": name,
                "extension": extension.lower(),
                "size_bytes": int(stat.st_size),
                "content": content,
                "truncated": False,
            },
            "message": "Safe text file read successfully.",
        }

    def search_files(
        self,
        folder: str,
        pattern: str = "*",
        recursive: bool = False,
        max_results: int = 100,
    ) -> Dict[str, Any]:
        validation = self._validate_folder_path(folder)
        if not validation["valid"]:
            return {
                "status": "failed",
                "folder": validation["path"],
                "pattern": pattern or "*",
                "recursive": bool(recursive),
                "max_results": self._safe_max_results(max_results),
                "result_count": 0,
                "results": [],
                "message": validation["message"],
            }

        safe_folder = validation["path"]
        safe_pattern = str(pattern or "*").strip() or "*"
        safe_max_results = self._safe_max_results(max_results)
        results = []

        try:
            if recursive:
                for root, dirs, files in os.walk(safe_folder):
                    dirs[:] = [
                        directory
                        for directory in dirs
                        if not self._is_admin_folder(os.path.join(root, directory))
                    ]
                    self._append_matching_files(
                        results=results,
                        root=root,
                        files=files,
                        pattern=safe_pattern,
                        max_results=safe_max_results,
                    )
                    if len(results) >= safe_max_results:
                        break
            else:
                files = []
                with os.scandir(safe_folder) as entries:
                    for entry in entries:
                        if entry.is_file(follow_symlinks=False):
                            files.append(entry.name)
                self._append_matching_files(
                    results=results,
                    root=safe_folder,
                    files=files,
                    pattern=safe_pattern,
                    max_results=safe_max_results,
                )
        except Exception as exc:
            return {
                "status": "failed",
                "folder": safe_folder,
                "pattern": safe_pattern,
                "recursive": bool(recursive),
                "max_results": safe_max_results,
                "result_count": len(results),
                "results": results,
                "message": f"Failed to search files: {exc}",
            }

        results.sort(key=lambda item: item["path"].lower())
        return {
            "status": "success",
            "folder": safe_folder,
            "pattern": safe_pattern,
            "recursive": bool(recursive),
            "max_results": safe_max_results,
            "result_count": len(results),
            "results": results,
            "message": "",
        }

    def open_file_location(self, path: str) -> Dict[str, Any]:
        validation = self._validate_file_location_path(path)
        if not validation["valid"]:
            return {
                "status": "failed",
                "reason": validation["reason"],
                "path": validation["path"],
                "folder": "",
                "name": os.path.basename(validation["path"]) if validation["path"] else "",
                "message": validation["message"],
            }

        safe_path = validation["path"]
        folder = os.path.dirname(safe_path)
        name = os.path.basename(safe_path)

        try:
            subprocess.Popen(["explorer.exe", f"/select,{safe_path}"])
        except Exception as exc:
            return {
                "status": "failed",
                "reason": "open_error",
                "path": safe_path,
                "folder": folder,
                "name": name,
                "message": f"Failed to open file location: {exc}",
            }

        return {
            "status": "success",
            "path": safe_path,
            "folder": folder,
            "name": name,
            "message": "File location opened.",
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

    def _validate_readable_text_file(self, path: str) -> Dict[str, Any]:
        requested_path = str(path or "").strip().strip('"')
        if not requested_path:
            return self._read_validation(False, "", "file_not_found", "File path is required.")

        lowered = requested_path.lower()
        if requested_path.startswith(("\\\\", "//")):
            return self._read_validation(False, requested_path, "file_not_found", "Network and UNC paths are not allowed.")
        if any(token in lowered for token in ["shell:", "control panel", "::{", "registry", "regedit"]):
            return self._read_validation(False, requested_path, "file_not_found", "Shell, registry, and Control Panel paths are not allowed.")
        if not os.path.isabs(requested_path) or not os.path.splitdrive(requested_path)[0]:
            return self._read_validation(False, requested_path, "file_not_found", "Only absolute local file paths are allowed.")

        absolute_path = os.path.abspath(requested_path)
        if self._is_admin_folder(absolute_path):
            return self._read_validation(False, absolute_path, "file_not_found", "Administrative and system paths are not allowed.")
        if not os.path.exists(absolute_path):
            return self._read_validation(False, absolute_path, "file_not_found", "File does not exist.")
        if os.path.isdir(absolute_path):
            return self._read_validation(False, absolute_path, "path_is_directory", "Folders cannot be read as files.")
        if not os.path.isfile(absolute_path):
            return self._read_validation(False, absolute_path, "file_not_found", "Path is not a regular file.")

        _, extension = os.path.splitext(absolute_path)
        if extension.lower() not in self.SAFE_TEXT_EXTENSIONS:
            return self._read_validation(False, absolute_path, "unsupported_file_type", "File type is not allowed for safe text reading.")

        try:
            size_bytes = os.path.getsize(absolute_path)
        except OSError as exc:
            return self._read_validation(False, absolute_path, "read_error", f"Failed to inspect file size: {exc}")

        if size_bytes > self.MAX_SAFE_TEXT_BYTES:
            return self._read_validation(False, absolute_path, "file_too_large", "File exceeds the 1 MB safe read limit.")

        return self._read_validation(True, absolute_path, "", "")

    def _validate_file_location_path(self, path: str) -> Dict[str, Any]:
        requested_path = str(path or "").strip().strip('"')
        if not requested_path:
            return self._location_validation(False, "", "file_not_found", "File path is required.")

        lowered = requested_path.lower()
        if requested_path.startswith(("\\\\", "//")):
            return self._location_validation(False, requested_path, "unsafe_path", "Network and UNC paths are not allowed.")
        if any(token in lowered for token in ["shell:", "control panel", "::{", "registry", "regedit"]):
            return self._location_validation(False, requested_path, "unsafe_path", "Shell, registry, and Control Panel paths are not allowed.")
        if not os.path.isabs(requested_path) or not os.path.splitdrive(requested_path)[0]:
            return self._location_validation(False, requested_path, "unsafe_path", "Only absolute local file paths are allowed.")

        absolute_path = os.path.abspath(requested_path)
        folder = os.path.dirname(absolute_path)
        if self._is_admin_folder(absolute_path) or self._is_admin_folder(folder):
            return self._location_validation(False, absolute_path, "unsafe_path", "Administrative and system paths are not allowed.")
        if not os.path.exists(absolute_path):
            return self._location_validation(False, absolute_path, "file_not_found", "File does not exist.")
        if os.path.isdir(absolute_path):
            return self._location_validation(False, absolute_path, "path_is_directory", "Path is a directory, not a file.")
        if not os.path.isfile(absolute_path):
            return self._location_validation(False, absolute_path, "file_not_found", "Path is not a regular file.")
        if not os.path.isdir(folder):
            return self._location_validation(False, absolute_path, "file_not_found", "Containing folder does not exist.")

        return self._location_validation(True, absolute_path, "", "")

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

    def _safe_max_results(self, max_results: int) -> int:
        try:
            requested = int(max_results)
        except (TypeError, ValueError):
            requested = 100
        return max(1, min(requested, 1000))

    def _append_matching_files(
        self,
        results: list,
        root: str,
        files: list,
        pattern: str,
        max_results: int,
    ) -> None:
        for filename in files:
            if len(results) >= max_results:
                return
            if not fnmatch(filename.lower(), pattern.lower()):
                continue

            full_path = os.path.join(root, filename)
            if self._is_admin_folder(full_path):
                continue

            try:
                stat = os.stat(full_path, follow_symlinks=False)
            except OSError:
                continue

            _, extension = os.path.splitext(filename)
            results.append(
                {
                    "path": full_path,
                    "name": filename,
                    "extension": extension.lower(),
                    "size_bytes": int(stat.st_size),
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                }
            )

    def _folder_validation(self, valid: bool, path: str, message: str) -> Dict[str, Any]:
        return {
            "valid": valid,
            "path": path,
            "message": message,
        }

    def _read_validation(self, valid: bool, path: str, reason: str, message: str) -> Dict[str, Any]:
        return {
            "valid": valid,
            "path": path,
            "reason": reason,
            "message": message,
        }

    def _location_validation(self, valid: bool, path: str, reason: str, message: str) -> Dict[str, Any]:
        return {
            "valid": valid,
            "path": path,
            "reason": reason,
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

    def _empty_read_file_info(self, path: str) -> Dict[str, Any]:
        name = os.path.basename(path) if path else ""
        _, extension = os.path.splitext(name)
        return {
            "path": path,
            "exists": os.path.exists(path) if path else False,
            "name": name,
            "extension": extension.lower(),
            "size_bytes": 0,
            "content": "",
            "truncated": False,
        }

    def _is_binary_content(self, content: bytes) -> bool:
        if not content:
            return False
        if b"\x00" in content:
            return True

        allowed_controls = {7, 8, 9, 10, 12, 13, 27}
        control_count = 0
        for byte in content:
            if byte < 32 and byte not in allowed_controls:
                control_count += 1

        return (control_count / len(content)) > 0.05

    def _decode_text(self, content: bytes) -> str:
        try:
            return content.decode("utf-8-sig")
        except UnicodeDecodeError:
            return content.decode("cp1252")


desktop_agent = AthenaDesktopAgent()
