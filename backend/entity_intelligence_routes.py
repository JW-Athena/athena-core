from fastapi import APIRouter, UploadFile, File, Form
from typing import Optional

from entity_intelligence_engine import EntityIntelligenceEngine


router = APIRouter(
    prefix="/entity-intelligence",
    tags=["Entity Intelligence Engine"],
)

engine = EntityIntelligenceEngine()


@router.post("/extract")
async def extract_entities(
    file: UploadFile = File(...),
    document_type: Optional[str] = Form(default=None),
):
    content = await file.read()

    try:
        text = content.decode("utf-8", errors="ignore")
    except Exception:
        text = str(content)

    result = engine.extract(
        text=text,
        document_type=document_type,
    )

    return {
        "engine": "entity_intelligence",
        "name": "Entity Intelligence Engine",
        "filename": file.filename,
        "status": "success",
        "result": result,
    }