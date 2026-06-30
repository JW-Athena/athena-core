from fastapi import APIRouter

from semantic_memory_engine import SemanticMemoryEngine


router = APIRouter(prefix="/engine/008", tags=["Engine 008 - Semantic Memory Engine"])

semantic_memory_engine = SemanticMemoryEngine()


@router.post("/rebuild")
async def rebuild_semantic_memory():
    result = semantic_memory_engine.rebuild_from_knowledge()

    return {
        "engine": "008",
        "name": "Semantic Memory Engine",
        "status": "success",
        "result": result,
    }


@router.get("/search")
async def semantic_search(query: str, limit: int = 10):
    results = semantic_memory_engine.search(query=query, limit=limit)

    return {
        "engine": "008",
        "name": "Semantic Memory Engine",
        "status": "success",
        "query": query,
        "count": len(results),
        "results": results,
    }


@router.get("/similar/{document_id}")
async def find_similar_documents(document_id: int, limit: int = 10):
    result = semantic_memory_engine.find_similar(document_id=document_id, limit=limit)

    return {
        "engine": "008",
        "name": "Semantic Memory Engine",
        "status": "success" if result.get("found") else "not_found",
        "result": result,
    }