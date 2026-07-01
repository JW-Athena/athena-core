from typing import Optional

from fastapi import APIRouter, File, Form, UploadFile

from risk_register_engine import RiskRegisterEngine


router = APIRouter(
    prefix="/risk-register",
    tags=["Risk Register Intelligence"],
)

engine = RiskRegisterEngine()


@router.post("/generate")
async def generate_risk_register(
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
        "engine": "risk_register",
        "status": "success",
        "risk_register": result.get("risk_register", {}),
    }
