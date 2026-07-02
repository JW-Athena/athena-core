from typing import Any, Dict, Optional
import time

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from core.athena_core import AthenaCore
from contract_intelligence_engine import ContractIntelligenceEngine
from executive_dashboard_engine import ExecutiveDashboardEngine
from executive_report_engine import ExecutiveReportEngine
from executive_scenarios_engine import ExecutiveScenariosEngine
from timing_utils import new_request_context, timed_step


router = APIRouter(tags=["ATHENA Brain"])

athena_core = AthenaCore()
dashboard_engine = ExecutiveDashboardEngine()
report_engine = ExecutiveReportEngine()
contract_engine = ContractIntelligenceEngine()
scenarios_engine = ExecutiveScenariosEngine()


@router.post("/athena/analyze")
async def analyze_with_athena(
    file: Optional[UploadFile] = File(default=None),
    document_type: Optional[str] = Form(default=None),
    question: Optional[str] = Form(default=None),
    limit: int = Form(default=5),
):
    if file is None and not question:
        raise HTTPException(
            status_code=400,
            detail="Provide a file, a question, or both.",
        )

    if file is None:
        result = athena_core.answer(
            question=question or "",
            limit=limit,
        )

        return {
            "engine": "athena_brain",
            "status": "success",
            "result": result,
        }

    request_context = new_request_context()
    started = time.perf_counter()
    content = await file.read()
    print(
        "[timing] engine=athena_brain_route "
        f"step=file_read document={file.filename} "
        f"elapsed_ms={round((time.perf_counter() - started) * 1000, 2)}"
    )

    try:
        started = time.perf_counter()
        text = content.decode("utf-8", errors="ignore")
    except Exception:
        text = str(content)
    print(
        "[timing] engine=athena_brain_route "
        f"step=text_decode document={file.filename} "
        f"elapsed_ms={round((time.perf_counter() - started) * 1000, 2)}"
    )

    result = _analyze_document(
        text=text,
        document_type=document_type,
        question=question,
        limit=limit,
        request_context=request_context,
    )

    return {
        "engine": "athena_brain",
        "status": "success",
        "result": result,
    }


def _analyze_document(
    text: str,
    document_type: Optional[str],
    question: Optional[str],
    limit: int,
    request_context: Dict[str, Any],
) -> Dict[str, Any]:
    detected_workflow = _detect_workflow(
        question=question,
        document_type=document_type,
        text=text,
    )
    workflow = detected_workflow if question else "executive_document_analysis"
    brain_response = {}

    if question:
        brain_response = _safe_call(
            "athena_core",
            lambda: athena_core.answer(
                question=question,
                limit=limit,
            ),
            request_context,
        )

    dashboard_result = _safe_call(
        "executive_dashboard",
        lambda: dashboard_engine.analyze(
            text=text,
            document_type=document_type,
            request_context=request_context,
        ),
        request_context,
    )
    report_result = {}
    contract_result = {}
    scenarios_result = {}

    if detected_workflow in {"executive", "report", "contract", "scenario"}:
        report_result = _safe_call(
            "executive_report",
            lambda: report_engine.generate(
                text=text,
                document_type=document_type,
                request_context=request_context,
            ),
            request_context,
        )

    if detected_workflow == "contract":
        contract_result = _safe_call(
            "contract_intelligence",
            lambda: contract_engine.analyze(
                text=text,
                document_type=document_type,
                request_context=request_context,
            ),
            request_context,
        )

    if detected_workflow == "scenario":
        scenarios_result = _safe_call(
            "executive_scenarios",
            lambda: scenarios_engine.analyze(
                text=text,
                document_type=document_type,
                request_context=request_context,
            ),
            request_context,
        )

    dashboard = dashboard_result.get("executive_dashboard", {})
    report = report_result.get("executive_report", {})
    selected_engines = _selected_engines(
        dashboard_result=dashboard_result,
        report_result=report_result,
        contract_result=contract_result,
        scenarios_result=scenarios_result,
        brain_response=brain_response,
    )

    result = {
        "workflow": workflow,
        "question": question or "",
        "document_type": document_type or "",
        "brain_summary": _brain_summary(
            workflow=workflow,
            document_type=document_type,
            selected_engines=selected_engines,
            question=question,
        ),
        "executive_response": _executive_response(
            dashboard=dashboard,
            report=report,
            question=question,
        ),
        "selected_engines": selected_engines,
    }

    if dashboard:
        result["executive_dashboard"] = dashboard
    if report:
        result["executive_report"] = report
    contract = contract_result.get("contract_intelligence", {})
    if contract:
        result["contract_intelligence"] = contract
    scenario_analysis = scenarios_result.get("scenario_analysis", {})
    if scenario_analysis:
        result["scenario_analysis"] = scenario_analysis
    if brain_response:
        result["brain_response"] = brain_response

    return result


def _detect_workflow(
    question: Optional[str],
    document_type: Optional[str],
    text: str,
) -> str:
    signal = f"{question or ''} {document_type or ''} {text[:1000]}".lower()

    if any(term in signal for term in ["scenario", "option", "alternative", "what if"]):
        return "scenario"
    if any(term in signal for term in ["contract", "clause", "legal", "liability", "termination"]):
        return "contract"
    if any(term in signal for term in ["report", "summary", "recommendation", "decision"]):
        return "report"

    return "executive"


def _safe_call(name: str, callback, request_context: Dict[str, Any]) -> Dict[str, Any]:
    try:
        result = timed_step(
            request_context=request_context,
            engine="athena_brain",
            step=f"call_{name}",
            callback=callback,
        )
        return result if isinstance(result, dict) else {}
    except Exception as exc:
        print(f"[athena_brain] engine={name} status=skipped error={exc}")
        return {}


def _selected_engines(
    dashboard_result: Dict[str, Any],
    report_result: Dict[str, Any],
    contract_result: Dict[str, Any],
    scenarios_result: Dict[str, Any],
    brain_response: Dict[str, Any],
) -> list:
    selected = []
    if brain_response:
        selected.append("athena_core")
    if dashboard_result:
        selected.append("executive_dashboard")
    if report_result:
        selected.append("executive_report")
    if contract_result:
        selected.append("contract_intelligence")
    if scenarios_result:
        selected.append("executive_scenarios")
    return selected


def _brain_summary(
    workflow: str,
    document_type: Optional[str],
    selected_engines: list,
    question: Optional[str],
) -> str:
    engine_names = {
        "athena_core": "ATHENA Core",
        "executive_dashboard": "executive dashboard",
        "executive_report": "executive report",
        "contract_intelligence": "contract intelligence",
        "executive_scenarios": "executive scenarios",
    }
    selected = [
        engine_names.get(engine, engine.replace("_", " "))
        for engine in selected_engines
        if engine != "athena_core" or question
    ]
    selected_text = _join_words(selected)

    if workflow == "executive_document_analysis":
        document_label = f"{document_type.lower()}-style" if document_type else "executive"
        return (
            f"ATHENA identified this as a {document_label} document and "
            f"selected {selected_text} workflows."
        )

    if question:
        return (
            f"ATHENA used the question to guide document analysis and selected "
            f"{selected_text} workflows."
        )

    return f"ATHENA selected {selected_text} workflows for the document."


def _executive_response(
    dashboard: Dict[str, Any],
    report: Dict[str, Any],
    question: Optional[str],
) -> Dict[str, Any]:
    opportunity = report.get("opportunity_assessment", {})
    risk = report.get("risk_assessment", {})
    commercial = report.get("commercial_assessment", {})

    verdict = _first_value(
        dashboard.get("executive_verdict"),
        report.get("overall_verdict"),
        "Management review required.",
    )
    summary = _first_value(
        dashboard.get("management_summary"),
        report.get("executive_summary"),
        "The document was analyzed and requires executive review.",
    )
    next_step = _first_value(
        dashboard.get("recommended_next_step"),
        report.get("next_step"),
        "Assign accountable owners to close open commercial, compliance, and risk items.",
    )

    return {
        "mode": "question_guided" if question else "document_analysis",
        "verdict": verdict,
        "summary": summary,
        "opportunity_score": _number_or_default(
            _first_value(
                dashboard.get("opportunity_score"),
                opportunity.get("score"),
                0,
            ),
            default=0,
        ),
        "risk_level": _first_value(
            dashboard.get("executive_kpis", {}).get("risk_level"),
            risk.get("risk_level"),
            "Unknown",
        ),
        "commercial_exposure": _first_value(
            dashboard.get("executive_kpis", {}).get("commercial_exposure"),
            commercial.get("exposure_level"),
            "Unknown",
        ),
        "bid_posture": _first_value(
            dashboard.get("bid_posture"),
            opportunity.get("bid_posture"),
            "Conditional Bid",
        ),
        "next_step": next_step,
    }


def _first_value(*values: Any) -> str:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def _number_or_default(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            value = default
        return round(float(value))
    except (TypeError, ValueError):
        return default


def _join_words(values: list) -> str:
    clean_values = [str(value).strip() for value in values if str(value).strip()]
    if not clean_values:
        return "executive analysis"
    if len(clean_values) == 1:
        return clean_values[0]
    if len(clean_values) == 2:
        return f"{clean_values[0]} and {clean_values[1]}"
    return f"{', '.join(clean_values[:-1])}, and {clean_values[-1]}"
