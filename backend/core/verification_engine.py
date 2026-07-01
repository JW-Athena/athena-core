from typing import Dict


class VerificationEngine:
    """
    Verification Engine

    Adds safety checks before ATHENA writes the final answer.
    This reduces mistakes like confusing payment terms with warranty terms.
    """

    def verify(self, reasoning_package: Dict) -> Dict:
        question = reasoning_package.get("question", "").lower()
        warnings = []

        for evidence in reasoning_package.get("evidence", []):
            full_text = evidence.get("full_text", "").lower()

            if "warranty" in question or "guarantee" in question:
                if "payment terms" in full_text:
                    warnings.append(
                        "The question asks about warranty/guarantee. Payment terms must not be treated as warranty terms."
                    )

            if "payment" in question or "invoice" in question:
                if "warranty" in full_text or "guarantee" in full_text:
                    warnings.append(
                        "The question asks about payment. Warranty or guarantee terms must not be treated as payment terms."
                    )

            if "delivery" in question or "timeline" in question:
                if "payment terms" in full_text:
                    warnings.append(
                        "The question asks about delivery/timeline. Payment terms must not be treated as delivery terms."
                    )

            if "risk" in question or "penalty" in question:
                warnings.append(
                    "For risk questions, separate delivery risk, payment risk, warranty risk, penalty risk, and compliance risk."
                )

        return {
            "verified": True,
            "warnings": list(set(warnings)),
            "reasoning_package": reasoning_package,
        }