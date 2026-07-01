from typing import Any, Dict

from core.athena_core import AthenaCore


class RAGAnswerEngine:
    """
    Engine 009

    RAG Answer Engine now uses ATHENA Core instead of
    directly calling semantic memory, knowledge, and OpenAI.
    """

    def __init__(self):
        self.athena_core = AthenaCore()

    def answer(self, question: str, limit: int = 5) -> Dict[str, Any]:
        core_result = self.athena_core.answer(
            question=question,
            limit=limit,
        )

        return {
            "question": question,
            "answer": core_result.get("response", {}).get("answer", {}),
            "intent": core_result.get("intent", {}),
            "retrieved_documents": core_result.get("retrieved_documents", 0),
            "verification_warnings": core_result.get("verification_warnings", []),
            "status": core_result.get("response", {}).get("status", "success"),
            "engine": "009",
            "name": "RAG Answer Engine powered by ATHENA Core",
        }