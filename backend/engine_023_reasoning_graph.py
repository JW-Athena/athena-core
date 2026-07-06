from collections import deque
from typing import Any, Dict, List, Set

from engine_022_knowledge_graph import executive_knowledge_graph
from event_bus import event_bus


BUSINESS_TARGET_TYPES = {"strategic_objective", "organization", "customer", "tender", "contract"}
DEPENDENCY_RELATIONSHIPS = {"depends_on", "supports", "supplies", "participates_in", "manages", "owns"}
MAX_REASONING_DEPTH = 5


class ExecutiveReasoningGraph:
    def trace_reasoning(self, node_id: str) -> Dict[str, Any]:
        graph = self._graph_snapshot()
        start = self._find_node(graph["nodes"], node_id)
        if not start:
            return self._failure("node_not_found", "Starting node was not found.")

        chain = self._best_chain(start, graph, prefer_business_targets=False)
        result = self._reasoning_result(start, chain)
        self._publish_chain(start, chain, "trace_reasoning")
        return result

    def find_dependency_chain(self, node_id: str) -> Dict[str, Any]:
        graph = self._graph_snapshot()
        start = self._find_node(graph["nodes"], node_id)
        if not start:
            return self._failure("node_not_found", "Starting node was not found.")

        chain = self._best_chain(
            start,
            graph,
            relationship_filter=DEPENDENCY_RELATIONSHIPS,
            prefer_business_targets=False,
        )
        result = self._reasoning_result(start, chain)
        self._publish_chain(start, chain, "find_dependency_chain")
        return result

    def find_business_impact(self, node_id: str) -> Dict[str, Any]:
        graph = self._graph_snapshot()
        start = self._find_node(graph["nodes"], node_id)
        if not start:
            return self._failure("node_not_found", "Starting node was not found.")

        chain = self._best_chain(start, graph, prefer_business_targets=True)
        result = self._reasoning_result(start, chain)
        self._publish_chain(start, chain, "find_business_impact")
        return result

    def _graph_snapshot(self) -> Dict[str, Any]:
        nodes_result = executive_knowledge_graph.list_nodes()
        relationships_result = executive_knowledge_graph.list_relationships()
        nodes = {
            node.get("id", ""): dict(node)
            for node in nodes_result.get("nodes", [])
            if node.get("id")
        }
        relationships = [
            dict(relationship)
            for relationship in relationships_result.get("relationships", [])
            if relationship.get("source") and relationship.get("target")
        ]
        return {
            "nodes": nodes,
            "relationships": relationships,
        }

    def _best_chain(
        self,
        start: Dict[str, Any],
        graph: Dict[str, Any],
        relationship_filter: Set[str] = None,
        prefer_business_targets: bool = False,
    ) -> List[Dict[str, Any]]:
        node_index = graph["nodes"]
        relationships = graph["relationships"]
        adjacency = self._adjacency(relationships, relationship_filter)
        queue = deque([(start["id"], [])])
        visited = {start["id"]}
        fallback_chain: List[Dict[str, Any]] = []

        while queue:
            current_id, path = queue.popleft()
            if path and not fallback_chain:
                fallback_chain = path

            current_node = node_index.get(current_id, {})
            if (
                path
                and prefer_business_targets
                and current_node.get("type") in BUSINESS_TARGET_TYPES
            ):
                return path

            if path and not prefer_business_targets and len(path) >= 2:
                return path

            if len(path) >= MAX_REASONING_DEPTH:
                continue

            for relationship in adjacency.get(current_id, []):
                next_id = relationship.get("target", "")
                if next_id in visited or next_id not in node_index:
                    continue
                visited.add(next_id)
                queue.append((next_id, path + [self._chain_step(relationship, node_index)]))

        return fallback_chain

    def _adjacency(
        self,
        relationships: List[Dict[str, Any]],
        relationship_filter: Set[str] = None,
    ) -> Dict[str, List[Dict[str, Any]]]:
        adjacency: Dict[str, List[Dict[str, Any]]] = {}
        for relationship in relationships:
            relationship_type = relationship.get("relationship", "")
            if relationship_filter and relationship_type not in relationship_filter:
                continue
            adjacency.setdefault(relationship.get("source", ""), []).append(relationship)

        for source in adjacency:
            adjacency[source].sort(key=self._relationship_priority)
        return adjacency

    def _relationship_priority(self, relationship: Dict[str, Any]) -> int:
        priority = {
            "supplies": 1,
            "depends_on": 2,
            "supports": 3,
            "participates_in": 4,
            "manages": 5,
            "owns": 6,
            "belongs_to": 7,
            "works_with": 8,
            "related_to": 9,
        }
        return priority.get(relationship.get("relationship", ""), 20)

    def _chain_step(
        self,
        relationship: Dict[str, Any],
        nodes: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Any]:
        source = nodes.get(relationship.get("source", ""), {})
        target = nodes.get(relationship.get("target", ""), {})
        relationship_type = relationship.get("relationship", "")
        return {
            "source": dict(source),
            "relationship": relationship_type,
            "target": dict(target),
            "explanation": self._step_explanation(source, relationship_type, target),
        }

    def _reasoning_result(
        self,
        start: Dict[str, Any],
        chain: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        return self._success({
            "starting_node": start.get("id", ""),
            "starting_entity": dict(start),
            "reasoning_chain": chain,
            "executive_explanation": self._executive_explanation(start, chain),
        })

    def _step_explanation(
        self,
        source: Dict[str, Any],
        relationship: str,
        target: Dict[str, Any],
    ) -> str:
        source_name = source.get("name", source.get("id", "This entity"))
        target_name = target.get("name", target.get("id", "another entity"))
        phrase = relationship.replace("_", " ")
        return f"{source_name} {phrase} {target_name}."

    def _executive_explanation(
        self,
        start: Dict[str, Any],
        chain: List[Dict[str, Any]],
    ) -> str:
        start_name = start.get("name", start.get("id", "This entity"))
        if not chain:
            return f"{start_name} has no current reasoning chain in ATHENA's executive knowledge graph."

        final_target = chain[-1].get("target", {})
        final_name = final_target.get("name", final_target.get("id", "the business objective"))
        final_type = final_target.get("type", "entity").replace("_", " ")
        return f"{start_name} matters because it connects to {final_type} {final_name}."

    def _find_node(self, nodes: Dict[str, Dict[str, Any]], node_id: str) -> Dict[str, Any]:
        clean_node_id = str(node_id or "").strip()
        if clean_node_id in nodes:
            return nodes[clean_node_id]

        for node in nodes.values():
            if node.get("name", "").lower() == clean_node_id.lower():
                return node
        return {}

    def _publish_chain(
        self,
        start: Dict[str, Any],
        chain: List[Dict[str, Any]],
        operation: str,
    ) -> None:
        event_bus.publish(
            "ReasoningChainGenerated",
            "executive_reasoning_graph",
            {
                "operation": operation,
                "starting_node": start.get("id", ""),
                "starting_entity": start.get("name", ""),
                "chain_length": len(chain),
                "result": "success",
            },
        )

    def _success(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "engine": "executive_reasoning_graph",
            "status": "success",
            **payload,
        }

    def _failure(self, reason: str, message: str) -> Dict[str, Any]:
        return {
            "engine": "executive_reasoning_graph",
            "status": "failed",
            "reason": reason,
            "message": message,
        }


executive_reasoning_graph = ExecutiveReasoningGraph()
