import json
import os
from datetime import datetime
from typing import Any, Dict, Optional


class OrganizationAwareness:
    """
    ATHENA Organizational Awareness

    Maintains a lightweight generic organization state for ATHENA analysis.
    """

    def __init__(self, state_path: str = "database/organization_state.json"):
        self.state_path = state_path
        self._ensure_storage()

    def get_state(self) -> Dict[str, Any]:
        return self._load_state()

    def update_from_input(self, payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        state = self._load_state()
        if payload:
            organization_payload = payload.get("organization", payload)
            for key, value in organization_payload.items():
                if key in state["organization"]:
                    state["organization"][key] = value

            state["organization"]["overall_health"] = self._overall_health(state["organization"])
            self._save_state(state)

        return state

    def update_from_analysis(
        self,
        decision: Dict[str, Any],
        tasks: Dict[str, Any],
        notifications: Dict[str, Any],
        execution: Dict[str, Any],
        engine_outputs: Dict[str, Any],
    ) -> Dict[str, Any]:
        state = self._load_state()
        organization = state["organization"]

        organization["active_opportunities"] += self._active_opportunity_increment(engine_outputs)
        organization["critical_risks"] += self._critical_risk_count(engine_outputs, tasks)
        organization["pending_decisions"] += 1 if decision.get("status") in {"conditional", "blocked"} else 0
        organization["pending_tasks"] += len(tasks.get("items", []) or [])
        organization["pending_notifications"] += notifications.get("count", 0) or 0
        organization["execution_queue"] += len(execution.get("allowed_actions", []) or [])
        organization["last_analysis_time"] = datetime.utcnow().isoformat()
        organization["current_mode"] = self._current_mode(organization)
        organization["overall_health"] = self._overall_health(organization)

        self._save_state(state)
        return state

    def _ensure_storage(self) -> None:
        folder = os.path.dirname(self.state_path)
        if folder and not os.path.exists(folder):
            os.makedirs(folder)
        if not os.path.exists(self.state_path):
            self._save_state(self._default_state())

    def _load_state(self) -> Dict[str, Any]:
        self._ensure_storage()
        try:
            with open(self.state_path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            if "organization" in data:
                return self._with_defaults(data)
        except Exception:
            pass

        state = self._default_state()
        self._save_state(state)
        return state

    def _save_state(self, state: Dict[str, Any]) -> None:
        with open(self.state_path, "w", encoding="utf-8") as handle:
            json.dump(state, handle, indent=2)

    def _default_state(self) -> Dict[str, Any]:
        return {
            "organization": {
                "current_mode": "Normal",
                "active_opportunities": 0,
                "critical_risks": 0,
                "pending_decisions": 0,
                "pending_tasks": 0,
                "pending_notifications": 0,
                "execution_queue": 0,
                "last_analysis_time": "",
                "overall_health": "Stable",
            }
        }

    def _with_defaults(self, state: Dict[str, Any]) -> Dict[str, Any]:
        default = self._default_state()
        organization = state.setdefault("organization", {})
        for key, value in default["organization"].items():
            organization.setdefault(key, value)
        return state

    def _active_opportunity_increment(self, engine_outputs: Dict[str, Any]) -> int:
        if engine_outputs.get("opportunity_scoring"):
            return 1

        dashboard = engine_outputs.get("executive_dashboard", {})
        if dashboard.get("opportunity_score"):
            return 1

        return 0

    def _critical_risk_count(self, engine_outputs: Dict[str, Any], tasks: Dict[str, Any]) -> int:
        count = int(tasks.get("critical", 0) or 0)
        risk_register = engine_outputs.get("risk_register", {})
        contract = engine_outputs.get("contract_intelligence", {})
        dashboard = engine_outputs.get("executive_dashboard", {})

        if str(risk_register.get("overall_risk_level", "")).lower() == "critical":
            count += 1
        if str(contract.get("overall_contract_risk", "")).lower() == "critical":
            count += 1
        if str(dashboard.get("executive_kpis", {}).get("risk_level", "")).lower() == "critical":
            count += 1

        return count

    def _current_mode(self, organization: Dict[str, Any]) -> str:
        if organization.get("critical_risks", 0) > 0 or organization.get("pending_decisions", 0) > 0:
            return "Watch"
        return "Normal"

    def _overall_health(self, organization: Dict[str, Any]) -> str:
        if organization.get("critical_risks", 0) >= 3:
            return "Poor"
        if organization.get("critical_risks", 0) > 0 or organization.get("pending_decisions", 0) > 0:
            return "Watch"
        if organization.get("pending_tasks", 0) > 0 or organization.get("pending_notifications", 0) > 0:
            return "Stable"
        return "Strong"


organization_awareness = OrganizationAwareness()
