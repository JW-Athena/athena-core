from fastapi import APIRouter, UploadFile, File, Form
from typing import Optional

from capability_005_obligation_extraction import ObligationExtractor


router = APIRouter(prefix="/capability/005", tags=["Capability 005 - Obligation Extraction"])

extractor = ObligationExtractor()


@router.post("/extract")
async def extract_obligations(
    file: UploadFile = File(...),
    document_type: Optional[str] = Form(default=None),
):
    content = await file.read()

    try:
        text = content.decode("utf-8", errors="ignore")
    except Exception:
        text = str(content)

    result = extractor.extract(text=text, document_type=document_type)

    return {
        "capability": "005",
        "name": "Contract and Tender Obligation Extraction",
        "filename": file.filename,
        "status": "success",
        "result": result,
    }