from datetime import datetime
from typing import Any, Dict, List
from uuid import uuid4
import builtins

from event_bus import event_bus


VALID_STATUSES = {"active", "paused", "completed", "cancelled"}
VALID_PRIORITIES = {"low", "medium", "high", "critical"}


class StrategicObjectiveManager:
    def __init__(self):
        if not hasattr(builtins, "_ATHENA_STRATEGIC_OBJECTIVES"):
            builtins._ATHENA_STRATEGIC_OBJECTIVES = {}
        self._objectives: Dict[str, Dict[str, Any]] = builtins._ATHENA_STRATEGIC_OBJECTIVES

    def create_strategic_objective(
        self,
        title: str,
        description: str = "",
        priority: str = "medium",
    ) -> Dict[str, Any]:
        clean_title = str(title or "").strip()
        if not clean_title:
            return self._failure("title_required", "Strategic objective title is required.")

        now = self._now()
        objective = {
            "strategic_objective_id": str(uuid4()),
            "title": clean_title,
            "description": str(description or "").strip(),
            "status": "active",
            "priority": self._normalize_priority(priority),
            "progress": 0,
            "missions": [],
            "recommended_next_mission": "",
            "created_at": now,
            "updated_at": now,
        }
        objective["recommended_next_mission"] = self._recommend_next_mission(objective)
        self._objectives[objective["strategic_objective_id"]] = objective

        event_bus.publish(
            "StrategicObjectiveCreated",
            "strategic_objective_manager",
            self._event_payload(objective, result="success"),
        )
        return self._success({"strategic_objective": dict(objective)})

    def list_strategic_objectives(self) -> Dict[str, Any]:
        objectives = [dict(objective) for objective in self._objectives.values()]
        objectives.sort(key=lambda item: item.get("created_at", ""), reverse=True)
        return self._success({
            "count": len(objectives),
            "strategic_objectives": objectives,
        })

    def get_strategic_objective(self, strategic_objective_id: str) -> Dict[str, Any]:
        objective = self._find_objective(strategic_objective_id)
        if not objective:
            return self._failure("strategic_objective_not_found", "Strategic objective was not found.")
        return self._success({"strategic_objective": dict(objective)})

    def update_status(self, strategic_objective_id: str, status: str) -> Dict[str, Any]:
        objective = self._find_objective(strategic_objective_id)
        if not objective:
            return self._failure("strategic_objective_not_found", "Strategic objective was not found.")

        normalized_status = self._normalize_status(status)
        if not normalized_status:
            return self._failure("invalid_status", "Status must be active, paused, completed, or cancelled.")

        objective["status"] = normalized_status
        objective["progress"] = self._calculate_progress(objective)
        objective["recommended_next_mission"] = self._recommend_next_mission(objective)
        objective["updated_at"] = self._now()

        event_bus.publish(
            "StrategicObjectiveUpdated",
            "strategic_objective_manager",
            self._event_payload(objective, result="success"),
        )
        return self._success({"strategic_objective": dict(objective)})

    def attach_mission(self, strategic_objective_id: str, mission: Dict[str, Any]) -> Dict[str, Any]:
        objective = self._find_objective(strategic_objective_id)
        if not objective:
            return self._failure("strategic_objective_not_found", "Strategic objective was not found.")

        mission_record = self._normalize_mission(mission)
        objective["missions"].append(mission_record)
        objective["progress"] = self._calculate_progress(objective)
        objective["recommended_next_mission"] = self._recommend_next_mission(objective)
        objective["updated_at"] = self._now()

        event_bus.publish(
            "StrategicObjectiveMissionAttached",
            "strategic_objective_manager",
            {
                **self._event_payload(objective, result="success"),
                "mission_id": mission_record.get("mission_id", ""),
                "mission": mission_record.get("mission", ""),
                "mission_status": mission_record.get("mission_status", ""),
            },
        )
        event_bus.publish(
            "StrategicObjectiveUpdated",
            "strategic_objective_manager",
            self._event_payload(objective, result="success"),
        )
        return self._success({"strategic_objective": dict(objective)})

    def recommend_next_mission(self, strategic_objective_id: str) -> Dict[str, Any]:
        objective = self._find_objective(strategic_objective_id)
        if not objective:
            return self._failure("strategic_objective_not_found", "Strategic objective was not found.")

        recommendation = self._recommend_next_mission(objective)
        objective["recommended_next_mission"] = recommendation
        objective["updated_at"] = self._now()

        event_bus.publish(
            "StrategicObjectiveNextMissionRecommended",
            "strategic_objective_manager",
            {
                **self._event_payload(objective, result="success"),
                "recommended_next_mission": recommendation,
            },
        )
        return self._success({
            "strategic_objective_id": objective["strategic_objective_id"],
            "recommended_next_mission": recommendation,
            "strategic_objective": dict(objective),
        })

    def _find_objective(self, strategic_objective_id: str) -> Dict[str, Any]:
        return self._objectives.get(str(strategic_objective_id or "").strip(), {})

    def _normalize_status(self, status: str) -> str:
        normalized = str(status or "").strip().lower()
        return normalized if normalized in VALID_STATUSES else ""

    def _normalize_priority(self, priority: str) -> str:
        normalized = str(priority or "").strip().lower()
        return normalized if normalized in VALID_PRIORITIES else "medium"

    def _normalize_mission(self, mission: Dict[str, Any]) -> Dict[str, Any]:
        source = mission or {}
        return {
            "mission_id": str(source.get("mission_id") or source.get("id") or uuid4()),
            "mission": str(source.get("mission") or source.get("title") or source.get("objective") or "").strip(),
            "mission_status": str(source.get("mission_status") or source.get("status") or "completed").strip().lower(),
            "summary": str(source.get("summary") or source.get("executive_summary") or "").strip(),
            "decision_ready": bool(source.get("decision_ready", False)),
            "approval_required": bool(source.get("approval_required", False)),
            "attached_at": self._now(),
            "payload": source,
        }

    def _calculate_progress(self, objective: Dict[str, Any]) -> int:
        status = objective.get("status", "")
        if status == "completed":
            return 100
        if status == "cancelled":
            return int(objective.get("progress", 0) or 0)

        missions = objective.get("missions", []) or []
        if not missions:
            return 0

        score = 0
        for mission in missions:
            mission_status = str(mission.get("mission_status", "") or "").lower()
            if mission_status == "completed":
                score += 25
            elif mission_status == "pending_approval":
                score += 18
            elif mission_status in {"partial", "running"}:
                score += 12
            elif mission_status in {"failed", "rejected"}:
                score += 5
            else:
                score += 10

            if mission.get("decision_ready"):
                score += 5
            if mission.get("approval_required"):
                score -= 3

        return max(0, min(score, 95))

    def _recommend_next_mission(self, objective: Dict[str, Any]) -> str:
        status = objective.get("status", "active")
        if status == "completed":
            return "No further mission is required. Archive outcomes and capture lessons learned."
        if status == "cancelled":
            return "No mission recommended. Objective has been cancelled."
        if status == "paused":
            return "Confirm whether this objective should be resumed before assigning a new mission."

        title_text = f"{objective.get('title', '')} {objective.get('description', '')}".lower()
        progress = int(objective.get("progress", 0) or 0)
        missions = objective.get("missions", []) or []

        if not missions:
            if "ministry of interior" in title_text or "moi" in title_text or "tender" in title_text:
                return "Analyze the current tender package and identify missing award, submission, pricing, and compliance requirements."
            if "supplier" in title_text:
                return "Review supplier exposure, dependency risk, and replacement options for executive decision."
            if "bid" in title_text or "submission" in title_text:
                return "Prepare a bid readiness mission covering pricing, compliance, documentation, and approval blockers."
            return "Run an executive discovery mission to define success criteria, risks, blockers, and required decisions."

        latest = missions[-1]
        latest_status = latest.get("mission_status", "")
        if latest.get("approval_required") or latest_status == "pending_approval":
            return "Resolve the pending executive approval and clarify any missing decision inputs before continuing."
        if latest_status in {"failed", "rejected"}:
            return "Run a recovery mission to isolate failure causes, unresolved risks, and alternate execution paths."
        if progress < 50:
            return "Execute a planning mission to convert findings into milestones, owners, risks, and next executive decisions."
        if progress < 80:
            return "Execute a readiness mission to validate commercial, operational, legal, and approval requirements."
        return "Prepare the executive decision brief and final action plan for approval."

    def _event_payload(self, objective: Dict[str, Any], result: str) -> Dict[str, Any]:
        return {
            "strategic_objective_id": objective.get("strategic_objective_id", ""),
            "title": objective.get("title", ""),
            "status": objective.get("status", ""),
            "priority": objective.get("priority", ""),
            "progress": objective.get("progress", 0),
            "result": result,
        }

    def _success(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "engine": "strategic_objective_manager",
            "status": "success",
            **payload,
        }

    def _failure(self, reason: str, message: str) -> Dict[str, Any]:
        return {
            "engine": "strategic_objective_manager",
            "status": "failed",
            "reason": reason,
            "message": message,
        }

    def _now(self) -> str:
        return datetime.utcnow().isoformat()


strategic_objective_manager = StrategicObjectiveManager()
