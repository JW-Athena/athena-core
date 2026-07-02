from typing import Any, Callable, Dict, List

from athena_action_planner import AthenaActionPlanner
from athena_approval_agent import AthenaApprovalAgent
from athena_browser_agent import AthenaBrowserAgent
from athena_clarification_agent import AthenaClarificationAgent
from athena_decision_engine import AthenaDecisionEngine
from athena_execution_agent import AthenaExecutionAgent
from athena_memory_agent import AthenaMemoryAgent
from athena_notification_agent import AthenaNotificationAgent
from athena_planner import AthenaPlanner
from athena_reasoning_agent import AthenaReasoningAgent
from athena_task_agent import AthenaTaskAgent
from athena_workflow_agent import AthenaWorkflowAgent
from desktop_agent import AthenaDesktopAgent


class AgentRegistry:
    """
    Read-only ATHENA Agent Registry.

    Provides a central catalog and factory lookup for current and future
    ATHENA agents. It does not dynamically execute agents.
    """

    def __init__(self):
        self._agents = {
            "brain": {
                "id": "brain",
                "name": "ATHENA Brain",
                "version": "1.0",
                "enabled": True,
                "type": "orchestrator",
                "description": "Orchestrates ATHENA planning, reasoning, workflows, decisions, and response assembly.",
                "inputs": ["request"],
                "outputs": ["result"],
                "depends_on": [],
            },
            "planner": {
                "id": "planner",
                "name": "Planner",
                "version": "1.0",
                "enabled": True,
                "type": "cognitive",
                "description": "Selects the initial ATHENA workflow before engines execute.",
                "inputs": ["question", "document_type", "metadata"],
                "outputs": ["planning"],
                "depends_on": ["brain"],
                "factory": AthenaPlanner,
            },
            "memory_agent": {
                "id": "memory_agent",
                "name": "Memory Agent",
                "version": "1.0",
                "enabled": True,
                "type": "cognitive",
                "description": "Provides contextual organizational memory decisions.",
                "inputs": ["planning"],
                "outputs": ["memory"],
                "depends_on": ["planner"],
                "factory": AthenaMemoryAgent,
            },
            "reasoning_agent": {
                "id": "reasoning_agent",
                "name": "Reasoning Agent",
                "version": "1.0",
                "enabled": True,
                "type": "cognitive",
                "description": "Assesses sufficiency and missing information before response generation.",
                "inputs": ["planning", "question", "document_type", "document_text"],
                "outputs": ["reasoning"],
                "depends_on": ["planner", "memory_agent"],
                "factory": AthenaReasoningAgent,
            },
            "clarification_agent": {
                "id": "clarification_agent",
                "name": "Clarification Agent",
                "version": "1.0",
                "enabled": True,
                "type": "cognitive",
                "description": "Determines whether one advisory clarification question is needed.",
                "inputs": ["planning", "reasoning"],
                "outputs": ["clarification"],
                "depends_on": ["reasoning_agent"],
                "factory": AthenaClarificationAgent,
            },
            "workflow_agent": {
                "id": "workflow_agent",
                "name": "Workflow Agent",
                "version": "1.0",
                "enabled": True,
                "type": "workflow",
                "description": "Evaluates workflow continuation and optional additional intelligence steps.",
                "inputs": ["planning", "reasoning", "clarification", "engine_outputs"],
                "outputs": ["workflow_execution"],
                "depends_on": ["planner", "clarification_agent"],
                "factory": AthenaWorkflowAgent,
            },
            "decision_engine": {
                "id": "decision_engine",
                "name": "Decision Engine",
                "version": "1.0",
                "enabled": True,
                "type": "decision",
                "description": "Converts ATHENA intelligence into a formal executive decision.",
                "inputs": ["planning", "reasoning", "clarification", "workflow_execution", "engine_outputs", "tasks"],
                "outputs": ["decision"],
                "depends_on": ["workflow_agent"],
                "factory": AthenaDecisionEngine,
            },
            "task_agent": {
                "id": "task_agent",
                "name": "Task Agent",
                "version": "1.0",
                "enabled": True,
                "type": "action",
                "description": "Converts ATHENA intelligence into structured executive tasks.",
                "inputs": ["engine_outputs"],
                "outputs": ["tasks"],
                "depends_on": ["workflow_agent"],
                "factory": AthenaTaskAgent,
            },
            "notification_agent": {
                "id": "notification_agent",
                "name": "Notification Agent",
                "version": "1.0",
                "enabled": True,
                "type": "communication",
                "description": "Creates structured notification plans from ATHENA findings.",
                "inputs": ["decision", "tasks", "engine_outputs"],
                "outputs": ["notifications"],
                "depends_on": ["decision_engine", "task_agent"],
                "factory": AthenaNotificationAgent,
            },
            "execution_agent": {
                "id": "execution_agent",
                "name": "Execution Agent",
                "version": "1.0",
                "enabled": True,
                "type": "execution",
                "description": "Creates planning-only execution plans from decisions, tasks, and notifications.",
                "inputs": ["decision", "tasks", "notifications", "reasoning", "clarification"],
                "outputs": ["execution"],
                "depends_on": ["decision_engine", "task_agent", "notification_agent"],
                "factory": AthenaExecutionAgent,
            },
            "approval_agent": {
                "id": "approval_agent",
                "name": "Approval Agent",
                "version": "1.0",
                "enabled": True,
                "type": "approval",
                "description": "Determines whether future execution actions require management approval.",
                "inputs": ["decision", "tasks", "notifications", "execution"],
                "outputs": ["approval"],
                "depends_on": ["decision_engine", "task_agent", "notification_agent", "execution_agent"],
                "factory": AthenaApprovalAgent,
            },
            "action_planner": {
                "id": "action_planner",
                "name": "Action Planner",
                "version": "1.0",
                "enabled": True,
                "type": "planning",
                "description": "Converts execution plans into ordered future action sequences.",
                "inputs": ["execution", "decision", "tasks", "notifications", "approval"],
                "outputs": ["action_plan"],
                "depends_on": ["execution_agent", "approval_agent"],
                "factory": AthenaActionPlanner,
            },
            "browser_agent": {
                "id": "browser_agent",
                "name": "Browser Agent",
                "version": "1.0",
                "enabled": True,
                "type": "browser",
                "description": "Plans browser operations in simulation mode without controlling a browser.",
                "inputs": ["action_plan", "execution", "decision"],
                "outputs": ["browser_plan"],
                "depends_on": ["action_planner"],
                "factory": AthenaBrowserAgent,
            },
            "desktop_agent": {
                "id": "desktop_agent",
                "name": "Desktop Agent",
                "version": "1.0",
                "enabled": True,
                "type": "desktop",
                "description": "Provides planning-only desktop execution capability with execution disabled by default.",
                "inputs": ["approval", "execution"],
                "outputs": ["desktop_status"],
                "depends_on": ["approval_agent", "execution_agent"],
                "factory": AthenaDesktopAgent,
            },
        }

    def list_agents(self) -> List[Dict[str, Any]]:
        return [self._public_metadata(agent) for agent in self._agents.values()]

    def get_agent_metadata(self, agent_id: str) -> Dict[str, Any]:
        agent = self._agents.get(agent_id, {})
        return self._public_metadata(agent) if agent else {}

    def create_agent(self, agent_id: str) -> Any:
        agent = self._agents.get(agent_id)
        if not agent or not agent.get("enabled"):
            raise KeyError(f"Agent is not registered or enabled: {agent_id}")

        factory: Callable[[], Any] = agent.get("factory")
        if not factory:
            raise KeyError(f"Agent has no factory: {agent_id}")

        return factory()

    def _public_metadata(self, agent: Dict[str, Any]) -> Dict[str, Any]:
        return {
            key: value
            for key, value in agent.items()
            if key != "factory"
        }


agent_registry = AgentRegistry()
