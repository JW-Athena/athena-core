from fastapi import APIRouter

from organizational_knowledge_graph import organizational_knowledge_graph


router = APIRouter(tags=["ATHENA Organizational Knowledge Graph"])


@router.get("/athena/knowledge-graph")
async def get_knowledge_graph():
    return {
        "engine": "organizational_knowledge_graph",
        "status": "success",
        "knowledge_graph": organizational_knowledge_graph.get_graph(),
    }
