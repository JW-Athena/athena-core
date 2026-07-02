from typing import Any, Dict, List, Optional

from bid_no_bid_engine import BidNoBidEngine
from commercial_exposure_engine import CommercialExposureEngine
from contract_intelligence_engine import ContractIntelligenceEngine
from executive_dashboard_engine import ExecutiveDashboardEngine
from executive_report_engine import ExecutiveReportEngine
from opportunity_scoring_engine import OpportunityScoringEngine
from risk_register_engine import RiskRegisterEngine
from timing_utils import new_request_context, timed_step


class PortfolioIntelligenceEngine:
    """
    Portfolio Intelligence

    Analyzes one or more uploaded documents independently and aggregates the
    existing ATHENA intelligence into a portfolio-level executive view.
    """

    def __init__(self):
        self.dashboard_engine = ExecutiveDashboardEngine()
        self.report_engine = ExecutiveReportEngine()
        self.opportunity_engine = OpportunityScoringEngine()
        self.contract_engine = ContractIntelligenceEngine()
        self.risk_register_engine = RiskRegisterEngine()
        self.commercial_engine = CommercialExposureEngine()
        self.bid_engine = BidNoBidEngine()

    def analyze(
        self,
        documents: List[Dict[str, str]],
        document_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        document_results = []

        for document in documents:
            document_results.append(
                self._analyze_document(
                    document_name=document.get("document_name", "Uploaded document"),
                    text=document.get("text", ""),
                    document_type=document_type,
                )
            )

        portfolio = self._portfolio_summary(document_results)

        return {
            "engine": "portfolio_intelligence",
            "status": "success",
            "portfolio": portfolio,
        }

    def _analyze_document(
        self,
        document_name: str,
        text: str,
        document_type: Optional[str],
    ) -> Dict[str, Any]:
        request_context = new_request_context()

        dashboard_result = self._safe_call(
            "executive_dashboard",
            lambda: self.dashboard_engine.analyze(
                text=text,
                document_type=document_type,
                request_context=request_context,
            ),
            request_context,
        )
        report_result = self._safe_call(
            "executive_report",
            lambda: self.report_engine.generate(
                text=text,
                document_type=document_type,
                request_context=request_context,
            ),
            request_context,
        )
        opportunity_result = self._safe_call(
            "opportunity_scoring",
            lambda: self.opportunity_engine.evaluate(
                text=text,
                document_type=document_type,
                request_context=request_context,
            ),
            request_context,
        )
        contract_result = self._safe_call(
            "contract_intelligence",
            lambda: self.contract_engine.analyze(
                text=text,
                document_type=document_type,
                request_context=request_context,
            ),
            request_context,
        )
        risk_result = self._safe_call(
            "risk_register",
            lambda: self.risk_register_engine.generate(
                text=text,
                document_type=document_type,
                request_context=request_context,
            ),
            request_context,
        )
        commercial_result = self._safe_call(
            "commercial_exposure",
            lambda: self.commercial_engine.analyze(
                text=text,
                document_type=document_type,
                request_context=request_context,
            ),
            request_context,
        )
        bid_result = self._safe_call(
            "bid_no_bid",
            lambda: self.bid_engine.evaluate(
                text=text,
                document_type=document_type,
                request_context=request_context,
            ),
            request_context,
        )

        dashboard = dashboard_result.get("executive_dashboard", {})
        report = report_result.get("executive_report", {})
        opportunity = opportunity_result.get("opportunity_score", {})
        contract = contract_result.get("contract_intelligence", {})
        risk_register = risk_result.get("risk_register", {})
        commercial = commercial_result.get("commercial_exposure", {})
        decision = bid_result.get("decision", {})

        opportunity_score = self._number_or_default(
            dashboard.get("opportunity_score"),
            default=opportunity.get("overall_score") or 0,
        )
        risk_level = self._first_value(
            dashboard.get("executive_kpis", {}).get("risk_level"),
            contract.get("overall_contract_risk"),
            risk_register.get("overall_risk_level"),
            "Unknown",
        )
        bid_posture = self._conservative_bid_posture(
            dashboard.get("bid_posture"),
            opportunity.get("bid_recommendation"),
            report.get("final_decision"),
            decision.get("recommendation"),
            risk_level,
            commercial.get("overall_commercial_risk"),
        )
        overall_health = self._first_value(
            dashboard.get("overall_health"),
            self._health_from_score_and_risk(opportunity_score, risk_level),
        )

        return {
            "document_name": document_name,
            "opportunity_score": opportunity_score,
            "risk_level": risk_level,
            "bid_posture": bid_posture,
            "overall_health": overall_health,
            "executive_verdict": self._first_value(
                dashboard.get("executive_verdict"),
                report.get("overall_verdict"),
                commercial.get("executive_recommendation"),
                "Management review required before decision.",
            ),
        }

    def _safe_call(self, name: str, callback, request_context: Dict[str, Any]) -> Dict[str, Any]:
        try:
            result = timed_step(
                request_context=request_context,
                engine="portfolio_intelligence",
                step=f"call_{name}",
                callback=callback,
            )
            return result if isinstance(result, dict) else {}
        except Exception as exc:
            print(f"[portfolio_intelligence] engine={name} status=skipped error={exc}")
            return {}

    def _portfolio_summary(self, document_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        documents_analyzed = len(document_results)
        scores = [
            self._number_or_default(result.get("opportunity_score"), default=0)
            for result in document_results
        ]
        average_score = round(sum(scores) / len(scores)) if scores else 0

        highest_risk = self._highest_risk_document(document_results)
        highest_priority = self._highest_priority_document(document_results)
        overall_bid_posture = self._overall_bid_posture(document_results)
        portfolio_health = self._portfolio_health(
            average_score=average_score,
            document_results=document_results,
        )
        kpis = self._portfolio_kpis(document_results)

        return {
            "documents_analyzed": documents_analyzed,
            "portfolio_health": portfolio_health,
            "average_opportunity_score": average_score,
            "overall_bid_posture": overall_bid_posture,
            "highest_priority_document": highest_priority.get("document_name", ""),
            "highest_risk_document": highest_risk.get("document_name", ""),
            "portfolio_summary": self._portfolio_summary_text(
                documents_analyzed=documents_analyzed,
                portfolio_health=portfolio_health,
                average_score=average_score,
                overall_bid_posture=overall_bid_posture,
                kpis=kpis,
            ),
            "portfolio_kpis": kpis,
            "document_results": document_results,
            "portfolio_recommendations": self._portfolio_recommendations(
                portfolio_health=portfolio_health,
                overall_bid_posture=overall_bid_posture,
                kpis=kpis,
                highest_risk=highest_risk,
                highest_priority=highest_priority,
            ),
        }

    def _portfolio_kpis(self, document_results: List[Dict[str, Any]]) -> Dict[str, int]:
        return {
            "critical_documents": len(
                [result for result in document_results if result.get("risk_level") == "Critical"]
            ),
            "high_risk_documents": len(
                [result for result in document_results if result.get("risk_level") in ["Critical", "High"]]
            ),
            "recommended_bid_documents": len(
                [result for result in document_results if result.get("bid_posture") in ["Bid", "Strategic Bid"]]
            ),
            "conditional_bid_documents": len(
                [result for result in document_results if result.get("bid_posture") == "Conditional Bid"]
            ),
            "no_bid_documents": len(
                [result for result in document_results if result.get("bid_posture") == "No-Bid"]
            ),
        }

    def _portfolio_health(
        self,
        average_score: int,
        document_results: List[Dict[str, Any]],
    ) -> str:
        if any(result.get("risk_level") == "Critical" for result in document_results):
            return "Poor"
        if average_score <= 39:
            return "Poor"
        if average_score <= 64 or any(result.get("overall_health") == "Watch" for result in document_results):
            return "Watch"
        if average_score <= 84:
            return "Stable"
        return "Strong"

    def _overall_bid_posture(self, document_results: List[Dict[str, Any]]) -> str:
        if not document_results:
            return "No documents analyzed"

        postures = [result.get("bid_posture", "Conditional Bid") for result in document_results]
        if "No-Bid" in postures:
            return "Mixed Portfolio - Contains No-Bid"
        if "Conditional Bid" in postures:
            return "Conditional Portfolio"
        if "Strategic Bid" in postures:
            return "Strategic Bid Portfolio"
        return "Bid Portfolio"

    def _highest_risk_document(self, document_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not document_results:
            return {}
        return sorted(
            document_results,
            key=lambda result: (
                self._risk_rank(result.get("risk_level")),
                100 - self._number_or_default(result.get("opportunity_score"), default=0),
            ),
            reverse=True,
        )[0]

    def _highest_priority_document(self, document_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not document_results:
            return {}
        viable = [
            result
            for result in document_results
            if result.get("bid_posture") in ["Bid", "Strategic Bid", "Conditional Bid"]
        ]
        candidates = viable or document_results
        return sorted(
            candidates,
            key=lambda result: (
                self._posture_rank(result.get("bid_posture")),
                self._number_or_default(result.get("opportunity_score"), default=0),
                -self._risk_rank(result.get("risk_level")),
            ),
            reverse=True,
        )[0]

    def _portfolio_summary_text(
        self,
        documents_analyzed: int,
        portfolio_health: str,
        average_score: int,
        overall_bid_posture: str,
        kpis: Dict[str, int],
    ) -> str:
        return (
            f"Portfolio health is {portfolio_health} across {documents_analyzed} document(s), "
            f"with an average opportunity score of {average_score}/100. "
            f"Overall bid posture is {overall_bid_posture}. "
            f"{kpis.get('high_risk_documents', 0)} high-risk document(s) require management attention."
        )

    def _portfolio_recommendations(
        self,
        portfolio_health: str,
        overall_bid_posture: str,
        kpis: Dict[str, int],
        highest_risk: Dict[str, Any],
        highest_priority: Dict[str, Any],
    ) -> List[str]:
        recommendations = []

        if kpis.get("critical_documents", 0):
            recommendations.append("Hold executive approval for critical-risk documents until risk owners close the exposure.")
        if kpis.get("conditional_bid_documents", 0):
            recommendations.append("Proceed only with conditional bid documents after commercial, compliance, and risk gaps are closed.")
        if kpis.get("recommended_bid_documents", 0):
            recommendations.append("Prioritize bid-ready documents for management review and submission planning.")
        if kpis.get("no_bid_documents", 0):
            recommendations.append("Record no-bid documents separately unless management approves an exception.")
        if highest_risk.get("document_name"):
            recommendations.append(f"Review highest-risk document first: {highest_risk.get('document_name')}.")
        if highest_priority.get("document_name"):
            recommendations.append(f"Use highest-priority opportunity for immediate action planning: {highest_priority.get('document_name')}.")
        if not recommendations:
            recommendations.append("Complete management review and assign owners for all open portfolio actions.")

        return self._unique_text(recommendations)

    def _conservative_bid_posture(
        self,
        dashboard_posture: Any,
        opportunity_posture: Any,
        final_decision: Any,
        bid_decision: Any,
        risk_level: Any,
        commercial_exposure: Any,
    ) -> str:
        postures = [
            self._normalize_posture(dashboard_posture),
            self._normalize_posture(opportunity_posture),
            self._normalize_posture(final_decision),
            self._bid_decision_to_posture(bid_decision),
        ]
        postures = [posture for posture in postures if posture]

        if risk_level == "Critical":
            postures.append("Conditional Bid")
        if commercial_exposure in ["Medium-High", "High"]:
            postures.append("Conditional Bid")

        if not postures:
            return "Conditional Bid"

        return sorted(postures, key=self._posture_rank)[0]

    def _normalize_posture(self, value: Any) -> str:
        text = str(value or "").strip()
        if text == "Hold":
            return "Conditional Bid"
        if text in ["No-Bid", "Conditional Bid", "Bid", "Strategic Bid"]:
            return text
        return ""

    def _bid_decision_to_posture(self, value: Any) -> str:
        text = str(value or "").upper()
        if text == "NO GO":
            return "No-Bid"
        if text in ["INSUFFICIENT INFORMATION", "GO WITH CONDITIONS"]:
            return "Conditional Bid"
        if text == "GO":
            return "Bid"
        return ""

    def _health_from_score_and_risk(self, score: int, risk_level: str) -> str:
        if score <= 39 or risk_level == "Critical":
            return "Poor"
        if score <= 64:
            return "Watch"
        if score <= 84:
            return "Stable"
        return "Strong"

    def _risk_rank(self, value: Any) -> int:
        return {
            "Critical": 4,
            "High": 3,
            "Medium": 2,
            "Medium-High": 2,
            "Low": 1,
        }.get(str(value), 0)

    def _posture_rank(self, value: Any) -> int:
        return {
            "No-Bid": 0,
            "Conditional Bid": 1,
            "Bid": 2,
            "Strategic Bid": 3,
        }.get(str(value), 1)

    def _number_or_default(self, value: Any, default: Any) -> Any:
        try:
            return int(value)
        except Exception:
            return default

    def _first_value(self, *values) -> str:
        for value in values:
            if value not in (None, "", [], {}, "Unknown"):
                return str(value)
        return ""

    def _unique_text(self, values: List[str]) -> List[str]:
        results = []
        seen = set()
        for value in values:
            text = str(value or "").strip()
            if not text:
                continue
            key = text.lower()
            if key in seen:
                continue
            seen.add(key)
            results.append(text)
        return results
