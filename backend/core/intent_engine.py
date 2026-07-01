class IntentEngine:
    """
    Intent Engine

    Detects what kind of business question the user is asking.
    Later this will become AI-powered, but for now we keep it
    simple and reliable.
    """

    def detect(self, question: str) -> dict:
        text = question.lower()

        if any(word in text for word in ["risk", "danger", "problem", "penalty", "liability"]):
            intent = "risk_analysis"

        elif any(word in text for word in ["warranty", "guarantee", "defect", "replacement"]):
            intent = "warranty_question"

        elif any(word in text for word in ["payment", "invoice", "money", "amount", "price", "cost"]):
            intent = "commercial_question"

        elif any(word in text for word in ["delivery", "timeline", "deadline", "lead time", "closing date"]):
            intent = "delivery_question"

        elif any(word in text for word in ["should we bid", "proceed", "recommend", "decision"]):
            intent = "decision_question"

        elif any(word in text for word in ["document", "certificate", "submission", "required"]):
            intent = "compliance_question"

        else:
            intent = "general_question"

        return {
            "question": question,
            "intent": intent,
        }