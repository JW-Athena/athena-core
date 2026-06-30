from fastapi import APIRouter, UploadFile, File, Form
from typing import Optional

from capability_006_business_intelligence import BusinessIntelligenceEngine
from knowledge_engine import KnowledgeEngine


router = APIRouter(prefix="/capability/007", tags=["Capability 007 - Knowledge Engine"])

business_engine = BusinessIntelligenceEngine()
knowledge_engine = KnowledgeEngine()


@router.post("/save")
async def save_document_to_knowledge(
    file: UploadFile = File(...),
    document_type: Optional[str] = Form(default=None),
):
    content = await file.read()

    try:
        text = content.decode("utf-8", errors="ignore")
    except Exception:
        text = str(content)

    intelligence = business_engine.analyze(text=text, document_type=document_type)

    saved_record = knowledge_engine.save_document(
        filename=file.filename,
        document_type=document_type,
        full_text=text,
        intelligence=intelligence,
    )

    return {
        "capability": "007",
        "name": "Knowledge Engine",
        "status": "success",
        "message": "Document analyzed and saved into ATHENA knowledge database",
        "saved_record": saved_record,
        "intelligence": intelligence,
    }


@router.get("/documents")
async def list_knowledge_documents(limit: int = 20):
    documents = knowledge_engine.list_documents(limit=limit)

    return {
        "capability": "007",
        "name": "Knowledge Engine",
        "status": "success",
        "count": len(documents),
        "documents": documents,
    }


@router.get("/documents/{document_id}")
async def get_knowledge_document(document_id: int):
    document = knowledge_engine.get_document(document_id=document_id)

    return {
        "capability": "007",
        "name": "Knowledge Engine",
        "status": "success" if document.get("found") else "not_found",
        "document": document,
    }


@router.get("/search")
async def search_knowledge(query: str, limit: int = 20):
    results = knowledge_engine.search_documents(query=query, limit=limit)

    return {
        "capability": "007",
        "name": "Knowledge Engine",
        "status": "success",
        "query": query,
        "count": len(results),
        "results": results,
    }