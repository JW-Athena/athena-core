from typing import Dict, List


class ReasoningEngine:
    """
    Reasoning Engine

    Converts retrieved documents into a structured evidence package.
    It does not call AI. It prepares clean evidence for verification
    and response generation.
    """

    def reason(
        self,
        question: str,
        intent: Dict,
        retrieved_documents: List[Dict],
    ) -> Dict:

        evidence = []

        for item in retrieved_documents:
            search_result = item.get("search_result", {})
            full_document = item.get("full_document", {})

            evidence.append(
                {
                    "document_id": search_result.get("document_id"),
                    "filename": search_result.get("filename"),
                    "document_type": search_result.get("document_type"),
                    "semantic_score": search_result.get("semantic_score"),
                    "search_method": search_result.get("search_method"),
                    "summary": full_document.get("summary") or search_result.get("summary"),
                    "full_text": full_document.get("full_text", ""),
                    "intelligence": full_document.get("intelligence", {}),
                }
            )

        return {
            "question": question,
            "intent": intent,
            "evidence_count": len(evidence),
            "evidence": evidence,
        }