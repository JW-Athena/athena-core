from typing import Optional
import time

from fastapi import APIRouter, File, Form, UploadFile

from bid_no_bid_engine import BidNoBidEngine
from timing_utils import new_request_context


router = APIRouter(
    prefix="/bid-decision",
    tags=["Bid / No-Bid Intelligence"],
)

engine = BidNoBidEngine()


@router.post("/evaluate")
async def evaluate_bid_decision(
    file: UploadFile = File(...),
    document_type: Optional[str] = Form(default=None),
):
    request_context = new_request_context()
    started = time.perf_counter()
    content = await file.read()
    print(
        "[timing] engine=bid_no_bid_route "
        f"step=file_read elapsed_ms={round((time.perf_counter() - started) * 1000, 2)}"
    )

    try:
        started = time.perf_counter()
        text = content.decode("utf-8", errors="ignore")
    except Exception:
        text = str(content)
    print(
        "[timing] engine=bid_no_bid_route "
        f"step=text_decode elapsed_ms={round((time.perf_counter() - started) * 1000, 2)}"
    )

    result = engine.evaluate(
        text=text,
        document_type=document_type,
        request_context=request_context,
    )

    return {
        "engine": result.get("engine", "bid_no_bid"),
        "status": result.get("status", "success"),
        "decision": result.get("decision", {}),
    }
