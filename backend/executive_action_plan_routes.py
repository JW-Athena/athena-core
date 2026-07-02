from typing import Optional
import time

from fastapi import APIRouter, File, Form, UploadFile

from executive_action_plan_engine import ExecutiveActionPlanEngine
from timing_utils import new_request_context


router = APIRouter(
    prefix="/executive-action-plan",
    tags=["Executive Action Plan Intelligence"],
)

engine = ExecutiveActionPlanEngine()


@router.post("/generate")
async def generate_executive_action_plan(
    file: UploadFile = File(...),
    document_type: Optional[str] = Form(default=None),
):
    request_context = new_request_context()
    started = time.perf_counter()
    content = await file.read()
    print(
        "[timing] engine=executive_action_plan_route "
        f"step=file_read elapsed_ms={round((time.perf_counter() - started) * 1000, 2)}"
    )

    try:
        started = time.perf_counter()
        text = content.decode("utf-8", errors="ignore")
    except Exception:
        text = str(content)
    print(
        "[timing] engine=executive_action_plan_route "
        f"step=text_decode elapsed_ms={round((time.perf_counter() - started) * 1000, 2)}"
    )

    result = engine.generate(
        text=text,
        document_type=document_type,
        request_context=request_context,
    )

    return {
        "engine": "executive_action_plan",
        "status": "success",
        "action_plan": result.get("action_plan", {}),
    }
