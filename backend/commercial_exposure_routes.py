from typing import Optional
import time

from fastapi import APIRouter, File, Form, UploadFile

from commercial_exposure_engine import CommercialExposureEngine
from timing_utils import new_request_context


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
    request_context = new_request_context()
    started = time.perf_counter()
    content = await file.read()
    print(
        "[timing] engine=commercial_exposure_route "
        f"step=file_read elapsed_ms={round((time.perf_counter() - started) * 1000, 2)}"
    )

    try:
        started = time.perf_counter()
        text = content.decode("utf-8", errors="ignore")
    except Exception:
        text = str(content)
    print(
        "[timing] engine=commercial_exposure_route "
        f"step=text_decode elapsed_ms={round((time.perf_counter() - started) * 1000, 2)}"
    )

    result = engine.analyze(
        text=text,
        document_type=document_type,
        request_context=request_context,
    )

    return {
        "engine": "commercial_exposure",
        "status": "success",
        "commercial_exposure": result.get("commercial_exposure", {}),
    }
