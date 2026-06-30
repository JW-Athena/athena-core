from fastapi import APIRouter, UploadFile, File, Form
from typing import Optional

from capability_006_business_intelligence import BusinessIntelligenceEngine


router = APIRouter(prefix="/capability/006", tags=["Capability 006 - Business Intelligence Engine"])

engine = BusinessIntelligenceEngine()


@router.post("/analyze")
async def analyze_business_document(
    file: UploadFile = File(...),
    document_type: Optional[str] = Form(default=None),
):
    content = await file.read()

    try:
        text = content.decode("utf-8", errors="ignore")
    except Exception:
        text = str(content)

    result = engine.analyze(text=text, document_type=document_type)

    return {
        "capability": "006",
        "name": "Business Intelligence Engine",
        "filename": file.filename,
        "status": "success",
        "result": result,
    }