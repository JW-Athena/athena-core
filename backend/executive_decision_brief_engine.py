from typing import Any, Dict, List, Optional

from capability_004_executive_extraction import ExecutiveInformationExtractor
from capability_005_obligation_extraction import ObligationExtractor
from capability_006_business_intelligence import BusinessIntelligenceEngine
from timing_utils import cached_step, new_request_context, timed_step


class ExecutiveDecisionBriefEngine:
    """
    Executive Decision Brief Engine

    Produces a one-page executive brief by composing existing ATHENA
    intelligence engines. It does not own extraction logic.
    """

    def __init__(self):
        self.business_engine = BusinessIntelligenceEngine()
        self.obligation_engine = ObligationExtractor()
        self.executive_extractor = ExecutiveInformationExtractor()

    def generate(
        self,
        text: str,
        document_type: Optional[str] = None,
        request_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        request_context = new_request_context(request_context)

        return cached_step(
            request_context=request_context,
            cache_key="executive_decision_brief.generate",
            engine="executive_decision_brief",
            step="generate",
            callback=lambda: self._generate_uncached(
                text=text,
                document_type=document_type,
                request_context=request_context,
            ),
        )

    def _generate_uncached(
        self,
        text: str,
        document_type: Optional[str],
        request_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        business = cached_step(
            request_context=request_context,
            cache_key="business_intelligence.analyze",
            engine="business_intelligence",
            step="analyze",
            callback=lambda: self.business_engine.analyze(
                text=text,
                document_type=document_type,
            ),
        )
        obligations = cached_step(
            request_context=request_context,
            cache_key="obligation_extraction.extract",
            engine="obligation_extraction",
            step="extract",
            callback=lambda: self.obligation_engine.extract(
                text=text,
                document_type=document_type,
            ),
        )
        executive = cached_step(
            request_context=request_context,
            cache_key="executive_information.extract",
            engine="executive_information",
            step="extract",
            callback=lambda: self.executive_extractor.extract(
                text=text,
                document_type=document_type,
            ),
        )

        result = {
            "engine": "executive_decision_brief",
            "name": "Executive Decision Brief Engine",
            "document_type": self._first_value(
                business.get("document_type"),
                obligations.get("document_type"),
                executive.get("document_type"),
                document_type,
            ),
            "brief": {
                "executive_summary": self._first_value(
                    business.get("decision_summary_for_ceo"),
                    business.get("executive_summary"),
                    executive.get("executive_summary"),
                    obligations.get("executive_summary"),
                ),
                "recommendation": self._first_value(
                    business.get("overall_recommendation"),
                    business.get("should_bid_or_proceed"),
                ),
                "confidence": self._first_value(
                    business.get("confidence_score"),
                    obligations.get("confidence_score"),
                    executive.get("confidence_score"),
                ),
                "commercial_exposure": {
                    "financial_exposure": business.get("financial_exposure", ""),
                    "payment_quality": business.get("payment_quality", ""),
                    "commercial_risk_level": business.get("commercial_risk_level", ""),
                },
                "key_risks": self._unique_list(
                    business.get("key_risks", []),
                    business.get("commercial_risks", []),
                    obligations.get("commercial_risks", []),
                    executive.get("risks_or_missing_information", []),
                ),
                "required_actions": self._unique_list(
                    business.get("management_action_plan", []),
                    obligations.get("management_action_list", []),
                    executive.get("required_actions", []),
                ),
                "missing_information": self._unique_list(
                    obligations.get("missing_or_unclear_information", []),
                    executive.get("risks_or_missing_information", []),
                    business.get("missing_documents", []),
                ),
                "deadlines": self._unique_list(
                    business.get("important_deadlines", []),
                    obligations.get("important_dates", []),
                    executive.get("important_deadlines", []),
                ),
                "payment_terms": self._unique_list(
                    obligations.get("payment_obligations", []),
                    [executive.get("payment_terms", "")],
                ),
                "delivery_terms": self._unique_list(
                    obligations.get("delivery_obligations", []),
                    [executive.get("delivery_terms", "")],
                ),
                "warranty": self._unique_list(
                    obligations.get("warranty_or_guarantee_terms", []),
                    [business.get("warranty_exposure", "")],
                ),
                "penalties": self._unique_list(
                    obligations.get("penalties_or_liabilities", []),
                    [business.get("penalty_exposure", "")],
                ),
            },
            "source_intelligence": {
                "business_intelligence": business,
                "obligation_extraction": obligations,
                "executive_information": executive,
            },
        }
        timed_step(
            request_context=request_context,
            engine="executive_decision_brief",
            step="assemble",
            callback=lambda: None,
        )
        return result

    def _first_value(self, *values):
        for value in values:
            if value not in (None, "", [], {}):
                return value
        return ""

    def _unique_list(self, *groups) -> List[Any]:
        results = []
        seen = set()

        for group in groups:
            if not group:
                continue

            items = group if isinstance(group, list) else [group]

            for item in items:
                if item in (None, "", [], {}):
                    continue

                key = str(item)
                if key in seen:
                    continue

                seen.add(key)
                results.append(item)

        return results
