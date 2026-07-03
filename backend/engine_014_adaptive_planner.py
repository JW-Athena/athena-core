from collections import Counter
from typing import Any, Dict, List

from engine_013_learning_engine import (
    execution_learning_engine,
    find_similar_patterns,
    find_successful_patterns,
)
from event_bus import event_bus
from executive_execution_plan_routes import build_execution_plan


async def build_adaptive_plan(objective: str, path: str = "") -> Dict[str, Any]:
    objective_type = execution_learning_engine._objective_type(objective)
    event_bus.publish(
        "AdaptivePlanningStarted",
        "adaptive_planner",
        {
            "objective": objective,
            "objective_type": objective_type,
            "result": "started",
        },
    )

    successful = find_successful_patterns(objective_type=objective_type)
    similar = find_similar_patterns(objective=objective)
    historical_records = _merge_records(
        successful.get("records", []),
        similar.get("records", []),
    )
    hints = _adaptive_hints(
        objective_type=objective_type,
        historical_records=historical_records,
    )

    plan_result = await build_execution_plan(
        {
            "objective": objective,
            "path": path,
        }
    )

    if plan_result.get("status") != "success":
        event_bus.publish(
            "AdaptivePlanningFailed",
            "adaptive_planner",
            {
                "objective": objective,
                "objective_type": objective_type,
                "reason": plan_result.get("reason", "planning_error"),
                "result": "failed",
            },
        )
        return {
            "engine": "adaptive_planner",
            "status": plan_result.get("status", "failed"),
            "adaptive": True,
            "objective": objective,
            "objective_type": objective_type,
            "selected_plan": plan_result.get("selected_plan", ""),
            **hints,
            "plan": plan_result,
            "reason": plan_result.get("reason", "planning_error"),
            "message": plan_result.get("message", "Adaptive planning could not build a normal plan."),
        }

    selected_plan = plan_result.get("selected_plan", "")
    if not hints.get("preferred_plan"):
        hints["preferred_plan"] = selected_plan

    response = {
        "engine": "adaptive_planner",
        "status": "success",
        "adaptive": True,
        "objective": objective,
        "objective_type": objective_type,
        "selected_plan": selected_plan,
        **hints,
        "plan": plan_result,
    }

    event_bus.publish(
        "AdaptivePlanningCompleted",
        "adaptive_planner",
        {
            "objective": objective,
            "objective_type": objective_type,
            "historical_matches": response.get("historical_matches", 0),
            "historical_success_rate": response.get("historical_success_rate", 0.0),
            "selected_plan": selected_plan,
            "result": "success",
        },
    )
    return response


def adaptive_summary() -> Dict[str, Any]:
    records = execution_learning_engine.list_learning_records().get("records", [])
    objective_types = Counter(record.get("objective_type", "general_objective") for record in records)
    successful = [
        record
        for record in records
        if record.get("objective_satisfied") and record.get("completion_quality") in {"high", "medium"}
    ]
    plan_counts = Counter(record.get("selected_plan", "") for record in records if record.get("selected_plan"))
    success_rate = round((len(successful) / len(records)) if records else 0.0, 2)

    return {
        "engine": "adaptive_planner",
        "status": "success",
        "total_learning_records": len(records),
        "objective_types": dict(objective_types),
        "top_successful_patterns": successful[:5],
        "average_success_rate": success_rate,
        "most_used_plan": plan_counts.most_common(1)[0][0] if plan_counts else "",
    }


def objective_history(objective_type: str = "") -> Dict[str, Any]:
    clean_type = str(objective_type or "").strip()
    records = execution_learning_engine.list_learning_records().get("records", [])
    if clean_type:
        records = [
            record
            for record in records
            if record.get("objective_type") == clean_type
        ]

    return {
        "engine": "adaptive_planner",
        "status": "success",
        "objective_type": clean_type,
        "count": len(records),
        "records": records,
    }


def _adaptive_hints(
    objective_type: str,
    historical_records: List[Dict[str, Any]],
) -> Dict[str, Any]:
    historical_matches = len(historical_records)
    successful = [record for record in historical_records if record.get("objective_satisfied")]
    confidence_values = [
        _safe_int(record.get("confidence", 0))
        for record in historical_records
    ]
    plan_counts = Counter(record.get("selected_plan", "") for record in historical_records if record.get("selected_plan"))
    capability_counts = Counter()
    missing_counts = Counter()
    failed_counts = Counter()
    next_action_counts = Counter()

    for record in historical_records:
        capability_counts.update(record.get("capabilities_executed", []) or [])
        missing_counts.update(record.get("missing_information", []) or [])
        failed_counts.update(record.get("failed_capabilities", []) or [])
        action = str(record.get("recommended_next_action", "") or "").strip()
        if action:
            next_action_counts.update([action])

    planning_notes = []
    if not historical_records:
        planning_notes.append(f"No prior execution history found for {objective_type}.")
    else:
        planning_notes.append(f"Found {historical_matches} prior execution pattern(s) for adaptive planning.")

    return {
        "historical_matches": historical_matches,
        "historical_success_rate": round((len(successful) / historical_matches) if historical_matches else 0.0, 2),
        "average_confidence": round((sum(confidence_values) / len(confidence_values)) if confidence_values else 0),
        "preferred_plan": plan_counts.most_common(1)[0][0] if plan_counts else "",
        "preferred_capabilities": [item for item, _ in capability_counts.most_common(10)],
        "common_missing_information": [item for item, _ in missing_counts.most_common(10)],
        "common_failed_capabilities": [item for item, _ in failed_counts.most_common(10)],
        "common_next_actions": [item for item, _ in next_action_counts.most_common(5)],
        "planning_notes": planning_notes,
    }


def _merge_records(*record_groups: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    merged = []
    seen = set()
    for group in record_groups:
        for record in group or []:
            learning_id = record.get("learning_id")
            key = learning_id or record.get("fingerprint") or id(record)
            if key in seen:
                continue
            seen.add(key)
            merged.append(dict(record))
    return merged


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0
