from fastapi import APIRouter, UploadFile, File, Form
from typing import Optional

from capability_004_executive_extraction import ExecutiveInformationExtractor


router = APIRouter(prefix="/capability/004", tags=["Capability 004 - Executive Information Extraction"])

extractor = ExecutiveInformationExtractor()


@router.post("/extract")
async def extract_executive_information(
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
        "capability": "004",
        "name": "Executive Information Extraction",
        "filename": file.filename,
        "status": "success",
        "result": result,
    }