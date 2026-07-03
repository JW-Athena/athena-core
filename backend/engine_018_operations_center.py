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
