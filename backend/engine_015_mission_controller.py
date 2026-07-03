from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List
import asyncio

from engine_011_routes import execute_objective
from engine_013_learning_engine import execution_learning_engine
from engine_016_mission_context import MissionExecutionContext
from engine_017_approval_workflow import approval_workflow
from event_bus import event_bus


class MissionController:
    async def execute_mission(self, mission: str, path: str = "") -> Dict[str, Any]:
        clean_mission = str(mission or "").strip()
        objectives = self.decompose_mission(clean_mission)
        mission_context = MissionExecutionContext()
        mission_context.metadata["mission"] = clean_mission
        mission_context.metadata["path"] = path

        event_bus.publish(
            "MissionExecutionStarted",
            "executive_mission_controller",
            {
                "mission_id": mission_context.mission_id,
                "mission": clean_mission,
                "objectives_total": len(objectives),
                "result": "started",
            },
        )

        objective_results: Dict[str, Any] = {}
        completed = 0
        failed = 0
        stopped = False
        max_workers = 3
        dependency_levels = self._dependency_levels(objectives)
        parallelized_count = sum(1 for level in dependency_levels if len(level) > 1)

        event_bus.publish(
            "MissionParallelExecutionStarted",
            "executive_mission_controller",
            {
                "mission_id": mission_context.mission_id,
                "mission": clean_mission,
                "dependency_levels": dependency_levels,
                "result": "started",
            },
        )

        objective_map = {
            objective["objective_id"]: objective
            for objective in objectives
        }
        completed_ids = set()
        failed_ids = set()

        for level_index, level in enumerate(dependency_levels, start=1):
            ready_objectives = [
                objective_map[objective_id]
                for objective_id in level
                if self._dependencies_completed(objective_map[objective_id], completed_ids)
                and not self._dependencies_failed(objective_map[objective_id], failed_ids)
            ]
            skipped_objectives = [
                objective_map[objective_id]
                for objective_id in level
                if objective_id not in {objective["objective_id"] for objective in ready_objectives}
            ]
            for objective in skipped_objectives:
                objective["status"] = "failed"
                failed += 1
                failed_ids.add(objective["objective_id"])

            if stopped or not ready_objectives:
                continue

            event_bus.publish(
                "MissionDependencyLevelStarted",
                "executive_mission_controller",
                {
                    "mission_id": mission_context.mission_id,
                    "mission": clean_mission,
                    "dependency_level": level_index,
                    "objective_ids": [objective["objective_id"] for objective in ready_objectives],
                    "result": "started",
                },
            )

            level_results = self._execute_objective_level(
                objectives=ready_objectives,
                mission=clean_mission,
                path=path,
                mission_context=mission_context,
                max_workers=max_workers,
            )

            for objective in ready_objectives:
                objective_id = objective["objective_id"]
                result = level_results.get(objective_id, {})
                objective_results[objective_id] = result
                mission_context.store_objective_result(objective_id, result)

                if isinstance(result, dict) and result.get("status") == "success":
                    objective["status"] = "completed"
                    completed += 1
                    completed_ids.add(objective_id)
                    event_bus.publish(
                        "MissionObjectiveCompleted",
                        "executive_mission_controller",
                        {
                            "mission_id": mission_context.mission_id,
                            "mission": clean_mission,
                            "objective_id": objective_id,
                            "objective": objective["objective"],
                            "result": "success",
                        },
                    )
                else:
                    objective["status"] = "failed"
                    failed += 1
                    failed_ids.add(objective_id)
                    event_bus.publish(
                        "MissionObjectiveFailed",
                        "executive_mission_controller",
                        {
                            "mission_id": mission_context.mission_id,
                            "mission": clean_mission,
                            "objective_id": objective_id,
                            "objective": objective["objective"],
                            "reason": result.get("reason", "objective_execution_failed") if isinstance(result, dict) else "objective_execution_failed",
                            "result": "failed",
                        },
                    )
                    if objective.get("critical"):
                        stopped = True

            event_bus.publish(
                "MissionDependencyLevelCompleted",
                "executive_mission_controller",
                {
                    "mission_id": mission_context.mission_id,
                    "mission": clean_mission,
                    "dependency_level": level_index,
                    "objective_ids": [objective["objective_id"] for objective in ready_objectives],
                    "result": "success",
                },
            )

            if stopped:
                break

        event_bus.publish(
            "MissionParallelExecutionCompleted",
            "executive_mission_controller",
            {
                "mission_id": mission_context.mission_id,
                "mission": clean_mission,
                "dependency_levels": dependency_levels,
                "result": "success" if not stopped else "failed",
            },
        )

        for objective in objectives:
            if objective["status"] != "pending":
                continue
            objective_id = objective["objective_id"]
            objective["status"] = "failed"
            failed += 1
            failed_ids.add(objective_id)
            event_bus.publish(
                "MissionObjectiveFailed",
                "executive_mission_controller",
                {
                    "mission_id": mission_context.mission_id,
                    "mission": clean_mission,
                    "objective_id": objective_id,
                    "objective": objective["objective"],
                    "reason": "dependency_not_completed",
                    "result": "failed",
                },
            )

        mission_status = self._mission_status(
            completed=completed,
            failed=failed,
            objectives_total=len(objectives),
            stopped=stopped,
        )
        mission_evaluation = self.evaluate_mission(
            mission=clean_mission,
            mission_status=mission_status,
            objectives=objectives,
            objective_results=objective_results,
        )
        approval_request = {}
        approval_required = bool(mission_evaluation.get("approval_required", False))
        if approval_required:
            mission_status = "pending_approval"
            approval_request = approval_workflow.create_approval_request(
                mission_id=mission_context.mission_id,
                mission=clean_mission,
                reason=mission_evaluation.get("summary", "Executive approval is required."),
                required_action=mission_evaluation.get("recommended_next_action", "Review and approve mission outcome."),
                approval_payload={
                    "mission_evaluation": mission_evaluation,
                    "mission_statistics": mission_context.statistics(),
                    "objectives": objectives,
                },
            )

        response = {
            "engine": "executive_mission_controller",
            "status": "success" if mission_status != "failed" else "failed",
            "mission": clean_mission,
            "mission_status": mission_status,
            "objectives_total": len(objectives),
            "objectives_completed": completed,
            "objectives_failed": failed,
            "objectives": objectives,
            "objective_results": objective_results,
            "execution_mode": "parallel",
            "parallel_execution": {
                "enabled": True,
                "max_workers": max_workers,
                "objectives_parallelized": parallelized_count,
                "dependency_levels": dependency_levels,
            },
            "mission_statistics": mission_context.statistics(),
            "mission_evaluation": mission_evaluation,
            "approval_required": approval_required,
            "approval_request": approval_request,
            "executive_response": {
                "summary": mission_evaluation.get("summary", ""),
                "recommended_next_action": mission_evaluation.get("recommended_next_action", ""),
                "requires_approval": approval_required,
            },
        }

        event_type = "MissionExecutionCompleted" if response["status"] == "success" else "MissionExecutionFailed"
        event_bus.publish(
            event_type,
            "executive_mission_controller",
            {
                "mission_id": mission_context.mission_id,
                "mission": clean_mission,
                "mission_status": mission_status,
                "objectives_total": len(objectives),
                "objectives_completed": completed,
                "objectives_failed": failed,
                "result": response["status"],
            },
        )
        return response

    def _execute_objective_level(
        self,
        objectives: List[Dict[str, Any]],
        mission: str,
        path: str,
        mission_context: MissionExecutionContext,
        max_workers: int,
    ) -> Dict[str, Any]:
        results = {}
        workers = max(1, min(max_workers, len(objectives)))
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(
                    self._execute_objective_sync,
                    objective,
                    mission,
                    path,
                    mission_context,
                ): objective
                for objective in objectives
            }
            for future in as_completed(futures):
                objective = futures[future]
                try:
                    results[objective["objective_id"]] = future.result()
                except Exception as exc:
                    results[objective["objective_id"]] = {
                        "engine": "executive_brain",
                        "status": "failed",
                        "reason": "objective_execution_error",
                        "message": f"Objective execution failed: {exc}",
                    }
        return results

    def _execute_objective_sync(
        self,
        objective: Dict[str, Any],
        mission: str,
        path: str,
        mission_context: MissionExecutionContext,
    ) -> Dict[str, Any]:
        objective_id = objective["objective_id"]
        event_bus.publish(
            "MissionObjectiveStarted",
            "executive_mission_controller",
            {
                "mission_id": mission_context.mission_id,
                "mission": mission,
                "objective_id": objective_id,
                "objective": objective["objective"],
                "result": "started",
            },
        )
        return asyncio.run(
            execute_objective(
                {
                    "objective": objective["objective"],
                    "path": path,
                    "mission_context": mission_context,
                    "objective_id": objective_id,
                }
            )
        )

    def decompose_mission(self, mission: str) -> List[Dict[str, Any]]:
        signal = mission.lower()
        if "tender" in signal:
            objective_texts = [
                "Analyze this tender and prepare an executive summary",
                "Identify tender obligations and required documents",
                "Build a tender risk register",
                "Prepare an executive action plan",
                "Prepare an executive decision brief",
            ]
        elif "contract" in signal:
            objective_texts = [
                "Analyze this contract document and extract key terms",
                "Identify contract obligations and liabilities",
                "Build a contract risk register for this document",
                "Prepare an executive decision brief",
                "Prepare an executive action plan",
            ]
        elif "supplier" in signal:
            objective_texts = [
                "Analyze this supplier document and prepare an executive summary",
                "Identify supplier risks",
                "Prepare supplier executive action plan",
            ]
        else:
            objective_texts = [
                "Analyze this document and prepare an executive summary",
                "Identify risks",
                "Prepare executive action plan",
            ]

        objectives = []
        for index, objective in enumerate(objective_texts, start=1):
            objectives.append(
                {
                    "objective_id": f"OBJ-{index:03d}",
                    "objective": objective,
                    "objective_type": execution_learning_engine._objective_type(objective),
                    "status": "pending",
                    "depends_on": [] if index == 1 else [f"OBJ-{index - 1:03d}"],
                    "critical": index == 1,
                }
            )
        return objectives

    def _dependency_levels(self, objectives: List[Dict[str, Any]]) -> List[List[str]]:
        remaining = {
            objective["objective_id"]: set(objective.get("depends_on", []) or [])
            for objective in objectives
        }
        levels = []
        resolved = set()

        while remaining:
            ready = sorted(
                objective_id
                for objective_id, dependencies in remaining.items()
                if dependencies.issubset(resolved)
            )
            if not ready:
                levels.append(sorted(remaining.keys()))
                break
            levels.append(ready)
            resolved.update(ready)
            for objective_id in ready:
                remaining.pop(objective_id, None)

        return levels

    def _dependencies_completed(self, objective: Dict[str, Any], completed_ids: set) -> bool:
        return all(
            dependency in completed_ids
            for dependency in objective.get("depends_on", []) or []
        )

    def _dependencies_failed(self, objective: Dict[str, Any], failed_ids: set) -> bool:
        return any(
            dependency in failed_ids
            for dependency in objective.get("depends_on", []) or []
        )

    def evaluate_mission(
        self,
        mission: str,
        mission_status: str,
        objectives: List[Dict[str, Any]],
        objective_results: Dict[str, Any],
    ) -> Dict[str, Any]:
        evaluations = []
        critical_blockers = []
        missing_information = []
        approval_required = False

        for objective in objectives:
            result = objective_results.get(objective["objective_id"], {})
            evaluation = result.get("execution_evaluation", {}) if isinstance(result, dict) else {}
            if evaluation:
                evaluations.append(evaluation)
                missing_information.extend(evaluation.get("missing_information", []) or [])
                approval_required = approval_required or bool(evaluation.get("approval_required", False))
                if not evaluation.get("objective_satisfied", False) and objective.get("critical"):
                    critical_blockers.append(objective["objective"])
            elif objective.get("status") == "failed":
                critical_blockers.append(objective["objective"])

        decision_ready = bool(evaluations) and all(
            bool(evaluation.get("decision_ready", False))
            for evaluation in evaluations
        )
        confidence = self._average_confidence(evaluations, mission_status)
        mission_satisfied = (
            mission_status == "completed"
            and bool(evaluations)
            and all(bool(evaluation.get("objective_satisfied", False)) for evaluation in evaluations)
        )
        recommended_next_action = self._recommended_next_action(
            evaluations=evaluations,
            missing_information=missing_information,
            critical_blockers=critical_blockers,
            decision_ready=decision_ready,
            approval_required=approval_required,
        )

        return {
            "mission_satisfied": mission_satisfied,
            "decision_ready": decision_ready,
            "confidence": confidence,
            "approval_required": approval_required,
            "critical_blockers": self._dedupe(critical_blockers),
            "missing_information": self._dedupe(missing_information),
            "recommended_next_action": recommended_next_action,
            "summary": self._summary(
                mission=mission,
                mission_satisfied=mission_satisfied,
                decision_ready=decision_ready,
                confidence=confidence,
                critical_blockers=critical_blockers,
                missing_information=missing_information,
            ),
        }

    def _mission_status(self, completed: int, failed: int, objectives_total: int, stopped: bool) -> str:
        if stopped or (failed and completed == 0):
            return "failed"
        if completed == objectives_total and failed == 0:
            return "completed"
        return "partial"

    def _average_confidence(self, evaluations: List[Dict[str, Any]], mission_status: str) -> int:
        if not evaluations:
            return 0
        confidence = round(
            sum(int(evaluation.get("confidence", 0) or 0) for evaluation in evaluations) / len(evaluations)
        )
        if mission_status == "partial":
            confidence = min(confidence, 65)
        if mission_status == "failed":
            confidence = min(confidence, 35)
        return max(0, min(100, confidence))

    def _recommended_next_action(
        self,
        evaluations: List[Dict[str, Any]],
        missing_information: List[str],
        critical_blockers: List[str],
        decision_ready: bool,
        approval_required: bool,
    ) -> str:
        if critical_blockers:
            return f"Resolve critical blocker: {critical_blockers[0]}."
        if missing_information:
            return f"Resolve missing information: {missing_information[0]}."
        if decision_ready and approval_required:
            return "Proceed to executive approval review."
        if decision_ready:
            return "Proceed with the coordinated mission action plan."
        for evaluation in evaluations:
            action = str(evaluation.get("recommended_next_action", "") or "").strip()
            if action:
                return action
        return "Review mission objective results and assign accountable owners."

    def _summary(
        self,
        mission: str,
        mission_satisfied: bool,
        decision_ready: bool,
        confidence: int,
        critical_blockers: List[str],
        missing_information: List[str],
    ) -> str:
        if mission_satisfied and decision_ready:
            return "Mission completed and is decision-ready."
        if mission_satisfied:
            return "Mission objectives were executed, but final decision readiness remains conditional."
        if critical_blockers:
            return "Mission execution found critical blockers that must be resolved."
        if missing_information:
            return "Mission execution completed with missing information that prevents full satisfaction."
        return f"Mission execution completed with confidence {confidence}."

    def _dedupe(self, values: List[Any]) -> List[str]:
        deduped = []
        for value in values:
            text = str(value or "").strip()
            if text and text not in deduped:
                deduped.append(text)
        return deduped


mission_controller = MissionController()
