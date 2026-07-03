from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List

from athena_memory_agent import AthenaMemoryAgent
from athena_reasoning_agent import AthenaReasoningAgent
from athena_workflow_agent import AthenaWorkflowAgent
from capability_004_executive_extraction import ExecutiveInformationExtractor
from capability_005_obligation_extraction import ObligationExtractor
from desktop_agent import desktop_agent
from event_bus import event_bus
from engine_012_execution_evaluator import evaluate_execution
from executive_action_plan_engine import ExecutiveActionPlanEngine
from executive_decision_brief_engine import ExecutiveDecisionBriefEngine
from executive_file_intelligence_loop_routes import file_intelligence_loop
from risk_register_engine import RiskRegisterEngine
from timing_utils import new_request_context


@dataclass
class ExecutionPlanStep:
    capability: str
    order: int = 0
    purpose: str = ""
    required_inputs: List[str] = field(default_factory=list)
    output_key: str = ""
    depends_on: List[str] = field(default_factory=list)
    critical: bool = False

    @classmethod
    def from_dict(cls, step: Dict[str, Any]) -> "ExecutionPlanStep":
        capability = str(step.get("capability", "") or "").strip()
        return cls(
            capability=capability,
            order=_safe_int(step.get("order", 0)),
            purpose=str(step.get("purpose") or step.get("reason") or ""),
            required_inputs=[
                str(item)
                for item in step.get("required_inputs", []) or []
                if str(item or "").strip()
            ],
            output_key=str(step.get("output_key") or capability),
            depends_on=[
                str(item)
                for item in step.get("depends_on", []) or []
                if str(item or "").strip()
            ],
            critical=bool(step.get("critical", False)),
        )


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
    results: Dict[str, Any] = field(default_factory=dict)
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
        self.capability_handlers: Dict[str, Callable[[ExecutionContext, ExecutionPlanStep], Any]] = {
            "file_intelligence_loop": self._handle_file_intelligence_loop,
            "file_understanding_with_memory": self._handle_file_understanding_with_memory,
            "executive_extraction": self._handle_executive_extraction,
            "obligation_extraction": self._handle_obligation_extraction,
            "risk_register": self._handle_risk_register,
            "executive_decision_brief": self._handle_executive_decision_brief,
            "executive_action_plan": self._handle_executive_action_plan,
        }

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
            steps = [
                ExecutionPlanStep.from_dict(step)
                for step in context.execution_plan.get("steps", [])
                if isinstance(step, dict)
            ]
            for step in sorted(steps, key=lambda item: item.order):
                capability_result = await self.execute_capability(context, step, results)
                capability_results.append(capability_result)
                output_key = step.output_key or capability_result.capability
                results[output_key] = capability_result.to_dict()
                context.results[output_key] = capability_result.to_dict()
                if step.critical and capability_result.status != "success":
                    break

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
                "plan_driven": True,
            }
            response["execution_evaluation"] = self._evaluate_execution(response)

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
                "plan_driven": True,
            }

    async def execute_capability(
        self,
        context: ExecutionContext,
        step: ExecutionPlanStep,
        results: Dict[str, Any],
    ) -> CapabilityExecutionResult:
        capability = step.capability
        event_bus.publish(
            "CapabilityExecutionStarted",
            "executive_brain",
            {
                "objective": context.objective,
                "selected_plan": context.selected_plan,
                "capability": capability,
                "order": step.order,
                "result": "started",
            },
        )

        try:
            skip_result = self._dependency_or_input_skip(context, step)
            if skip_result:
                self._publish_capability_skipped(context, step, skip_result)
                return skip_result

            result = await self._execute_supported_capability(context, step)
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
            elif result.status == "skipped":
                self._publish_capability_skipped(context, step, result)
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
        step: ExecutionPlanStep,
    ) -> CapabilityExecutionResult:
        handler = self.capability_handlers.get(step.capability)
        if handler:
            return await handler(context, step)

        return CapabilityExecutionResult(
            capability=step.capability,
            status="unsupported",
            reason="unsupported_capability",
            message="No runtime executor is registered for this capability.",
        )

    async def _handle_file_intelligence_loop(
        self,
        context: ExecutionContext,
        step: ExecutionPlanStep,
    ) -> CapabilityExecutionResult:
        result = await file_intelligence_loop(
            {
                "path": context.path,
                "query": context.query or context.objective,
            }
        )
        return self._capability_result(step.capability, result)

    async def _handle_file_understanding_with_memory(
        self,
        context: ExecutionContext,
        step: ExecutionPlanStep,
    ) -> CapabilityExecutionResult:
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
                    capability=step.capability,
                    status="failed",
                    result=result,
                    reason=read_result.get("reason", "read_error"),
                    message=read_result.get("message", "Safe file read failed."),
                )
        return self._capability_result(step.capability, result)

    async def _handle_executive_extraction(
        self,
        context: ExecutionContext,
        step: ExecutionPlanStep,
    ) -> CapabilityExecutionResult:
        result = self.executive_extractor.extract(
            text=context.text,
            document_type=context.document_type or None,
        )
        context.request_context["cache"]["executive_information.extract"] = result
        return CapabilityExecutionResult(capability=step.capability, status="success", result=result)

    async def _handle_obligation_extraction(
        self,
        context: ExecutionContext,
        step: ExecutionPlanStep,
    ) -> CapabilityExecutionResult:
        result = self.obligation_extractor.extract(
            text=context.text,
            document_type=context.document_type or None,
        )
        context.request_context["cache"]["obligation_extraction.extract"] = result
        return CapabilityExecutionResult(capability=step.capability, status="success", result=result)

    async def _handle_risk_register(
        self,
        context: ExecutionContext,
        step: ExecutionPlanStep,
    ) -> CapabilityExecutionResult:
        result = self.risk_register_engine.generate(
            text=context.text,
            document_type=context.document_type or None,
            request_context=context.request_context,
        )
        return self._capability_result(step.capability, result, result_key="risk_register")

    async def _handle_executive_decision_brief(
        self,
        context: ExecutionContext,
        step: ExecutionPlanStep,
    ) -> CapabilityExecutionResult:
        result = self.decision_brief_engine.generate(
            text=context.text,
            document_type=context.document_type or None,
            request_context=context.request_context,
        )
        return self._capability_result(step.capability, result, result_key="brief")

    async def _handle_executive_action_plan(
        self,
        context: ExecutionContext,
        step: ExecutionPlanStep,
    ) -> CapabilityExecutionResult:
        result = self.action_plan_engine.generate(
            text=context.text,
            document_type=context.document_type or None,
            request_context=context.request_context,
        )
        return self._capability_result(step.capability, result, result_key="action_plan")

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

    def _dependency_or_input_skip(
        self,
        context: ExecutionContext,
        step: ExecutionPlanStep,
    ) -> CapabilityExecutionResult:
        for dependency in step.depends_on:
            dependency_result = context.results.get(dependency, {})
            if not dependency_result:
                return CapabilityExecutionResult(
                    capability=step.capability,
                    status="skipped",
                    reason="missing_dependency",
                    message=f"Required dependency result is missing: {dependency}.",
                )
            if dependency_result.get("status") != "success":
                return CapabilityExecutionResult(
                    capability=step.capability,
                    status="skipped",
                    reason="dependency_failed",
                    message=f"Required dependency did not succeed: {dependency}.",
                )

        for required_input in step.required_inputs:
            if required_input == "text" and not context.text:
                return CapabilityExecutionResult(
                    capability=step.capability,
                    status="skipped",
                    reason="missing_document_text",
                    message="Document text is not available from an earlier capability.",
                )
            if required_input == "file" and not context.file_data:
                return CapabilityExecutionResult(
                    capability=step.capability,
                    status="skipped",
                    reason="missing_file_context",
                    message="File context is not available from an earlier capability.",
                )

        return None

    def _publish_capability_skipped(
        self,
        context: ExecutionContext,
        step: ExecutionPlanStep,
        result: CapabilityExecutionResult,
    ) -> None:
        event_bus.publish(
            "CapabilityExecutionSkipped",
            "executive_brain",
            {
                "objective": context.objective,
                "selected_plan": context.selected_plan,
                "capability": step.capability,
                "reason": result.reason,
                "result": "skipped",
            },
        )

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

    def _evaluate_execution(self, response: Dict[str, Any]) -> Dict[str, Any]:
        try:
            evaluation = evaluate_execution(
                objective=response.get("objective", ""),
                selected_plan=response.get("selected_plan", ""),
                execution_status=response.get("execution_status", ""),
                capabilities_executed=response.get("capabilities_executed", []),
                results=response.get("results", {}),
                executive_response=response.get("executive_response", {}),
            )
            event_bus.publish(
                "ExecutionEvaluationCompleted",
                "executive_brain",
                {
                    "objective": response.get("objective", ""),
                    "selected_plan": response.get("selected_plan", ""),
                    "objective_satisfied": bool(evaluation.get("objective_satisfied", False)),
                    "decision_ready": bool(evaluation.get("decision_ready", False)),
                    "confidence": int(evaluation.get("confidence", 0) or 0),
                    "approval_required": bool(evaluation.get("approval_required", False)),
                    "result": "success",
                },
            )
            return evaluation
        except Exception as exc:
            event_bus.publish(
                "ExecutionEvaluationFailed",
                "executive_brain",
                {
                    "objective": response.get("objective", ""),
                    "selected_plan": response.get("selected_plan", ""),
                    "reason": "execution_evaluation_error",
                    "result": "failed",
                },
            )
            return {
                "evaluation_status": "failed",
                "objective_satisfied": False,
                "decision_ready": False,
                "confidence": 0,
                "approval_required": False,
                "completion_quality": "low",
                "failed_capabilities": [],
                "skipped_capabilities": [],
                "unsupported_capabilities": [],
                "missing_information": [],
                "key_findings": [],
                "recommended_next_action": "Review execution results manually before making a decision.",
                "evaluation_summary": f"Execution evaluation failed: {exc}",
                "reason": "execution_evaluation_error",
            }


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0
