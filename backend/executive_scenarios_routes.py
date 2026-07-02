from typing import Optional
import time

from fastapi import APIRouter, File, Form, UploadFile

from executive_scenarios_engine import ExecutiveScenariosEngine
from timing_utils import new_request_context


router = APIRouter(
    prefix="/executive-scenarios",
    tags=["Executive Scenario Intelligence"],
)

engine = ExecutiveScenariosEngine()


@router.post("/analyze")
async def analyze_executive_scenarios(
    file: UploadFile = File(...),
    document_type: Optional[str] = Form(default=None),
):
    request_context = new_request_context()

    started = time.perf_counter()
    content = await file.read()
    print(
        "[timing] engine=executive_scenarios_route "
        f"step=file_read document={file.filename} "
        f"elapsed_ms={round((time.perf_counter() - started) * 1000, 2)}"
    )

    try:
        started = time.perf_counter()
        text = content.decode("utf-8", errors="ignore")
    except Exception:
        text = str(content)
    print(
        "[timing] engine=executive_scenarios_route "
        f"step=text_decode document={file.filename} "
        f"elapsed_ms={round((time.perf_counter() - started) * 1000, 2)}"
    )

    result = engine.analyze(
        text=text,
        document_type=document_type,
        request_context=request_context,
    )

    return {
        "engine": "executive_scenarios",
        "status": "success",
        "scenario_analysis": result.get("scenario_analysis", {}),
    }
