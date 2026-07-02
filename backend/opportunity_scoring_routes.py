from typing import Optional
import time

from fastapi import APIRouter, File, Form, UploadFile

from opportunity_scoring_engine import OpportunityScoringEngine
from timing_utils import new_request_context


router = APIRouter(
    prefix="/opportunity-score",
    tags=["Opportunity Scoring Intelligence"],
)

engine = OpportunityScoringEngine()


@router.post("/evaluate")
async def evaluate_opportunity_score(
    file: UploadFile = File(...),
    document_type: Optional[str] = Form(default=None),
):
    request_context = new_request_context()
    started = time.perf_counter()
    content = await file.read()
    print(
        "[timing] engine=opportunity_scoring_route "
        f"step=file_read elapsed_ms={round((time.perf_counter() - started) * 1000, 2)}"
    )

    try:
        started = time.perf_counter()
        text = content.decode("utf-8", errors="ignore")
    except Exception:
        text = str(content)
    print(
        "[timing] engine=opportunity_scoring_route "
        f"step=text_decode elapsed_ms={round((time.perf_counter() - started) * 1000, 2)}"
    )

    result = engine.evaluate(
        text=text,
        document_type=document_type,
        request_context=request_context,
    )

    return {
        "engine": "opportunity_scoring",
        "status": "success",
        "opportunity_score": result.get("opportunity_score", {}),
    }
