import re
from typing import Any, Dict, List, Optional


class AthenaReasoningAgent:
    """
    ATHENA Reasoning Agent

    Reviews whether ATHENA has enough request and document context to produce
    a reliable executive response. It does not run intelligence engines and
    does not expose chain-of-thought.
    """

    def evaluate(
        self,
        plan: Dict[str, Any],
        question: Optional[str] = None,
        document_type: Optional[str] = None,
        text: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        metadata = metadata or {}
        intent = plan.get("intent", "")
        missing_information = self._missing_information(
            intent=intent,
            question=question,
            document_type=document_type,
            text=text,
            metadata=metadata,
        )

        if self._has_uploaded_file(metadata) and not self._has_readable_text(text):
            return {
                "status": "insufficient",
                "confidence": "Low",
                "missing_information": ["Readable document text"],
                "reasoning_summary": "The uploaded document did not provide readable text for analysis.",
                "recommended_handling": "ask_clarifying_question",
            }

        if not self._has_uploaded_file(metadata) and not question:
            return {
                "status": "insufficient",
                "confidence": "Low",
                "missing_information": ["Question or uploaded document"],
                "reasoning_summary": "No question or document was provided.",
                "recommended_handling": "ask_clarifying_question",
            }

        if missing_information:
            return {
                "status": "partial",
                "confidence": "Medium" if self._has_readable_text(text) or question else "Low",
                "missing_information": missing_information,
                "reasoning_summary": "ATHENA has enough context to respond, but key information is incomplete.",
                "recommended_handling": "answer_with_caution",
            }

        return {
            "status": "sufficient",
            "confidence": "High" if self._has_readable_text(text) else "Medium",
            "missing_information": [],
            "reasoning_summary": "ATHENA has enough context to generate an executive response.",
            "recommended_handling": "answer",
        }

    def _missing_information(
        self,
        intent: str,
        question: Optional[str],
        document_type: Optional[str],
        text: str,
        metadata: Dict[str, Any],
    ) -> List[str]:
        missing = []

        if not question and not self._has_uploaded_file(metadata):
            missing.append("Question or uploaded document")

        if self._requires_document(intent) and not self._has_uploaded_file(metadata):
            missing.append("Uploaded document")

        if self._has_uploaded_file(metadata) and not self._has_readable_text(text):
            missing.append("Readable document text")

        if self._question_is_vague(question) and self._has_uploaded_file(metadata):
            missing.append("Specific executive question")

        if intent in {
            "executive_document_analysis",
            "commercial_review",
            "opportunity_assessment",
            "report_generation",
            "scenario_analysis",
        }:
            if not self._contains_value(text):
                missing.append("Commercial value")
            if not self._contains_currency(text):
                missing.append("Currency")

        if intent in {"contract_review", "risk_review", "scenario_analysis"}:
            if not self._contains_any(text, ["warranty", "penalty", "termination", "liability", "indemnity"]):
                missing.append("Key contractual risk terms")

        if not document_type and self._has_uploaded_file(metadata):
            missing.append("Document type")

        return self._dedupe(missing)

    def _requires_document(self, intent: str) -> bool:
        return intent != "question_answering"

    def _has_uploaded_file(self, metadata: Dict[str, Any]) -> bool:
        return bool(metadata.get("filename") or metadata.get("size_bytes"))

    def _has_readable_text(self, text: str) -> bool:
        return len((text or "").strip()) >= 20

    def _question_is_vague(self, question: Optional[str]) -> bool:
        if not question:
            return False
        words = re.findall(r"[A-Za-z0-9]+", question)
        return len(words) <= 2

    def _contains_value(self, text: str) -> bool:
        return bool(re.search(r"\b\d[\d,]*(?:\.\d+)?\b", text or ""))

    def _contains_currency(self, text: str) -> bool:
        signal = (text or "").lower()
        return any(
            token in signal
            for token in [
                "usd",
                "aed",
                "eur",
                "gbp",
                "sar",
                "qar",
                "omr",
                "currency",
                "$",
                "€",
                "£",
            ]
        )

    def _contains_any(self, text: str, terms: List[str]) -> bool:
        signal = (text or "").lower()
        return any(term in signal for term in terms)

    def _dedupe(self, values: List[str]) -> List[str]:
        deduped = []
        for value in values:
            if value and value not in deduped:
                deduped.append(value)
        return deduped
