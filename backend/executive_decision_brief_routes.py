from typing import Optional

from fastapi import APIRouter, File, Form, UploadFile

from executive_decision_brief_engine import ExecutiveDecisionBriefEngine


router = APIRouter(
    prefix="/executive-decision-brief",
    tags=["Executive Decision Brief Engine"],
)

engine = ExecutiveDecisionBriefEngine()


@router.post("/generate")
async def generate_executive_decision_brief(
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
        "engine": result.get("engine", "executive_decision_brief"),
        "status": "success",
        "brief": result.get("brief", {}),
    }
