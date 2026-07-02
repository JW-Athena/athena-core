from typing import Any, Dict, List


class AthenaWorkflowAgent:
    """
    ATHENA Workflow Agent

    Reviews executed workflow outputs and decides whether one additional
    intelligence step is justified before ATHENA produces its executive response.
    """

    ALLOWED_ADDITIONAL_STEPS = {
        "risk_register",
        "executive_dashboard",
        "executive_report",
        "contract_intelligence",
        "commercial_exposure",
        "opportunity_scoring",
        "bid_no_bid",
        "executive_scenarios",
    }

    def file_understanding(self, desktop_agent: Any, reasoning_agent: Any, path: str) -> Dict[str, Any]:
        steps_completed = []

        try:
            metadata_result = desktop_agent.file_info(path)
            if metadata_result.get("status") != "success":
                return self._workflow_blocked(
                    step="inspect_metadata",
                    reason=self._metadata_failure_reason(metadata_result),
                    message=metadata_result.get("message", "File metadata inspection failed."),
                )
            steps_completed.append("inspect_metadata")

            summary_request_result = desktop_agent.request_file_summary(path)
            if summary_request_result.get("status") != "success":
                return self._workflow_blocked(
                    step="request_file_summary",
                    reason=summary_request_result.get("reason", "request_file_summary_failed"),
                    message=summary_request_result.get("message", "File summary request preparation failed."),
                    steps_completed=steps_completed,
                    file_data=metadata_result.get("file", {}),
                )
            steps_completed.append("request_file_summary")

            reasoning_result = reasoning_agent.summarize_file_request(
                summary_request_result.get("summary_request", {})
            )
            if reasoning_result.get("status") != "success":
                return self._workflow_blocked(
                    step="summarize_file_request",
                    reason=reasoning_result.get("reason", "summarize_file_request_failed"),
                    message=reasoning_result.get("message", "File summary generation failed."),
                    steps_completed=steps_completed,
                    file_data=metadata_result.get("file", {}),
                )
            steps_completed.append("summarize_file_request")

            return {
                "status": "success",
                "workflow": {
                    "name": "file_understanding",
                    "steps_completed": steps_completed,
                    "file": metadata_result.get("file", {}),
                    "summary": reasoning_result.get("summary", {}),
                },
                "message": "File understanding workflow completed.",
            }
        except Exception as exc:
            return self._workflow_blocked(
                step="workflow",
                reason="workflow_error",
                message=f"File understanding workflow failed: {exc}",
                steps_completed=steps_completed,
            )

    def file_understanding_with_memory(
        self,
        desktop_agent: Any,
        reasoning_agent: Any,
        memory_agent: Any,
        path: str,
    ) -> Dict[str, Any]:
        result = self.file_understanding(
            desktop_agent=desktop_agent,
            reasoning_agent=reasoning_agent,
            path=path,
        )
        workflow = result.get("workflow", {})

        if result.get("status") != "success":
            workflow["name"] = "file_understanding_with_memory"
            result["workflow"] = workflow
            return result

        memory_workflow = dict(workflow)
        memory_workflow["name"] = "file_understanding"

        memory_result = memory_agent.store_file_understanding(memory_workflow)
        if memory_result.get("status") != "success":
            return {
                "status": "blocked",
                "step": "store_file_understanding",
                "reason": memory_result.get("reason", "memory_store_error"),
                "workflow": {
                    "name": "file_understanding_with_memory",
                    "steps_completed": list(workflow.get("steps_completed", [])),
                    "file": workflow.get("file", {}),
                    "summary": workflow.get("summary", {}),
                    "memory_record": {},
                },
                "message": memory_result.get("message", "File understanding memory storage failed."),
            }

        return {
            "status": "success",
            "workflow": {
                "name": "file_understanding_with_memory",
                "steps_completed": list(workflow.get("steps_completed", [])) + ["store_file_understanding"],
                "file": workflow.get("file", {}),
                "summary": workflow.get("summary", {}),
                "memory_record": memory_result.get("memory_record", {}),
            },
            "message": "File understanding workflow completed and stored in memory.",
        }

    def evaluate(
        self,
        initial_workflow: List[str],
        engine_outputs: Dict[str, Any],
        reasoning: Dict[str, Any],
        clarification: Dict[str, Any],
    ) -> Dict[str, Any]:
        additional_steps = []
        execution_summary = "Workflow Agent executed the planner workflow without additional steps."

        if clarification.get("needed") and self._commercial_value_missing(reasoning):
            return self._result(
                initial_workflow=initial_workflow,
                executed_workflow=list(engine_outputs.keys()),
                additional_steps=[],
                execution_summary=(
                    "Workflow Agent did not add engines because critical commercial "
                    "information requires clarification."
                ),
            )

        if (
            "contract_intelligence" in engine_outputs
            and "risk_register" not in engine_outputs
            and self._contract_risk(engine_outputs) == "Critical"
        ):
            additional_steps.append("risk_register")
            execution_summary = (
                "Workflow Agent added Risk Register because Contract Intelligence "
                "detected Critical contract risk."
            )

        if (
            not additional_steps
            and "opportunity_scoring" in engine_outputs
            and "bid_no_bid" not in engine_outputs
        ):
            additional_steps.append("bid_no_bid")
            execution_summary = (
                "Workflow Agent added Bid/No-Bid because Opportunity Scoring was executed."
            )

        additional_steps = self._allowed_new_steps(additional_steps, engine_outputs)[:1]

        return self._result(
            initial_workflow=initial_workflow,
            executed_workflow=list(engine_outputs.keys()) + additional_steps,
            additional_steps=additional_steps,
            execution_summary=execution_summary,
        )

    def after_execution(
        self,
        initial_workflow: List[str],
        engine_outputs: Dict[str, Any],
        additional_steps: List[str],
        execution_summary: str,
    ) -> Dict[str, Any]:
        return self._result(
            initial_workflow=initial_workflow,
            executed_workflow=list(engine_outputs.keys()),
            additional_steps=additional_steps,
            execution_summary=execution_summary,
        )

    def _contract_risk(self, engine_outputs: Dict[str, Any]) -> str:
        contract = engine_outputs.get("contract_intelligence", {})
        return str(contract.get("overall_contract_risk") or "").strip().title()

    def _commercial_value_missing(self, reasoning: Dict[str, Any]) -> bool:
        missing = reasoning.get("missing_information", [])
        return "Commercial value" in missing or "Currency" in missing

    def _allowed_new_steps(
        self,
        steps: List[str],
        engine_outputs: Dict[str, Any],
    ) -> List[str]:
        allowed = []
        for step in steps:
            if step in self.ALLOWED_ADDITIONAL_STEPS and step not in engine_outputs:
                allowed.append(step)
        return allowed

    def _result(
        self,
        initial_workflow: List[str],
        executed_workflow: List[str],
        additional_steps: List[str],
        execution_summary: str,
    ) -> Dict[str, Any]:
        return {
            "initial_workflow": list(initial_workflow),
            "executed_workflow": list(executed_workflow),
            "additional_steps": list(additional_steps),
            "execution_summary": execution_summary,
        }

    def _workflow_blocked(
        self,
        step: str,
        reason: str,
        message: str,
        steps_completed: List[str] = None,
        file_data: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        return {
            "status": "blocked",
            "step": step,
            "reason": reason,
            "workflow": {
                "name": "file_understanding",
                "steps_completed": list(steps_completed or []),
                "file": file_data or {},
                "summary": {},
            },
            "message": message,
        }

    def _metadata_failure_reason(self, metadata_result: Dict[str, Any]) -> str:
        message = str(metadata_result.get("message", "")).lower()
        if any(term in message for term in ["network", "unc", "administrative", "system", "shell", "registry", "control panel"]):
            return "unsafe_path"
        return "inspect_metadata_failed"
