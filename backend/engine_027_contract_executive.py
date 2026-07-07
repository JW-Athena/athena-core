from pathlib import Path
from typing import Any, Dict, List, Optional

from contract_intelligence_engine import ContractIntelligenceEngine
from engine_021_organization_impact import organization_impact_analysis
from engine_024_executive_reasoning_engine import executive_reasoning_engine
from event_bus import event_bus
from reader import AthenaReader
from timing_utils import new_request_context


class ContractExecutive:
    def __init__(self):
        self.reader = AthenaReader()
        self.contract_engine = ContractIntelligenceEngine()

    def evaluate_contract(self, question: str, path: str = "") -> Dict[str, Any]:
        clean_question = str(question or "").strip()
        clean_path = str(path or "").strip()
        if not clean_question:
            return self._failure("question_required", "Contract executive question is required.")

        event_bus.publish(
            "ContractExecutiveStarted",
            "contract_executive",
            {"question": clean_question, "path": clean_path, "result": "started"},
        )

        try:
            contract_result = {}
            if clean_path:
                text = self._read_document(clean_path)
                contract_result = self.contract_engine.analyze(
                    text=text,
                    document_type="Contract",
                    request_context=new_request_context(),
                )

            organization_impact = organization_impact_analysis.analyze(
                mission=clean_question,
                context={"path": clean_path, "document_type": "Contract"},
            )
            executive_reasoning = executive_reasoning_engine.reason(
                clean_question,
                context={"path": clean_path, "document_type": "Contract"},
            )

            result = self._assemble_response(
                question=clean_question,
                path=clean_path,
                contract_result=contract_result,
                organization_impact=organization_impact,
                executive_reasoning=executive_reasoning,
            )
            event_bus.publish(
                "ContractExecutiveCompleted",
                "contract_executive",
                {
                    "question": clean_question,
                    "path": clean_path,
                    "contract_decision": result.get("contract_decision", ""),
                    "confidence": result.get("confidence", 0),
                    "result": "success",
                },
            )
            return result
        except Exception as exc:
            event_bus.publish(
                "ContractExecutiveCompleted",
                "contract_executive",
                {"question": clean_question, "path": clean_path, "reason": "contract_executive_error", "result": "failed"},
            )
            return self._failure("contract_executive_error", f"Contract executive assessment failed: {exc}")

    def _assemble_response(
        self,
        question: str,
        path: str,
        contract_result: Dict[str, Any],
        organization_impact: Dict[str, Any],
        executive_reasoning: Dict[str, Any],
    ) -> Dict[str, Any]:
        contract = contract_result.get("contract_intelligence", {}) if contract_result else {}
        risk_level = self._risk_level(contract, organization_impact)
        missing_information = self._unique_text(
            contract.get("missing_contract_information", []),
            [] if path else ["Contract document path was not provided."],
        )
        key_risks = self._key_risks(contract, organization_impact)
        contract_decision = self._contract_decision(risk_level, missing_information, key_risks)
        recommended_actions = self._recommended_actions(contract, contract_decision, missing_information, key_risks)
        executive_reasoning_text = self._executive_reasoning(contract_decision, key_risks, missing_information, executive_reasoning)

        return {
            "engine": "contract_executive",
            "status": "success",
            "executive_summary": self._executive_summary(contract, contract_decision, risk_level, key_risks, missing_information),
            "contract_decision": contract_decision,
            "confidence": self._confidence(contract, executive_reasoning, missing_information),
            "risk_level": risk_level,
            "key_risks": key_risks,
            "missing_information": missing_information,
            "recommended_actions": recommended_actions,
            "executive_reasoning": executive_reasoning_text,
        }

    def _read_document(self, path: str) -> str:
        document_path = Path(path)
        if document_path.suffix.lower() in {".txt", ".md", ".csv"}:
            return document_path.read_text(encoding="utf-8", errors="ignore")
        return self.reader.read(path)

    def _contract_decision(self, risk_level: str, missing_information: List[str], key_risks: List[str]) -> str:
        risk = risk_level.lower()
        if risk == "critical":
            return "Reject"
        if risk == "high" or len(missing_information) >= 3:
            return "Review"
        if missing_information or key_risks:
            return "Review"
        return "Approve"

    def _risk_level(self, contract: Dict[str, Any], organization_impact: Dict[str, Any]) -> str:
        contract_risk = str(contract.get("overall_contract_risk") or "").strip().title()
        impact = str(organization_impact.get("impact_level") or "").strip().title()
        for level in ["Critical", "High", "Medium", "Low"]:
            if contract_risk == level or impact == level:
                return level
        return contract_risk or "Medium"

    def _key_risks(self, contract: Dict[str, Any], organization_impact: Dict[str, Any]) -> List[str]:
        clauses = [
            clause.get("summary") or clause.get("clause_type")
            for clause in contract.get("critical_clauses", [])
            if clause.get("summary") or clause.get("clause_type")
        ]
        risks = self._unique_text(
            clauses,
            [organization_impact.get("impact_summary", "")] if organization_impact.get("requires_management_attention") else [],
        )
        return risks[:6]

    def _recommended_actions(
        self,
        contract: Dict[str, Any],
        decision: str,
        missing_information: List[str],
        key_risks: List[str],
    ) -> List[str]:
        actions = self._unique_text(contract.get("recommended_actions", []))
        if missing_information:
            actions.append(f"Close information gap: {missing_information[0]}")
        if key_risks:
            actions.append(f"Assign owner to resolve risk: {key_risks[0]}")
        if decision == "Approve":
            actions.append("Proceed to management approval with legal and commercial record attached.")
        return self._unique_text(actions)[:6]

    def _executive_summary(
        self,
        contract: Dict[str, Any],
        decision: str,
        risk_level: str,
        key_risks: List[str],
        missing_information: List[str],
    ) -> str:
        source_summary = contract.get("contract_summary") or "ATHENA completed the contract executive review from available evidence."
        reason = key_risks[0] if key_risks else missing_information[0] if missing_information else "no material blocker is visible in current evidence"
        return f"{source_summary} Recommendation is {decision}. Risk level is {risk_level}. Primary reason: {reason}"

    def _executive_reasoning(
        self,
        decision: str,
        key_risks: List[str],
        missing_information: List[str],
        executive_reasoning: Dict[str, Any],
    ) -> str:
        reason = key_risks[0] if key_risks else missing_information[0] if missing_information else executive_reasoning.get("executive_explanation", "")
        return f"ATHENA recommends {decision} because {str(reason or 'the current contract evidence supports this position').rstrip('.')}."

    def _confidence(self, contract: Dict[str, Any], executive_reasoning: Dict[str, Any], missing_information: List[str]) -> int:
        label = str(contract.get("confidence") or "").lower()
        base = {"high": 82, "medium": 65, "low": 45}.get(label, self._safe_int(executive_reasoning.get("confidence")) or 55)
        return max(0, min(base - min(len(missing_information) * 4, 25), 100))

    def _safe_int(self, value: Any) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    def _unique_text(self, *groups: Any) -> List[str]:
        values = []
        seen = set()
        for group in groups:
            items = group if isinstance(group, list) else [group]
            for item in items:
                text = str(item or "").strip()
                key = text.lower()
                if text and key not in seen:
                    values.append(text)
                    seen.add(key)
        return values

    def _failure(self, reason: str, message: str) -> Dict[str, Any]:
        return {"engine": "contract_executive", "status": "failed", "reason": reason, "message": message}


contract_executive = ContractExecutive()


def evaluate_contract(question: str, path: str = "") -> Dict[str, Any]:
    return contract_executive.evaluate_contract(question=question, path=path)
