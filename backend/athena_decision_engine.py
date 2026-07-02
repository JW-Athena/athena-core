from typing import Any, Dict, List


class AthenaDecisionEngine:
    """
    ATHENA Decision Engine

    Final decision layer for ATHENA Brain orchestration. This is distinct from
    standalone Executive Decision Intelligence.
    """

    def decide(
        self,
        plan: Dict[str, Any],
        memory: Dict[str, Any],
        reasoning: Dict[str, Any],
        clarification: Dict[str, Any],
        workflow_execution: Dict[str, Any],
        engine_outputs: Dict[str, Any],
        tasks: Dict[str, Any],
    ) -> Dict[str, Any]:
        blocking_factors = self._blocking_factors(
            reasoning=reasoning,
            clarification=clarification,
            workflow_execution=workflow_execution,
            engine_outputs=engine_outputs,
            tasks=tasks,
        )
        required_before_decision = self._required_before_decision(
            reasoning=reasoning,
            clarification=clarification,
            tasks=tasks,
        )

        if self._rejected_by_intelligence(engine_outputs):
            return self._decision(
                status="rejected",
                confidence=self._confidence(reasoning, blocking_factors),
                reason="Existing intelligence indicates the opportunity should not proceed.",
                blocking_factors=blocking_factors,
                required_before_decision=required_before_decision,
                instruction="Record the rejection rationale and do not proceed without new information.",
                next_workflow="Executive Review",
            )

        if self._blocked(reasoning, clarification, workflow_execution, blocking_factors):
            return self._decision(
                status="blocked",
                confidence="Low",
                reason=self._blocked_reason(reasoning, blocking_factors),
                blocking_factors=blocking_factors,
                required_before_decision=required_before_decision,
                instruction="Do not approve until blocking information is resolved.",
                next_workflow=self._next_workflow(required_before_decision, plan),
            )

        if self._conditional(reasoning, clarification, engine_outputs, tasks):
            return self._decision(
                status="conditional",
                confidence=self._confidence(reasoning, blocking_factors),
                reason=self._conditional_reason(reasoning, clarification, engine_outputs),
                blocking_factors=blocking_factors,
                required_before_decision=required_before_decision,
                instruction="Proceed only as a conditional management decision with named owners for open actions.",
                next_workflow=self._next_workflow(required_before_decision, plan),
            )

        return self._decision(
            status="approved",
            confidence="High",
            reason="Reasoning is sufficient, no clarification is required, and no critical blockers were identified.",
            blocking_factors=[],
            required_before_decision=[],
            instruction="Management may proceed subject to normal governance and final accountability.",
            next_workflow="Execution Planning",
        )

    def evaluate_recommendation(self, recommendation: Dict[str, Any]) -> Dict[str, Any]:
        if not recommendation:
            return self._recommendation_failure(
                reason="missing_recommendation",
                message="Recommendation is required.",
            )
        if not isinstance(recommendation, dict):
            return self._recommendation_failure(
                reason="invalid_recommendation",
                message="Recommendation must be an object.",
            )

        next_step = str(recommendation.get("next_step", "") or "").strip()
        reason = str(recommendation.get("reason", "") or "").strip()
        risk = str(recommendation.get("risk", "") or "").strip().lower()
        requires_approval = bool(recommendation.get("requires_approval", False))

        if not next_step or not risk:
            return self._recommendation_failure(
                reason="invalid_recommendation",
                message="Recommendation must include next_step and risk.",
            )

        try:
            if risk == "low" and not requires_approval:
                outcome = "approved"
            elif risk == "medium" and not requires_approval:
                outcome = "conditionally_approved"
            elif risk == "high" or requires_approval:
                outcome = "requires_approval"
            else:
                outcome = "needs_review"

            return {
                "status": "success",
                "decision": {
                    "outcome": outcome,
                    "next_step": next_step,
                    "reason": reason,
                    "risk": risk,
                    "requires_approval": requires_approval,
                },
                "message": "Planner recommendation evaluated.",
            }
        except Exception as exc:
            return self._recommendation_failure(
                reason="decision_error",
                message=f"Decision evaluation failed: {exc}",
            )

    def _decision(
        self,
        status: str,
        confidence: str,
        reason: str,
        blocking_factors: List[str],
        required_before_decision: List[str],
        instruction: str,
        next_workflow: str,
    ) -> Dict[str, Any]:
        return {
            "status": status,
            "confidence": confidence,
            "decision_owner": "Management",
            "decision_reason": reason,
            "blocking_factors": self._dedupe(blocking_factors),
            "required_before_decision": self._dedupe(required_before_decision),
            "executive_instruction": instruction,
            "next_workflow": next_workflow,
        }

    def _blocking_factors(
        self,
        reasoning: Dict[str, Any],
        clarification: Dict[str, Any],
        workflow_execution: Dict[str, Any],
        engine_outputs: Dict[str, Any],
        tasks: Dict[str, Any],
    ) -> List[str]:
        factors = []
        for item in reasoning.get("missing_information", []) or []:
            factors.append(self._fact_for_missing(item))

        if clarification.get("needed"):
            factors.append(self._clarification_fact(reasoning))

        if workflow_execution.get("additional_steps"):
            factors.append("Additional workflow step required before final decision")

        if self._critical_risk_exists(engine_outputs):
            factors.append("Critical risk remains unresolved")

        if tasks.get("critical", 0):
            factors.append(self._critical_task_factor(tasks))

        return [factor for factor in factors if factor]

    def _required_before_decision(
        self,
        reasoning: Dict[str, Any],
        clarification: Dict[str, Any],
        tasks: Dict[str, Any],
    ) -> List[str]:
        required = []

        for item in reasoning.get("missing_information", []) or []:
            required.append(self._requirement_for_missing(item))

        for task in tasks.get("items", []) or []:
            if task.get("priority") in {"Critical", "High"}:
                required.append(task.get("title", ""))

        return [item for item in required if item]

    def _blocked(
        self,
        reasoning: Dict[str, Any],
        clarification: Dict[str, Any],
        workflow_execution: Dict[str, Any],
        blocking_factors: List[str],
    ) -> bool:
        if reasoning.get("status") == "insufficient":
            return True
        if "Readable document text not available" in blocking_factors:
            return True
        if "Question or uploaded document not provided" in blocking_factors:
            return True
        if not workflow_execution.get("executed_workflow"):
            return True
        if clarification.get("needed") and reasoning.get("status") == "insufficient":
            return True
        return False

    def _conditional(
        self,
        reasoning: Dict[str, Any],
        clarification: Dict[str, Any],
        engine_outputs: Dict[str, Any],
        tasks: Dict[str, Any],
    ) -> bool:
        if reasoning.get("status") == "partial":
            return True
        if clarification.get("needed"):
            return True
        if self._critical_risk_exists(engine_outputs):
            return True
        if tasks.get("critical", 0) or tasks.get("high", 0):
            return True
        return False

    def _critical_risk_exists(self, engine_outputs: Dict[str, Any]) -> bool:
        risk_register = engine_outputs.get("risk_register", {})
        contract = engine_outputs.get("contract_intelligence", {})
        dashboard = engine_outputs.get("executive_dashboard", {})

        if str(risk_register.get("overall_risk_level", "")).lower() == "critical":
            return True
        if str(contract.get("overall_contract_risk", "")).lower() == "critical":
            return True
        if str(dashboard.get("executive_kpis", {}).get("risk_level", "")).lower() == "critical":
            return True

        for risk in risk_register.get("risks", []) or []:
            if str(risk.get("severity", "")).lower() == "critical":
                return True

        return False

    def _rejected_by_intelligence(self, engine_outputs: Dict[str, Any]) -> bool:
        texts = []
        dashboard = engine_outputs.get("executive_dashboard", {})
        report = engine_outputs.get("executive_report", {})
        opportunity = engine_outputs.get("opportunity_scoring", {})
        bid = engine_outputs.get("bid_no_bid", {})

        texts.extend(
            [
                dashboard.get("bid_posture"),
                dashboard.get("executive_verdict"),
                report.get("final_decision"),
                report.get("overall_verdict"),
                opportunity.get("bid_recommendation"),
                bid.get("recommendation"),
            ]
        )
        signal = " ".join(str(text or "") for text in texts).lower()
        return any(term in signal for term in ["no-bid", "no bid", "no-go", "no go", "do not proceed", "rejected"])

    def _confidence(self, reasoning: Dict[str, Any], blocking_factors: List[str]) -> str:
        if blocking_factors:
            return "Low" if reasoning.get("status") == "insufficient" else "Medium"
        return reasoning.get("confidence") or "Medium"

    def _blocked_reason(self, reasoning: Dict[str, Any], blocking_factors: List[str]) -> str:
        if reasoning.get("status") == "insufficient":
            return "Critical information is missing and ATHENA cannot support a reliable executive decision."
        if blocking_factors:
            return f"Decision is blocked by: {', '.join(blocking_factors[:3])}."
        return "Workflow could not produce enough intelligence to support a decision."

    def _conditional_reason(
        self,
        reasoning: Dict[str, Any],
        clarification: Dict[str, Any],
        engine_outputs: Dict[str, Any],
    ) -> str:
        if clarification.get("needed"):
            return "Clarification is required before management can make a final decision."
        if self._critical_risk_exists(engine_outputs):
            return "Critical risk exists, but the opportunity may remain viable after risk closure."
        if reasoning.get("status") == "partial":
            return "Information is incomplete, so only a conditional executive decision is supported."
        return "Open actions remain before final approval."

    def _fact_for_missing(self, item: str) -> str:
        mapping = {
            "Commercial value": "Contract value not confirmed",
            "Currency": "Currency not confirmed",
            "Customer or buyer": "Customer or buyer not confirmed",
            "Supplier": "Supplier not confirmed",
            "Submission deadline": "Submission deadline not confirmed",
            "Pricing basis": "Pricing basis not confirmed",
            "Readable document text": "Readable document text not available",
            "Question or uploaded document": "Question or uploaded document not provided",
            "Uploaded document": "Uploaded document not provided",
            "Document type": "Document type not confirmed",
            "Key contractual risk terms": "Key contractual risk terms not confirmed",
            "Specific executive question": "Specific executive question not confirmed",
        }
        return mapping.get(item, f"{item} not confirmed")

    def _clarification_fact(self, reasoning: Dict[str, Any]) -> str:
        missing = reasoning.get("missing_information", []) or []
        if "Commercial value" in missing or "Currency" in missing:
            return "Critical commercial information missing"
        if "Readable document text" in missing:
            return "Readable document text not available"
        if "Key contractual risk terms" in missing:
            return "Key contractual risk terms not confirmed"
        return "Critical decision information missing"

    def _critical_task_factor(self, tasks: Dict[str, Any]) -> str:
        titles = " ".join(
            task.get("title", "")
            for task in tasks.get("items", []) or []
            if task.get("priority") == "Critical"
        ).lower()

        if any(term in titles for term in ["commercial", "value", "currency", "pricing", "payment"]):
            return "Outstanding critical commercial tasks"
        if any(term in titles for term in ["risk", "penalty", "liability", "warranty", "contract"]):
            return "Outstanding critical risk actions"
        return "Outstanding critical management actions"

    def _requirement_for_missing(self, item: str) -> str:
        mapping = {
            "Commercial value": "Confirm contract value.",
            "Currency": "Confirm currency.",
            "Customer or buyer": "Confirm customer or buyer.",
            "Supplier": "Confirm supplier.",
            "Submission deadline": "Confirm submission deadline.",
            "Pricing basis": "Confirm pricing basis.",
            "Readable document text": "Provide readable document text.",
            "Document type": "Confirm document type.",
            "Key contractual risk terms": "Review key contractual risk terms.",
        }
        return mapping.get(item, f"Confirm {item.lower()}.")

    def _next_workflow(self, required: List[str], plan: Dict[str, Any]) -> str:
        signal = " ".join(required).lower()
        if any(term in signal for term in ["value", "currency", "pricing", "commercial"]):
            return "Commercial Review"
        if any(term in signal for term in ["contract", "warranty", "penalty", "liability"]):
            return "Contract Review"
        if any(term in signal for term in ["risk", "critical"]):
            return "Risk Review"
        if plan.get("intent"):
            return str(plan["intent"]).replace("_", " ").title()
        return "Management Review"

    def _dedupe(self, values: List[str]) -> List[str]:
        deduped = []
        for value in values:
            text = str(value or "").strip()
            if text and text not in deduped:
                deduped.append(text)
        return deduped

    def _recommendation_failure(self, reason: str, message: str) -> Dict[str, Any]:
        return {
            "status": "blocked",
            "reason": reason,
            "decision": {},
            "message": message,
        }
