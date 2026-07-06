from datetime import datetime
from typing import Any, Dict, List
from uuid import uuid4
import builtins

from engine_015_mission_controller import mission_controller
from engine_019_strategic_objective_manager import strategic_objective_manager
from engine_020_organization_model import organization_model
from event_bus import event_bus


NODE_TYPES = {
    "organization",
    "department",
    "person",
    "supplier",
    "customer",
    "product",
    "mission",
    "strategic_objective",
    "contract",
    "tender",
}

RELATIONSHIP_TYPES = {
    "belongs_to",
    "works_with",
    "supplies",
    "supports",
    "manages",
    "owns",
    "participates_in",
    "related_to",
    "depends_on",
}


class ExecutiveKnowledgeGraph:
    def __init__(self):
        if not hasattr(builtins, "_ATHENA_KNOWLEDGE_GRAPH_NODES"):
            builtins._ATHENA_KNOWLEDGE_GRAPH_NODES = {}
        if not hasattr(builtins, "_ATHENA_KNOWLEDGE_GRAPH_RELATIONSHIPS"):
            builtins._ATHENA_KNOWLEDGE_GRAPH_RELATIONSHIPS = {}
        self._nodes: Dict[str, Dict[str, Any]] = builtins._ATHENA_KNOWLEDGE_GRAPH_NODES
        self._relationships: Dict[str, Dict[str, Any]] = builtins._ATHENA_KNOWLEDGE_GRAPH_RELATIONSHIPS

    def create_node(self, node_type: str, name: str, node_id: str = "") -> Dict[str, Any]:
        normalized_type = self._normalize_node_type(node_type)
        if not normalized_type:
            return self._failure("invalid_node_type", "Node type is not supported.")

        clean_name = str(name or "").strip()
        if not clean_name:
            return self._failure("node_name_required", "Node name is required.")

        existing = self._find_node_by_type_name(normalized_type, clean_name)
        if existing:
            return self._success({"node": dict(existing)})

        clean_id = str(node_id or "").strip() or self._node_id(normalized_type, clean_name)
        node = {
            "id": clean_id,
            "type": normalized_type,
            "name": clean_name,
        }
        self._nodes[node["id"]] = node

        event_bus.publish(
            "KnowledgeNodeCreated",
            "executive_knowledge_graph",
            {
                "node_id": node["id"],
                "type": node["type"],
                "name": node["name"],
                "result": "success",
            },
        )
        return self._success({"node": dict(node)})

    def create_relationship(self, source: str, target: str, relationship: str) -> Dict[str, Any]:
        self._sync_reference_nodes()
        normalized_relationship = self._normalize_relationship(relationship)
        if not normalized_relationship:
            return self._failure("invalid_relationship_type", "Relationship type is not supported.")

        source_node = self._find_node(source)
        target_node = self._find_node(target)
        if not source_node:
            return self._failure("source_node_not_found", "Source node was not found.")
        if not target_node:
            return self._failure("target_node_not_found", "Target node was not found.")

        existing = self._find_relationship(source_node["id"], target_node["id"], normalized_relationship)
        if existing:
            return self._success({"relationship": dict(existing)})

        relationship_record = {
            "id": str(uuid4()),
            "source": source_node["id"],
            "target": target_node["id"],
            "relationship": normalized_relationship,
            "created_at": self._now(),
        }
        self._relationships[relationship_record["id"]] = relationship_record

        event_bus.publish(
            "KnowledgeRelationshipCreated",
            "executive_knowledge_graph",
            {
                "relationship_id": relationship_record["id"],
                "source": relationship_record["source"],
                "target": relationship_record["target"],
                "relationship": relationship_record["relationship"],
                "result": "success",
            },
        )
        return self._success({"relationship": dict(relationship_record)})

    def list_nodes(self) -> Dict[str, Any]:
        self._sync_reference_nodes()
        nodes = [dict(node) for node in self._nodes.values()]
        nodes.sort(key=lambda item: (item.get("type", ""), item.get("name", "")))
        return self._success({
            "count": len(nodes),
            "nodes": nodes,
        })

    def list_relationships(self) -> Dict[str, Any]:
        self._sync_reference_nodes()
        relationships = [dict(relationship) for relationship in self._relationships.values()]
        relationships.sort(key=lambda item: item.get("created_at", ""))
        return self._success({
            "count": len(relationships),
            "relationships": relationships,
        })

    def get_related_entities(self, node: str) -> Dict[str, Any]:
        self._sync_reference_nodes()
        node_record = self._find_node(node)
        if not node_record:
            return self._failure("node_not_found", "Node was not found.")

        related = []
        for relationship in self._relationships.values():
            if relationship.get("source") == node_record["id"]:
                target = self._find_node(relationship.get("target", ""))
                if target:
                    related.append({
                        "direction": "outgoing",
                        "relationship": relationship.get("relationship", ""),
                        "node": dict(target),
                    })
            elif relationship.get("target") == node_record["id"]:
                source = self._find_node(relationship.get("source", ""))
                if source:
                    related.append({
                        "direction": "incoming",
                        "relationship": relationship.get("relationship", ""),
                        "node": dict(source),
                    })

        return self._success({
            "node": dict(node_record),
            "count": len(related),
            "related_entities": related,
        })

    def _sync_reference_nodes(self) -> None:
        organization = organization_model.organization_summary()
        self._upsert_reference_node("organization", "organization:icc", organization.get("organization_name", "ICC"))

        for department in organization.get("departments", []):
            self._upsert_reference_node("department", f"department:{department.get('id', '')}", department.get("name", ""))
        for person in organization.get("people", []):
            self._upsert_reference_node("person", f"person:{person.get('id', '')}", person.get("name", ""))
        for supplier in organization.get("suppliers", []):
            self._upsert_reference_node("supplier", f"supplier:{supplier.get('id', '')}", supplier.get("name", ""))
        for customer in organization.get("customers", []):
            self._upsert_reference_node("customer", f"customer:{customer.get('id', '')}", customer.get("name", ""))
        for product in organization.get("products", []):
            self._upsert_reference_node("product", f"product:{product.get('id', '')}", product.get("name", ""))

        objectives = strategic_objective_manager.list_strategic_objectives().get("strategic_objectives", [])
        for objective in objectives:
            self._upsert_reference_node(
                "strategic_objective",
                f"strategic_objective:{objective.get('strategic_objective_id', '')}",
                objective.get("title", ""),
            )

        for mission in mission_controller.list_mission_records():
            self._upsert_reference_node(
                "mission",
                f"mission:{mission.get('mission_id', '')}",
                mission.get("mission", ""),
            )

    def _upsert_reference_node(self, node_type: str, node_id: str, name: str) -> None:
        clean_id = str(node_id or "").strip()
        clean_name = str(name or "").strip()
        if not clean_id or not clean_name:
            return
        self._nodes[clean_id] = {
            "id": clean_id,
            "type": node_type,
            "name": clean_name,
        }

    def _find_node(self, node: str) -> Dict[str, Any]:
        clean_node = str(node or "").strip()
        if clean_node in self._nodes:
            return self._nodes[clean_node]
        for node_record in self._nodes.values():
            if node_record.get("name", "").lower() == clean_node.lower():
                return node_record
        return {}

    def _find_node_by_type_name(self, node_type: str, name: str) -> Dict[str, Any]:
        clean_name = str(name or "").strip().lower()
        for node in self._nodes.values():
            if node.get("type") == node_type and node.get("name", "").lower() == clean_name:
                return node
        return {}

    def _find_relationship(self, source: str, target: str, relationship: str) -> Dict[str, Any]:
        for relationship_record in self._relationships.values():
            if (
                relationship_record.get("source") == source
                and relationship_record.get("target") == target
                and relationship_record.get("relationship") == relationship
            ):
                return relationship_record
        return {}

    def _normalize_node_type(self, node_type: str) -> str:
        normalized = str(node_type or "").strip().lower()
        return normalized if normalized in NODE_TYPES else ""

    def _normalize_relationship(self, relationship: str) -> str:
        normalized = str(relationship or "").strip().lower()
        return normalized if normalized in RELATIONSHIP_TYPES else ""

    def _node_id(self, node_type: str, name: str) -> str:
        slug = "".join(
            character.lower() if character.isalnum() else "-"
            for character in str(name or "").strip()
        )
        slug = "-".join([part for part in slug.split("-") if part])
        return f"{node_type}:{slug or uuid4()}"

    def _success(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "engine": "executive_knowledge_graph",
            "status": "success",
            **payload,
        }

    def _failure(self, reason: str, message: str) -> Dict[str, Any]:
        return {
            "engine": "executive_knowledge_graph",
            "status": "failed",
            "reason": reason,
            "message": message,
        }

    def _now(self) -> str:
        return datetime.utcnow().isoformat()


executive_knowledge_graph = ExecutiveKnowledgeGraph()
