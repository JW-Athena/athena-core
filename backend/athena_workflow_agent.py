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
