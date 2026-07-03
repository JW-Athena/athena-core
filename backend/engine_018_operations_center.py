from datetime import datetime
from typing import Any, Dict, List
import builtins

from engine_013_learning_engine import execution_learning_engine
from engine_014_adaptive_planner import adaptive_summary
from engine_015_mission_controller import mission_controller
from engine_017_approval_workflow import approval_workflow
from event_bus import event_bus


class OperationsCenter:
    def __init__(self):
        self.started_at = datetime.utcnow()

    def overview(self) -> Dict[str, Any]:
        event_bus.publish(
            "OperationsOverviewRequested",
            "operations_center",
            {"result": "success"},
        )
        missions = mission_controller.list_mission_records()
        learning = execution_learning_engine.list_learning_records()
        approvals = self._approval_records()
        events = event_bus.latest(limit=100)
        timeline = self.get_operations_timeline(limit=100, publish_event=False)
        execution = self._execution_totals(missions)
        objective_types = adaptive_summary().get("objective_types", {})
        successful_patterns = execution_learning_engine.find_successful_patterns().get("count", 0)

        return {
            "engine": "operations_center",
            "status": "success",
            "system_status": "healthy",
            "brain": {
                "missions_active": self._count_status(missions, {"running", "pending"}),
                "missions_completed": self._count_status(missions, {"completed"}),
                "missions_pending_approval": self._count_status(missions, {"pending_approval"}),
                "parallel_enabled": True,
                "adaptive_planning": True,
            },
            "execution": execution,
            "learning": {
                "records": learning.get("count", 0),
                "objective_types": objective_types,
                "successful_patterns": successful_patterns,
            },
            "approvals": {
                "pending": len([item for item in approvals if item.get("status") == "pending"]),
                "approved_today": len([item for item in approvals if item.get("status") in {"approved", "resumed"} and self._is_today(item.get("resolved_at"))]),
                "rejected_today": len([item for item in approvals if item.get("status") == "rejected" and self._is_today(item.get("resolved_at"))]),
            },
            "event_bus": {
                "events": len(events),
            },
            "timeline": {
                "recent_events": timeline.get("count", 0),
                "errors": len([item for item in timeline.get("timeline", []) if item.get("severity") == "error"]),
                "warnings": len([item for item in timeline.get("timeline", []) if item.get("severity") == "warning"]),
            },
            "statistics": {
                "uptime": self._uptime(),
                "version": "4.0",
            },
        }

    def health(self) -> Dict[str, Any]:
        event_bus.publish(
            "OperationsHealthRequested",
            "operations_center",
            {"result": "success"},
        )
        missions = mission_controller.list_mission_records()
        learning = execution_learning_engine.list_learning_records()
        approvals = approval_workflow.list_pending_approvals()
        events = event_bus.latest(limit=1)
        execution = self._execution_totals(missions)

        return {
            "system_status": "healthy",
            "brain_status": "healthy",
            "runtime_status": "healthy",
            "mission_controller": "healthy",
            "learning_engine": "healthy" if learning.get("status") == "success" else "degraded",
            "approval_engine": "healthy" if approvals.get("status") == "success" else "degraded",
            "event_bus": "healthy" if isinstance(events, list) else "degraded",
            "cache": "healthy" if execution.get("cache_hits", 0) >= 0 else "degraded",
            "overall": "healthy",
        }

    def live_missions(self) -> Dict[str, Any]:
        missions = mission_controller.list_mission_records()
        pending = [
            mission
            for mission in missions
            if mission.get("mission_status") == "pending_approval"
        ]
        completed = [
            mission
            for mission in missions
            if mission.get("mission_status") == "completed"
        ]

        return {
            "engine": "operations_center",
            "status": "success",
            "current_missions": [
                mission
                for mission in missions
                if mission.get("mission_status") in {"running", "pending", "pending_approval"}
            ],
            "pending_missions": pending,
            "completed_missions": completed,
            "mission_statistics": {
                "total": len(missions),
                "pending": len(pending),
                "completed": len(completed),
                "failed": len([mission for mission in missions if mission.get("mission_status") == "failed"]),
                "partial": len([mission for mission in missions if mission.get("mission_status") == "partial"]),
            },
        }

    def live_events(self, limit: int = 100) -> Dict[str, Any]:
        events = event_bus.latest(limit=limit)
        events.reverse()
        return {
            "engine": "operations_center",
            "status": "success",
            "count": len(events),
            "events": events,
        }

    def get_operations_timeline(self, limit: int = 50, publish_event: bool = True) -> Dict[str, Any]:
        if publish_event:
            event_bus.publish(
                "OperationsTimelineRequested",
                "operations_center",
                {"limit": limit, "result": "success"},
            )
        safe_limit = max(1, min(int(limit or 50), 250))
        events = event_bus.latest(limit=safe_limit)
        events.reverse()
        timeline = [self._timeline_item(event) for event in events]
        return {
            "engine": "operations_center",
            "status": "success",
            "count": len(timeline),
            "timeline": timeline,
        }

    def _timeline_item(self, event: Dict[str, Any]) -> Dict[str, Any]:
        event_type = str(event.get("event_type", "") or "")
        payload = event.get("payload", {}) or {}
        return {
            "timestamp": event.get("timestamp", ""),
            "event_type": event_type,
            "source": event.get("source", ""),
            "category": self._event_category(event_type),
            "severity": self._event_severity(event_type),
            "title": self._event_title(event_type),
            "summary": self._event_summary(payload),
            "payload": payload,
        }

    def _event_category(self, event_type: str) -> str:
        if event_type.startswith("MissionExecution") or event_type.startswith("MissionObjective") or event_type.startswith("MissionDependency") or event_type.startswith("MissionParallel"):
            return "mission"
        if event_type.startswith("BrainObjective"):
            return "objective"
        if event_type.startswith("CapabilityExecution"):
            return "capability"
        if event_type.startswith("MissionApproval") or event_type in {"MissionApproved", "MissionRejected", "MissionResumed"}:
            return "approval"
        if event_type in {"ExecutionLearned", "ExecutionLearningFailed"}:
            return "learning"
        if event_type.startswith("AdaptivePlanning") or event_type.startswith("ExecutiveExecutionPlan"):
            return "planning"
        return "system"

    def _event_severity(self, event_type: str) -> str:
        if "Failed" in event_type:
            return "error"
        if "Required" in event_type or "Pending" in event_type:
            return "warning"
        return "info"

    def _event_title(self, event_type: str) -> str:
        special_titles = {
            "MissionExecutionStarted": "Mission execution started",
            "MissionExecutionCompleted": "Mission execution completed",
            "MissionExecutionFailed": "Mission execution failed",
            "MissionApprovalRequired": "Mission approval required",
            "MissionApproved": "Mission approved",
            "MissionRejected": "Mission rejected",
            "MissionResumed": "Mission resumed",
            "CapabilityExecutionCompleted": "Capability completed",
            "CapabilityExecutionFailed": "Capability failed",
            "ExecutionLearned": "Execution learned",
            "OperationsTimelineRequested": "Operations timeline requested",
        }
        if event_type in special_titles:
            return special_titles[event_type]
        words = []
        current = ""
        for char in event_type:
            if char.isupper() and current:
                words.append(current)
                current = char
            else:
                current += char
        if current:
            words.append(current)
        title = " ".join(words).strip()
        return title[:1].upper() + title[1:].lower() if title else "System event"

    def _event_summary(self, payload: Dict[str, Any]) -> str:
        parts = []
        for key in ["mission", "objective", "capability", "selected_plan", "result", "reason"]:
            value = str(payload.get(key, "") or "").strip()
            if value:
                parts.append(f"{key}: {value}")
        return "; ".join(parts) if parts else "ATHENA event recorded."

    def _execution_totals(self, missions: List[Dict[str, Any]]) -> Dict[str, int]:
        totals = {
            "capabilities_executed": 0,
            "capabilities_reused": 0,
            "cache_hits": 0,
            "cache_misses": 0,
        }
        for mission in missions:
            stats = mission.get("mission_statistics", {}) or {}
            totals["capabilities_executed"] += int(stats.get("executed", 0) or 0)
            totals["capabilities_reused"] += int(stats.get("reused", 0) or 0)
            totals["cache_hits"] += int(stats.get("cache_hits", 0) or 0)
            totals["cache_misses"] += int(stats.get("cache_misses", 0) or 0)
        return totals

    def _count_status(self, missions: List[Dict[str, Any]], statuses: set) -> int:
        return len([
            mission
            for mission in missions
            if mission.get("mission_status") in statuses
        ])

    def _approval_records(self) -> List[Dict[str, Any]]:
        return [
            dict(item)
            for item in getattr(builtins, "_ATHENA_MISSION_APPROVALS", [])
        ]

    def _is_today(self, value: Any) -> bool:
        text = str(value or "")
        return bool(text and text[:10] == datetime.utcnow().date().isoformat())

    def _uptime(self) -> str:
        delta = datetime.utcnow() - self.started_at
        return str(delta).split(".")[0]


operations_center = OperationsCenter()
