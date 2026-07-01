from typing import Dict, List

from semantic_memory_engine import SemanticMemoryEngine
from knowledge_engine import KnowledgeEngine


class RetrievalEngine:
    """
    Retrieval Engine

    Finds relevant documents using semantic memory,
    then loads the full original document from
    the Knowledge Engine.

    This prevents ATHENA from answering only from
    short summaries.
    """

    def __init__(self):
        self.semantic_memory = SemanticMemoryEngine()
        self.knowledge_engine = KnowledgeEngine()

    def retrieve(
        self,
        question: str,
        limit: int = 5,
    ) -> List[Dict]:

        search_results = self.semantic_memory.search(
            query=question,
            limit=limit,
        )

        enriched_results = []

        for result in search_results:
            document_id = result.get("document_id")

            full_document = {
                "found": False,
                "message": "No document id available",
            }

            if document_id:
                full_document = self.knowledge_engine.get_document(
                    document_id=document_id
                )

            enriched_results.append(
                {
                    "search_result": result,
                    "full_document": full_document,
                }
            )

        return enriched_results