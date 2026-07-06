from typing import Any, Dict, List

from engine_020_organization_model import organization_model
from event_bus import event_bus


class OrganizationImpactAnalysis:
    def analyze(self, mission: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        clean_mission = str(mission or "").strip()
        if not clean_mission:
            return self._failure("mission_required", "Mission is required for organization impact analysis.")

        organization = organization_model.organization_summary()
        supplier_index = organization_model.list_suppliers()
        normalized_mission = clean_mission.lower()
        impacted_departments = self._impacted_departments(normalized_mission)
        impacted_suppliers = self._impacted_suppliers(
            clean_mission,
            supplier_index.get("suppliers", organization.get("suppliers", [])),
        )
        impacted_people = self._impacted_people(impacted_departments, organization.get("people", []))
        impacted_responsibilities = self._impacted_responsibilities(impacted_people)
        impact_level = self._impact_level(impacted_departments, impacted_suppliers, normalized_mission)
        recommended_coordination = self._recommended_coordination(
            impacted_departments,
            impacted_suppliers,
            impacted_responsibilities,
        )
        requires_management_attention = (
            "Management" in impacted_departments
            or impact_level in {"high", "critical"}
        )
        impact_summary = self._impact_summary(
            mission=clean_mission,
            impacted_departments=impacted_departments,
            impacted_suppliers=impacted_suppliers,
            impact_level=impact_level,
        )

        result = {
            "engine": "organization_impact_analysis",
            "status": "success",
            "mission": clean_mission,
            "impacted_departments": impacted_departments,
            "impacted_people": impacted_people,
            "impacted_suppliers": impacted_suppliers,
            "impacted_responsibilities": impacted_responsibilities,
            "impact_level": impact_level,
            "impact_summary": impact_summary,
            "recommended_coordination": recommended_coordination,
            "requires_management_attention": requires_management_attention,
            "context": context or {},
        }

        event_bus.publish(
            "OrganizationImpactAnalyzed",
            "organization_impact_analysis",
            {
                "mission": clean_mission,
                "impact_level": impact_level,
                "impacted_departments": impacted_departments,
                "impacted_suppliers": [
                    supplier.get("name", "")
                    for supplier in impacted_suppliers
                ],
                "requires_management_attention": requires_management_attention,
                "result": "success",
            },
        )
        return result

    def _impacted_departments(self, normalized_mission: str) -> List[str]:
        departments: List[str] = []

        if "tender" in normalized_mission:
            departments.extend([
                "Commercial",
                "Procurement",
                "Finance",
                "Operations",
                "Legal",
                "Management",
            ])
        if "supplier" in normalized_mission:
            departments.extend(["Procurement", "Operations", "Commercial"])
        if "contract" in normalized_mission:
            departments.extend(["Legal", "Finance", "Commercial", "Management"])
        if "product" in normalized_mission:
            departments.extend(["Commercial", "Procurement", "Operations"])

        if not departments:
            departments.extend(["Commercial", "Management"])

        return self._unique(departments)

    def _impacted_suppliers(
        self,
        mission: str,
        suppliers: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        impacted = []
        normalized_mission = self._normalize_match_text(mission)
        for supplier in suppliers:
            supplier_name = str(supplier.get("name", "") or "").strip()
            if supplier_name and self._supplier_name_matches(supplier_name, normalized_mission):
                impacted.append(dict(supplier))
        return impacted

    def _impacted_people(
        self,
        impacted_departments: List[str],
        people: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        departments = {department.lower() for department in impacted_departments}
        impacted = []
        for person in people:
            department = str(person.get("department", "") or "").lower()
            if department in departments:
                impacted.append(dict(person))
        return impacted

    def _impacted_responsibilities(self, impacted_people: List[Dict[str, Any]]) -> List[str]:
        responsibilities = []
        for person in impacted_people:
            for responsibility in person.get("responsibilities", []) or []:
                responsibilities.append(str(responsibility or "").strip())
        return self._unique([item for item in responsibilities if item])

    def _impact_level(
        self,
        departments: List[str],
        suppliers: List[Dict[str, Any]],
        normalized_mission: str,
    ) -> str:
        if "tender" in normalized_mission or len(departments) >= 5:
            return "critical"
        if "contract" in normalized_mission or any(
            supplier.get("risk_level") in {"high", "critical"}
            for supplier in suppliers
        ):
            return "high"
        if "supplier" in normalized_mission or "product" in normalized_mission or len(departments) >= 3:
            return "medium"
        return "low"

    def _impact_summary(
        self,
        mission: str,
        impacted_departments: List[str],
        impacted_suppliers: List[Dict[str, Any]],
        impact_level: str,
    ) -> str:
        department_text = self._human_join(impacted_departments)
        supplier_names = [
            supplier.get("name", "")
            for supplier in impacted_suppliers
            if supplier.get("name")
        ]

        supplier_text = ""
        if supplier_names:
            supplier_text = f" It also directly impacts supplier {self._human_join(supplier_names)}."

        if "tender" in mission.lower():
            reason = (
                "The tender requires pricing, compliance, delivery, financial review, "
                "legal review, and executive approval."
            )
        elif "supplier" in mission.lower():
            reason = (
                "The supplier-related mission affects sourcing, operational continuity, "
                "and commercial commitments."
            )
        elif "contract" in mission.lower():
            reason = (
                "The contract-related mission affects legal obligations, financial exposure, "
                "commercial terms, and executive approval."
            )
        elif "product" in mission.lower():
            reason = (
                "The product-related mission affects commercial positioning, procurement readiness, "
                "and operational delivery."
            )
        else:
            reason = "The mission affects executive coordination and operating ownership."

        return (
            f"This mission has {impact_level} organizational impact. "
            f"It impacts {department_text}.{supplier_text} {reason}"
        )

    def _recommended_coordination(
        self,
        departments: List[str],
        suppliers: List[Dict[str, Any]],
        responsibilities: List[str],
    ) -> List[str]:
        coordination = [
            f"Coordinate with {department} for mission input and decision readiness."
            for department in departments
        ]
        for supplier in suppliers:
            coordination.append(
                f"Review supplier dependency and risk exposure for {supplier.get('name', '')}."
            )
        if responsibilities:
            coordination.append(
                f"Confirm ownership for: {self._human_join(responsibilities[:4])}."
            )
        return coordination

    def _unique(self, values: List[str]) -> List[str]:
        seen = set()
        unique_values = []
        for value in values:
            clean_value = str(value or "").strip()
            key = clean_value.lower()
            if clean_value and key not in seen:
                unique_values.append(clean_value)
                seen.add(key)
        return unique_values

    def _supplier_name_matches(self, supplier_name: str, normalized_mission: str) -> bool:
        normalized_supplier = self._normalize_match_text(supplier_name)
        if not normalized_supplier:
            return False

        padded_mission = f" {normalized_mission} "
        if f" {normalized_supplier} " in padded_mission:
            return True

        supplier_tokens = normalized_supplier.split()
        mission_tokens = set(normalized_mission.split())
        return bool(supplier_tokens and all(token in mission_tokens for token in supplier_tokens))

    def _normalize_match_text(self, value: str) -> str:
        normalized_characters = [
            character.lower() if character.isalnum() else " "
            for character in str(value or "")
        ]
        return " ".join("".join(normalized_characters).split())

    def _human_join(self, values: List[str]) -> str:
        clean_values = [str(value or "").strip() for value in values if str(value or "").strip()]
        if not clean_values:
            return "no specific organizational unit"
        if len(clean_values) == 1:
            return clean_values[0]
        if len(clean_values) == 2:
            return f"{clean_values[0]} and {clean_values[1]}"
        return f"{', '.join(clean_values[:-1])}, and {clean_values[-1]}"

    def _failure(self, reason: str, message: str) -> Dict[str, Any]:
        return {
            "engine": "organization_impact_analysis",
            "status": "failed",
            "reason": reason,
            "message": message,
        }


organization_impact_analysis = OrganizationImpactAnalysis()
