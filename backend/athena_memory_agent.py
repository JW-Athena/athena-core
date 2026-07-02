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

    def store_file_understanding(self, workflow: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(workflow, dict) or workflow.get("name") != "file_understanding":
            return self._memory_store_failure(
                reason="invalid_workflow",
                message="A valid file_understanding workflow is required.",
            )

        file_data = workflow.get("file", {})
        if not isinstance(file_data, dict) or not file_data.get("path") or not file_data.get("name"):
            return self._memory_store_failure(
                reason="missing_file",
                message="Workflow file metadata is required.",
            )

        summary = workflow.get("summary", {})
        summary_text = str(summary.get("summary_text", "") or "").strip() if isinstance(summary, dict) else ""
        if not isinstance(summary, dict) or not summary_text:
            return self._memory_store_failure(
                reason="missing_summary",
                message="Workflow summary text is required.",
            )

        memory_record = {
            "type": "file_understanding",
            "source_path": str(file_data.get("path", "") or ""),
            "source_name": str(file_data.get("name", "") or ""),
            "summary_text": summary_text,
            "confidence": str(summary.get("confidence", "limited") or "limited"),
        }

        try:
            self.business_memory.remember(
                memory_type=memory_record["type"],
                subject=memory_record["source_path"],
                title=memory_record["source_name"],
                summary=memory_record["summary_text"],
                metadata={
                    "extension": file_data.get("extension", ""),
                    "size_bytes": file_data.get("size_bytes", 0),
                    "steps_completed": workflow.get("steps_completed", []),
                    "summary_method": summary.get("method", ""),
                    "confidence": memory_record["confidence"],
                },
            )
        except Exception as exc:
            return self._memory_store_failure(
                reason="memory_store_error",
                message=f"Failed to store file understanding in memory: {exc}",
            )

        return {
            "status": "success",
            "memory_record": memory_record,
            "message": "File understanding stored in memory.",
        }

    def list_file_understandings(self, limit: int = 20) -> Dict[str, Any]:
        try:
            safe_limit = int(limit)
        except (TypeError, ValueError):
            return self._memory_store_failure(
                reason="invalid_limit",
                message="Limit must be a number.",
            )

        if safe_limit < 1:
            return self._memory_store_failure(
                reason="invalid_limit",
                message="Limit must be greater than zero.",
            )

        safe_limit = min(safe_limit, 100)

        try:
            memories = self.business_memory.recall(subject="")
            records = []
            for memory in memories:
                if memory.get("memory_type") != "file_understanding":
                    continue
                metadata = memory.get("metadata", {}) or {}
                records.append(
                    {
                        "type": "file_understanding",
                        "source_path": memory.get("subject", ""),
                        "source_name": memory.get("title", ""),
                        "summary_text": memory.get("summary", ""),
                        "confidence": metadata.get("confidence", "limited"),
                    }
                )
                if len(records) >= safe_limit:
                    break
        except Exception as exc:
            return self._memory_store_failure(
                reason="memory_read_error",
                message=f"Failed to read stored file understandings: {exc}",
            )

        return {
            "status": "success",
            "count": len(records),
            "records": records,
            "message": "Stored file understandings listed.",
        }

    def search_file_understandings(self, query: str, limit: int = 20) -> Dict[str, Any]:
        clean_query = str(query or "").strip()
        if not clean_query:
            return self._memory_store_failure(
                reason="empty_query",
                message="Search query is required.",
            )

        try:
            safe_limit = int(limit)
        except (TypeError, ValueError):
            return self._memory_store_failure(
                reason="invalid_limit",
                message="Limit must be a number.",
            )

        if safe_limit < 1:
            return self._memory_store_failure(
                reason="invalid_limit",
                message="Limit must be greater than zero.",
            )

        safe_limit = min(safe_limit, 100)
        query_lower = clean_query.lower()

        try:
            memories = self.business_memory.recall(subject="")
            records = []
            for memory in memories:
                if memory.get("memory_type") != "file_understanding":
                    continue

                metadata = memory.get("metadata", {}) or {}
                record = {
                    "type": "file_understanding",
                    "source_path": memory.get("subject", ""),
                    "source_name": memory.get("title", ""),
                    "summary_text": memory.get("summary", ""),
                    "confidence": metadata.get("confidence", "limited"),
                }
                searchable_text = " ".join(
                    [
                        record["source_name"],
                        record["source_path"],
                        record["summary_text"],
                    ]
                ).lower()
                if query_lower in searchable_text:
                    records.append(record)
                if len(records) >= safe_limit:
                    break
        except Exception as exc:
            return self._memory_store_failure(
                reason="memory_search_error",
                message=f"Failed to search stored file understandings: {exc}",
            )

        return {
            "status": "success",
            "query": clean_query,
            "count": len(records),
            "records": records,
            "message": "Stored file understandings searched.",
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

    def _memory_store_failure(self, reason: str, message: str) -> Dict[str, Any]:
        return {
            "status": "blocked",
            "reason": reason,
            "memory_record": {},
            "records": [],
            "count": 0,
            "message": message,
        }
