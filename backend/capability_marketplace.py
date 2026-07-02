from typing import Any, Dict, List


class CapabilityMarketplace:
    """
    ATHENA Capability Marketplace

    Read-only catalog of what ATHENA knows how to do. This is separate from
    the Agent Registry, which describes who performs work.
    """

    def __init__(self):
        self._capabilities = [
            {
                "id": "executive_analysis",
                "name": "Executive Analysis",
                "category": "Executive Intelligence",
                "version": "1.0",
                "enabled": True,
                "description": "Produces executive-ready analysis from business documents.",
                "required_agents": ["planner", "workflow_agent", "decision_engine"],
                "requires_approval": False,
                "execution_supported": False,
            },
            {
                "id": "risk_intelligence",
                "name": "Risk Intelligence",
                "category": "Risk",
                "version": "1.0",
                "enabled": True,
                "description": "Identifies and summarizes risks from documents and analysis outputs.",
                "required_agents": ["reasoning_agent", "workflow_agent"],
                "requires_approval": False,
                "execution_supported": False,
            },
            {
                "id": "contract_intelligence",
                "name": "Contract Intelligence",
                "category": "Legal",
                "version": "1.0",
                "enabled": True,
                "description": "Reviews contract-like documents for obligations, missing terms, and risk.",
                "required_agents": ["planner", "reasoning_agent"],
                "requires_approval": False,
                "execution_supported": False,
            },
            {
                "id": "commercial_intelligence",
                "name": "Commercial Intelligence",
                "category": "Commercial",
                "version": "1.0",
                "enabled": True,
                "description": "Assesses commercial exposure, payment terms, value, and financial gaps.",
                "required_agents": ["reasoning_agent", "decision_engine"],
                "requires_approval": False,
                "execution_supported": False,
            },
            {
                "id": "opportunity_intelligence",
                "name": "Opportunity Intelligence",
                "category": "Opportunity",
                "version": "1.0",
                "enabled": True,
                "description": "Scores opportunities and supports bid posture assessment.",
                "required_agents": ["planner", "decision_engine"],
                "requires_approval": False,
                "execution_supported": False,
            },
            {
                "id": "portfolio_intelligence",
                "name": "Portfolio Intelligence",
                "category": "Portfolio",
                "version": "1.0",
                "enabled": True,
                "description": "Aggregates multiple documents into an executive portfolio assessment.",
                "required_agents": ["planner", "decision_engine"],
                "requires_approval": False,
                "execution_supported": False,
            },
            {
                "id": "executive_reports",
                "name": "Executive Reports",
                "category": "Reporting",
                "version": "1.0",
                "enabled": True,
                "description": "Generates structured executive reports from ATHENA intelligence.",
                "required_agents": ["planner", "task_agent", "decision_engine"],
                "requires_approval": False,
                "execution_supported": False,
            },
            {
                "id": "memory",
                "name": "Memory",
                "category": "Knowledge",
                "version": "1.0",
                "enabled": True,
                "description": "Consults historical organizational knowledge when useful.",
                "required_agents": ["memory_agent"],
                "requires_approval": False,
                "execution_supported": False,
            },
            {
                "id": "reasoning",
                "name": "Reasoning",
                "category": "Cognitive",
                "version": "1.0",
                "enabled": True,
                "description": "Assesses information sufficiency and missing information.",
                "required_agents": ["reasoning_agent"],
                "requires_approval": False,
                "execution_supported": False,
            },
            {
                "id": "workflow_planning",
                "name": "Workflow Planning",
                "category": "Planning",
                "version": "1.0",
                "enabled": True,
                "description": "Plans and adjusts ATHENA intelligence workflows.",
                "required_agents": ["planner", "workflow_agent"],
                "requires_approval": False,
                "execution_supported": False,
            },
            {
                "id": "decision_support",
                "name": "Decision Support",
                "category": "Decision",
                "version": "1.0",
                "enabled": True,
                "description": "Produces formal executive decision support from analysis outputs.",
                "required_agents": ["decision_engine"],
                "requires_approval": False,
                "execution_supported": False,
            },
            {
                "id": "task_planning",
                "name": "Task Planning",
                "category": "Action",
                "version": "1.0",
                "enabled": True,
                "description": "Converts intelligence into structured executive tasks.",
                "required_agents": ["task_agent"],
                "requires_approval": False,
                "execution_supported": False,
            },
            {
                "id": "notification_planning",
                "name": "Notification Planning",
                "category": "Communication",
                "version": "1.0",
                "enabled": True,
                "description": "Plans who should be informed about ATHENA findings.",
                "required_agents": ["notification_agent"],
                "requires_approval": False,
                "execution_supported": False,
            },
            {
                "id": "approval_planning",
                "name": "Approval Planning",
                "category": "Approval",
                "version": "1.0",
                "enabled": True,
                "description": "Determines which future actions require management approval.",
                "required_agents": ["approval_agent"],
                "requires_approval": False,
                "execution_supported": False,
            },
            {
                "id": "execution_planning",
                "name": "Execution Planning",
                "category": "Execution",
                "version": "1.0",
                "enabled": True,
                "description": "Creates planning-only execution plans without executing actions.",
                "required_agents": ["execution_agent", "action_planner"],
                "requires_approval": True,
                "execution_supported": False,
            },
            {
                "id": "browser_simulation",
                "name": "Browser Simulation",
                "category": "Execution",
                "version": "1.0",
                "enabled": True,
                "description": "Plans browser activities without execution.",
                "required_agents": ["browser_agent"],
                "requires_approval": True,
                "execution_supported": False,
            },
            {
                "id": "organization_awareness",
                "name": "Organization Awareness",
                "category": "Organizational Intelligence",
                "version": "1.0",
                "enabled": True,
                "description": "Maintains generic organizational state awareness from ATHENA analysis.",
                "required_agents": [],
                "requires_approval": False,
                "execution_supported": False,
            },
            {
                "id": "knowledge_graph",
                "name": "Knowledge Graph",
                "category": "Knowledge",
                "version": "1.0",
                "enabled": True,
                "description": "Builds a lightweight organizational knowledge graph from ATHENA outputs.",
                "required_agents": [],
                "requires_approval": False,
                "execution_supported": False,
            },
        ]

    def list_capabilities(self) -> List[Dict[str, Any]]:
        return [dict(capability) for capability in self._capabilities]

    def get_capability(self, capability_id: str) -> Dict[str, Any]:
        for capability in self._capabilities:
            if capability["id"] == capability_id:
                return dict(capability)
        return {}

    def enabled_capabilities(self) -> List[Dict[str, Any]]:
        return [
            dict(capability)
            for capability in self._capabilities
            if capability.get("enabled")
        ]


capability_marketplace = CapabilityMarketplace()
