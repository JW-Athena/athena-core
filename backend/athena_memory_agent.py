from typing import Any, Dict, List, Optional

from business_memory_engine import BusinessMemoryEngine
from entity_database import EntityDatabase
from knowledge_engine import KnowledgeEngine
from semantic_memory_engine import SemanticMemoryEngine


class AthenaMemoryAgent:
    """
    ATHENA Memory Agent

    Decides whether historical context should be consulted before engine
    execution. It does not answer the user and does not expose memory contents.
    """

    def __init__(self):
        self.business_memory = BusinessMemoryEngine()
        self.semantic_memory = SemanticMemoryEngine()
        self.knowledge_engine = KnowledgeEngine()
        self.entity_database = EntityDatabase()

    def evaluate(
        self,
        plan: Dict[str, Any],
        question: Optional[str] = None,
        document_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        metadata = metadata or {}
        intent = plan.get("intent", "")
        query = self._query(
            intent=intent,
            question=question,
            document_type=document_type,
            metadata=metadata,
        )

        if not self._should_search(intent=intent, question=question, document_type=document_type):
            return self._unused("No relevant historical context was required.")

        sources = []
        self._consult_business_memory(query=query, sources=sources)
        self._consult_semantic_memory(query=query, sources=sources)
        self._consult_knowledge_engine(query=query, sources=sources)
        self._consult_entity_database(
            query=query,
            intent=intent,
            document_type=document_type,
            sources=sources,
        )

        if not sources:
            return self._unused("No relevant historical context was found.")

        return {
            "used": True,
            "sources": sources,
            "reasoning": self._reasoning(intent=intent, document_type=document_type),
        }

    def _should_search(
        self,
        intent: str,
        question: Optional[str],
        document_type: Optional[str],
    ) -> bool:
        if intent == "question_answering":
            return True

        signal = f"{question or ''} {document_type or ''}".lower()
        memory_intents = {
            "executive_document_analysis",
            "contract_review",
            "risk_review",
            "commercial_review",
            "opportunity_assessment",
            "scenario_analysis",
            "report_generation",
        }

        return intent in memory_intents or any(
            term in signal
            for term in [
                "previous",
                "history",
                "similar",
                "past",
                "supplier",
                "tender",
                "contract",
            ]
        )

    def _query(
        self,
        intent: str,
        question: Optional[str],
        document_type: Optional[str],
        metadata: Dict[str, Any],
    ) -> str:
        parts = [
            question or "",
            document_type or "",
            metadata.get("filename") or "",
            intent.replace("_", " "),
        ]
        query = " ".join(part for part in parts if str(part).strip()).strip()
        return query or intent.replace("_", " ")

    def _consult_business_memory(self, query: str, sources: List[str]) -> None:
        try:
            if self.business_memory.recall(subject=query):
                self._add_source(sources, "business_memory")
        except Exception as exc:
            print(f"[athena_memory_agent] source=business_memory status=skipped error={exc}")

    def _consult_semantic_memory(self, query: str, sources: List[str]) -> None:
        try:
            if self.semantic_memory.search(query=query, limit=3):
                self._add_source(sources, "semantic_memory")
        except Exception as exc:
            print(f"[athena_memory_agent] source=semantic_memory status=skipped error={exc}")

    def _consult_knowledge_engine(self, query: str, sources: List[str]) -> None:
        try:
            if self.knowledge_engine.search_documents(query=query, limit=3):
                self._add_source(sources, "knowledge_engine")
        except Exception as exc:
            print(f"[athena_memory_agent] source=knowledge_engine status=skipped error={exc}")

    def _consult_entity_database(
        self,
        query: str,
        intent: str,
        document_type: Optional[str],
        sources: List[str],
    ) -> None:
        signal = f"{query} {intent} {document_type or ''}".lower()
        if not any(term in signal for term in ["supplier", "entity", "contract", "tender"]):
            return

        try:
            if self.entity_database.search_entities(query=query, limit=3):
                self._add_source(sources, "entity_database")
        except Exception as exc:
            print(f"[athena_memory_agent] source=entity_database status=skipped error={exc}")

    def _reasoning(self, intent: str, document_type: Optional[str]) -> str:
        if intent == "contract_review":
            return "Previous contract findings and commercial observations may improve the analysis."
        if intent == "opportunity_assessment":
            return "Previous tender, decision, and opportunity knowledge may improve the assessment."
        if intent == "risk_review":
            return "Previous risk and executive decision knowledge may improve the review."
        if "supplier" in str(document_type or "").lower():
            return "Supplier history and stored entity knowledge may improve the analysis."
        return "Previous executive and tender knowledge may improve the analysis."

    def _unused(self, reasoning: str) -> Dict[str, Any]:
        return {
            "used": False,
            "sources": [],
            "reasoning": reasoning,
        }

    def _add_source(self, sources: List[str], source: str) -> None:
        if source not in sources:
            sources.append(source)
