from fastapi import APIRouter, UploadFile, File, Form
from typing import Optional

from entity_intelligence_engine import EntityIntelligenceEngine
from entity_database import EntityDatabase


router = APIRouter(
    prefix="/entity-database",
    tags=["Entity Database"],
)

entity_engine = EntityIntelligenceEngine()
entity_database = EntityDatabase()


@router.post("/reset")
async def reset_entity_database():
    result = entity_database.reset()

    return {
        "engine": "entity_database",
        "status": "success",
        "result": result,
    }


@router.post("/save")
async def save_entities_from_document(
    file: UploadFile = File(...),
    document_type: Optional[str] = Form(default=None),
):
    content = await file.read()

    try:
        text = content.decode("utf-8", errors="ignore")
    except Exception:
        text = str(content)

    extraction = entity_engine.extract(
        text=text,
        document_type=document_type,
    )

    saved = entity_database.save_extraction(
        filename=file.filename,
        document_type=document_type,
        extraction=extraction,
    )

    return {
        "engine": "entity_database",
        "name": "Entity Database",
        "filename": file.filename,
        "status": "success",
        "saved": saved,
        "extraction": extraction,
    }


@router.get("/entities")
async def list_entities(limit: int = 50):
    entities = entity_database.list_entities(limit=limit)

    return {
        "engine": "entity_database",
        "status": "success",
        "count": len(entities),
        "entities": entities,
    }


@router.get("/search")
async def search_entities(query: str, limit: int = 50):
    entities = entity_database.search_entities(query=query, limit=limit)

    return {
        "engine": "entity_database",
        "status": "success",
        "query": query,
        "count": len(entities),
        "entities": entities,
    }


@router.get("/relationships")
async def list_relationships(limit: int = 50):
    relationships = entity_database.list_relationships(limit=limit)

    return {
        "engine": "entity_database",
        "status": "success",
        "count": len(relationships),
        "relationships": relationships,
    }