from core.intent_engine import IntentEngine
from core.retrieval_engine import RetrievalEngine
from core.reasoning_engine import ReasoningEngine
from core.verification_engine import VerificationEngine
from core.response_engine import ResponseEngine


class AthenaCore:
    """
    ATHENA Core

    This is the orchestration layer.

    Every future engine (Tender, Finance, Inventory,
    Manufacturing, Email, Voice...) should call
    AthenaCore instead of directly calling AI,
    Semantic Memory or the Database.
    """

    def __init__(self):
        self.intent_engine = IntentEngine()
        self.retrieval_engine = RetrievalEngine()
        self.reasoning_engine = ReasoningEngine()
        self.verification_engine = VerificationEngine()
        self.response_engine = ResponseEngine()

    def answer(
        self,
        question: str,
        limit: int = 5,
    ) -> dict:

        # STEP 1
        intent = self.intent_engine.detect(question)

        # STEP 2
        retrieved_documents = self.retrieval_engine.retrieve(
            question=question,
            limit=limit,
        )

        # STEP 3
        reasoning = self.reasoning_engine.reason(
            question=question,
            intent=intent,
            retrieved_documents=retrieved_documents,
        )

        # STEP 4
        verification = self.verification_engine.verify(
            reasoning
        )

        # STEP 5
        response = self.response_engine.respond(
            verification
        )

        return {
            "question": question,
            "intent": intent,
            "retrieved_documents": len(retrieved_documents),
            "verification_warnings": verification.get(
                "warnings",
                [],
            ),
            "response": response,
        }