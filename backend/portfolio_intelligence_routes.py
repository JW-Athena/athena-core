from typing import List, Optional
import time

from fastapi import APIRouter, File, Form, UploadFile

from portfolio_intelligence_engine import PortfolioIntelligenceEngine


router = APIRouter(
    prefix="/portfolio-intelligence",
    tags=["Portfolio Intelligence"],
)

engine = PortfolioIntelligenceEngine()


@router.post("/analyze")
async def analyze_portfolio_intelligence(
    files: List[UploadFile] = File(...),
    document_type: Optional[str] = Form(default=None),
):
    documents = []

    for file in files:
        started = time.perf_counter()
        content = await file.read()
        print(
            "[timing] engine=portfolio_intelligence_route "
            f"step=file_read document={file.filename} "
            f"elapsed_ms={round((time.perf_counter() - started) * 1000, 2)}"
        )

        try:
            started = time.perf_counter()
            text = content.decode("utf-8", errors="ignore")
        except Exception:
            text = str(content)
        print(
            "[timing] engine=portfolio_intelligence_route "
            f"step=text_decode document={file.filename} "
            f"elapsed_ms={round((time.perf_counter() - started) * 1000, 2)}"
        )

        documents.append(
            {
                "document_name": file.filename or "Uploaded document",
                "text": text,
            }
        )

    result = engine.analyze(
        documents=documents,
        document_type=document_type,
    )

    return {
        "engine": "portfolio_intelligence",
        "status": "success",
        "portfolio": result.get("portfolio", {}),
    }
