from typing import Dict

from decision_rules_engine import DecisionRulesEngine
from tender_comparison_engine import TenderComparisonEngine
from tender_profile_engine import TenderProfileEngine


class ExecutiveDecisionEngine:

    def __init__(self):

        self.tender_profile_engine = TenderProfileEngine()
        self.tender_comparison_engine = TenderComparisonEngine()
        self.rules_engine = DecisionRulesEngine()

    def evaluate_tender(
        self,
        tender_reference: str,
    ) -> Dict:

        comparison = self.tender_comparison_engine.compare_all()

        profile_result = self.tender_profile_engine.get_profile(
            tender_reference=tender_reference,
        )

        profile = profile_result["profile"]

        decision = self.rules_engine.evaluate(
            profile=profile,
        )

        return {
            "tender_reference": tender_reference,

            "recommendation": decision["recommendation"],

            "confidence": decision["confidence"],

            "score": decision["score"],

            "reasons": decision["reasons"],

            "risks": decision["risks"],

            "comparison_summary": {
                "total_tenders": comparison["total_tenders"],
                "highest_score": (
                    comparison["winner"]["score"]
                    if comparison["winner"]
                    else None
                ),
            },

            "profile": profile,
        }