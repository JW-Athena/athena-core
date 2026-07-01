from typing import Optional

from fastapi import APIRouter, File, Form, UploadFile

from executive_action_plan_engine import ExecutiveActionPlanEngine


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
    content = await file.read()

    try:
        text = content.decode("utf-8", errors="ignore")
    except Exception:
        text = str(content)

    result = engine.generate(
        text=text,
        document_type=document_type,
    )

    return {
        "engine": "executive_action_plan",
        "status": "success",
        "action_plan": result.get("action_plan", {}),
    }
