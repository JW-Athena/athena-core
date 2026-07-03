from dataclasses import dataclass, field
from typing import Any, Dict, List

from athena_memory_agent import AthenaMemoryAgent
from athena_reasoning_agent import AthenaReasoningAgent
from athena_workflow_agent import AthenaWorkflowAgent
from capability_004_executive_extraction import ExecutiveInformationExtractor
from capability_005_obligation_extraction import ObligationExtractor
from desktop_agent import desktop_agent
from event_bus import event_bus
from executive_action_plan_engine import ExecutiveActionPlanEngine
from executive_decision_brief_engine import ExecutiveDecisionBriefEngine
from executive_file_intelligence_loop_routes import file_intelligence_loop
from risk_register_engine import RiskRegisterEngine
from timing_utils import new_request_context


@dataclass
class ExecutionContext:
    objective: str
    path: str
    selected_plan: str
    execution_plan: Dict[str, Any]
    document_type: str = ""
    query: str = ""
    text: str = ""
    file_data: Dict[str, Any] = field(default_factory=dict)
    request_context: Dict[str, Any] = field(default_factory=new_request_context)


@dataclass
class CapabilityExecutionResult:
    capability: str
    status: str
    result: Dict[str, Any] = field(default_factory=dict)
    reason: str = ""
    message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        response = {
            "capability": self.capability,
            "status": self.status,
            "result": self.result,
        }
        if self.reason:
            response["reason"] = self.reason
        if self.message:
            response["message"] = self.message
        return response


class ExecutiveExecutionRuntime:
    def __init__(self):
        self.workflow_agent = AthenaWorkflowAgent()
        self.reasoning_agent = AthenaReasoningAgent()
        self.memory_agent = AthenaMemoryAgent()
        self.executive_extractor = ExecutiveInformationExtractor()
        self.obligation_extractor = ObligationExtractor()
        self.risk_register_engine = RiskRegisterEngine()
        self.decision_brief_engine = ExecutiveDecisionBriefEngine()
        self.action_plan_engine = ExecutiveActionPlanEngine()

    async def execute_plan(self, context: ExecutionContext) -> Dict[str, Any]:
        event_bus.publish(
            "BrainObjectiveExecutionStarted",
            "executive_brain",
            {
                "objective": context.objective,
                "selected_plan": context.selected_plan,
                "path": context.path,
                "result": "started",
            },
        )

        capability_results: List[CapabilityExecutionResult] = []
        results: Dict[str, Any] = {}

        try:
            steps = context.execution_plan.get("steps", [])
            for step in sorted(steps, key=lambda item: int(item.get("order", 0) or 0)):
                capability_result = await self.execute_capability(context, step, results)
                capability_results.append(capability_result)
                results[capability_result.capability] = capability_result.to_dict()

            execution_status = self._execution_status(capability_results)
            response = {
                "engine": "executive_brain",
                "status": "success",
                "objective": context.objective,
                "selected_plan": context.selected_plan,
                "execution_status": execution_status,
                "capabilities_executed": [
                    result.capability
                    for result in capability_results
                    if result.status == "success"
                ],
                "results": results,
                "executive_response": self._executive_response(results),
            }

            event_bus.publish(
                "BrainObjectiveExecutionCompleted",
                "executive_brain",
                {
                    "objective": context.objective,
                    "selected_plan": context.selected_plan,
                    "execution_status": execution_status,
                    "capabilities_executed": response["capabilities_executed"],
                    "result": "success",
                },
            )
            return response
        except Exception as exc:
            event_bus.publish(
                "BrainObjectiveExecutionFailed",
                "executive_brain",
                {
                    "objective": context.objective,
                    "selected_plan": context.selected_plan,
                    "reason": "execution_runtime_error",
                    "result": "failed",
                },
            )
            return {
                "engine": "executive_brain",
                "status": "failed",
                "objective": context.objective,
                "selected_plan": context.selected_plan,
                "execution_status": "failed",
                "capabilities_executed": [
                    result.capability
                    for result in capability_results
                    if result.status == "success"
                ],
                "results": results,
                "executive_response": {
                    "summary": f"Executive objective execution failed: {exc}",
                    "recommended_next_action": "Review the failed execution event and retry after resolving the cause.",
                    "requires_approval": False,
                },
                "reason": "execution_runtime_error",
            }

    async def execute_capability(
        self,
        context: ExecutionContext,
        step: Dict[str, Any],
        results: Dict[str, Any],
    ) -> CapabilityExecutionResult:
        capability = str(step.get("capability", "") or "").strip()
        event_bus.publish(
            "CapabilityExecutionStarted",
            "executive_brain",
            {
                "objective": context.objective,
                "selected_plan": context.selected_plan,
                "capability": capability,
                "order": step.get("order", 0),
                "result": "started",
            },
        )

        try:
            result = await self._execute_supported_capability(context, capability, results)
            if result.status == "success":
                event_bus.publish(
                    "CapabilityExecutionCompleted",
                    "executive_brain",
                    {
                        "objective": context.objective,
                        "selected_plan": context.selected_plan,
                        "capability": capability,
                        "result": "success",
                    },
                )
            else:
                event_bus.publish(
                    "CapabilityExecutionFailed",
                    "executive_brain",
                    {
                        "objective": context.objective,
                        "selected_plan": context.selected_plan,
                        "capability": capability,
                        "reason": result.reason,
                        "status": result.status,
                        "result": "failed",
                    },
                )
            return result
        except Exception as exc:
            event_bus.publish(
                "CapabilityExecutionFailed",
                "executive_brain",
                {
                    "objective": context.objective,
                    "selected_plan": context.selected_plan,
                    "capability": capability,
                    "reason": f"{capability}_error",
                    "result": "failed",
                },
            )
            return CapabilityExecutionResult(
                capability=capability,
                status="failed",
                reason=f"{capability}_error",
                message=f"Capability execution failed: {exc}",
            )

    async def _execute_supported_capability(
        self,
        context: ExecutionContext,
        capability: str,
        results: Dict[str, Any],
    ) -> CapabilityExecutionResult:
        if capability == "file_intelligence_loop":
            result = await file_intelligence_loop(
                {
                    "path": context.path,
                    "query": context.query or context.objective,
                }
            )
            return self._capability_result(capability, result)

        if capability == "file_understanding_with_memory":
            result = self.workflow_agent.file_understanding_with_memory(
                desktop_agent=desktop_agent,
                reasoning_agent=self.reasoning_agent,
                memory_agent=self.memory_agent,
                path=context.path,
            )
            if result.get("status") == "success":
                workflow = result.get("workflow", {})
                context.file_data = workflow.get("file", {})
                read_result = desktop_agent.read_file(context.path)
                if read_result.get("status") == "success":
                    context.text = read_result.get("file", {}).get("content", "")
                else:
                    return CapabilityExecutionResult(
                        capability=capability,
                        status="failed",
                        result=result,
                        reason=read_result.get("reason", "read_error"),
                        message=read_result.get("message", "Safe file read failed."),
                    )
            return self._capability_result(capability, result)

        if not context.text and capability in {
            "executive_extraction",
            "obligation_extraction",
            "risk_register",
            "executive_decision_brief",
            "executive_action_plan",
        }:
            return CapabilityExecutionResult(
                capability=capability,
                status="skipped",
                reason="missing_document_text",
                message="Document text is not available from an earlier capability.",
            )

        if capability == "executive_extraction":
            result = self.executive_extractor.extract(
                text=context.text,
                document_type=context.document_type or None,
            )
            context.request_context["cache"]["executive_information.extract"] = result
            return CapabilityExecutionResult(capability=capability, status="success", result=result)

        if capability == "obligation_extraction":
            result = self.obligation_extractor.extract(
                text=context.text,
                document_type=context.document_type or None,
            )
            context.request_context["cache"]["obligation_extraction.extract"] = result
            return CapabilityExecutionResult(capability=capability, status="success", result=result)

        if capability == "risk_register":
            result = self.risk_register_engine.generate(
                text=context.text,
                document_type=context.document_type or None,
                request_context=context.request_context,
            )
            return self._capability_result(capability, result, result_key="risk_register")

        if capability == "executive_decision_brief":
            result = self.decision_brief_engine.generate(
                text=context.text,
                document_type=context.document_type or None,
                request_context=context.request_context,
            )
            return self._capability_result(capability, result, result_key="brief")

        if capability == "executive_action_plan":
            result = self.action_plan_engine.generate(
                text=context.text,
                document_type=context.document_type or None,
                request_context=context.request_context,
            )
            return self._capability_result(capability, result, result_key="action_plan")

        return CapabilityExecutionResult(
            capability=capability,
            status="unsupported",
            reason="unsupported_capability",
            message="No runtime executor is registered for this capability.",
        )

    def _capability_result(
        self,
        capability: str,
        result: Dict[str, Any],
        result_key: str = "",
    ) -> CapabilityExecutionResult:
        if not isinstance(result, dict):
            return CapabilityExecutionResult(
                capability=capability,
                status="failed",
                reason="invalid_capability_result",
                message="Capability returned an invalid result.",
            )

        status = result.get("status", "success")
        if status != "success":
            return CapabilityExecutionResult(
                capability=capability,
                status="failed",
                result=result,
                reason=result.get("reason", f"{capability}_failed"),
                message=result.get("message", "Capability failed."),
            )

        normalized = result.get(result_key, result) if result_key else result
        return CapabilityExecutionResult(
            capability=capability,
            status="success",
            result=normalized if isinstance(normalized, dict) else result,
            message=result.get("message", ""),
        )

    def _execution_status(self, capability_results: List[CapabilityExecutionResult]) -> str:
        if not capability_results:
            return "completed_with_no_capabilities"
        if any(result.status == "failed" for result in capability_results):
            return "completed_with_failures"
        if any(result.status in {"skipped", "unsupported"} for result in capability_results):
            return "completed_with_skips"
        return "completed"

    def _executive_response(self, results: Dict[str, Any]) -> Dict[str, Any]:
        action_plan = self._result_payload(results, "executive_action_plan")
        decision_brief = self._result_payload(results, "executive_decision_brief")
        file_loop = self._result_payload(results, "file_intelligence_loop")
        file_understanding = self._result_payload(results, "file_understanding_with_memory")

        summary = self._first_text(
            action_plan.get("executive_summary"),
            decision_brief.get("executive_summary"),
            file_loop.get("message"),
            file_understanding.get("workflow", {}).get("summary", {}).get("summary_text"),
            "Executive objective execution completed.",
        )
        recommended_next_action = self._recommended_next_action(
            action_plan=action_plan,
            decision_brief=decision_brief,
            file_loop=file_loop,
        )
        requires_approval = bool(
            file_loop.get("decision", {}).get("requires_approval", False)
            or any(
                action.get("requires_approval", False)
                for action in action_plan.get("actions", []) or []
                if isinstance(action, dict)
            )
        )

        return {
            "summary": summary,
            "recommended_next_action": recommended_next_action,
            "requires_approval": requires_approval,
        }

    def _result_payload(self, results: Dict[str, Any], capability: str) -> Dict[str, Any]:
        item = results.get(capability, {})
        payload = item.get("result", {}) if isinstance(item, dict) else {}
        return payload if isinstance(payload, dict) else {}

    def _recommended_next_action(
        self,
        action_plan: Dict[str, Any],
        decision_brief: Dict[str, Any],
        file_loop: Dict[str, Any],
    ) -> str:
        actions = action_plan.get("actions", []) or []
        if actions and isinstance(actions[0], dict):
            return self._first_text(
                actions[0].get("action"),
                actions[0].get("title"),
                actions[0].get("description"),
            )

        required_actions = decision_brief.get("required_actions", []) or []
        if required_actions:
            return str(required_actions[0])

        next_step = file_loop.get("decision", {}).get("next_step") or file_loop.get("recommendation", {}).get("next_step")
        if next_step:
            return str(next_step)

        return "Review the completed executive results and assign accountable owners."

    def _first_text(self, *values: Any) -> str:
        for value in values:
            text = str(value or "").strip()
            if text:
                return text
        return ""
