from typing import Optional

from fastapi import APIRouter, File, Form, UploadFile

from commercial_exposure_engine import CommercialExposureEngine


router = APIRouter(
    prefix="/commercial-exposure",
    tags=["Commercial Exposure Intelligence"],
)

engine = CommercialExposureEngine()


@router.post("/analyze")
async def analyze_commercial_exposure(
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
        "engine": "commercial_exposure",
        "status": "success",
        "commercial_exposure": result.get("commercial_exposure", {}),
    }
