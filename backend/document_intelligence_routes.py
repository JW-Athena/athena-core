from fastapi import APIRouter, UploadFile, File, Form
from typing import Optional

from document_intelligence_engine import DocumentIntelligenceEngine


router = APIRouter(
    prefix="/document-intelligence",
    tags=["Document Intelligence Engine"],
)

engine = DocumentIntelligenceEngine()


@router.post("/analyze")
async def analyze_document(
    file: UploadFile = File(...),
    document_type: Optional[str] = Form(default=None),
):
    content = await file.read()

    try:
        text = content.decode("utf-8", errors="ignore")
    except Exception:
        text = str(content)

    result = engine.analyze(
        text=text,
        document_type=document_type,
    )

    return {
        "engine": "document_intelligence",
        "name": "Document Intelligence Engine",
        "filename": file.filename,
        "status": "success",
        "result": result,
    }