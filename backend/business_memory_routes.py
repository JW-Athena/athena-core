from fastapi import APIRouter
from pydantic import BaseModel

from business_memory_engine import BusinessMemoryEngine


router = APIRouter(
    prefix="/business-memory",
    tags=["Business Memory Engine"],
)

engine = BusinessMemoryEngine()


class MemoryRequest(BaseModel):
    memory_type: str
    subject: str
    title: str
    summary: str
    metadata: dict = {}


@router.post("/remember")
async def remember(request: MemoryRequest):

    result = engine.remember(
        memory_type=request.memory_type,
        subject=request.subject,
        title=request.title,
        summary=request.summary,
        metadata=request.metadata,
    )

    return {
        "engine": "business_memory_engine",
        "status": "success",
        "result": result,
    }


@router.get("/recall/{subject}")
async def recall(subject: str):

    memories = engine.recall(subject)

    return {
        "engine": "business_memory_engine",
        "status": "success",
        "count": len(memories),
        "memories": memories,
    }