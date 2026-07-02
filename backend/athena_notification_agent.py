from typing import Any, Dict, List


class AthenaNotificationAgent:
    """
    ATHENA Notification Agent

    Produces a structured communication plan. It does not send notifications.
    """

    DELIVERY_BY_PRIORITY = {
        "Critical": "Immediate",
        "High": "Today",
        "Medium": "Next Business Day",
        "Low": "Routine",
    }

    def generate(
        self,
        decision: Dict[str, Any],
        tasks: Dict[str, Any],
        engine_outputs: Dict[str, Any],
    ) -> Dict[str, Any]:
        candidates = []

        self._from_decision(decision, candidates)
        self._from_tasks(tasks, candidates)
        self._from_dashboard(engine_outputs.get("executive_dashboard", {}), candidates)
        self._from_risk_register(engine_outputs.get("risk_register", {}), candidates)
        self._from_commercial(engine_outputs.get("commercial_exposure", {}), candidates)
        self._from_report(engine_outputs.get("executive_report", {}), candidates)
        self._from_contract(engine_outputs.get("contract_intelligence", {}), candidates)

        items = self._dedupe(candidates)
        for index, item in enumerate(items, start=1):
            item["id"] = f"NOTIFY-{index:03d}"

        return {
            "generated": bool(items),
            "count": len(items),
            "items": items,
        }

    def _from_decision(self, decision: Dict[str, Any], candidates: List[Dict[str, Any]]) -> None:
        status = str(decision.get("status") or "").lower()
        if status in {"blocked", "conditional", "rejected"}:
            priority = "Critical" if status == "blocked" else "High"
            self._add(
                candidates,
                priority=priority,
                recipient_role="Management",
                notification_type="Executive Decision",
                title="Executive decision requires management attention.",
                message=decision.get("executive_instruction") or decision.get("decision_reason") or "Management decision requires review.",
                trigger=f"{status.title()} Decision",
            )

    def _from_tasks(self, tasks: Dict[str, Any], candidates: List[Dict[str, Any]]) -> None:
        for task in tasks.get("items", []) or []:
            priority = task.get("priority", "Low")
            if priority not in {"Critical", "High"}:
                continue

            role = self._role(task.get("owner"))
            self._add(
                candidates,
                priority=priority,
                recipient_role=role,
                notification_type=self._notification_type_for_role(role),
                title=f"{role} action required.",
                message=task.get("title") or "Executive task requires action.",
                trigger=f"{priority} Task",
            )

    def _from_dashboard(self, dashboard: Dict[str, Any], candidates: List[Dict[str, Any]]) -> None:
        kpis = dashboard.get("executive_kpis", {}) or {}
        risk_level = str(kpis.get("risk_level") or "").title()
        commercial_exposure = str(kpis.get("commercial_exposure") or "").title()

        if risk_level == "Critical":
            self._add(
                candidates,
                priority="Critical",
                recipient_role="Management",
                notification_type="Risk Alert",
                title="Critical risk requires executive review.",
                message="Critical risk remains unresolved before approval.",
                trigger="Critical Risk",
            )

        if commercial_exposure in {"Medium-High", "High", "Critical"}:
            self._add(
                candidates,
                priority="High",
                recipient_role="Commercial",
                notification_type="Commercial Alert",
                title="Commercial exposure requires review.",
                message="Commercial exposure requires assessment and mitigation actions.",
                trigger="Commercial Exposure",
            )

    def _from_risk_register(self, risk_register: Dict[str, Any], candidates: List[Dict[str, Any]]) -> None:
        if str(risk_register.get("overall_risk_level") or "").title() == "Critical":
            self._add(
                candidates,
                priority="Critical",
                recipient_role="Management",
                notification_type="Risk Alert",
                title="Critical risk register finding.",
                message="Risk Register identified Critical risk requiring management attention.",
                trigger="Critical Risk",
            )

        for risk in (risk_register.get("risks", []) or [])[:5]:
            if str(risk.get("severity") or "").title() != "Critical":
                continue
            role = self._role_for_text(f"{risk.get('category', '')} {risk.get('title', '')}")
            self._add(
                candidates,
                priority="Critical",
                recipient_role=role,
                notification_type=self._notification_type_for_role(role),
                title="Critical risk action required.",
                message=risk.get("title") or risk.get("description") or "Critical risk requires action.",
                trigger="Critical Risk",
            )

    def _from_commercial(self, commercial: Dict[str, Any], candidates: List[Dict[str, Any]]) -> None:
        if not commercial:
            return

        exposure = str(commercial.get("overall_commercial_risk") or "").title()
        if exposure in {"Medium-High", "High", "Critical"}:
            self._add(
                candidates,
                priority="High" if exposure != "Critical" else "Critical",
                recipient_role="Commercial",
                notification_type="Commercial Alert",
                title="Commercial exposure requires review.",
                message="Commercial exposure requires assessment before approval.",
                trigger="Commercial Exposure",
            )

        if commercial.get("contract_value") in ["", "Unknown", "Not stated", None]:
            self._add(
                candidates,
                priority="High",
                recipient_role="Commercial",
                notification_type="Commercial Alert",
                title="Commercial value information missing.",
                message="Contract value, pricing basis, or currency must be confirmed before approval.",
                trigger="Missing Commercial Information",
            )

    def _from_report(self, report: Dict[str, Any], candidates: List[Dict[str, Any]]) -> None:
        readiness = report.get("readiness_assessment", {}) or {}
        if str(readiness.get("readiness_level") or "").lower() in {"blocked", "poor"}:
            self._add(
                candidates,
                priority="High",
                recipient_role="Operations",
                notification_type="Operational Alert",
                title="Execution readiness requires action.",
                message="Execution readiness is not sufficient for approval.",
                trigger="Readiness Issue",
            )

        commercial = report.get("commercial_assessment", {}) or {}
        if str(commercial.get("exposure_level") or "").title() in {"Medium-High", "High", "Critical"}:
            self._add(
                candidates,
                priority="High",
                recipient_role="Commercial",
                notification_type="Commercial Alert",
                title="Commercial exposure requires review.",
                message="Executive report identified commercial exposure requiring action.",
                trigger="Commercial Exposure",
            )

    def _from_contract(self, contract: Dict[str, Any], candidates: List[Dict[str, Any]]) -> None:
        if str(contract.get("overall_contract_risk") or "").title() == "Critical":
            self._add(
                candidates,
                priority="Critical",
                recipient_role="Legal",
                notification_type="Legal Alert",
                title="Critical contract risk requires legal review.",
                message="Contract Intelligence identified Critical contractual risk.",
                trigger="Critical Contract Risk",
            )

    def _add(
        self,
        candidates: List[Dict[str, Any]],
        priority: str,
        recipient_role: str,
        notification_type: str,
        title: str,
        message: str,
        trigger: str,
    ) -> None:
        priority = priority if priority in self.DELIVERY_BY_PRIORITY else "Low"
        candidates.append(
            {
                "id": "",
                "priority": priority,
                "recipient_role": self._role(recipient_role),
                "notification_type": notification_type,
                "title": self._sentence(title),
                "message": self._sentence(message),
                "trigger": trigger,
                "recommended_delivery": self.DELIVERY_BY_PRIORITY[priority],
            }
        )

    def _dedupe(self, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        priority_rank = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
        by_key = {}

        for candidate in candidates:
            key = (
                candidate.get("recipient_role"),
                candidate.get("notification_type"),
                self._trigger_key(candidate.get("trigger", "")),
            )
            existing = by_key.get(key)
            if not existing or priority_rank[candidate["priority"]] < priority_rank[existing["priority"]]:
                by_key[key] = candidate

        return sorted(
            by_key.values(),
            key=lambda item: (
                priority_rank.get(item.get("priority"), 3),
                item.get("recipient_role", ""),
                item.get("title", ""),
            ),
        )[:12]

    def _role(self, role: Any) -> str:
        allowed = {
            "Management",
            "Commercial",
            "Legal",
            "Finance",
            "Compliance",
            "Operations",
            "Procurement",
            "Supply Chain",
            "Quality",
        }
        role_text = str(role or "").strip()
        return role_text if role_text in allowed else "Management"

    def _role_for_text(self, text: str) -> str:
        signal = text.lower()
        if any(term in signal for term in ["legal", "contract", "warranty", "penalty", "liability", "indemnity"]):
            return "Legal"
        if any(term in signal for term in ["commercial", "value", "price", "currency", "payment"]):
            return "Commercial"
        if any(term in signal for term in ["finance", "cash"]):
            return "Finance"
        if any(term in signal for term in ["compliance", "certificate", "license", "document"]):
            return "Compliance"
        if any(term in signal for term in ["supplier", "vendor"]):
            return "Procurement"
        if any(term in signal for term in ["quality", "inspection", "test"]):
            return "Quality"
        if any(term in signal for term in ["delivery", "operations", "execution"]):
            return "Operations"
        if any(term in signal for term in ["supply", "logistics"]):
            return "Supply Chain"
        return "Management"

    def _notification_type_for_role(self, role: str) -> str:
        if role == "Legal":
            return "Legal Alert"
        if role == "Commercial":
            return "Commercial Alert"
        if role == "Compliance":
            return "Compliance Alert"
        if role in {"Operations", "Supply Chain", "Quality", "Procurement"}:
            return "Operational Alert"
        return "Risk Alert"

    def _trigger_key(self, trigger: str) -> str:
        signal = str(trigger or "").lower()
        if "commercial" in signal:
            return "commercial"
        if "risk" in signal:
            return "risk"
        if "decision" in signal:
            return "decision"
        if "compliance" in signal:
            return "compliance"
        if "legal" in signal or "contract" in signal:
            return "legal"
        return signal

    def _sentence(self, value: Any) -> str:
        text = " ".join(str(value or "").split()).strip()
        if not text:
            return ""
        if text[-1] not in ".!?":
            text += "."
        return text
