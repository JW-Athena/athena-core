import re
from typing import Any, Dict, List, Optional

from bid_no_bid_engine import BidNoBidEngine
from business_memory_engine import BusinessMemoryEngine
from commercial_exposure_engine import CommercialExposureEngine
from executive_decision_brief_engine import ExecutiveDecisionBriefEngine
from executive_decision_engine import ExecutiveDecisionEngine
from risk_register_engine import RiskRegisterEngine
from timing_utils import cached_step, new_request_context, timed_step


class ExecutiveActionPlanEngine:
    """
    Executive Action Plan Intelligence

    Converts existing ATHENA intelligence into a short, prioritized management
    action plan. The reasoning is generic for commercial, trading, contracting,
    procurement, and tendering companies.
    """

    def __init__(self):
        self.brief_engine = ExecutiveDecisionBriefEngine()
        self.bid_engine = BidNoBidEngine()
        self.risk_register_engine = RiskRegisterEngine()
        self.commercial_exposure_engine = CommercialExposureEngine()
        self.business_memory_engine = BusinessMemoryEngine()
        self.executive_decision_engine = ExecutiveDecisionEngine()

    def generate(
        self,
        text: str,
        document_type: Optional[str] = None,
        request_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        request_context = new_request_context(request_context)

        return cached_step(
            request_context=request_context,
            cache_key="executive_action_plan.generate",
            engine="executive_action_plan",
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
        brief_result = self.brief_engine.generate(
            text=text,
            document_type=document_type,
            request_context=request_context,
        )
        bid_result = self.bid_engine.evaluate(
            text=text,
            document_type=document_type,
            request_context=request_context,
        )
        risk_result = self.risk_register_engine.generate(
            text=text,
            document_type=document_type,
            request_context=request_context,
        )
        commercial_result = self.commercial_exposure_engine.analyze(
            text=text,
            document_type=document_type,
            request_context=request_context,
        )

        brief = brief_result.get("brief", {})
        decision = bid_result.get("decision", {})
        risk_register = risk_result.get("risk_register", {})
        commercial = commercial_result.get("commercial_exposure", {})

        actions = []

        self._add_commercial_actions(actions, commercial, decision)
        self._add_missing_information_actions(actions, brief, decision)
        self._add_risk_actions(actions, risk_register)
        self._add_brief_actions(actions, brief)
        self._add_memory_actions(actions, text, document_type)
        self._add_executive_decision_actions(actions, text)

        actions = self._consolidate_actions(actions)
        actions = self._sort_actions(actions)[:12]

        for index, action in enumerate(actions, start=1):
            action["id"] = f"ACT-{index:03d}"

        estimated_readiness = self._estimated_readiness(
            decision=decision,
            actions=actions,
            commercial=commercial,
        )
        priority = self._overall_priority(actions)
        overall_status = self._overall_status(
            estimated_readiness=estimated_readiness,
            actions=actions,
            decision=decision,
        )

        result = {
            "engine": "executive_action_plan",
            "name": "Executive Action Plan Intelligence",
            "status": "success",
            "action_plan": {
                "priority": priority,
                "overall_status": overall_status,
                "estimated_readiness": estimated_readiness,
                "actions": actions,
                "executive_summary": self._executive_summary(
                    priority=priority,
                    overall_status=overall_status,
                    estimated_readiness=estimated_readiness,
                    actions=actions,
                    decision=decision,
                    commercial=commercial,
                ),
            },
        }
        timed_step(
            request_context=request_context,
            engine="executive_action_plan",
            step="assemble",
            callback=lambda: None,
        )
        return result

    def _add_commercial_actions(
        self,
        actions: List[Dict],
        commercial: Dict[str, Any],
        decision: Dict[str, Any],
    ) -> None:
        if commercial.get("contract_value") in ["", "Unknown"] or not commercial.get("currency"):
            self._add_action(
                actions,
                priority="Critical",
                department="Commercial",
                title="Confirm contract value and currency",
                description="Confirm the monetary value, pricing basis, and currency before executive approval.",
                reason="Missing price, value, or currency prevents a reliable commercial decision.",
                estimated_time="Same day",
                depends_on=[],
            )

        payment_terms = commercial.get("payment_terms")
        cash_flow_risk = str(commercial.get("cash_flow_risk", ""))
        payment_quality = str(commercial.get("payment_quality", ""))

        if not payment_terms or cash_flow_risk == "High" or payment_quality == "Poor":
            self._add_action(
                actions,
                priority="High",
                department="Finance",
                title="Review payment and cash-flow exposure",
                description="Validate payment timing, collection risk, and working-capital exposure.",
                reason="Payment or cash-flow risk affects whether the opportunity is commercially acceptable.",
                estimated_time="Same day",
                depends_on=["Confirm contract value and currency"],
            )

        if commercial.get("penalty_exposure"):
            self._add_action(
                actions,
                priority="High",
                department="Legal",
                title="Review penalty clause",
                description="Assess delay penalties, liability limits, and whether the exposure can be accepted or negotiated.",
                reason="Penalty clauses can turn an otherwise viable opportunity into a loss-making commitment.",
                estimated_time="1 business day",
                depends_on=["Confirm contract value and currency"],
            )

        if commercial.get("warranty_liability"):
            self._add_action(
                actions,
                priority="Medium",
                department="Operations",
                title="Validate warranty support model",
                description="Confirm warranty coverage, cost responsibility, and after-sales support before approval.",
                reason="Warranty obligations create after-sales cost and operational responsibility.",
                estimated_time="1 business day",
                depends_on=[],
            )

        if decision.get("recommendation") in ["NO GO", "INSUFFICIENT INFORMATION"]:
            self._add_action(
                actions,
                priority="High",
                department="Management",
                title="Hold executive decision until blockers are closed",
                description="Do not approve the opportunity until critical blockers and missing information are resolved.",
                reason=f"Current bid decision is {decision.get('recommendation')}.",
                estimated_time="After blocker closure",
                depends_on=[],
            )

    def _add_missing_information_actions(
        self,
        actions: List[Dict],
        brief: Dict[str, Any],
        decision: Dict[str, Any],
    ) -> None:
        missing_text = self._combined_text(
            brief.get("missing_information", []),
            decision.get("missing_information", []),
            decision.get("blockers", []),
        )

        if any(word in missing_text for word in ["supplier", "vendor"]):
            self._add_action(
                actions,
                priority="High",
                department="Procurement",
                title="Confirm supplier identity and responsibility",
                description="Confirm the supplier, issuing party, and responsible counterparty before commitment.",
                reason="Supplier uncertainty prevents accountability for price, delivery, warranty, and claims.",
                estimated_time="Same day",
                depends_on=[],
            )

        if any(word in missing_text for word in ["customer", "buyer", "client"]):
            self._add_action(
                actions,
                priority="High",
                department="Management",
                title="Confirm customer or buyer context",
                description="Confirm who the buyer or customer is and whether the opportunity fits management intent.",
                reason="Customer uncertainty affects scope, authority, relationship risk, and commercial priority.",
                estimated_time="Same day",
                depends_on=[],
            )

        if any(word in missing_text for word in ["certificate", "document", "required documents"]):
            self._add_action(
                actions,
                priority="High",
                department="Compliance",
                title="Prepare mandatory documents and certificates",
                description="Confirm all required licenses, certificates, test reports, compliance sheets, and submission documents.",
                reason="Missing documents can block submission or create non-compliance risk.",
                estimated_time="1-2 business days",
                depends_on=[],
            )

    def _add_risk_actions(self, actions: List[Dict], risk_register: Dict[str, Any]) -> None:
        for risk in risk_register.get("risks", []):
            title = str(risk.get("title", ""))
            category = str(risk.get("category", ""))
            description = str(risk.get("description", ""))
            risk_text = f"{title} {category} {description}".lower()

            if "penalty" in risk_text or "liability" in risk_text:
                self._add_action(
                    actions,
                    priority="High",
                    department="Legal",
                    title="Review penalty liability",
                    description="Review penalty wording, liability caps, and negotiation options.",
                    reason="Penalty or liability exposure requires legal approval.",
                    estimated_time="1 business day",
                    depends_on=["Confirm contract value and currency"],
                )

            if "warranty" in risk_text or "guarantee" in risk_text:
                self._add_action(
                    actions,
                    priority="Medium",
                    department="Operations",
                    title="Validate warranty execution",
                    description="Confirm whether warranty commitments can be supported and costed.",
                    reason="Warranty exposure requires operational and quality review.",
                    estimated_time="1 business day",
                    depends_on=[],
                )

            if any(word in risk_text for word in ["delivery", "deadline", "lead time", "closing date"]):
                self._add_action(
                    actions,
                    priority="High" if risk.get("severity") in ["Critical", "High"] else "Medium",
                    department="Operations",
                    title="Confirm delivery feasibility",
                    description="Validate delivery schedule, deadline, capacity, and accountable owner.",
                    reason="Delivery or deadline risk needs operational confirmation.",
                    estimated_time="Same day",
                    depends_on=[],
                )

            if any(word in risk_text for word in ["certificate", "document", "compliance", "submission"]):
                self._add_action(
                    actions,
                    priority="High" if risk.get("severity") in ["Critical", "High"] else "Medium",
                    department="Compliance",
                    title="Close compliance requirements",
                    description="Verify the submission package and mandatory compliance evidence.",
                    reason="Compliance gaps can block submission or approval.",
                    estimated_time="1-2 business days",
                    depends_on=[],
                )

    def _add_brief_actions(self, actions: List[Dict], brief: Dict[str, Any]) -> None:
        for item in brief.get("required_actions", [])[:5]:
            text = str(item).strip()
            if not text:
                continue

            self._add_action(
                actions,
                priority=self._priority_from_text(text, default="Medium"),
                department=self._department_from_text(text),
                title=self._title_from_text(text),
                description=text,
                reason="Required by the executive decision brief.",
                estimated_time="Same day",
                depends_on=[],
            )

    def _add_memory_actions(
        self,
        actions: List[Dict],
        text: str,
        document_type: Optional[str],
    ) -> None:
        subjects = [
            self._extract_tender_reference(text),
            document_type,
        ]

        for subject in subjects:
            if not subject:
                continue

            try:
                memories = self.business_memory_engine.recall(subject)
            except Exception:
                memories = []

            if memories:
                self._add_action(
                    actions,
                    priority="Low",
                    department="Management",
                    title="Review relevant business memory",
                    description="Review previous ATHENA memory for similar subject, decision history, or lessons learned.",
                    reason=f"ATHENA found {len(memories)} related memory record(s).",
                    estimated_time="15 minutes",
                    depends_on=[],
                )
                return

    def _add_executive_decision_actions(self, actions: List[Dict], text: str) -> None:
        tender_reference = self._extract_tender_reference(text)
        if not tender_reference:
            return

        try:
            result = self.executive_decision_engine.evaluate_tender(tender_reference)
        except Exception:
            return

        recommendation = result.get("recommendation")
        if recommendation:
            self._add_action(
                actions,
                priority="Medium",
                department="Management",
                title="Review stored executive decision context",
                description="Compare this document against stored tender profile and decision scoring before final approval.",
                reason=f"Existing executive decision engine recommendation: {recommendation}.",
                estimated_time="30 minutes",
                depends_on=[],
            )

    def _add_action(
        self,
        actions: List[Dict],
        priority: str,
        department: str,
        title: str,
        description: str,
        reason: str,
        estimated_time: str,
        depends_on: List[str],
    ) -> None:
        actions.append(
            {
                "id": "",
                "priority": self._normalize_priority(priority),
                "department": self._normalize_department(department),
                "title": self._clean_title(title),
                "description": self._clean_sentence(description),
                "reason": self._clean_sentence(reason, max_words=18),
                "estimated_time": estimated_time,
                "depends_on": self._clean_dependencies(depends_on, title),
            }
        )

    def _consolidate_actions(self, actions: List[Dict]) -> List[Dict]:
        grouped: Dict[str, Dict] = {}

        for action in actions:
            key = self._action_key(action)
            if key not in grouped:
                grouped[key] = action.copy()
                continue

            existing = grouped[key]
            existing["priority"] = self._highest_priority(
                existing.get("priority"),
                action.get("priority"),
            )
            existing["description"] = self._merge_sentence(
                existing.get("description", ""),
                action.get("description", ""),
            )
            existing["reason"] = self._merge_sentence(
                existing.get("reason", ""),
                action.get("reason", ""),
            )
            existing["depends_on"] = self._merge_list(
                existing.get("depends_on", []),
                action.get("depends_on", []),
            )
            existing["depends_on"] = self._clean_dependencies(
                existing.get("depends_on", []),
                existing.get("title", ""),
            )

        return list(grouped.values())

    def _action_key(self, action: Dict) -> str:
        text = f"{action.get('department')} {action.get('title')}".lower()

        if any(word in text for word in ["contract value", "currency", "pricing"]):
            return "commercial_value_currency"
        if any(word in text for word in ["payment", "cash-flow", "cash flow"]):
            return "finance_payment_cashflow"
        if any(word in text for word in ["supplier", "vendor"]):
            return "procurement_supplier"
        if any(word in text for word in ["customer", "buyer", "client"]):
            return "management_customer"
        if any(word in text for word in ["certificate", "document", "compliance", "submission"]):
            return "compliance_documents"
        if any(word in text for word in ["penalty", "liability", "legal"]):
            return "legal_penalty_liability"
        if any(word in text for word in ["warranty", "guarantee"]):
            return "operations_warranty"
        if any(word in text for word in ["delivery", "deadline", "lead time"]):
            return "operations_delivery_deadline"

        return " ".join(text.split())[:80]

    def _sort_actions(self, actions: List[Dict]) -> List[Dict]:
        return sorted(
            actions,
            key=lambda action: (
                self._priority_rank(action.get("priority")),
                self._department_rank(action.get("department")),
            ),
            reverse=True,
        )

    def _estimated_readiness(
        self,
        decision: Dict[str, Any],
        actions: List[Dict],
        commercial: Dict[str, Any],
    ) -> int:
        readiness = int(decision.get("score") or decision.get("confidence") or 50)
        has_productive_information = self._has_productive_information(commercial)
        has_missing_value = commercial.get("contract_value") in ["", "Unknown"] or not commercial.get("currency")

        for action in actions:
            priority = action.get("priority")
            if priority == "Critical":
                readiness -= 8
            elif priority == "High":
                readiness -= 5
            elif priority == "Medium":
                readiness -= 2

        if commercial.get("overall_commercial_risk") == "High":
            readiness -= 10
        elif commercial.get("overall_commercial_risk") == "Medium-High":
            readiness -= 4

        if has_productive_information and has_missing_value:
            readiness = max(readiness, 50)
            readiness = min(readiness, 60)
        elif not has_productive_information:
            readiness = min(readiness, 20)

        return max(0, min(100, readiness))

    def _overall_priority(self, actions: List[Dict]) -> str:
        if not actions:
            return "Low"

        return sorted(
            (action.get("priority", "Low") for action in actions),
            key=self._priority_rank,
            reverse=True,
        )[0]

    def _overall_status(
        self,
        estimated_readiness: int,
        actions: List[Dict],
        decision: Dict[str, Any],
    ) -> str:
        if decision.get("recommendation") == "NO GO":
            return "Blocked"

        critical_actions = [
            action for action in actions
            if action.get("priority") == "Critical"
        ]
        if critical_actions and estimated_readiness < 45:
            return "Blocked"

        if estimated_readiness >= 75 and not any(
            action.get("priority") == "High"
            for action in actions
        ):
            return "Ready"

        return "Needs Review"

    def _executive_summary(
        self,
        priority: str,
        overall_status: str,
        estimated_readiness: int,
        actions: List[Dict],
        decision: Dict[str, Any],
        commercial: Dict[str, Any],
    ) -> str:
        top_actions = [
            action.get("title", "")
            for action in actions[:3]
            if action.get("title")
        ]
        action_summary = ", ".join(top_actions) if top_actions else "No major actions"

        return (
            f"Status is {overall_status} with {estimated_readiness}% estimated readiness. "
            f"Priority is {priority}. Bid decision is {decision.get('recommendation', 'Needs review')}. "
            f"Commercial risk is {commercial.get('overall_commercial_risk', 'Unknown')}. "
            f"Immediate focus: {action_summary}."
        )

    def _combined_text(self, *groups) -> str:
        parts = []
        for group in groups:
            if not group:
                continue
            items = group if isinstance(group, list) else [group]
            parts.extend(str(item) for item in items if item)
        return " ".join(parts).lower()

    def _extract_tender_reference(self, text: str) -> str:
        patterns = [
            r"(Tender\s*(?:No|Number|#)?[:\-]?\s*[A-Z0-9\-\/]+)",
            r"(RFQ\s*(?:No|Number|#)?[:\-]?\s*[A-Z0-9\-\/]+)",
            r"(RFP\s*(?:No|Number|#)?[:\-]?\s*[A-Z0-9\-\/]+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return ""

    def _priority_from_text(self, text: str, default: str) -> str:
        lower = text.lower()
        if any(word in lower for word in ["blocker", "critical", "before approval"]):
            return "Critical"
        if any(word in lower for word in ["penalty", "missing", "deadline", "confirm"]):
            return "High"
        if any(word in lower for word in ["review", "verify"]):
            return "Medium"
        return default

    def _department_from_text(self, text: str) -> str:
        lower = text.lower()
        if any(word in lower for word in ["price", "commercial", "value", "currency"]):
            return "Commercial"
        if any(word in lower for word in ["payment", "cash", "invoice"]):
            return "Finance"
        if any(word in lower for word in ["supplier", "vendor"]):
            return "Procurement"
        if any(word in lower for word in ["penalty", "liability", "legal"]):
            return "Legal"
        if any(word in lower for word in ["certificate", "document", "submission", "compliance"]):
            return "Compliance"
        if any(word in lower for word in ["delivery", "warranty", "operations"]):
            return "Operations"
        return "Management"

    def _title_from_text(self, text: str) -> str:
        clean = " ".join(text.strip().split())
        return self._clean_title(clean)

    def _merge_sentence(self, first: str, second: str) -> str:
        values = self._merge_list([first], [second])
        return self._clean_sentence(" ".join(values))

    def _merge_list(self, first: List[str], second: List[str]) -> List[str]:
        merged = []
        seen = set()

        for value in list(first or []) + list(second or []):
            if not value:
                continue

            key = str(value).lower()
            if key in seen:
                continue

            seen.add(key)
            merged.append(value)

        return merged

    def _clean_title(self, value: str) -> str:
        text = str(value or "").strip()
        text = re.sub(r"^\s*\d+[\.\)]\s*", "", text)
        text = re.sub(r"\s+", " ", text)
        text = text.replace("...", "").strip(" .:-")

        title_map = [
            ("contract value", "Confirm contract value"),
            ("currency", "Confirm contract value"),
            ("payment", "Review payment exposure"),
            ("cash", "Review payment exposure"),
            ("supplier", "Confirm supplier identity"),
            ("customer", "Confirm customer context"),
            ("buyer", "Confirm customer context"),
            ("certificate", "Prepare mandatory documents"),
            ("document", "Prepare mandatory documents"),
            ("compliance", "Close compliance requirements"),
            ("submission", "Close submission requirements"),
            ("penalty", "Review penalty liability"),
            ("liability", "Review penalty liability"),
            ("warranty", "Validate warranty support"),
            ("production capacity", "Confirm delivery feasibility"),
            ("capacity", "Confirm delivery feasibility"),
            ("production", "Confirm delivery feasibility"),
            ("delivery", "Confirm delivery feasibility"),
            ("deadline", "Confirm delivery feasibility"),
            ("executive decision", "Review decision context"),
            ("business memory", "Review business memory"),
        ]

        lower = text.lower()
        for keyword, title in title_map:
            if keyword in lower:
                return title

        if any(
            phrase in lower
            for phrase in [
                "conduct a thorough review",
                "thorough review",
                "ensure timely",
                "assess capacity",
            ]
        ):
            return "Confirm delivery feasibility"

        words = text.split()
        if not words:
            return "Review management action"

        if len(words) > 8:
            return "Review management action"

        return " ".join(words).strip(" .:-")

    def _clean_sentence(self, value: str, max_words: int = 24) -> str:
        text = str(value or "").strip()
        text = re.sub(r"^\s*\d+[\.\)]\s*", "", text)
        text = re.sub(r"\s+", " ", text).strip()

        if not text:
            return "Review and close this action before approval."

        sentence = re.split(r"(?<=[.!?])\s+", text)[0].strip()
        words = sentence.split()

        if len(words) > max_words:
            sentence = " ".join(words[:max_words]).strip()

        sentence = sentence.strip(" .")
        if not sentence:
            return "Review and close this action before approval."

        return sentence + "."

    def _clean_dependencies(self, dependencies: List[str], title: str) -> List[str]:
        cleaned = []
        seen = set()
        action_title = self._clean_title(title).lower()

        for dependency in dependencies or []:
            dep = self._clean_title(str(dependency))
            key = dep.lower()

            if not dep or key == action_title or key in seen:
                continue

            seen.add(key)
            cleaned.append(dep)

        return cleaned

    def _has_productive_information(self, commercial: Dict[str, Any]) -> bool:
        return any(
            commercial.get(field)
            for field in [
                "payment_terms",
                "penalty_exposure",
                "warranty_liability",
            ]
        )

    def _highest_priority(self, first: str, second: str) -> str:
        return first if self._priority_rank(first) >= self._priority_rank(second) else second

    def _normalize_priority(self, value: str) -> str:
        value = str(value).strip()
        if value in ["Critical", "High", "Medium", "Low"]:
            return value
        return "Medium"

    def _normalize_department(self, value: str) -> str:
        value = str(value).strip()
        allowed = {
            "Commercial",
            "Legal",
            "Procurement",
            "Operations",
            "Compliance",
            "Finance",
            "Management",
        }
        return value if value in allowed else "Management"

    def _priority_rank(self, value: str) -> int:
        return {
            "Critical": 4,
            "High": 3,
            "Medium": 2,
            "Low": 1,
        }.get(str(value), 2)

    def _department_rank(self, value: str) -> int:
        return {
            "Management": 7,
            "Commercial": 6,
            "Finance": 5,
            "Legal": 4,
            "Compliance": 3,
            "Procurement": 2,
            "Operations": 1,
        }.get(str(value), 0)
