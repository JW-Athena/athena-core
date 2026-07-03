from typing import Any, Dict

from fastapi import APIRouter, Body

from athena_memory_agent import AthenaMemoryAgent
from athena_reasoning_agent import AthenaReasoningAgent
from athena_workflow_agent import AthenaWorkflowAgent
from capability_004_executive_extraction import ExecutiveInformationExtractor
from capability_005_obligation_extraction import ObligationExtractor
from desktop_agent import desktop_agent
from event_bus import event_bus
from executive_action_plan_engine import ExecutiveActionPlanEngine
from executive_decision_brief_engine import ExecutiveDecisionBriefEngine
from risk_register_engine import RiskRegisterEngine
from timing_utils import new_request_context


router = APIRouter(tags=["ATHENA Executive OS"])

workflow_agent = AthenaWorkflowAgent()
reasoning_agent = AthenaReasoningAgent()
memory_agent = AthenaMemoryAgent()
executive_extractor = ExecutiveInformationExtractor()
obligation_extractor = ObligationExtractor()
risk_register_engine = RiskRegisterEngine()
decision_brief_engine = ExecutiveDecisionBriefEngine()
action_plan_engine = ExecutiveActionPlanEngine()


@router.post("/athena/executive/document-intelligence-loop")
async def document_intelligence_loop(payload: Dict[str, Any] = Body(default_factory=dict)):
    path = str(payload.get("path", "") or "")
    document_type = str(payload.get("document_type", "") or "") or None
    steps_completed = []
    request_context = new_request_context()

    file_result = workflow_agent.file_understanding_with_memory(
        desktop_agent=desktop_agent,
        reasoning_agent=reasoning_agent,
        memory_agent=memory_agent,
        path=path,
    )
    if file_result.get("status") != "success":
        return _failed_response(
            failed_step="file_understanding_with_memory",
            reason=file_result.get("reason", "workflow_error"),
            message=file_result.get("message", "File understanding with memory failed."),
            steps_completed=steps_completed,
        )
    steps_completed.append("file_understanding_with_memory")
    workflow = file_result.get("workflow", {})
    file_data = workflow.get("file", {})

    read_result = desktop_agent.read_file(path)
    if read_result.get("status") != "success":
        return _failed_response(
            failed_step="executive_extraction",
            reason=read_result.get("reason", "read_error"),
            message=read_result.get("message", "Safe file read failed before executive extraction."),
            steps_completed=steps_completed,
            file_data=file_data,
        )
    text = read_result.get("file", {}).get("content", "")

    extraction_result = _run_engine_step(
        failed_step="executive_extraction",
        callback=lambda: executive_extractor.extract(
            text=text,
            document_type=document_type,
        ),
        steps_completed=steps_completed,
        file_data=file_data,
    )
    if extraction_result.get("status") == "failed":
        return extraction_result
    extraction = extraction_result["result"]
    request_context["cache"]["executive_information.extract"] = extraction
    steps_completed.append("executive_extraction")

    obligation_result = _run_engine_step(
        failed_step="obligation_extraction",
        callback=lambda: obligation_extractor.extract(
            text=text,
            document_type=document_type,
        ),
        steps_completed=steps_completed,
        file_data=file_data,
        extraction=extraction,
    )
    if obligation_result.get("status") == "failed":
        return obligation_result
    obligations = obligation_result["result"]
    request_context["cache"]["obligation_extraction.extract"] = obligations
    steps_completed.append("obligation_extraction")

    risk_result = _run_engine_step(
        failed_step="risk_register",
        callback=lambda: risk_register_engine.generate(
            text=text,
            document_type=document_type,
            request_context=request_context,
        ),
        steps_completed=steps_completed,
        file_data=file_data,
        extraction=extraction,
        obligations=obligations,
    )
    if risk_result.get("status") == "failed":
        return risk_result
    risks = risk_result["result"].get("risk_register", {})
    steps_completed.append("risk_register")

    brief_result = _run_engine_step(
        failed_step="executive_decision_brief",
        callback=lambda: decision_brief_engine.generate(
            text=text,
            document_type=document_type,
            request_context=request_context,
        ),
        steps_completed=steps_completed,
        file_data=file_data,
        extraction=extraction,
        obligations=obligations,
        risks=risks,
    )
    if brief_result.get("status") == "failed":
        return brief_result
    decision_brief = brief_result["result"].get("brief", {})
    steps_completed.append("executive_decision_brief")

    action_plan_result = _run_engine_step(
        failed_step="executive_action_plan",
        callback=lambda: action_plan_engine.generate(
            text=text,
            document_type=document_type,
            request_context=request_context,
        ),
        steps_completed=steps_completed,
        file_data=file_data,
        extraction=extraction,
        obligations=obligations,
        risks=risks,
        decision_brief=decision_brief,
    )
    if action_plan_result.get("status") == "failed":
        return action_plan_result
    action_plan = action_plan_result["result"].get("action_plan", {})
    steps_completed.append("executive_action_plan")

    event_bus.publish(
        "ExecutiveDocumentIntelligenceLoopCompleted",
        "executive_os",
        {
            "path": file_data.get("path", ""),
            "name": file_data.get("name", ""),
            "document_type": document_type or "",
            "steps_completed": steps_completed,
            "risk_count": len(risks.get("risks", []) or []),
            "action_count": len(action_plan.get("actions", []) or []),
            "result": "success",
        },
    )

    return {
        "engine": "executive_os",
        "status": "success",
        "capability": "document_intelligence_loop",
        "steps_completed": steps_completed,
        "file": file_data,
        "extraction": extraction,
        "obligations": obligations,
        "risks": risks,
        "decision_brief": decision_brief,
        "action_plan": action_plan,
        "message": "Executive document intelligence loop completed.",
    }


def _run_engine_step(
    failed_step: str,
    callback: Any,
    steps_completed: list,
    file_data: Dict[str, Any],
    extraction: Dict[str, Any] = None,
    obligations: Dict[str, Any] = None,
    risks: Dict[str, Any] = None,
    decision_brief: Dict[str, Any] = None,
) -> Dict[str, Any]:
    try:
        result = callback()
    except Exception as exc:
        return _failed_response(
            failed_step=failed_step,
            reason=f"{failed_step}_error",
            message=f"{failed_step.replace('_', ' ').title()} failed: {exc}",
            steps_completed=steps_completed,
            file_data=file_data,
            extraction=extraction,
            obligations=obligations,
            risks=risks,
            decision_brief=decision_brief,
        )

    if not isinstance(result, dict):
        return _failed_response(
            failed_step=failed_step,
            reason="invalid_engine_result",
            message=f"{failed_step.replace('_', ' ').title()} returned an invalid result.",
            steps_completed=steps_completed,
            file_data=file_data,
            extraction=extraction,
            obligations=obligations,
            risks=risks,
            decision_brief=decision_brief,
        )

    if result.get("status") and result.get("status") != "success":
        return _failed_response(
            failed_step=failed_step,
            reason=result.get("reason", f"{failed_step}_error"),
            message=result.get("message", f"{failed_step.replace('_', ' ').title()} failed."),
            steps_completed=steps_completed,
            file_data=file_data,
            extraction=extraction,
            obligations=obligations,
            risks=risks,
            decision_brief=decision_brief,
        )

    return {
        "status": "success",
        "result": result,
    }


def _failed_response(
    failed_step: str,
    reason: str,
    message: str,
    steps_completed: list,
    file_data: Dict[str, Any] = None,
    extraction: Dict[str, Any] = None,
    obligations: Dict[str, Any] = None,
    risks: Dict[str, Any] = None,
    decision_brief: Dict[str, Any] = None,
) -> Dict[str, Any]:
    event_bus.publish(
        "ExecutiveDocumentIntelligenceLoopFailed",
        "executive_os",
        {
            "action": "document_intelligence_loop",
            "failed_step": failed_step,
            "reason": reason,
            "result": "failed",
        },
    )

    response = {
        "engine": "executive_os",
        "status": "failed",
        "capability": "document_intelligence_loop",
        "steps_completed": list(steps_completed),
        "failed_step": failed_step,
        "reason": reason,
        "message": message,
    }
    if file_data is not None:
        response["file"] = file_data
    if extraction is not None:
        response["extraction"] = extraction
    if obligations is not None:
        response["obligations"] = obligations
    if risks is not None:
        response["risks"] = risks
    if decision_brief is not None:
        response["decision_brief"] = decision_brief
    return response
