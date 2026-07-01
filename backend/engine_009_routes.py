from fastapi import APIRouter, Form

from engine_009_rag_answer_engine import RAGAnswerEngine


router = APIRouter(prefix="/engine/009", tags=["Engine 009 - RAG Answer Engine"])

rag_engine = RAGAnswerEngine()


@router.post("/answer")
async def answer_from_knowledge(
    question: str = Form(...),
    limit: int = Form(default=5),
):
    result = rag_engine.answer(question=question, limit=limit)

    return {
        "engine": "009",
        "name": "RAG Answer Engine",
        "status": result.get("status", "success"),
        "result": result,
    }