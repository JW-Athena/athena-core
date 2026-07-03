from datetime import datetime
from hashlib import sha256
from typing import Any, Dict, List, Optional
from uuid import uuid4
import builtins
import re

from event_bus import event_bus


class ExecutionLearningEngine:
    def __init__(self):
        if not hasattr(builtins, "_ATHENA_EXECUTION_LEARNING_RECORDS"):
            builtins._ATHENA_EXECUTION_LEARNING_RECORDS = []
        self._records: List[Dict[str, Any]] = builtins._ATHENA_EXECUTION_LEARNING_RECORDS

    def learn_from_execution(self, response: Dict[str, Any]) -> Dict[str, Any]:
        try:
            objective = str(response.get("objective", "") or "").strip()
            selected_plan = str(response.get("selected_plan", "") or "").strip()
            evaluation = response.get("execution_evaluation", {}) or {}
            capabilities_executed = list(response.get("capabilities_executed", []) or [])

            fingerprint = self._fingerprint(
                objective=objective,
                selected_plan=selected_plan,
                capabilities_executed=capabilities_executed,
            )
            learning_id = str(uuid4())
            objective_type = self._objective_type(objective)

            record = {
                "learning_id": learning_id,
                "fingerprint": fingerprint,
                "objective": objective,
                "objective_type": objective_type,
                "selected_plan": selected_plan,
                "execution_status": str(response.get("execution_status", "") or ""),
                "decision_ready": bool(evaluation.get("decision_ready", False)),
                "objective_satisfied": bool(evaluation.get("objective_satisfied", False)),
                "approval_required": bool(evaluation.get("approval_required", False)),
                "confidence": self._safe_int(evaluation.get("confidence", 0)),
                "completion_quality": str(evaluation.get("completion_quality", "") or ""),
                "capabilities_executed": capabilities_executed,
                "failed_capabilities": list(evaluation.get("failed_capabilities", []) or []),
                "skipped_capabilities": list(evaluation.get("skipped_capabilities", []) or []),
                "unsupported_capabilities": list(evaluation.get("unsupported_capabilities", []) or []),
                "missing_information": list(evaluation.get("missing_information", []) or []),
                "recommended_next_action": str(evaluation.get("recommended_next_action", "") or ""),
                "execution_duration_ms": response.get("execution_duration_ms"),
                "created_at": datetime.utcnow().isoformat(),
            }
            self._records.append(record)

            event_bus.publish(
                "ExecutionLearned",
                "execution_learning_engine",
                {
                    "learning_id": learning_id,
                    "fingerprint": fingerprint,
                    "objective": objective,
                    "selected_plan": selected_plan,
                    "objective_type": objective_type,
                    "confidence": record["confidence"],
                    "decision_ready": record["decision_ready"],
                    "objective_satisfied": record["objective_satisfied"],
                    "result": "success",
                },
            )

            return {
                "engine": "execution_learning_engine",
                "status": "success",
                "learning_id": learning_id,
                "fingerprint": fingerprint,
                "objective_type": objective_type,
                "stored": True,
                "message": "Execution learning record stored.",
            }
        except Exception as exc:
            objective = str(response.get("objective", "") or "") if isinstance(response, dict) else ""
            selected_plan = str(response.get("selected_plan", "") or "") if isinstance(response, dict) else ""
            event_bus.publish(
                "ExecutionLearningFailed",
                "execution_learning_engine",
                {
                    "objective": objective,
                    "selected_plan": selected_plan,
                    "reason": "execution_learning_error",
                    "result": "failed",
                },
            )
            return {
                "engine": "execution_learning_engine",
                "status": "failed",
                "stored": False,
                "reason": "execution_learning_error",
                "message": f"Execution learning failed: {exc}",
            }

    def list_learning_records(self) -> Dict[str, Any]:
        records = [dict(record) for record in self._records]
        return {
            "engine": "execution_learning_engine",
            "status": "success",
            "count": len(records),
            "records": records,
        }

    def find_successful_patterns(self, objective_type: Optional[str] = None) -> Dict[str, Any]:
        clean_type = str(objective_type or "").strip()
        records = []
        for record in self._records:
            if clean_type and record.get("objective_type") != clean_type:
                continue
            if record.get("objective_satisfied") and record.get("completion_quality") in {"high", "medium"}:
                records.append(dict(record))

        return {
            "engine": "execution_learning_engine",
            "status": "success",
            "objective_type": clean_type,
            "count": len(records),
            "records": records,
        }

    def find_similar_patterns(self, objective: str) -> Dict[str, Any]:
        clean_objective = self._normalize_objective(objective)
        query_terms = set(clean_objective.split())
        records = []

        for record in self._records:
            record_terms = set(self._normalize_objective(record.get("objective", "")).split())
            if not query_terms or not record_terms:
                continue
            overlap = len(query_terms.intersection(record_terms))
            if overlap <= 0:
                continue
            score = round(overlap / max(len(query_terms), 1), 2)
            enriched = dict(record)
            enriched["similarity_score"] = score
            records.append(enriched)

        records.sort(key=lambda item: item.get("similarity_score", 0), reverse=True)
        return {
            "engine": "execution_learning_engine",
            "status": "success",
            "objective": str(objective or "").strip(),
            "count": len(records),
            "records": records,
        }

    def _fingerprint(
        self,
        objective: str,
        selected_plan: str,
        capabilities_executed: List[str],
    ) -> str:
        normalized = self._normalize_objective(objective)
        capabilities = "|".join(sorted(str(item) for item in capabilities_executed))
        source = f"{normalized}|{selected_plan}|{capabilities}"
        return sha256(source.encode("utf-8")).hexdigest()

    def _normalize_objective(self, objective: Any) -> str:
        return re.sub(r"\s+", " ", str(objective or "").strip().lower())

    def _objective_type(self, objective: str) -> str:
        signal = self._normalize_objective(objective)
        if "tender" in signal:
            return "tender_analysis"
        if "contract" in signal:
            return "contract_analysis"
        if "supplier" in signal:
            return "supplier_review"
        if "product" in signal:
            return "product_analysis"
        if "portfolio" in signal:
            return "portfolio_review"
        return "general_objective"

    def _safe_int(self, value: Any) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0


execution_learning_engine = ExecutionLearningEngine()


def learn_from_execution(response: Dict[str, Any]) -> Dict[str, Any]:
    return execution_learning_engine.learn_from_execution(response)


def list_learning_records() -> Dict[str, Any]:
    return execution_learning_engine.list_learning_records()


def find_successful_patterns(objective_type: Optional[str] = None) -> Dict[str, Any]:
    return execution_learning_engine.find_successful_patterns(objective_type=objective_type)


def find_similar_patterns(objective: str) -> Dict[str, Any]:
    return execution_learning_engine.find_similar_patterns(objective=objective)
