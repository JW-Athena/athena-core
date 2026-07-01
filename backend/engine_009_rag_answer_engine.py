from typing import Any, Dict

from core.athena_core import AthenaCore
from product_profile_engine import ProductProfileEngine


class RAGAnswerEngine:
    """
    Engine 009

    RAG Answer Engine powered by ATHENA Core.
    It now also understands product profile questions.
    """

    def __init__(self):
        self.athena_core = AthenaCore()
        self.product_profile_engine = ProductProfileEngine()

    def answer(self, question: str, limit: int = 5) -> Dict[str, Any]:
        core_result = self.athena_core.answer(
            question=question,
            limit=limit,
        )

        intent = core_result.get("intent", {}).get("intent")

        if intent == "product_profile_question":
            product_name = self._extract_product_name(question)
            product_profile = self.product_profile_engine.get_profile(product_name)

            return {
                "question": question,
                "answer": {
                    "direct_answer": self._format_product_direct_answer(product_profile),
                    "executive_summary": "ATHENA retrieved a structured product profile from the entity database.",
                    "supporting_points": self._product_supporting_points(product_profile),
                    "risks_or_uncertainties": self._product_risks(product_profile),
                    "recommended_actions": self._product_actions(product_profile),
                    "confidence_score": 90,
                },
                "intent": core_result.get("intent", {}),
                "retrieved_documents": core_result.get("retrieved_documents", 0),
                "verification_warnings": core_result.get("verification_warnings", []),
                "product_profile": product_profile,
                "status": "success",
                "engine": "009",
                "name": "RAG Answer Engine powered by ATHENA Core",
            }

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

    def _extract_product_name(self, question: str) -> str:
        text = question.strip()

        replacements = [
            "Tell me about",
            "tell me about",
            "Product profile of",
            "product profile of",
            "Profile of",
            "profile of",
            "product profile",
        ]

        for replacement in replacements:
            text = text.replace(replacement, "")

        text = text.strip(" ?.")

        if not text:
            return question

        return text

    def _format_product_direct_answer(self, product_profile: Dict) -> str:
        profile = product_profile.get("profile", {})
        product_name = profile.get("product_name")
        category = profile.get("category")
        quantities = profile.get("quantities", [])
        delivery_terms = profile.get("delivery_terms", [])
        warranties = profile.get("warranties", [])
        payment_terms = profile.get("payment_terms", [])
        penalties = profile.get("penalties", [])
        locations = profile.get("locations", [])

        parts = [f"{product_name} is recorded as a {category or 'product'} in ATHENA."]

        if quantities:
            parts.append(f"Recorded quantity: {', '.join(str(q) for q in quantities)}.")
        if delivery_terms:
            parts.append(f"Delivery term: {', '.join(delivery_terms)}.")
        if warranties:
            parts.append(f"Warranty: {', '.join(warranties)}.")
        if payment_terms:
            parts.append(f"Payment term: {', '.join(payment_terms)}.")
        if penalties:
            parts.append(f"Penalty exposure: {', '.join(penalties)}.")
        if locations:
            parts.append(f"Location: {', '.join(locations)}.")

        return " ".join(parts)

    def _product_supporting_points(self, product_profile: Dict):
        profile = product_profile.get("profile", {})
        points = []

        for doc in profile.get("source_documents", []):
            points.append(f"Source document: {doc}")

        if profile.get("delivery_terms"):
            points.append(f"Delivery: {', '.join(profile.get('delivery_terms'))}")

        if profile.get("warranties"):
            points.append(f"Warranty: {', '.join(profile.get('warranties'))}")

        if profile.get("payment_terms"):
            points.append(f"Payment: {', '.join(profile.get('payment_terms'))}")

        return points

    def _product_risks(self, product_profile: Dict):
        profile = product_profile.get("profile", {})
        risks = []

        if profile.get("penalties"):
            risks.append(f"Penalty exposure detected: {', '.join(profile.get('penalties'))}")

        if profile.get("warranties"):
            risks.append(f"Warranty exposure detected: {', '.join(profile.get('warranties'))}")

        if not risks:
            risks.append("No major product-specific risks detected in stored entities.")

        return risks

    def _product_actions(self, product_profile: Dict):
        profile = product_profile.get("profile", {})
        actions = [
            "Review the source document before final decision.",
            "Confirm supplier capability and delivery schedule.",
        ]

        if profile.get("warranties"):
            actions.append("Confirm warranty responsibility with supplier.")

        if profile.get("penalties"):
            actions.append("Review penalty clause before approving bid.")

        return actions