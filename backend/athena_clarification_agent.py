from typing import Any, Dict, Optional


class AthenaClarificationAgent:
    """
    ATHENA Clarification Agent

    Decides whether ATHENA should ask one advisory clarification question
    before relying on a cautious executive answer.
    """

    FINAL_DECISION_TERMS = [
        "should we bid",
        "should we approve",
        "can we proceed",
        "is this acceptable",
        "final decision",
    ]

    CRITICAL_COMMERCIAL_FIELDS = [
        "Commercial value",
        "Currency",
        "Customer or buyer",
        "Supplier",
        "Submission deadline",
        "Pricing basis",
    ]

    def evaluate(
        self,
        plan: Dict[str, Any],
        reasoning: Dict[str, Any],
        question: Optional[str] = None,
    ) -> Dict[str, Any]:
        missing_information = list(reasoning.get("missing_information", []))

        if reasoning.get("status") == "insufficient":
            return self._needed(
                question=self._question_for_missing(missing_information),
                reason="ATHENA does not have enough readable information to answer reliably.",
                impact_if_missing="ATHENA cannot provide a reliable executive response without this information.",
            )

        if self._asks_for_final_decision(question) and self._missing_critical_commercial(
            missing_information
        ):
            return self._needed(
                question=self._commercial_question(missing_information),
                reason="A final executive decision requires critical commercial information.",
                impact_if_missing="ATHENA can only provide a conditional recommendation without this information.",
            )

        return {
            "needed": False,
            "question": "",
            "reason": "Available information is sufficient for a cautious executive response.",
            "impact_if_missing": "",
        }

    def _asks_for_final_decision(self, question: Optional[str]) -> bool:
        signal = (question or "").lower()
        return any(term in signal for term in self.FINAL_DECISION_TERMS)

    def _missing_critical_commercial(self, missing_information: list) -> bool:
        return any(field in missing_information for field in self.CRITICAL_COMMERCIAL_FIELDS)

    def _commercial_question(self, missing_information: list) -> str:
        if "Commercial value" in missing_information and "Currency" in missing_information:
            return "What is the contract value and currency for this opportunity?"
        if "Commercial value" in missing_information:
            return "What is the contract value for this opportunity?"
        if "Currency" in missing_information:
            return "What currency applies to this opportunity?"
        if "Customer or buyer" in missing_information:
            return "Who is the customer or buyer for this opportunity?"
        if "Supplier" in missing_information:
            return "Which supplier is being evaluated?"
        if "Submission deadline" in missing_information:
            return "What is the submission deadline?"
        if "Pricing basis" in missing_information:
            return "What pricing basis should ATHENA use for this decision?"
        return "What critical commercial information should ATHENA use for this decision?"

    def _question_for_missing(self, missing_information: list) -> str:
        if "Readable document text" in missing_information:
            return "Can you provide a readable document or paste the key document text?"
        if "Question or uploaded document" in missing_information:
            return "What question or document should ATHENA analyze?"
        if "Uploaded document" in missing_information:
            return "Can you upload the document needed for this analysis?"
        return "What missing information should ATHENA use to complete the analysis?"

    def _needed(
        self,
        question: str,
        reason: str,
        impact_if_missing: str,
    ) -> Dict[str, Any]:
        return {
            "needed": True,
            "question": question,
            "reason": reason,
            "impact_if_missing": impact_if_missing,
        }
