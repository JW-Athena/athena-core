from typing import Any, Dict, List

from engine_013_learning_engine import execution_learning_engine
from engine_014_adaptive_planner import adaptive_summary
from engine_015_mission_controller import mission_controller
from engine_018_operations_center import operations_center
from engine_019_strategic_objective_manager import strategic_objective_manager
from engine_020_organization_model import organization_model
from engine_021_organization_impact import organization_impact_analysis
from engine_022_knowledge_graph import executive_knowledge_graph
from engine_023_reasoning_graph import executive_reasoning_graph
from event_bus import event_bus


class ExecutiveReasoningEngine:
    def reason(self, question: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        clean_question = str(question or "").strip()
        if not clean_question:
            return self._failure("question_required", "Executive question is required.")

        safe_context = context if isinstance(context, dict) else {}
        domain = self._reasoning_domain(clean_question)

        event_bus.publish(
            "ExecutiveReasoningStarted",
            "executive_reasoning_engine",
            {
                "question": clean_question,
                "reasoning_domain": domain,
                "result": "started",
            },
        )

        evidence = self._collect_evidence(clean_question, domain, safe_context)
        key_findings = self._key_findings(clean_question, domain, evidence)
        recommendation = self._executive_recommendation(domain, evidence, key_findings)
        explanation = self._executive_explanation(domain, evidence, key_findings)
        confidence = self._confidence(evidence, key_findings)
        next_action = self._recommended_next_action(domain, evidence, key_findings)
        attention = self._requires_executive_attention(domain, evidence, key_findings)

        result = self._success({
            "question": clean_question,
            "reasoning_domain": domain,
            "evidence": evidence,
            "key_findings": key_findings,
            "executive_recommendation": recommendation,
            "executive_explanation": explanation,
            "confidence": confidence,
            "recommended_next_action": next_action,
            "requires_executive_attention": attention,
        })

        event_bus.publish(
            "ExecutiveReasoningCompleted",
            "executive_reasoning_engine",
            {
                "question": clean_question,
                "reasoning_domain": domain,
                "confidence": confidence,
                "requires_executive_attention": attention,
                "result": "success",
            },
        )
        return result

    def _reasoning_domain(self, question: str) -> str:
        normalized = question.lower()
        if any(term in normalized for term in ["bid", "tender", "rfp", "proposal"]):
            return "bid_decision"
        if "supplier" in normalized or "vendor" in normalized:
            return "supplier_review"
        if "contract" in normalized or "agreement" in normalized:
            return "contract_review"
        if any(term in normalized for term in ["organization", "department", "impact", "affect"]):
            return "organization_impact"
        return "general_executive_question"

    def _collect_evidence(
        self,
        question: str,
        domain: str,
        context: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        evidence = []
        organization = organization_model.organization_summary()
        impact = organization_impact_analysis.analyze(question, context=context)
        learning = execution_learning_engine.find_similar_patterns(question)
        objectives = strategic_objective_manager.list_strategic_objectives()
        missions = mission_controller.list_mission_records()
        graph_nodes = executive_knowledge_graph.list_nodes()
        graph_relationships = executive_knowledge_graph.list_relationships()
        operations = operations_center.overview()
        adaptive = adaptive_summary()

        evidence.append(self._evidence(
            source="organization_model",
            summary=f"Organization model contains {organization.get('statistics', {}).get('departments', 0)} departments, {organization.get('statistics', {}).get('suppliers', 0)} suppliers, and {organization.get('statistics', {}).get('strategic_objectives', 0)} strategic objectives.",
            data={
                "statistics": organization.get("statistics", {}),
                "departments": [item.get("name", "") for item in organization.get("departments", [])],
                "suppliers": [item.get("name", "") for item in organization.get("suppliers", [])],
            },
        ))
        evidence.append(self._evidence(
            source="organization_impact_analysis",
            summary=impact.get("impact_summary", "Organization impact could not be determined."),
            data={
                "impact_level": impact.get("impact_level", ""),
                "impacted_departments": impact.get("impacted_departments", []),
                "impacted_suppliers": impact.get("impacted_suppliers", []),
                "requires_management_attention": impact.get("requires_management_attention", False),
            },
        ))
        evidence.append(self._evidence(
            source="strategic_objective_manager",
            summary=f"{objectives.get('count', 0)} strategic objective(s) are currently available for alignment.",
            data={
                "count": objectives.get("count", 0),
                "active_objectives": [
                    item
                    for item in objectives.get("strategic_objectives", [])
                    if item.get("status") == "active"
                ],
            },
        ))
        evidence.append(self._evidence(
            source="execution_learning_engine",
            summary=f"{learning.get('count', 0)} similar prior execution pattern(s) found.",
            data={
                "count": learning.get("count", 0),
                "records": learning.get("records", [])[:5],
            },
        ))
        evidence.append(self._evidence(
            source="adaptive_planner",
            summary=f"Adaptive planning has {adaptive.get('total_learning_records', 0)} learning record(s) and average success rate {adaptive.get('average_success_rate', 0)}.",
            data=adaptive,
        ))
        evidence.append(self._evidence(
            source="mission_controller",
            summary=f"{len(missions)} mission record(s) are available from prior executive execution.",
            data={
                "count": len(missions),
                "recent_missions": missions[-5:],
            },
        ))
        evidence.append(self._evidence(
            source="executive_knowledge_graph",
            summary=f"Knowledge graph contains {graph_nodes.get('count', 0)} node(s) and {graph_relationships.get('count', 0)} relationship(s).",
            data={
                "nodes": graph_nodes.get("count", 0),
                "relationships": graph_relationships.get("count", 0),
            },
        ))
        evidence.append(self._evidence(
            source="operations_center",
            summary=f"Operations status is {operations.get('system_status', 'unknown')}.",
            data={
                "system_status": operations.get("system_status", ""),
                "approvals": operations.get("approvals", {}),
                "timeline": operations.get("timeline", {}),
            },
        ))

        reasoning_subject = self._reasoning_subject(question, context)
        if reasoning_subject:
            reasoning = executive_reasoning_graph.find_business_impact(reasoning_subject)
            if reasoning.get("status") == "success":
                evidence.append(self._evidence(
                    source="executive_reasoning_graph",
                    summary=reasoning.get("executive_explanation", ""),
                    data={
                        "starting_node": reasoning.get("starting_node", ""),
                        "reasoning_chain": reasoning.get("reasoning_chain", []),
                    },
                ))

        return self._domain_evidence(domain, evidence)

    def _domain_evidence(self, domain: str, evidence: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        preferred_sources = {
            "bid_decision": {
                "organization_impact_analysis",
                "strategic_objective_manager",
                "execution_learning_engine",
                "adaptive_planner",
                "executive_knowledge_graph",
                "executive_reasoning_graph",
                "operations_center",
            },
            "supplier_review": {
                "organization_model",
                "organization_impact_analysis",
                "execution_learning_engine",
                "executive_knowledge_graph",
                "executive_reasoning_graph",
                "operations_center",
            },
            "contract_review": {
                "organization_impact_analysis",
                "strategic_objective_manager",
                "execution_learning_engine",
                "executive_knowledge_graph",
                "operations_center",
            },
            "organization_impact": {
                "organization_model",
                "organization_impact_analysis",
                "strategic_objective_manager",
                "mission_controller",
                "operations_center",
            },
        }
        sources = preferred_sources.get(domain)
        if not sources:
            return evidence
        return [item for item in evidence if item.get("source") in sources]

    def _key_findings(
        self,
        question: str,
        domain: str,
        evidence: List[Dict[str, Any]],
    ) -> List[str]:
        findings = []
        evidence_by_source = {item.get("source"): item for item in evidence}
        impact_data = evidence_by_source.get("organization_impact_analysis", {}).get("data", {})
        learning_data = evidence_by_source.get("execution_learning_engine", {}).get("data", {})
        objectives_data = evidence_by_source.get("strategic_objective_manager", {}).get("data", {})
        operations_data = evidence_by_source.get("operations_center", {}).get("data", {})
        knowledge_data = evidence_by_source.get("executive_knowledge_graph", {}).get("data", {})

        impact_level = impact_data.get("impact_level", "")
        departments = impact_data.get("impacted_departments", [])
        if impact_level:
            findings.append(f"Organizational impact is {impact_level}.")
        if departments:
            findings.append(f"Impacted departments: {self._human_join(departments)}.")

        active_objectives = objectives_data.get("active_objectives", [])
        if active_objectives:
            findings.append(f"{len(active_objectives)} active strategic objective(s) may require alignment.")
        elif domain in {"bid_decision", "contract_review"}:
            findings.append("No active strategic objective was found for explicit alignment.")

        if learning_data.get("count", 0):
            findings.append(f"{learning_data.get('count')} similar learning record(s) are available.")
        else:
            findings.append("No similar execution learning was found.")

        approvals = operations_data.get("approvals", {})
        if approvals.get("pending", 0):
            findings.append(f"{approvals.get('pending')} pending approval(s) may affect execution readiness.")

        if knowledge_data.get("relationships", 0):
            findings.append("Knowledge graph relationships are available for business context.")
        else:
            findings.append("Knowledge graph relationships are limited; ATHENA cannot infer all dependencies.")

        if domain == "bid_decision" and "tender" not in question.lower() and "bid" not in question.lower():
            findings.append("The question was classified as a bid decision, but tender evidence is not explicit.")

        return self._unique(findings)

    def _executive_recommendation(
        self,
        domain: str,
        evidence: List[Dict[str, Any]],
        findings: List[str],
    ) -> str:
        impact = self._source_data(evidence, "organization_impact_analysis")
        impact_level = impact.get("impact_level", "")
        missing_learning = any("No similar execution learning" in item for item in findings)
        limited_graph = any("Knowledge graph relationships are limited" in item for item in findings)

        if domain == "bid_decision":
            if impact_level in {"critical", "high"} and (missing_learning or limited_graph):
                return "Do not approve the bid decision yet. Proceed to clarification and evidence completion before commitment."
            if impact_level in {"critical", "high"}:
                return "Proceed cautiously with bid evaluation, subject to executive review of risk, pricing, and delivery obligations."
            return "Proceed with bid assessment and prepare a concise executive decision brief."

        if domain == "supplier_review":
            if impact_level in {"critical", "high"}:
                return "Escalate supplier review before committing operational or commercial dependency."
            return "Continue supplier review and validate operational continuity, commercial exposure, and replacement options."

        if domain == "contract_review":
            if impact_level in {"critical", "high"}:
                return "Do not approve the contract until legal, financial, and management obligations are confirmed."
            return "Proceed with contract review and confirm commercial terms before approval."

        if domain == "organization_impact":
            return "Treat this as an organizational coordination question and align impacted departments before execution."

        return "Proceed with an executive discovery mission to clarify objective, risks, required decisions, and next action."

    def _executive_explanation(
        self,
        domain: str,
        evidence: List[Dict[str, Any]],
        findings: List[str],
    ) -> str:
        if not findings:
            return "ATHENA does not have enough evidence to produce a reliable executive explanation."

        domain_text = domain.replace("_", " ")
        return (
            f"ATHENA classified this as {domain_text} and evaluated available evidence from the Executive Brain. "
            f"The decision is based on: {self._human_join(findings[:3])}"
        )

    def _recommended_next_action(
        self,
        domain: str,
        evidence: List[Dict[str, Any]],
        findings: List[str],
    ) -> str:
        if any("No active strategic objective" in item for item in findings):
            return "Create or select the strategic objective this decision should support."
        if any("Knowledge graph relationships are limited" in item for item in findings):
            return "Map the key supplier, product, tender, and strategic objective relationships before approval."
        if any("No similar execution learning" in item for item in findings):
            return "Run a focused mission to collect missing evidence and establish a decision baseline."

        if domain == "bid_decision":
            return "Prepare the executive bid brief covering pricing, compliance, delivery obligations, and approval blockers."
        if domain == "supplier_review":
            return "Request supplier risk, continuity, and replacement-option evidence."
        if domain == "contract_review":
            return "Request legal, financial, and commercial obligation review."
        return "Run an executive discovery mission and return one recommendation."

    def _confidence(self, evidence: List[Dict[str, Any]], findings: List[str]) -> int:
        score = 45
        source_count = len([item for item in evidence if item.get("summary")])
        score += min(source_count * 5, 30)
        if any("similar learning record" in item for item in findings):
            score += 10
        if any("Knowledge graph relationships are available" in item for item in findings):
            score += 10
        if any("No similar execution learning" in item for item in findings):
            score -= 10
        if any("relationships are limited" in item for item in findings):
            score -= 10
        if any("No active strategic objective" in item for item in findings):
            score -= 5
        return max(0, min(score, 100))

    def _requires_executive_attention(
        self,
        domain: str,
        evidence: List[Dict[str, Any]],
        findings: List[str],
    ) -> bool:
        impact = self._source_data(evidence, "organization_impact_analysis")
        if impact.get("requires_management_attention"):
            return True
        if domain in {"bid_decision", "contract_review"}:
            return True
        return any("pending approval" in item.lower() for item in findings)

    def _reasoning_subject(self, question: str, context: Dict[str, Any]) -> str:
        explicit = str(context.get("node_id", "") or context.get("entity", "") or "").strip()
        if explicit:
            return explicit

        words = [
            word.strip(".,:;!?()[]{}")
            for word in question.split()
            if word.strip(".,:;!?()[]{}")
        ]
        for word in words:
            if len(word) > 2 and word[:1].isupper():
                return word
        return ""

    def _source_data(self, evidence: List[Dict[str, Any]], source: str) -> Dict[str, Any]:
        for item in evidence:
            if item.get("source") == source:
                return item.get("data", {}) or {}
        return {}

    def _evidence(self, source: str, summary: str, data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "source": source,
            "summary": summary,
            "data": data,
        }

    def _human_join(self, values: List[Any]) -> str:
        clean_values = [str(value or "").strip() for value in values if str(value or "").strip()]
        if not clean_values:
            return ""
        if len(clean_values) == 1:
            return clean_values[0]
        if len(clean_values) == 2:
            return f"{clean_values[0]} and {clean_values[1]}"
        return f"{', '.join(clean_values[:-1])}, and {clean_values[-1]}"

    def _unique(self, values: List[str]) -> List[str]:
        seen = set()
        unique_values = []
        for value in values:
            clean_value = str(value or "").strip()
            key = clean_value.lower()
            if clean_value and key not in seen:
                unique_values.append(clean_value)
                seen.add(key)
        return unique_values

    def _success(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "engine": "executive_reasoning_engine",
            "status": "success",
            **payload,
        }

    def _failure(self, reason: str, message: str) -> Dict[str, Any]:
        return {
            "engine": "executive_reasoning_engine",
            "status": "failed",
            "reason": reason,
            "message": message,
        }


executive_reasoning_engine = ExecutiveReasoningEngine()
