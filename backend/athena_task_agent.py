import re
from typing import Any, Dict, List, Optional


class AthenaTaskAgent:
    """
    ATHENA Task Agent

    Converts intelligence outputs into structured executive tasks. It does not
    execute tasks or modify engine outputs.
    """

    DUE_BY_PRIORITY = {
        "Critical": "Immediate",
        "High": "3 Days",
        "Medium": "7 Days",
        "Low": "14 Days",
    }
    ACTION_VERBS = {
        "confirm",
        "review",
        "prepare",
        "assess",
        "validate",
        "obtain",
        "assign",
        "approve",
        "reject",
        "investigate",
        "close",
        "update",
        "verify",
        "conduct",
        "define",
    }

    def generate(self, engine_outputs: Dict[str, Any]) -> Dict[str, Any]:
        candidates = []

        self._from_dashboard(engine_outputs.get("executive_dashboard", {}), candidates)
        self._from_report(engine_outputs.get("executive_report", {}), candidates)
        self._from_risk_register(engine_outputs.get("risk_register", {}), candidates)
        self._from_commercial(engine_outputs.get("commercial_exposure", {}), candidates)
        self._from_action_plan(engine_outputs.get("executive_action_plan", {}), candidates)
        self._from_contract(engine_outputs.get("contract_intelligence", {}), candidates)
        self._from_opportunity(engine_outputs.get("opportunity_scoring", {}), candidates)

        items = self._dedupe(candidates)
        for index, item in enumerate(items, start=1):
            item["id"] = f"TASK-{index:03d}"

        counts = {
            "Critical": 0,
            "High": 0,
            "Medium": 0,
            "Low": 0,
        }
        for item in items:
            counts[item["priority"]] += 1

        return {
            "generated": bool(items),
            "critical": counts["Critical"],
            "high": counts["High"],
            "medium": counts["Medium"],
            "low": counts["Low"],
            "items": items,
        }

    def _from_dashboard(self, dashboard: Dict[str, Any], candidates: List[Dict[str, Any]]) -> None:
        for action in dashboard.get("priority_actions", []) or []:
            self._add_action_candidate(candidates, action, default_priority="High")

        next_step = dashboard.get("recommended_next_step")
        if next_step:
            self._add_text_candidate(candidates, next_step, default_priority="Medium")

    def _from_report(self, report: Dict[str, Any], candidates: List[Dict[str, Any]]) -> None:
        for action in report.get("priority_actions", []) or []:
            self._add_action_candidate(candidates, action, default_priority="High")

        for recommendation in report.get("executive_recommendations", []) or []:
            self._add_text_candidate(candidates, recommendation, default_priority="Medium")

        for risk in report.get("risk_assessment", {}).get("top_risks", []) or []:
            self._add_risk_candidate(candidates, risk)

        next_step = report.get("next_step")
        if next_step:
            self._add_text_candidate(candidates, next_step, default_priority="Medium")

    def _from_risk_register(self, risk_register: Dict[str, Any], candidates: List[Dict[str, Any]]) -> None:
        for risk in risk_register.get("risks", []) or []:
            self._add_risk_candidate(candidates, risk)

    def _from_commercial(self, commercial: Dict[str, Any], candidates: List[Dict[str, Any]]) -> None:
        if not commercial:
            return

        recommendation = commercial.get("executive_recommendation")
        if recommendation:
            self._add_text_candidate(candidates, recommendation, default_priority="High")

        if commercial.get("contract_value") in ["", "Unknown", "Not stated", None]:
            self._add_text_candidate(
                candidates,
                "Confirm contract value, pricing basis, and currency.",
                default_priority="High",
            )

    def _from_action_plan(self, action_plan: Dict[str, Any], candidates: List[Dict[str, Any]]) -> None:
        for action in action_plan.get("actions", []) or []:
            self._add_action_candidate(candidates, action, default_priority="Medium")

    def _from_contract(self, contract: Dict[str, Any], candidates: List[Dict[str, Any]]) -> None:
        for action in contract.get("recommended_actions", []) or []:
            self._add_text_candidate(candidates, action, default_priority=self._priority_from_risk(contract.get("overall_contract_risk")))

        for clause in contract.get("critical_clauses", []) or []:
            title = self._first_value(
                clause.get("title"),
                clause.get("clause"),
                clause.get("summary"),
                "Review critical contract clause.",
            )
            self._add_text_candidate(
                candidates,
                title,
                default_priority=self._priority_from_risk(clause.get("risk_level")),
                reason=clause.get("summary") or "Critical contract clause requires owner review.",
            )

        for missing in contract.get("missing_contract_information", []) or []:
            self._add_text_candidate(
                candidates,
                f"Close missing contract information: {missing}",
                default_priority="High",
            )

    def _from_opportunity(self, opportunity: Dict[str, Any], candidates: List[Dict[str, Any]]) -> None:
        for concern in opportunity.get("key_concerns", []) or []:
            self._add_text_candidate(candidates, concern, default_priority="Medium")

        next_action = opportunity.get("recommended_next_action")
        if next_action:
            self._add_text_candidate(candidates, next_action, default_priority="Medium")

    def _add_action_candidate(
        self,
        candidates: List[Dict[str, Any]],
        action: Any,
        default_priority: str,
    ) -> None:
        if isinstance(action, dict):
            title = self._first_value(
                action.get("title"),
                action.get("action"),
                action.get("description"),
                action.get("summary"),
            )
            reason = self._first_value(
                action.get("reason"),
                action.get("description"),
                action.get("summary"),
                "Recommended by ATHENA intelligence.",
            )
            priority = self._priority_from_risk(action.get("priority") or action.get("severity"), default_priority)
        else:
            title = str(action or "").strip()
            reason = "Recommended by ATHENA intelligence."
            priority = default_priority

        self._add_task(candidates, title=title, priority=priority, reason=reason)

    def _add_risk_candidate(self, candidates: List[Dict[str, Any]], risk: Any) -> None:
        if isinstance(risk, dict):
            title = self._first_value(risk.get("title"), risk.get("risk"), risk.get("description"))
            mitigation = self._first_value(risk.get("mitigation"), risk.get("recommended_action"))
            reason = self._first_value(mitigation, risk.get("description"), "Risk requires executive owner review.")
            priority = self._priority_from_risk(risk.get("severity") or risk.get("risk_level"))
        else:
            title = str(risk or "").strip()
            reason = "Risk requires executive owner review."
            priority = "Medium"

        self._add_task(candidates, title=title, priority=priority, reason=reason)

    def _add_text_candidate(
        self,
        candidates: List[Dict[str, Any]],
        text: Any,
        default_priority: str,
        reason: Optional[str] = None,
    ) -> None:
        title = str(text or "").strip()
        self._add_task(
            candidates,
            title=title,
            priority=self._priority_from_text(title, default_priority),
            reason=reason or "Recommended by ATHENA intelligence.",
        )

    def _add_task(
        self,
        candidates: List[Dict[str, Any]],
        title: str,
        priority: str,
        reason: str,
    ) -> None:
        title = self._clean_title(title)
        if not title:
            return

        candidates.append(
            {
                "id": "",
                "priority": priority if priority in self.DUE_BY_PRIORITY else "Low",
                "title": title,
                "owner": self._owner_for(title),
                "reason": self._clean_sentence(reason),
                "recommended_due": self.DUE_BY_PRIORITY.get(priority, "14 Days"),
                "status": "Pending",
            }
        )

    def _dedupe(self, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        by_key = {}
        priority_rank = {
            "Critical": 0,
            "High": 1,
            "Medium": 2,
            "Low": 3,
        }

        for candidate in candidates:
            key = self._dedupe_key(candidate.get("title", ""))
            if not key:
                continue

            existing = by_key.get(key)
            if not existing or priority_rank[candidate["priority"]] < priority_rank[existing["priority"]]:
                by_key[key] = candidate

        return sorted(
            by_key.values(),
            key=lambda item: (
                priority_rank.get(item.get("priority"), 3),
                item.get("title", ""),
            ),
        )[:12]

    def _owner_for(self, text: str) -> str:
        signal = text.lower()
        if any(word in signal for word in ["contract value", "value", "price", "pricing", "commercial", "margin", "cost"]):
            return "Commercial"
        if any(word in signal for word in ["payment", "currency", "finance", "cash flow"]):
            return "Finance"
        if any(word in signal for word in ["penalty", "warranty", "termination", "liability", "indemnity", "legal", "clause", "contract"]):
            return "Legal"
        if any(word in signal for word in ["certificate", "compliance", "license", "vat", "mandatory document", "document"]):
            return "Compliance"
        if any(word in signal for word in ["supplier", "vendor"]):
            return "Procurement"
        if any(word in signal for word in ["delivery", "readiness", "execution", "operational"]):
            return "Operations"
        if any(word in signal for word in ["quality", "iso", "test report", "inspection"]):
            return "Quality"
        if any(word in signal for word in ["supply", "logistics", "inventory"]):
            return "Supply Chain"
        if any(word in signal for word in ["approval", "management", "decision"]):
            return "Management"
        return "Management"

    def _priority_from_risk(self, value: Any, default: str = "Low") -> str:
        text = str(value or "").strip().title()
        if text == "Critical":
            return "Critical"
        if text == "High":
            return "High"
        if text == "Medium":
            return "Medium"
        if text in self.DUE_BY_PRIORITY:
            return text
        return default

    def _priority_from_text(self, text: str, default: str) -> str:
        signal = text.lower()
        if any(word in signal for word in ["critical", "blocker", "hold approval", "do not approve"]):
            return "Critical"
        if any(word in signal for word in ["high", "penalty", "missing", "deadline", "approval"]):
            return "High"
        return default if default in self.DUE_BY_PRIORITY else "Low"

    def _clean_title(self, text: str) -> str:
        text = self._clean_sentence(text)
        text = self._observation_to_action(text)
        replacements = {
            "confirm contract value": "Confirm contract value, pricing basis, and currency.",
            "confirm contract value, pricing basis, and currency": "Confirm contract value, pricing basis, and currency.",
        }
        text = replacements.get(text.lower().rstrip("."), text)
        return self._ensure_action_title(text)

    def _clean_sentence(self, text: Any) -> str:
        value = re.sub(r"\s+", " ", str(text or "")).strip(" ;")
        if not value:
            return ""
        if value[-1] not in ".!?":
            value += "."
        return value

    def _dedupe_key(self, title: str) -> str:
        signal = title.lower()
        if "critical risk" in signal or "overall risk" in signal:
            return "conduct_executive_review_critical_risks"
        if "commercial exposure" in signal:
            return "assess_commercial_exposure"
        if "commercial" in signal and "compliance" in signal and "risk" in signal and "gap" in signal:
            return "close_commercial_compliance_risk_gaps"
        if "contract value" in signal or "currency" in signal or "pricing basis" in signal:
            return "confirm_contract_value_currency"
        if "penalty" in signal:
            return "review_penalty_clause"
        if "warranty" in signal:
            return "review_warranty_obligation"
        if "supplier" in signal:
            return "confirm_supplier_identity"
        if "compliance" in signal or "certificate" in signal or "mandatory document" in signal:
            return "prepare_compliance_documents"
        return re.sub(r"[^a-z0-9]+", "_", signal).strip("_")

    def _observation_to_action(self, text: str) -> str:
        signal = text.lower().strip()

        if "overall risk" in signal and "critical" in signal:
            return "Conduct executive review of critical risks."
        if "risk is critical" in signal or signal == "critical risk.":
            return "Conduct executive review of critical risks."
        if "commercial exposure" in signal and any(level in signal for level in ["medium-high", "high", "critical"]):
            return "Assess commercial exposure and define mitigation actions."
        if signal.startswith("proceed only after") or "proceed only after" in signal:
            return "Close commercial, compliance, and risk gaps."
        if signal.startswith("do not approve") or signal.startswith("hold approval"):
            return "Close approval blockers before management decision."
        if signal.startswith("no-bid") or signal.startswith("no bid"):
            return "Review no-bid rationale before final management decision."
        if signal.startswith("conditional bid"):
            return "Close conditions required for bid approval."

        return text

    def _ensure_action_title(self, text: str) -> str:
        words = re.findall(r"[A-Za-z]+", text)
        if not words:
            return ""

        first = words[0].lower()
        if first in self.ACTION_VERBS:
            return text[0].upper() + text[1:]

        signal = text.lower()
        if "contract value" in signal or "currency" in signal or "pricing basis" in signal:
            return "Confirm contract value, pricing basis, and currency."
        if "penalty" in signal:
            return "Review penalty clause."
        if "warranty" in signal:
            return "Review warranty obligation."
        if "supplier" in signal:
            return "Confirm supplier identity."
        if "compliance" in signal or "certificate" in signal or "mandatory document" in signal:
            return "Prepare compliance documents."
        if "commercial exposure" in signal:
            return "Assess commercial exposure and define mitigation actions."
        if "risk" in signal:
            return "Review risk item and define mitigation actions."
        if "approval" in signal or "decision" in signal:
            return "Assign management owner for approval decision."
        if "missing" in signal or "gap" in signal:
            return "Close missing information gaps."

        return f"Review {text[0].lower() + text[1:]}"

    def _first_value(self, *values: Any) -> str:
        for value in values:
            if value is None:
                continue
            text = str(value).strip()
            if text:
                return text
        return ""
