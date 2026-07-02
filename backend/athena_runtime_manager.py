from typing import Any, Dict

from agent_registry import agent_registry
from capability_marketplace import capability_marketplace
from organization_awareness import organization_awareness
from organizational_knowledge_graph import organizational_knowledge_graph


class AthenaRuntimeManager:
    """
    Read-only ATHENA Runtime Manager.

    Provides system health and safety posture by composing existing ATHENA
    registries and state services. It does not execute actions.
    """

    def status(self) -> Dict[str, Any]:
        agents = agent_registry.list_agents()
        capabilities = capability_marketplace.list_capabilities()
        organization_state = organization_awareness.get_state()
        graph = organizational_knowledge_graph.get_graph()

        organization = organization_state.get("organization", {})
        graph_summary = graph.get("summary", {})
        organization_health = organization.get("overall_health", "Stable")

        return {
            "system_mode": "online",
            "core_status": "healthy",
            "agents_registered": len(agents),
            "capabilities_registered": len(capabilities),
            "organization_health": organization_health,
            "knowledge_graph_nodes": int(graph_summary.get("total_nodes", 0) or 0),
            "knowledge_graph_edges": int(graph_summary.get("total_edges", 0) or 0),
            "execution_enabled": False,
            "approval_required": True,
            "safety_mode": "planning_only",
            "summary": self._summary(
                agents_registered=len(agents),
                capabilities_registered=len(capabilities),
                organization_health=organization_health,
            ),
        }

    def _summary(
        self,
        agents_registered: int,
        capabilities_registered: int,
        organization_health: str,
    ) -> str:
        return (
            "ATHENA runtime is online with "
            f"{agents_registered} registered agents and "
            f"{capabilities_registered} registered capabilities. "
            f"Organization health is {organization_health}. "
            "Execution remains disabled in planning-only safety mode."
        )


athena_runtime_manager = AthenaRuntimeManager()
