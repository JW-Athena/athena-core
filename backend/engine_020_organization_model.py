from datetime import datetime
from typing import Any, Dict, List
from uuid import uuid4
import builtins

from engine_015_mission_controller import mission_controller
from engine_019_strategic_objective_manager import strategic_objective_manager
from event_bus import event_bus


DEFAULT_DEPARTMENTS = [
    "Commercial",
    "Procurement",
    "Finance",
    "Operations",
    "Legal",
    "Management",
]


class OrganizationOperatingModel:
    def __init__(self):
        if not hasattr(builtins, "_ATHENA_ORGANIZATION_MODEL"):
            builtins._ATHENA_ORGANIZATION_MODEL = {
                "organization_name": "ICC",
                "departments": [],
                "people": [],
                "suppliers": [],
                "customers": [],
                "projects": [],
                "products": [],
            }
        self._model: Dict[str, Any] = builtins._ATHENA_ORGANIZATION_MODEL
        self._ensure_default_departments()

    def create_department(self, name: str, description: str = "") -> Dict[str, Any]:
        clean_name = str(name or "").strip()
        if not clean_name:
            return self._failure("department_name_required", "Department name is required.")

        existing = self._find_department(clean_name)
        if existing:
            return self._success({"department": dict(existing)})

        department = {
            "id": str(uuid4()),
            "name": clean_name,
            "description": str(description or "").strip(),
            "created_at": self._now(),
            "updated_at": self._now(),
        }
        self._model["departments"].append(department)

        event_bus.publish(
            "OrganizationDepartmentCreated",
            "organization_model",
            {
                "department_id": department["id"],
                "department": department["name"],
                "result": "success",
            },
        )
        return self._success({"department": dict(department)})

    def list_departments(self) -> Dict[str, Any]:
        departments = [dict(department) for department in self._model.get("departments", [])]
        departments.sort(key=lambda item: item.get("name", ""))
        return self._success({
            "count": len(departments),
            "departments": departments,
        })

    def create_person(
        self,
        name: str,
        title: str = "",
        department: str = "",
        responsibilities: List[str] = None,
    ) -> Dict[str, Any]:
        clean_name = str(name or "").strip()
        if not clean_name:
            return self._failure("person_name_required", "Person name is required.")

        clean_department = str(department or "").strip()
        if clean_department and not self._find_department(clean_department):
            self.create_department(clean_department)

        person = {
            "id": str(uuid4()),
            "name": clean_name,
            "title": str(title or "").strip(),
            "department": clean_department,
            "responsibilities": self._normalize_string_list(responsibilities or []),
            "created_at": self._now(),
            "updated_at": self._now(),
        }
        self._model["people"].append(person)

        event_bus.publish(
            "OrganizationPersonCreated",
            "organization_model",
            {
                "person_id": person["id"],
                "name": person["name"],
                "department": person["department"],
                "result": "success",
            },
        )
        return self._success({"person": dict(person)})

    def list_people(self) -> Dict[str, Any]:
        people = [dict(person) for person in self._model.get("people", [])]
        people.sort(key=lambda item: (item.get("department", ""), item.get("name", "")))
        return self._success({
            "count": len(people),
            "people": people,
        })

    def create_supplier(
        self,
        name: str,
        status: str = "active",
        risk_level: str = "medium",
        products: List[str] = None,
    ) -> Dict[str, Any]:
        clean_name = str(name or "").strip()
        if not clean_name:
            return self._failure("supplier_name_required", "Supplier name is required.")

        supplier = {
            "id": str(uuid4()),
            "name": clean_name,
            "status": self._normalize_status(status),
            "risk_level": self._normalize_risk_level(risk_level),
            "products": self._normalize_string_list(products or []),
            "created_at": self._now(),
            "updated_at": self._now(),
        }
        self._model["suppliers"].append(supplier)

        event_bus.publish(
            "OrganizationSupplierCreated",
            "organization_model",
            {
                "supplier_id": supplier["id"],
                "name": supplier["name"],
                "status": supplier["status"],
                "risk_level": supplier["risk_level"],
                "result": "success",
            },
        )
        return self._success({"supplier": dict(supplier)})

    def list_suppliers(self) -> Dict[str, Any]:
        suppliers = [dict(supplier) for supplier in self._model.get("suppliers", [])]
        suppliers.sort(key=lambda item: (item.get("risk_level", ""), item.get("name", "")))
        return self._success({
            "count": len(suppliers),
            "suppliers": suppliers,
        })

    def organization_summary(self) -> Dict[str, Any]:
        departments = [dict(department) for department in self._model.get("departments", [])]
        people = [dict(person) for person in self._model.get("people", [])]
        suppliers = [dict(supplier) for supplier in self._model.get("suppliers", [])]
        strategic_objectives = strategic_objective_manager.list_strategic_objectives()
        objective_records = strategic_objectives.get("strategic_objectives", [])
        mission_records = mission_controller.list_mission_records()

        return self._success({
            "organization_name": self._model.get("organization_name", "ICC"),
            "departments": departments,
            "people": people,
            "suppliers": suppliers,
            "customers": [dict(customer) for customer in self._model.get("customers", [])],
            "projects": [dict(project) for project in self._model.get("projects", [])],
            "products": [dict(product) for product in self._model.get("products", [])],
            "strategic_objectives": objective_records,
            "missions": mission_records,
            "statistics": {
                "departments": len(departments),
                "people": len(people),
                "suppliers": len(suppliers),
                "customers": len(self._model.get("customers", [])),
                "projects": len(self._model.get("projects", [])),
                "products": len(self._model.get("products", [])),
                "strategic_objectives": strategic_objectives.get("count", len(objective_records)),
                "missions": len(mission_records),
                "high_risk_suppliers": len([
                    supplier
                    for supplier in suppliers
                    if supplier.get("risk_level") in {"high", "critical"}
                ]),
            },
        })

    def _ensure_default_departments(self) -> None:
        for department_name in DEFAULT_DEPARTMENTS:
            if not self._find_department(department_name):
                self._model["departments"].append({
                    "id": str(uuid4()),
                    "name": department_name,
                    "description": "",
                    "created_at": self._now(),
                    "updated_at": self._now(),
                })

    def _find_department(self, name: str) -> Dict[str, Any]:
        clean_name = str(name or "").strip().lower()
        for department in self._model.get("departments", []):
            if str(department.get("name", "")).strip().lower() == clean_name:
                return department
        return {}

    def _normalize_string_list(self, values: List[Any]) -> List[str]:
        if not isinstance(values, list):
            return []
        return [
            str(value).strip()
            for value in values
            if str(value or "").strip()
        ]

    def _normalize_status(self, status: str) -> str:
        normalized = str(status or "").strip().lower()
        return normalized if normalized else "active"

    def _normalize_risk_level(self, risk_level: str) -> str:
        normalized = str(risk_level or "").strip().lower()
        return normalized if normalized in {"low", "medium", "high", "critical"} else "medium"

    def _success(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "engine": "organization_operating_model",
            "status": "success",
            **payload,
        }

    def _failure(self, reason: str, message: str) -> Dict[str, Any]:
        return {
            "engine": "organization_operating_model",
            "status": "failed",
            "reason": reason,
            "message": message,
        }

    def _now(self) -> str:
        return datetime.utcnow().isoformat()


organization_model = OrganizationOperatingModel()
