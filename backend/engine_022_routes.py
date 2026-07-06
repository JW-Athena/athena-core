from typing import Any, Dict

from fastapi import APIRouter, Body, HTTPException

from engine_022_knowledge_graph import executive_knowledge_graph


router = APIRouter(tags=["ATHENA Executive Knowledge Graph"])


@router.post("/athena/knowledge/nodes")
async def create_node(payload: Dict[str, Any] = Body(default_factory=dict)):
    result = executive_knowledge_graph.create_node(
        node_type=str(payload.get("type", "") or ""),
        name=str(payload.get("name", "") or ""),
        node_id=str(payload.get("id", "") or ""),
    )
    return _raise_on_failure(result)


@router.post("/athena/knowledge/relationships")
async def create_relationship(payload: Dict[str, Any] = Body(default_factory=dict)):
    result = executive_knowledge_graph.create_relationship(
        source=str(payload.get("source", "") or ""),
        target=str(payload.get("target", "") or ""),
        relationship=str(payload.get("relationship", "") or ""),
    )
    return _raise_on_failure(result)


@router.get("/athena/knowledge/nodes")
async def list_nodes():
    return executive_knowledge_graph.list_nodes()


@router.get("/athena/knowledge/relationships")
async def list_relationships():
    return executive_knowledge_graph.list_relationships()


@router.get("/athena/knowledge/related/{node_id}")
async def get_related_entities(node_id: str):
    result = executive_knowledge_graph.get_related_entities(node_id)
    return _raise_on_failure(result)


def _raise_on_failure(result: Dict[str, Any]) -> Dict[str, Any]:
    if result.get("status") != "failed":
        return result

    reason = result.get("reason", "")
    status_code = 404 if reason.endswith("_not_found") else 400
    raise HTTPException(status_code=status_code, detail=result)
