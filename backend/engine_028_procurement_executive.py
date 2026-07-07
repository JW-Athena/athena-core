from typing import Any, Dict, List

from engine_020_organization_model import organization_model
from engine_021_organization_impact import organization_impact_analysis
from engine_022_knowledge_graph import executive_knowledge_graph
from engine_023_reasoning_graph import executive_reasoning_graph
from engine_024_executive_reasoning_engine import executive_reasoning_engine
from engine_026_supplier_executive import evaluate_supplier
from event_bus import event_bus


class ProcurementExecutive:
    def evaluate_procurement(self, question: str, item: str = "", supplier: str = "") -> Dict[str, Any]:
        clean_question = str(question or "").strip()
        clean_item = str(item or "").strip()
        clean_supplier = str(supplier or "").strip()
        if not clean_question:
            return self._failure("question_required", "Procurement executive question is required.")

        event_bus.publish(
            "ProcurementExecutiveStarted",
            "procurement_executive",
            {"question": clean_question, "item": clean_item, "supplier": clean_supplier, "result": "started"},
        )

        try:
            organization = organization_model.organization_summary()
            organization_impact = organization_impact_analysis.analyze(
                mission=clean_question,
                context={"item": clean_item, "supplier": clean_supplier},
            )
            supplier_result = evaluate_supplier(clean_question, clean_supplier) if clean_supplier else {}
            knowledge = executive_knowledge_graph.get_related_entities(clean_supplier or clean_item) if (clean_supplier or clean_item) else {}
            reasoning_graph = executive_reasoning_graph.find_business_impact(clean_supplier or clean_item) if (clean_supplier or clean_item) else {}
            executive_reasoning = executive_reasoning_engine.reason(
                clean_question,
                context={"item": clean_item, "supplier": clean_supplier},
            )

            result = self._assemble_response(
                question=clean_question,
                item=clean_item,
                supplier=clean_supplier,
                organization=organization,
                organization_impact=organization_impact,
                supplier_result=supplier_result,
                knowledge=knowledge,
                reasoning_graph=reasoning_graph,
                executive_reasoning=executive_reasoning,
            )
            event_bus.publish(
                "ProcurementExecutiveCompleted",
                "procurement_executive",
                {
                    "question": clean_question,
                    "procurement_decision": result.get("procurement_decision", ""),
                    "confidence": result.get("confidence", 0),
                    "result": "success",
                },
            )
            return result
        except Exception as exc:
            event_bus.publish(
                "ProcurementExecutiveCompleted",
                "procurement_executive",
                {"question": clean_question, "reason": "procurement_executive_error", "result": "failed"},
            )
            return self._failure("procurement_executive_error", f"Procurement executive assessment failed: {exc}")

    def _assemble_response(
        self,
        question: str,
        item: str,
        supplier: str,
        organization: Dict[str, Any],
        organization_impact: Dict[str, Any],
        supplier_result: Dict[str, Any],
        knowledge: Dict[str, Any],
        reasoning_graph: Dict[str, Any],
        executive_reasoning: Dict[str, Any],
    ) -> Dict[str, Any]:
        supplier_risk = supplier_result.get("risk_level") or self._organization_supplier_risk(supplier, organization)
        commercial_risk = self._commercial_risk(question, item, organization_impact, supplier_result)
        concerns = self._unique_text(
            supplier_result.get("key_concerns", []),
            [organization_impact.get("impact_summary", "")] if organization_impact.get("requires_management_attention") else [],
        )
        decision = self._decision(supplier_risk, commercial_risk, concerns, supplier)
        actions = self._recommended_actions(decision, item, supplier, concerns, supplier_result)

        return {
            "engine": "procurement_executive",
            "status": "success",
            "executive_summary": self._executive_summary(decision, item, supplier, supplier_risk, commercial_risk, concerns),
            "procurement_decision": decision,
            "confidence": self._confidence(executive_reasoning, supplier_result, knowledge, reasoning_graph, organization_impact),
            "supplier_risk": supplier_risk or "Unknown",
            "commercial_risk": commercial_risk,
            "required_departments": self._required_departments(organization_impact),
            "recommended_actions": actions,
            "executive_reasoning": self._executive_reasoning(decision, concerns, executive_reasoning, reasoning_graph),
        }

    def _decision(self, supplier_risk: str, commercial_risk: str, concerns: List[str], supplier: str) -> str:
        risk_text = f"{supplier_risk} {commercial_risk}".lower()
        if "critical" in risk_text:
            return "Reject"
        if "high" in risk_text:
            return "Hold"
        if concerns or not supplier:
            return "Review"
        return "Proceed"

    def _commercial_risk(self, question: str, item: str, organization_impact: Dict[str, Any], supplier_result: Dict[str, Any]) -> str:
        combined = f"{question} {item}".lower()
        if any(term in combined for term in ["urgent", "sole source", "advance payment", "penalty", "unbudgeted"]):
            return "High"
        if organization_impact.get("requires_management_attention"):
            return "Medium"
        if supplier_result.get("supplier_decision") in {"Replace", "Monitor"}:
            return "Medium"
        return "Low"

    def _organization_supplier_risk(self, supplier: str, organization: Dict[str, Any]) -> str:
        clean_supplier = supplier.lower()
        for record in organization.get("suppliers", []):
            if str(record.get("name", "")).lower() == clean_supplier:
                return str(record.get("risk_level") or "Unknown").title()
        return "Unknown" if supplier else "Not provided"

    def _required_departments(self, organization_impact: Dict[str, Any]) -> List[str]:
        departments = organization_impact.get("impacted_departments", []) or []
        return self._unique_text(departments, ["Procurement", "Finance", "Operations"])[:6]

    def _recommended_actions(
        self,
        decision: str,
        item: str,
        supplier: str,
        concerns: List[str],
        supplier_result: Dict[str, Any],
    ) -> List[str]:
        actions = self._unique_text(supplier_result.get("recommended_actions", []))
        subject = item or supplier or "the procurement request"
        if decision in {"Hold", "Reject"}:
            actions.append(f"Hold commitment for {subject} until supplier and commercial risks are resolved.")
        elif decision == "Review":
            actions.append(f"Complete procurement evidence review for {subject}.")
        else:
            actions.append(f"Proceed with procurement for {subject} under normal approval controls.")
        if concerns:
            actions.append(f"Resolve concern: {concerns[0]}")
        return self._unique_text(actions)[:6]

    def _executive_summary(self, decision: str, item: str, supplier: str, supplier_risk: str, commercial_risk: str, concerns: List[str]) -> str:
        subject = item or supplier or "this procurement"
        reason = concerns[0] if concerns else f"supplier risk is {supplier_risk} and commercial risk is {commercial_risk}"
        return f"ATHENA completed the procurement executive review for {subject}. Recommendation is {decision}. Primary reason: {reason}"

    def _executive_reasoning(self, decision: str, concerns: List[str], executive_reasoning: Dict[str, Any], reasoning_graph: Dict[str, Any]) -> str:
        reason = concerns[0] if concerns else executive_reasoning.get("executive_explanation") or reasoning_graph.get("executive_explanation") or "available procurement evidence supports this position"
        return f"ATHENA recommends {decision} because {str(reason).rstrip('.')}."

    def _confidence(
        self,
        executive_reasoning: Dict[str, Any],
        supplier_result: Dict[str, Any],
        knowledge: Dict[str, Any],
        reasoning_graph: Dict[str, Any],
        organization_impact: Dict[str, Any],
    ) -> int:
        values = [self._safe_int(executive_reasoning.get("confidence")), self._safe_int(supplier_result.get("confidence"))]
        if knowledge.get("count", 0) > 0:
            values.append(70)
        if reasoning_graph.get("status") == "success":
            values.append(68)
        if organization_impact.get("impact_level"):
            values.append(65)
        values = [value for value in values if value > 0]
        return round(sum(values) / len(values)) if values else 55

    def _safe_int(self, value: Any) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    def _unique_text(self, *groups: Any) -> List[str]:
        values = []
        seen = set()
        for group in groups:
            items = group if isinstance(group, list) else [group]
            for item in items:
                text = str(item or "").strip()
                key = text.lower()
                if text and key not in seen:
                    values.append(text)
                    seen.add(key)
        return values

    def _failure(self, reason: str, message: str) -> Dict[str, Any]:
        return {"engine": "procurement_executive", "status": "failed", "reason": reason, "message": message}


procurement_executive = ProcurementExecutive()


def evaluate_procurement(question: str, item: str = "", supplier: str = "") -> Dict[str, Any]:
    return procurement_executive.evaluate_procurement(question=question, item=item, supplier=supplier)
