from typing import Any, Dict, Optional


class AthenaPlanner:
    """
    ATHENA Planner

    Deterministically decides how ATHENA should answer before any intelligence
    engine executes. It does not answer questions or inspect engine outputs.
    """

    WORKFLOWS = {
        "executive_document_analysis": [
            "executive_dashboard",
            "executive_report",
        ],
        "contract_review": [
            "contract_intelligence",
            "executive_dashboard",
        ],
        "risk_review": [
            "risk_register",
            "executive_dashboard",
        ],
        "commercial_review": [
            "commercial_exposure",
            "executive_dashboard",
        ],
        "opportunity_assessment": [
            "opportunity_scoring",
            "bid_no_bid",
            "executive_dashboard",
        ],
        "scenario_analysis": [
            "executive_scenarios",
            "executive_dashboard",
        ],
        "report_generation": [
            "executive_report",
            "executive_dashboard",
        ],
        "question_answering": [
            "rag_answer",
        ],
    }

    def plan(
        self,
        question: Optional[str] = None,
        document_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        metadata = metadata or {}
        intent = self._detect_intent(question)
        workflow = list(self.WORKFLOWS[intent])

        return {
            "intent": intent,
            "reasoning": self._reasoning(intent, question, document_type),
            "requires_document": self._requires_document(intent, metadata),
            "requires_memory": intent == "question_answering",
            "requires_risk": intent in {"risk_review"},
            "requires_dashboard": "executive_dashboard" in workflow,
            "requires_report": "executive_report" in workflow,
            "workflow": workflow,
            "memory_used": intent == "question_answering",
            "engines_selected": len(workflow),
        }

    def public_plan(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "intent": plan.get("intent", ""),
            "reasoning": plan.get("reasoning", ""),
            "workflow": list(plan.get("workflow", [])),
            "memory_used": bool(plan.get("memory_used", False)),
            "engines_selected": len(plan.get("workflow", [])),
        }

    def _detect_intent(self, question: Optional[str]) -> str:
        signal = (question or "").lower()

        if not signal.strip():
            return "executive_document_analysis"

        if any(
            term in signal
            for term in [
                "contract",
                "legal",
                "terms",
                "obligation",
                "warranty",
                "penalty",
                "termination",
            ]
        ):
            return "contract_review"
        if any(
            term in signal
            for term in [
                "commercial",
                "price",
                "value",
                "payment",
                "currency",
                "margin",
                "cost",
            ]
        ):
            return "commercial_review"
        if any(
            term in signal
            for term in [
                "risk",
                "exposure",
                "liability",
                "critical",
                "danger",
            ]
        ):
            return "risk_review"
        if any(
            term in signal
            for term in [
                "opportunity",
                "score",
                "bid",
                "no-bid",
                "should we bid",
            ]
        ):
            return "opportunity_assessment"
        if any(
            term in signal
            for term in [
                "scenario",
                "option",
                "what if",
                "proceed",
                "delay",
                "no bid",
            ]
        ):
            return "scenario_analysis"
        if any(term in signal for term in ["report", "summary", "brief"]):
            return "report_generation"

        return "question_answering"

    def _reasoning(
        self,
        intent: str,
        question: Optional[str],
        document_type: Optional[str],
    ) -> str:
        if intent == "executive_document_analysis":
            label = document_type or "uploaded"
            return f"No specific question was provided, so ATHENA selected executive analysis for the {label} document."
        if intent == "contract_review":
            return "The request is asking about contractual terms, obligations, or clauses."
        if intent == "risk_review":
            return "The request is asking about risk, exposure, liability, or critical issues."
        if intent == "commercial_review":
            return "The request is asking about commercial value, payment, pricing, cost, or currency."
        if intent == "opportunity_assessment":
            return "The request is asking about opportunity scoring or bid posture."
        if intent == "scenario_analysis":
            return "The request is asking ATHENA to compare executive decision options."
        if intent == "report_generation":
            return "The request is asking for a report, summary, or executive brief."
        return "The request is a general knowledge question, so ATHENA selected question answering."

    def _requires_document(self, intent: str, metadata: Dict[str, Any]) -> bool:
        if intent == "question_answering":
            return bool(metadata.get("filename"))
        return True
