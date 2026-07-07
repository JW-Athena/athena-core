from typing import Any, Dict, List

from engine_013_learning_engine import execution_learning_engine
from engine_020_organization_model import organization_model
from engine_021_organization_impact import organization_impact_analysis
from engine_022_knowledge_graph import executive_knowledge_graph
from engine_023_reasoning_graph import executive_reasoning_graph
from engine_024_executive_reasoning_engine import executive_reasoning_engine
from event_bus import event_bus
from supplier_profile_engine import SupplierProfileEngine


class SupplierExecutive:
    def __init__(self):
        self.supplier_profile_engine = SupplierProfileEngine()

    def evaluate_supplier(self, question: str, supplier: str = "") -> Dict[str, Any]:
        clean_question = str(question or "").strip()
        clean_supplier = str(supplier or "").strip() or self._supplier_from_question(clean_question)
        if not clean_question:
            return self._failure("question_required", "Supplier executive question is required.")
        if not clean_supplier:
            return self._failure("supplier_required", "Supplier name is required.")

        event_bus.publish(
            "SupplierExecutiveStarted",
            "supplier_executive",
            {
                "question": clean_question,
                "supplier": clean_supplier,
                "result": "started",
            },
        )

        try:
            profile = self.supplier_profile_engine.get_profile(clean_supplier)
            organization = organization_model.organization_summary()
            organization_supplier = self._organization_supplier(clean_supplier, organization.get("suppliers", []))
            organization_impact = organization_impact_analysis.analyze(
                mission=clean_question,
                context={"supplier": clean_supplier},
            )
            knowledge = executive_knowledge_graph.get_related_entities(clean_supplier)
            reasoning = executive_reasoning_graph.find_business_impact(clean_supplier)
            executive_reasoning = executive_reasoning_engine.reason(
                clean_question,
                context={"entity": clean_supplier, "supplier": clean_supplier},
            )
            learning = execution_learning_engine.find_similar_patterns(clean_question)

            result = self._assemble_response(
                question=clean_question,
                supplier=clean_supplier,
                profile=profile,
                organization_supplier=organization_supplier,
                organization_impact=organization_impact,
                knowledge=knowledge,
                reasoning=reasoning,
                executive_reasoning=executive_reasoning,
                learning=learning,
            )
            event_bus.publish(
                "SupplierExecutiveCompleted",
                "supplier_executive",
                {
                    "question": clean_question,
                    "supplier": clean_supplier,
                    "supplier_decision": result.get("supplier_decision", ""),
                    "confidence": result.get("confidence", 0),
                    "result": "success",
                },
            )
            return result
        except Exception as exc:
            event_bus.publish(
                "SupplierExecutiveCompleted",
                "supplier_executive",
                {
                    "question": clean_question,
                    "supplier": clean_supplier,
                    "reason": "supplier_executive_error",
                    "result": "failed",
                },
            )
            return self._failure("supplier_executive_error", f"Supplier executive assessment failed: {exc}")

    def _assemble_response(
        self,
        question: str,
        supplier: str,
        profile: Dict[str, Any],
        organization_supplier: Dict[str, Any],
        organization_impact: Dict[str, Any],
        knowledge: Dict[str, Any],
        reasoning: Dict[str, Any],
        executive_reasoning: Dict[str, Any],
        learning: Dict[str, Any],
    ) -> Dict[str, Any]:
        supplier_profile = profile.get("profile", {})
        risk_level = str(organization_supplier.get("risk_level") or "unknown").lower()
        status = str(organization_supplier.get("status") or "").lower()
        key_strengths = self._key_strengths(supplier_profile, organization_supplier, knowledge)
        key_concerns = self._key_concerns(
            supplier=supplier,
            risk_level=risk_level,
            status=status,
            supplier_profile=supplier_profile,
            organization_supplier=organization_supplier,
            organization_impact=organization_impact,
            knowledge=knowledge,
        )
        supplier_decision = self._supplier_decision(risk_level, status, key_strengths, key_concerns)
        recommended_actions = self._recommended_actions(supplier_decision, supplier, key_concerns)
        executive_summary = self._executive_summary(
            supplier=supplier,
            supplier_decision=supplier_decision,
            risk_level=risk_level,
            key_concerns=key_concerns,
            key_strengths=key_strengths,
        )
        executive_reasoning_text = self._executive_reasoning(
            supplier=supplier,
            supplier_decision=supplier_decision,
            key_concerns=key_concerns,
            key_strengths=key_strengths,
            reasoning=reasoning,
            executive_reasoning=executive_reasoning,
        )

        return {
            "engine": "supplier_executive",
            "status": "success",
            "question": question,
            "supplier": supplier,
            "executive_summary": executive_summary,
            "supplier_decision": supplier_decision,
            "confidence": self._confidence(
                executive_reasoning=executive_reasoning,
                organization_supplier=organization_supplier,
                supplier_profile=supplier_profile,
                knowledge=knowledge,
                learning=learning,
            ),
            "risk_level": self._risk_label(risk_level),
            "key_strengths": key_strengths,
            "key_concerns": key_concerns,
            "recommended_actions": recommended_actions,
            "executive_reasoning": executive_reasoning_text,
            "executive_brief": {
                "supplier_profile": profile,
                "organization_supplier": organization_supplier,
                "organization_impact": organization_impact,
                "knowledge_graph": knowledge,
                "reasoning_graph": reasoning,
                "executive_reasoning": executive_reasoning,
                "learning": learning,
            },
        }

    def _supplier_from_question(self, question: str) -> str:
        words = [
            word.strip(".,:;!?()[]{}")
            for word in str(question or "").split()
            if word.strip(".,:;!?()[]{}")
        ]
        ignored = {"Should", "Can", "Could", "Would", "We", "ICC", "Continue", "Working", "With", "Supplier"}
        for word in reversed(words):
            if word[:1].isupper() and word not in ignored:
                return word
        if words:
            return words[-1]
        return ""

    def _organization_supplier(self, supplier: str, suppliers: List[Dict[str, Any]]) -> Dict[str, Any]:
        clean_supplier = supplier.lower()
        for item in suppliers:
            if str(item.get("name", "")).lower() == clean_supplier:
                return dict(item)
        return {}

    def _key_strengths(
        self,
        supplier_profile: Dict[str, Any],
        organization_supplier: Dict[str, Any],
        knowledge: Dict[str, Any],
    ) -> List[str]:
        strengths = []
        products = self._unique_text(supplier_profile.get("products", []), organization_supplier.get("products", []))
        if products:
            strengths.append(f"Supplies {self._human_join(products[:4])}.")
        if supplier_profile.get("certificates"):
            strengths.append("Supplier has certificate or required-document references in ATHENA records.")
        if knowledge.get("count", 0) > 0:
            strengths.append("Supplier has mapped relationships in the executive knowledge graph.")
        if str(organization_supplier.get("status", "")).lower() == "active":
            strengths.append("Supplier is currently active in the organization model.")
        return strengths[:5]

    def _key_concerns(
        self,
        supplier: str,
        risk_level: str,
        status: str,
        supplier_profile: Dict[str, Any],
        organization_supplier: Dict[str, Any],
        organization_impact: Dict[str, Any],
        knowledge: Dict[str, Any],
    ) -> List[str]:
        concerns = []
        if not organization_supplier:
            concerns.append(f"{supplier} is not registered in the organization supplier model.")
        if risk_level in {"critical", "high"}:
            concerns.append(f"Supplier risk level is {self._risk_label(risk_level)}.")
        if status and status not in {"active", "approved"}:
            concerns.append(f"Supplier status is {status}.")
        if not supplier_profile.get("products") and not organization_supplier.get("products"):
            concerns.append("No supplier product dependency is recorded.")
        if organization_impact.get("requires_management_attention"):
            concerns.append("Supplier decision requires management attention.")
        if knowledge.get("count", 0) == 0:
            concerns.append("Supplier relationships are not yet mapped in the knowledge graph.")
        return self._unique_text(concerns)[:6]

    def _supplier_decision(
        self,
        risk_level: str,
        status: str,
        key_strengths: List[str],
        key_concerns: List[str],
    ) -> str:
        concern_text = " ".join(item.lower() for item in key_concerns)
        if risk_level == "critical" or "replace" in concern_text or status in {"blocked", "rejected", "inactive"}:
            return "Replace"
        if risk_level == "high":
            return "Monitor"
        if not key_strengths or "not registered" in concern_text:
            return "Review"
        if key_concerns:
            return "Monitor"
        return "Continue"

    def _recommended_actions(self, decision: str, supplier: str, key_concerns: List[str]) -> List[str]:
        if decision == "Replace":
            return [
                f"Identify replacement options for {supplier}.",
                "Assess operational continuity before further purchase commitment.",
                "Escalate supplier decision to Procurement and Management.",
            ]
        if decision == "Monitor":
            actions = [
                f"Continue with {supplier} under active procurement monitoring.",
                "Review delivery, quality, and commercial exposure before renewal.",
            ]
            if key_concerns:
                actions.append(f"Resolve concern: {key_concerns[0]}")
            return actions
        if decision == "Continue":
            return [
                f"Continue working with {supplier}.",
                "Keep supplier performance and dependency evidence current.",
            ]
        return [
            f"Complete supplier evidence review for {supplier}.",
            "Map supplier products, relationships, and risk ownership before decision.",
        ]

    def _executive_summary(
        self,
        supplier: str,
        supplier_decision: str,
        risk_level: str,
        key_concerns: List[str],
        key_strengths: List[str],
    ) -> str:
        reason = key_concerns[0] if key_concerns else (key_strengths[0] if key_strengths else "available evidence is limited")
        return (
            f"ATHENA completed the supplier assessment for {supplier}. "
            f"Recommendation is {supplier_decision}. "
            f"Risk level is {self._risk_label(risk_level)}. "
            f"Primary reason: {reason}"
        )

    def _executive_reasoning(
        self,
        supplier: str,
        supplier_decision: str,
        key_concerns: List[str],
        key_strengths: List[str],
        reasoning: Dict[str, Any],
        executive_reasoning: Dict[str, Any],
    ) -> str:
        reason = (
            key_concerns[0]
            if key_concerns
            else key_strengths[0]
            if key_strengths
            else executive_reasoning.get("executive_explanation")
            or reasoning.get("executive_explanation")
            or "available evidence is limited"
        )
        return f"ATHENA recommends {supplier_decision} for {supplier} because {str(reason).rstrip('.')}."

    def _confidence(
        self,
        executive_reasoning: Dict[str, Any],
        organization_supplier: Dict[str, Any],
        supplier_profile: Dict[str, Any],
        knowledge: Dict[str, Any],
        learning: Dict[str, Any],
    ) -> int:
        values = []
        reasoning_confidence = self._safe_int(executive_reasoning.get("confidence"))
        if reasoning_confidence > 0:
            values.append(reasoning_confidence)
        if organization_supplier:
            values.append(75)
        if supplier_profile.get("products") or supplier_profile.get("documents"):
            values.append(65)
        if knowledge.get("count", 0) > 0:
            values.append(70)
        if learning.get("count", 0) > 0:
            values.append(68)
        if values:
            return max(1, min(round(sum(values) / len(values)), 100))
        return 50

    def _risk_label(self, risk_level: str) -> str:
        normalized = str(risk_level or "").strip().lower()
        if normalized in {"critical", "high", "medium", "low"}:
            return normalized.title()
        return "Unknown"

    def _safe_int(self, value: Any) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    def _unique_text(self, *groups: Any) -> List[str]:
        values = []
        seen = set()
        for group in groups:
            if not group:
                continue
            items = group if isinstance(group, list) else [group]
            for item in items:
                text = str(item or "").strip()
                key = text.lower()
                if text and key not in seen:
                    values.append(text)
                    seen.add(key)
        return values

    def _human_join(self, values: List[Any]) -> str:
        clean_values = [str(value or "").strip() for value in values if str(value or "").strip()]
        if not clean_values:
            return ""
        if len(clean_values) == 1:
            return clean_values[0]
        if len(clean_values) == 2:
            return f"{clean_values[0]} and {clean_values[1]}"
        return f"{', '.join(clean_values[:-1])}, and {clean_values[-1]}"

    def _failure(self, reason: str, message: str) -> Dict[str, Any]:
        return {
            "engine": "supplier_executive",
            "status": "failed",
            "reason": reason,
            "message": message,
        }


supplier_executive = SupplierExecutive()


def evaluate_supplier(question: str, supplier: str = "") -> Dict[str, Any]:
    return supplier_executive.evaluate_supplier(question=question, supplier=supplier)
