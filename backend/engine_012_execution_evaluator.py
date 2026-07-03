from typing import Any, Dict, List


def evaluate_execution(
    objective: str,
    selected_plan: str,
    execution_status: str,
    capabilities_executed: List[str],
    results: Dict[str, Any],
    executive_response: Dict[str, Any],
) -> Dict[str, Any]:
    failed_capabilities = _capabilities_by_status(results, "failed")
    skipped_capabilities = _capabilities_by_status(results, "skipped")
    unsupported_capabilities = _capabilities_by_status(results, "unsupported")

    action_plan = _result_payload(results, "executive_action_plan")
    decision_brief = _result_payload(results, "executive_decision_brief")
    risk_register = _result_payload(results, "risk_register")
    file_loop = _result_payload(results, "file_intelligence_loop")

    missing_information = _missing_information(decision_brief, action_plan, file_loop)
    key_findings = _key_findings(action_plan, decision_brief, risk_register, executive_response)
    approval_required = _approval_required(
        action_plan=action_plan,
        risk_register=risk_register,
        file_loop=file_loop,
        executive_response=executive_response,
    )
    decision_ready = _decision_ready(
        execution_status=execution_status,
        failed_capabilities=failed_capabilities,
        unsupported_capabilities=unsupported_capabilities,
        action_plan=action_plan,
        decision_brief=decision_brief,
        risk_register=risk_register,
        missing_information=missing_information,
    )
    confidence = _confidence(
        execution_status=execution_status,
        failed_capabilities=failed_capabilities,
        skipped_capabilities=skipped_capabilities,
        unsupported_capabilities=unsupported_capabilities,
        action_plan=action_plan,
        decision_brief=decision_brief,
        risk_register=risk_register,
        missing_information=missing_information,
        capabilities_executed=capabilities_executed,
    )
    completion_quality = _completion_quality(
        confidence=confidence,
        risk_register=risk_register,
        failed_capabilities=failed_capabilities,
        skipped_capabilities=skipped_capabilities,
        unsupported_capabilities=unsupported_capabilities,
    )
    objective_satisfied = _objective_satisfied(
        execution_status=execution_status,
        selected_plan=selected_plan,
        action_plan=action_plan,
        file_loop=file_loop,
        failed_capabilities=failed_capabilities,
        unsupported_capabilities=unsupported_capabilities,
        confidence=confidence,
    )
    recommended_next_action = _recommended_next_action(
        decision_ready=decision_ready,
        approval_required=approval_required,
        action_plan=action_plan,
        decision_brief=decision_brief,
        executive_response=executive_response,
        missing_information=missing_information,
        failed_capabilities=failed_capabilities,
        skipped_capabilities=skipped_capabilities,
        unsupported_capabilities=unsupported_capabilities,
    )

    return {
        "evaluation_status": "completed",
        "objective_satisfied": objective_satisfied,
        "decision_ready": decision_ready,
        "confidence": confidence,
        "approval_required": approval_required,
        "completion_quality": completion_quality,
        "failed_capabilities": failed_capabilities,
        "skipped_capabilities": skipped_capabilities,
        "unsupported_capabilities": unsupported_capabilities,
        "missing_information": missing_information,
        "key_findings": key_findings,
        "recommended_next_action": recommended_next_action,
        "evaluation_summary": _evaluation_summary(
            objective=objective,
            objective_satisfied=objective_satisfied,
            decision_ready=decision_ready,
            confidence=confidence,
            approval_required=approval_required,
            missing_information=missing_information,
            failed_capabilities=failed_capabilities,
            skipped_capabilities=skipped_capabilities,
            unsupported_capabilities=unsupported_capabilities,
        ),
    }


def _capabilities_by_status(results: Dict[str, Any], status: str) -> List[str]:
    capabilities = []
    for key, item in (results or {}).items():
        if not isinstance(item, dict):
            continue
        if item.get("status") == status:
            capabilities.append(str(item.get("capability") or key))
    return capabilities


def _result_payload(results: Dict[str, Any], capability: str) -> Dict[str, Any]:
    item = (results or {}).get(capability, {})
    payload = item.get("result", {}) if isinstance(item, dict) else {}
    return payload if isinstance(payload, dict) else {}


def _missing_information(
    decision_brief: Dict[str, Any],
    action_plan: Dict[str, Any],
    file_loop: Dict[str, Any],
) -> List[str]:
    values = []
    values.extend(_as_list(decision_brief.get("missing_information")))
    values.extend(_as_list(decision_brief.get("key_risks")))
    values.extend(_as_list(action_plan.get("missing_information")))
    required_before_decision = file_loop.get("decision", {}).get("required_before_decision")
    values.extend(_as_list(required_before_decision))
    return _dedupe(values)


def _key_findings(
    action_plan: Dict[str, Any],
    decision_brief: Dict[str, Any],
    risk_register: Dict[str, Any],
    executive_response: Dict[str, Any],
) -> List[str]:
    findings = []
    for value in [
        action_plan.get("overall_status"),
        action_plan.get("priority"),
        decision_brief.get("recommendation"),
        risk_register.get("overall_risk_level"),
        executive_response.get("summary"),
    ]:
        text = str(value or "").strip()
        if text:
            findings.append(text)

    risks = risk_register.get("risks", []) or []
    for risk in risks[:3]:
        if isinstance(risk, dict):
            findings.append(str(risk.get("description") or risk.get("title") or "").strip())

    return _dedupe(findings)


def _approval_required(
    action_plan: Dict[str, Any],
    risk_register: Dict[str, Any],
    file_loop: Dict[str, Any],
    executive_response: Dict[str, Any],
) -> bool:
    if bool(executive_response.get("requires_approval", False)):
        return True
    if bool(file_loop.get("decision", {}).get("requires_approval", False)):
        return True
    if _risk_level(risk_register) == "critical":
        return True
    return any(
        bool(action.get("requires_approval", False))
        for action in action_plan.get("actions", []) or []
        if isinstance(action, dict)
    )


def _decision_ready(
    execution_status: str,
    failed_capabilities: List[str],
    unsupported_capabilities: List[str],
    action_plan: Dict[str, Any],
    decision_brief: Dict[str, Any],
    risk_register: Dict[str, Any],
    missing_information: List[str],
) -> bool:
    if execution_status != "completed":
        return False
    if failed_capabilities or unsupported_capabilities:
        return False
    if missing_information:
        return False
    if _risk_level(risk_register) == "critical":
        return False
    if _estimated_readiness(action_plan) < 70:
        return False
    if str(action_plan.get("overall_status", "")).strip().lower() == "needs review":
        return False
    if decision_brief.get("missing_information"):
        return False
    return True


def _confidence(
    execution_status: str,
    failed_capabilities: List[str],
    skipped_capabilities: List[str],
    unsupported_capabilities: List[str],
    action_plan: Dict[str, Any],
    decision_brief: Dict[str, Any],
    risk_register: Dict[str, Any],
    missing_information: List[str],
    capabilities_executed: List[str],
) -> int:
    confidence = 85

    if execution_status != "completed":
        confidence = min(confidence, 40)
    confidence -= len(failed_capabilities) * 20
    confidence -= len(unsupported_capabilities) * 15
    confidence -= len(skipped_capabilities) * 10
    confidence -= min(len(missing_information) * 5, 25)

    readiness = _estimated_readiness(action_plan)
    if readiness:
        confidence = int((confidence + readiness) / 2)
    if _risk_level(risk_register) == "critical":
        confidence = min(confidence, 65)
    if str(action_plan.get("overall_status", "")).strip().lower() == "needs review":
        confidence = min(confidence, 65)
    if decision_brief.get("missing_information"):
        confidence = min(confidence, 60)
    if not capabilities_executed:
        confidence = min(confidence, 35)

    return max(0, min(100, int(confidence)))


def _completion_quality(
    confidence: int,
    risk_register: Dict[str, Any],
    failed_capabilities: List[str],
    skipped_capabilities: List[str],
    unsupported_capabilities: List[str],
) -> str:
    if failed_capabilities or unsupported_capabilities or confidence < 50:
        return "low"
    if skipped_capabilities or confidence < 75 or _risk_level(risk_register) == "critical":
        return "medium"
    return "high"


def _objective_satisfied(
    execution_status: str,
    selected_plan: str,
    action_plan: Dict[str, Any],
    file_loop: Dict[str, Any],
    failed_capabilities: List[str],
    unsupported_capabilities: List[str],
    confidence: int,
) -> bool:
    if execution_status != "completed" or failed_capabilities or unsupported_capabilities:
        return False
    if selected_plan == "document_intelligence_plan":
        return bool(action_plan) and confidence >= 50
    if selected_plan == "file_intelligence_plan":
        return bool(file_loop) and confidence >= 50
    return confidence >= 60


def _recommended_next_action(
    decision_ready: bool,
    approval_required: bool,
    action_plan: Dict[str, Any],
    decision_brief: Dict[str, Any],
    executive_response: Dict[str, Any],
    missing_information: List[str],
    failed_capabilities: List[str],
    skipped_capabilities: List[str],
    unsupported_capabilities: List[str],
) -> str:
    if failed_capabilities or unsupported_capabilities:
        return "Review failed or unsupported capabilities before relying on the execution result."
    if skipped_capabilities:
        return "Review skipped capabilities and rerun after required inputs are available."
    if missing_information:
        return f"Resolve missing information: {missing_information[0]}."
    if decision_ready and approval_required:
        return "Proceed to executive approval review."
    if decision_ready:
        return "Proceed with the recommended executive action plan."

    actions = action_plan.get("actions", []) or []
    if actions and isinstance(actions[0], dict):
        return _first_text(actions[0].get("action"), actions[0].get("title"), actions[0].get("description"))

    required_actions = decision_brief.get("required_actions", []) or []
    if required_actions:
        return str(required_actions[0])

    return _first_text(
        executive_response.get("recommended_next_action"),
        "Review the execution results and close open issues before decision.",
    )


def _evaluation_summary(
    objective: str,
    objective_satisfied: bool,
    decision_ready: bool,
    confidence: int,
    approval_required: bool,
    missing_information: List[str],
    failed_capabilities: List[str],
    skipped_capabilities: List[str],
    unsupported_capabilities: List[str],
) -> str:
    if failed_capabilities or unsupported_capabilities:
        return "Execution completed with capability issues, so ATHENA cannot fully satisfy the objective yet."
    if skipped_capabilities:
        return "Execution completed with skipped capabilities, so the objective is only partially evaluated."
    if missing_information:
        return "Execution completed, but missing information prevents a decision-ready executive outcome."
    if objective_satisfied and decision_ready:
        if approval_required:
            return "Execution satisfied the objective and is ready for executive approval."
        return "Execution satisfied the objective and is decision-ready."
    if objective_satisfied:
        return "Execution produced the requested executive output, but a final decision is not ready."
    return f"Execution evaluated the objective but confidence is limited at {confidence}."


def _estimated_readiness(action_plan: Dict[str, Any]) -> int:
    return _safe_int(action_plan.get("estimated_readiness"), default=0)


def _risk_level(risk_register: Dict[str, Any]) -> str:
    return str(risk_register.get("overall_risk_level", "") or "").strip().lower()


def _as_list(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item or "").strip()]
    if str(value or "").strip():
        return [str(value).strip()]
    return []


def _dedupe(values: List[str]) -> List[str]:
    deduped = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in deduped:
            deduped.append(text)
    return deduped


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _first_text(*values: Any) -> str:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return ""
