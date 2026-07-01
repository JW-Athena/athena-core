from typing import Optional

from fastapi import APIRouter, File, Form, UploadFile

from bid_no_bid_engine import BidNoBidEngine


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
    content = await file.read()

    try:
        text = content.decode("utf-8", errors="ignore")
    except Exception:
        text = str(content)

    result = engine.evaluate(
        text=text,
        document_type=document_type,
    )

    return {
        "engine": result.get("engine", "bid_no_bid"),
        "status": result.get("status", "success"),
        "decision": result.get("decision", {}),
    }
