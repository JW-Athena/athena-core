import json
from pathlib import Path
from typing import Dict, List


class DecisionRulesEngine:

    def __init__(self):

        self.rules_file = Path("database/decision_rules.json")

        self.rules = self._load_rules()

    def _load_rules(self) -> List[Dict]:

        if not self.rules_file.exists():

            default_rules = [
                {
                    "id": 1,
                    "name": "Products Identified",
                    "weight": 20,
                    "condition": "products"
                },
                {
                    "id": 2,
                    "name": "Warranty Available",
                    "weight": 20,
                    "condition": "warranty"
                },
                {
                    "id": 3,
                    "name": "Payment Terms",
                    "weight": 15,
                    "condition": "payment"
                },
                {
                    "id": 4,
                    "name": "Delivery Terms",
                    "weight": 15,
                    "condition": "delivery"
                },
                {
                    "id": 5,
                    "name": "Certificates",
                    "weight": 15,
                    "condition": "certificates"
                },
                {
                    "id": 6,
                    "name": "Location",
                    "weight": 5,
                    "condition": "location"
                },
                {
                    "id": 7,
                    "name": "Penalty",
                    "weight": -10,
                    "condition": "penalty"
                }
            ]

            self.rules_file.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            self.rules_file.write_text(
                json.dumps(
                    default_rules,
                    indent=4,
                ),
                encoding="utf-8",
            )

        return json.loads(
            self.rules_file.read_text(
                encoding="utf-8",
            )
        )

    def evaluate(
        self,
        profile: Dict,
    ):

        score = 0

        reasons = []

        risks = []

        for rule in self.rules:

            condition = rule["condition"]

            weight = rule["weight"]

            if condition == "products" and profile["products"]:

                score += weight

                reasons.append(rule["name"])

            elif condition == "warranty" and profile["warranties"]:

                score += weight

                reasons.append(rule["name"])

            elif condition == "payment" and profile["payment_terms"]:

                score += weight

                reasons.append(rule["name"])

            elif condition == "delivery" and profile["delivery_terms"]:

                score += weight

                reasons.append(rule["name"])

            elif condition == "certificates" and profile["certificates"]:

                score += weight

                reasons.append(rule["name"])

            elif condition == "location" and profile["locations"]:

                score += weight

                reasons.append(rule["name"])

            elif condition == "penalty" and profile["penalties"]:

                score += weight

                risks.append(rule["name"])

        confidence = max(
            0,
            min(
                score,
                100,
            ),
        )

        recommendation = (
            "Proceed with Bid"
            if confidence >= 60
            else "Review Before Bidding"
        )

        return {
            "score": score,
            "confidence": confidence,
            "recommendation": recommendation,
            "reasons": reasons,
            "risks": risks,
        }