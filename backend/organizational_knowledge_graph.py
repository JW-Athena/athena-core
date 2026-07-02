import json
import os
import re
from typing import Any, Dict, List


class OrganizationalKnowledgeGraph:
    """
    Lightweight organizational knowledge graph for ATHENA.

    Stores generic nodes and relationships extracted from ATHENA analysis
    outputs. This is backend graph intelligence, not visualization.
    """

    def __init__(self, graph_path: str = "database/organizational_knowledge_graph.json"):
        self.graph_path = graph_path
        self._ensure_storage()

    def get_graph(self) -> Dict[str, Any]:
        graph = self._load_graph()
        graph["summary"] = self._summary(graph)
        return graph

    def update_from_analysis(
        self,
        metadata: Dict[str, Any],
        document_type: str,
        decision: Dict[str, Any],
        tasks: Dict[str, Any],
        notifications: Dict[str, Any],
        execution: Dict[str, Any],
        action_plan: Dict[str, Any],
        browser_plan: Dict[str, Any],
        engine_outputs: Dict[str, Any],
    ) -> Dict[str, Any]:
        graph = self._load_graph()
        document_id = self._document_node(graph, metadata, document_type)

        decision_id = self._add_node(
            graph,
            node_type="decision",
            label=f"Decision: {decision.get('status', 'unknown')}",
            metadata={
                "status": decision.get("status"),
                "confidence": decision.get("confidence"),
                "owner": decision.get("decision_owner"),
            },
        )
        self._add_edge(graph, document_id, decision_id, "opportunity_has_decision", {})

        self._add_task_nodes(graph, document_id, tasks)
        self._add_notification_nodes(graph, document_id, notifications)
        self._add_risk_nodes(graph, document_id, engine_outputs)
        self._add_contract_nodes(graph, document_id, engine_outputs)
        self._add_action_nodes(graph, document_id, execution, action_plan, browser_plan)

        graph["summary"] = self._summary(graph)
        self._save_graph(graph)
        return graph

    def _document_node(self, graph: Dict[str, Any], metadata: Dict[str, Any], document_type: str) -> str:
        label = metadata.get("filename") or document_type or "ATHENA analysis"
        return self._add_node(
            graph,
            node_type="document",
            label=label,
            metadata={
                "document_type": document_type or "",
                "content_type": metadata.get("content_type", ""),
                "size_bytes": metadata.get("size_bytes", 0),
            },
        )

    def _add_task_nodes(self, graph: Dict[str, Any], document_id: str, tasks: Dict[str, Any]) -> None:
        for task in tasks.get("items", []) or []:
            task_id = self._add_node(
                graph,
                node_type="task",
                label=task.get("title", "Task"),
                metadata={
                    "priority": task.get("priority"),
                    "status": task.get("status"),
                    "due": task.get("recommended_due"),
                },
            )
            self._add_edge(graph, document_id, task_id, "opportunity_requires_task", {})

            owner = task.get("owner")
            if owner:
                department_id = self._add_node(
                    graph,
                    node_type="department",
                    label=owner,
                    metadata={},
                )
                self._add_edge(graph, task_id, department_id, "task_assigned_to_department", {})

    def _add_notification_nodes(self, graph: Dict[str, Any], document_id: str, notifications: Dict[str, Any]) -> None:
        for notification in notifications.get("items", []) or []:
            notification_id = self._add_node(
                graph,
                node_type="notification",
                label=notification.get("title", "Notification"),
                metadata={
                    "priority": notification.get("priority"),
                    "type": notification.get("notification_type"),
                    "delivery": notification.get("recommended_delivery"),
                },
            )
            self._add_edge(graph, document_id, notification_id, "notification_sent_to_role", {})

            role = notification.get("recipient_role")
            if role:
                department_id = self._add_node(graph, "department", role, {})
                self._add_edge(graph, notification_id, department_id, "notification_sent_to_role", {})

    def _add_risk_nodes(self, graph: Dict[str, Any], document_id: str, engine_outputs: Dict[str, Any]) -> None:
        risk_register = engine_outputs.get("risk_register", {})
        for risk in risk_register.get("risks", []) or []:
            label = risk.get("title") or risk.get("description") or risk.get("category")
            if not label:
                continue
            risk_id = self._add_node(
                graph,
                node_type="risk",
                label=label,
                metadata={
                    "severity": risk.get("severity"),
                    "category": risk.get("category"),
                },
            )
            self._add_edge(graph, document_id, risk_id, "document_contains_risk", {})

    def _add_contract_nodes(self, graph: Dict[str, Any], document_id: str, engine_outputs: Dict[str, Any]) -> None:
        contract = engine_outputs.get("contract_intelligence", {})
        if not contract:
            return

        contract_id = self._add_node(
            graph,
            node_type="contract",
            label=contract.get("contract_type") or "Contract intelligence",
            metadata={
                "risk": contract.get("overall_contract_risk"),
                "confidence": contract.get("confidence"),
            },
        )
        self._add_edge(graph, document_id, contract_id, "contract_related_to_document", {})

        for clause in contract.get("critical_clauses", []) or []:
            label = clause.get("title") or clause.get("summary")
            if not label:
                continue
            clause_id = self._add_node(
                graph,
                node_type="risk",
                label=label,
                metadata={
                    "risk_level": clause.get("risk_level"),
                    "category": clause.get("category"),
                },
            )
            self._add_edge(graph, contract_id, clause_id, "contract_has_clause", {})

    def _add_action_nodes(
        self,
        graph: Dict[str, Any],
        document_id: str,
        execution: Dict[str, Any],
        action_plan: Dict[str, Any],
        browser_plan: Dict[str, Any],
    ) -> None:
        for step in action_plan.get("steps", []) or []:
            action_id = self._add_node(
                graph,
                node_type="action",
                label=step.get("action", "Action"),
                metadata={
                    "agent": step.get("agent"),
                    "approval_required": step.get("approval_required"),
                },
            )
            self._add_edge(graph, document_id, action_id, "document_requires_action", {})

        for action in browser_plan.get("browser_actions", []) or []:
            action_id = self._add_node(
                graph,
                node_type="action",
                label=action.get("action", "Browser action"),
                metadata={
                    "mode": browser_plan.get("mode"),
                    "approval_required": action.get("approval_required"),
                },
            )
            self._add_edge(graph, document_id, action_id, "document_requires_action", {})

    def _add_node(
        self,
        graph: Dict[str, Any],
        node_type: str,
        label: str,
        metadata: Dict[str, Any],
    ) -> str:
        clean_label = self._clean_label(label)
        node_id = f"{node_type}:{self._slug(clean_label)}"

        for node in graph["nodes"]:
            if node["id"] == node_id:
                node["metadata"].update(self._clean_metadata(metadata))
                return node_id

        graph["nodes"].append(
            {
                "id": node_id,
                "type": node_type,
                "label": clean_label,
                "metadata": self._clean_metadata(metadata),
            }
        )
        return node_id

    def _add_edge(
        self,
        graph: Dict[str, Any],
        source: str,
        target: str,
        relationship: str,
        metadata: Dict[str, Any],
    ) -> None:
        if not source or not target or source == target:
            return

        for edge in graph["edges"]:
            if edge["source"] == source and edge["target"] == target and edge["relationship"] == relationship:
                edge["metadata"].update(self._clean_metadata(metadata))
                return

        graph["edges"].append(
            {
                "source": source,
                "target": target,
                "relationship": relationship,
                "metadata": self._clean_metadata(metadata),
            }
        )

    def _ensure_storage(self) -> None:
        folder = os.path.dirname(self.graph_path)
        if folder and not os.path.exists(folder):
            os.makedirs(folder)
        if not os.path.exists(self.graph_path):
            self._save_graph(self._empty_graph())

    def _load_graph(self) -> Dict[str, Any]:
        self._ensure_storage()
        try:
            with open(self.graph_path, "r", encoding="utf-8") as handle:
                graph = json.load(handle)
            graph.setdefault("nodes", [])
            graph.setdefault("edges", [])
            graph.setdefault("summary", {})
            return graph
        except Exception:
            graph = self._empty_graph()
            self._save_graph(graph)
            return graph

    def _save_graph(self, graph: Dict[str, Any]) -> None:
        with open(self.graph_path, "w", encoding="utf-8") as handle:
            json.dump(graph, handle, indent=2)

    def _empty_graph(self) -> Dict[str, Any]:
        return {
            "nodes": [],
            "edges": [],
            "summary": {
                "total_nodes": 0,
                "total_edges": 0,
                "node_types": {},
                "relationship_types": {},
            },
        }

    def _summary(self, graph: Dict[str, Any]) -> Dict[str, Any]:
        node_types = {}
        relationship_types = {}

        for node in graph.get("nodes", []):
            node_types[node.get("type", "")] = node_types.get(node.get("type", ""), 0) + 1

        for edge in graph.get("edges", []):
            relationship = edge.get("relationship", "")
            relationship_types[relationship] = relationship_types.get(relationship, 0) + 1

        return {
            "total_nodes": len(graph.get("nodes", [])),
            "total_edges": len(graph.get("edges", [])),
            "node_types": node_types,
            "relationship_types": relationship_types,
        }

    def _clean_label(self, label: Any) -> str:
        text = " ".join(str(label or "").split()).strip()
        return text[:140] if text else "Unknown"

    def _slug(self, label: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")
        return slug[:80] or "unknown"

    def _clean_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        clean = {}
        for key, value in (metadata or {}).items():
            if value in [None, "", [], {}]:
                continue
            if isinstance(value, (str, int, float, bool)):
                clean[key] = value
        return clean


organizational_knowledge_graph = OrganizationalKnowledgeGraph()
