from typing import Any, Dict, Optional
import time

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from core.athena_core import AthenaCore
from bid_no_bid_engine import BidNoBidEngine
from commercial_exposure_engine import CommercialExposureEngine
from contract_intelligence_engine import ContractIntelligenceEngine
from engine_009_rag_answer_engine import RAGAnswerEngine
from executive_dashboard_engine import ExecutiveDashboardEngine
from executive_report_engine import ExecutiveReportEngine
from executive_scenarios_engine import ExecutiveScenariosEngine
from opportunity_scoring_engine import OpportunityScoringEngine
from risk_register_engine import RiskRegisterEngine
from athena_planner import AthenaPlanner
from timing_utils import new_request_context, timed_step


router = APIRouter(tags=["ATHENA Brain"])

athena_core = AthenaCore()
dashboard_engine = ExecutiveDashboardEngine()
report_engine = ExecutiveReportEngine()
contract_engine = ContractIntelligenceEngine()
scenarios_engine = ExecutiveScenariosEngine()
risk_engine = RiskRegisterEngine()
commercial_engine = CommercialExposureEngine()
opportunity_engine = OpportunityScoringEngine()
bid_engine = BidNoBidEngine()
rag_engine = RAGAnswerEngine()
planner = AthenaPlanner()


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

    request_context = new_request_context()

    if file is None:
        result = _analyze_document(
            text="",
            document_type=document_type,
            question=question,
            limit=limit,
            request_context=request_context,
            metadata={},
        )

        return {
            "engine": "athena_brain",
            "status": "success",
            "result": result,
        }

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
        metadata={
            "filename": file.filename,
            "content_type": file.content_type,
            "size_bytes": len(content),
        },
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
    metadata: Dict[str, Any],
) -> Dict[str, Any]:
    plan = planner.plan(
        question=question,
        document_type=document_type,
        metadata=metadata,
    )
    workflow = plan.get("intent", "question_answering")
    engine_outputs = _run_workflow(
        workflow=workflow,
        text=text,
        document_type=document_type,
        question=question,
        limit=limit,
        request_context=request_context,
    )
    selected_engines = list(engine_outputs.keys())

    return {
        "workflow": workflow,
        "question": question or "",
        "document_type": document_type or "",
        "planning": planner.public_plan(plan),
        "brain_summary": _brain_summary(
            workflow=workflow,
            document_type=document_type,
            selected_engines=selected_engines,
            question=question,
        ),
        "executive_response": _executive_response(
            workflow=workflow,
            engine_outputs=engine_outputs,
            question=question,
        ),
        "selected_engines": selected_engines,
        "engine_outputs": engine_outputs,
    }


def _run_workflow(
    workflow: str,
    text: str,
    document_type: Optional[str],
    question: Optional[str],
    limit: int,
    request_context: Dict[str, Any],
) -> Dict[str, Any]:
    outputs = {}

    if workflow == "executive_document_analysis":
        _add_output(
            outputs,
            "executive_dashboard",
            _safe_call(
                "executive_dashboard",
                lambda: dashboard_engine.analyze(
                    text=text,
                    document_type=document_type,
                    request_context=request_context,
                ),
                request_context,
            ).get("executive_dashboard", {}),
        )
        _add_output(
            outputs,
            "executive_report",
            _safe_call(
                "executive_report",
                lambda: report_engine.generate(
                    text=text,
                    document_type=document_type,
                    request_context=request_context,
                ),
                request_context,
            ).get("executive_report", {}),
        )
        return outputs

    if workflow == "contract_review":
        _add_output(
            outputs,
            "contract_intelligence",
            _safe_call(
                "contract_intelligence",
                lambda: contract_engine.analyze(
                    text=text,
                    document_type=document_type,
                    request_context=request_context,
                ),
                request_context,
            ).get("contract_intelligence", {}),
        )
        _add_dashboard(outputs, text, document_type, request_context)
        return outputs

    if workflow == "risk_review":
        _add_output(
            outputs,
            "risk_register",
            _safe_call(
                "risk_register",
                lambda: risk_engine.generate(
                    text=text,
                    document_type=document_type,
                    request_context=request_context,
                ),
                request_context,
            ).get("risk_register", {}),
        )
        _add_dashboard(outputs, text, document_type, request_context)
        return outputs

    if workflow == "commercial_review":
        _add_output(
            outputs,
            "commercial_exposure",
            _safe_call(
                "commercial_exposure",
                lambda: commercial_engine.analyze(
                    text=text,
                    document_type=document_type,
                    request_context=request_context,
                ),
                request_context,
            ).get("commercial_exposure", {}),
        )
        _add_dashboard(outputs, text, document_type, request_context)
        return outputs

    if workflow == "opportunity_assessment":
        _add_output(
            outputs,
            "opportunity_scoring",
            _safe_call(
                "opportunity_scoring",
                lambda: opportunity_engine.evaluate(
                    text=text,
                    document_type=document_type,
                    request_context=request_context,
                ),
                request_context,
            ).get("opportunity_score", {}),
        )
        _add_output(
            outputs,
            "bid_no_bid",
            _safe_call(
                "bid_no_bid",
                lambda: bid_engine.evaluate(
                    text=text,
                    document_type=document_type,
                    request_context=request_context,
                ),
                request_context,
            ).get("decision", {}),
        )
        _add_dashboard(outputs, text, document_type, request_context)
        return outputs

    if workflow == "scenario_analysis":
        _add_output(
            outputs,
            "executive_scenarios",
            _safe_call(
                "executive_scenarios",
                lambda: scenarios_engine.analyze(
                    text=text,
                    document_type=document_type,
                    request_context=request_context,
                ),
                request_context,
            ).get("scenario_analysis", {}),
        )
        _add_dashboard(outputs, text, document_type, request_context)
        return outputs

    if workflow == "report_generation":
        _add_output(
            outputs,
            "executive_report",
            _safe_call(
                "executive_report",
                lambda: report_engine.generate(
                    text=text,
                    document_type=document_type,
                    request_context=request_context,
                ),
                request_context,
            ).get("executive_report", {}),
        )
        _add_dashboard(outputs, text, document_type, request_context)
        return outputs

    _add_output(
        outputs,
        "rag_answer",
        _safe_call(
            "rag_answer",
            lambda: rag_engine.answer(
                question=question or "",
                limit=limit,
            ),
            request_context,
        ),
    )
    return outputs


def _add_dashboard(
    outputs: Dict[str, Any],
    text: str,
    document_type: Optional[str],
    request_context: Dict[str, Any],
) -> None:
    _add_output(
        outputs,
        "executive_dashboard",
        _safe_call(
            "executive_dashboard",
            lambda: dashboard_engine.analyze(
                text=text,
                document_type=document_type,
                request_context=request_context,
            ),
            request_context,
        ).get("executive_dashboard", {}),
    )


def _add_output(outputs: Dict[str, Any], key: str, value: Any) -> None:
    if value:
        outputs[key] = value


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


def _brain_summary(
    workflow: str,
    document_type: Optional[str],
    selected_engines: list,
    question: Optional[str],
) -> str:
    engine_names = {
        "executive_dashboard": "executive dashboard",
        "executive_report": "executive report",
        "contract_intelligence": "contract intelligence",
        "executive_scenarios": "executive scenarios",
        "risk_register": "risk register",
        "commercial_exposure": "commercial exposure",
        "opportunity_scoring": "opportunity scoring",
        "bid_no_bid": "bid/no-bid",
        "rag_answer": "knowledge answer",
    }
    selected = [
        engine_names.get(engine, engine.replace("_", " "))
        for engine in selected_engines
    ]
    selected_text = _join_words(selected)

    if workflow == "executive_document_analysis":
        document_label = f"{document_type.lower()}-style" if document_type else "executive"
        return (
            f"ATHENA identified this as a {document_label} executive document and "
            f"selected {selected_text} workflows."
        )

    if workflow == "question_answering":
        return "ATHENA classified the request as question answering and selected the knowledge answer workflow."

    if question:
        return (
            f"ATHENA classified the request as {workflow.replace('_', ' ')} and selected "
            f"{selected_text} workflows."
        )

    return f"ATHENA selected {selected_text} workflows for the document."


def _executive_response(
    workflow: str,
    engine_outputs: Dict[str, Any],
    question: Optional[str],
) -> Dict[str, Any]:
    dashboard = engine_outputs.get("executive_dashboard", {})
    report = engine_outputs.get("executive_report", {})
    contract = engine_outputs.get("contract_intelligence", {})
    risk_register = engine_outputs.get("risk_register", {})
    commercial_exposure = engine_outputs.get("commercial_exposure", {})
    opportunity_scoring = engine_outputs.get("opportunity_scoring", {})
    bid_no_bid = engine_outputs.get("bid_no_bid", {})
    scenarios = engine_outputs.get("executive_scenarios", {})
    rag_answer = engine_outputs.get("rag_answer", {})

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

    response = {
        "mode": workflow,
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

    if workflow == "contract_review":
        response.update(
            {
                "contract_risk": _first_value(contract.get("overall_contract_risk"), "Unknown"),
                "contract_summary": _first_value(contract.get("contract_summary"), summary),
                "next_step": _first_list_value(contract.get("recommended_actions")) or next_step,
            }
        )
    elif workflow == "risk_review":
        response.update(
            {
                "risk_level": _first_value(
                    risk_register.get("overall_risk_level"),
                    response.get("risk_level"),
                ),
                "major_risk_count": _number_or_default(
                    _first_value(risk_register.get("high_risks"), 0),
                    default=0,
                ),
            }
        )
    elif workflow == "commercial_review":
        response.update(
            {
                "commercial_exposure": _first_value(
                    commercial_exposure.get("overall_commercial_risk"),
                    response.get("commercial_exposure"),
                ),
                "payment_terms": _first_value(commercial_exposure.get("payment_terms"), "Not stated"),
            }
        )
    elif workflow == "opportunity_assessment":
        response.update(
            {
                "opportunity_score": _number_or_default(
                    _first_value(opportunity_scoring.get("overall_score"), response.get("opportunity_score")),
                    default=0,
                ),
                "opportunity_level": _first_value(opportunity_scoring.get("opportunity_level"), "Unknown"),
                "bid_posture": _first_value(
                    opportunity_scoring.get("bid_recommendation"),
                    bid_no_bid.get("recommendation"),
                    response.get("bid_posture"),
                ),
            }
        )
    elif workflow == "scenario_analysis":
        response.update(
            {
                "recommended_scenario": _first_value(scenarios.get("recommended_scenario"), "Proceed After Risk Closure"),
                "best_business_outcome": _first_value(scenarios.get("best_business_outcome"), ""),
                "next_step": _first_value(scenarios.get("recommended_next_step"), next_step),
            }
        )
    elif workflow == "question_answering":
        answer = rag_answer.get("answer", {})
        response.update(
            {
                "verdict": "Question answered from available ATHENA knowledge.",
                "summary": _first_value(
                    answer.get("direct_answer") if isinstance(answer, dict) else answer,
                    "ATHENA could not find enough information to answer with confidence.",
                ),
                "next_step": "Review the supporting ATHENA response before taking action.",
            }
        )

    return response


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


def _first_list_value(value: Any) -> str:
    if isinstance(value, list) and value:
        first = value[0]
        if isinstance(first, dict):
            return _first_value(first.get("action"), first.get("title"), first.get("summary"))
        return _first_value(first)
    return ""


def _join_words(values: list) -> str:
    clean_values = [str(value).strip() for value in values if str(value).strip()]
    if not clean_values:
        return "executive analysis"
    if len(clean_values) == 1:
        return clean_values[0]
    if len(clean_values) == 2:
        return f"{clean_values[0]} and {clean_values[1]}"
    return f"{', '.join(clean_values[:-1])}, and {clean_values[-1]}"
