from typing import Dict, List

from tender_index_engine import TenderIndexEngine
from tender_profile_engine import TenderProfileEngine


class TenderComparisonEngine:

    def __init__(self):
        self.index_engine = TenderIndexEngine()
        self.profile_engine = TenderProfileEngine()

    def compare_all(self) -> Dict:

        tenders = self.index_engine.list_tenders()

        results = []

        for tender in tenders:

            profile = self.profile_engine.get_profile(
                tender["tender_reference"]
            )["profile"]

            score = self._score(profile)

            results.append(
                {
                    "tender_reference": tender["tender_reference"],
                    "score": score,
                    "profile": profile,
                }
            )

        results.sort(
            key=lambda x: x["score"],
            reverse=True,
        )

        winner = results[0] if results else None

        return {
            "total_tenders": len(results),
            "winner": winner,
            "ranking": results,
        }

    def _score(self, profile: Dict) -> int:

        score = 0

        score += len(profile["products"]) * 10
        score += len(profile["certificates"]) * 5
        score += len(profile["warranties"]) * 15
        score += len(profile["payment_terms"]) * 10
        score += len(profile["delivery_terms"]) * 10
        score += len(profile["locations"]) * 5
        score -= len(profile["penalties"]) * 5

        return score
    