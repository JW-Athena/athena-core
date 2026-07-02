import re
from typing import Any, Dict, List, Optional

from business_memory_engine import BusinessMemoryEngine
from commercial_exposure_engine import CommercialExposureEngine
from document_intelligence_engine import DocumentIntelligenceEngine
from entity_intelligence_engine import EntityIntelligenceEngine
from executive_decision_engine import ExecutiveDecisionEngine
from knowledge_engine import KnowledgeEngine
from risk_register_engine import RiskRegisterEngine
from timing_utils import cached_step, new_request_context, timed_step


class ContractIntelligenceEngine:
    """
    Contract Intelligence

    Extracts and evaluates contractual obligations, liabilities, and key
    commercial/legal terms by reusing existing ATHENA intelligence outputs.
    """

    def __init__(self):
        self.document_engine = DocumentIntelligenceEngine()
        self.entity_engine = EntityIntelligenceEngine()
        self.risk_register_engine = RiskRegisterEngine()
        self.commercial_engine = CommercialExposureEngine()
        self.executive_decision_engine = ExecutiveDecisionEngine()
        self.business_memory_engine = BusinessMemoryEngine()
        self.knowledge_engine = KnowledgeEngine()

    def analyze(
        self,
        text: str,
        document_type: Optional[str] = None,
        request_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        request_context = new_request_context(request_context)

        return cached_step(
            request_context=request_context,
            cache_key="contract_intelligence.analyze",
            engine="contract_intelligence",
            step="analyze",
            callback=lambda: self._analyze_uncached(
                text=text,
                document_type=document_type,
                request_context=request_context,
            ),
        )

    def _analyze_uncached(
        self,
        text: str,
        document_type: Optional[str],
        request_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        clean_text = self._clean_text(text)
        document = self._safe_call(
            "document_intelligence",
            lambda: cached_step(
                request_context=request_context,
                cache_key="document_intelligence.analyze",
                engine="document_intelligence",
                step="analyze",
                callback=lambda: self.document_engine.analyze(
                    text=clean_text,
                    document_type=document_type,
                ),
            ),
            request_context,
        )
        entities = self._safe_call(
            "entity_intelligence",
            lambda: cached_step(
                request_context=request_context,
                cache_key="entity_intelligence.extract",
                engine="entity_intelligence",
                step="extract",
                callback=lambda: self.entity_engine.extract(
                    text=clean_text,
                    document_type=document_type,
                ),
            ),
            request_context,
        )
        risk_result = self._safe_call(
            "risk_register",
            lambda: self.risk_register_engine.generate(
                text=clean_text,
                document_type=document_type,
                request_context=request_context,
            ),
            request_context,
        )
        commercial_result = self._safe_call(
            "commercial_exposure",
            lambda: self.commercial_engine.analyze(
                text=clean_text,
                document_type=document_type,
                request_context=request_context,
            ),
            request_context,
        )

        entity_groups = entities.get("entities", {})
        risk_register = risk_result.get("risk_register", {})
        commercial = commercial_result.get("commercial_exposure", {})
        executive_decision = self._executive_decision_context(clean_text)
        memory_count = self._business_memory_count(clean_text, document_type, document)
        knowledge_count = self._knowledge_count(document_type)

        key_terms = self._key_terms(
            text=clean_text,
            document=document,
            entities=entity_groups,
            commercial=commercial,
        )
        missing_information = self._missing_contract_information(
            key_terms=key_terms,
            text=clean_text,
            document=document,
        )
        legal_obligations = self._legal_obligations(clean_text, entity_groups)
        commercial_obligations = self._commercial_obligations(clean_text, entity_groups, commercial)
        critical_clauses = self._critical_clauses(clean_text, entity_groups, risk_register)
        overall_risk = self._overall_contract_risk(
            risk_register=risk_register,
            commercial=commercial,
            critical_clauses=critical_clauses,
            missing_information=missing_information,
        )
        confidence = self._confidence_label(
            document=document,
            entities=entities,
            risk_register=risk_register,
            missing_information=missing_information,
        )

        result = {
            "engine": "contract_intelligence",
            "status": "success",
            "contract_intelligence": {
                "contract_type": self._contract_type(clean_text, document_type, document),
                "confidence": confidence,
                "overall_contract_risk": overall_risk,
                "contract_summary": self._contract_summary(
                    contract_type=self._contract_type(clean_text, document_type, document),
                    overall_risk=overall_risk,
                    key_terms=key_terms,
                    critical_clauses=critical_clauses,
                ),
                "key_terms": key_terms,
                "legal_obligations": legal_obligations,
                "commercial_obligations": commercial_obligations,
                "critical_clauses": critical_clauses,
                "missing_contract_information": missing_information,
                "executive_assessment": self._executive_assessment(
                    overall_risk=overall_risk,
                    confidence=confidence,
                    commercial=commercial,
                    missing_information=missing_information,
                    executive_decision=executive_decision,
                    memory_count=memory_count,
                    knowledge_count=knowledge_count,
                ),
                "recommended_actions": self._recommended_actions(
                    overall_risk=overall_risk,
                    missing_information=missing_information,
                    critical_clauses=critical_clauses,
                    commercial=commercial,
                ),
            },
        }
        timed_step(
            request_context=request_context,
            engine="contract_intelligence",
            step="assemble",
            callback=lambda: None,
        )
        return result

    def _safe_call(self, name: str, callback, request_context: Dict[str, Any]) -> Dict[str, Any]:
        try:
            result = timed_step(
                request_context=request_context,
                engine="contract_intelligence",
                step=f"call_{name}",
                callback=callback,
            )
            return result if isinstance(result, dict) else {}
        except Exception as exc:
            print(f"[contract_intelligence] engine={name} status=skipped error={exc}")
            return {}

    def _key_terms(
        self,
        text: str,
        document: Dict[str, Any],
        entities: Dict[str, Any],
        commercial: Dict[str, Any],
    ) -> Dict[str, str]:
        terms = {
            "contract_value": self._first_value(
                commercial.get("contract_value"),
                self._contract_amount_from_text(text),
            ),
            "currency": self._first_value(
                commercial.get("currency"),
                self._currency_from_text(text),
            ),
            "payment_terms": self._first_value(
                commercial.get("payment_terms"),
                self._entity_values(entities.get("payment_terms", [])),
                self._line_after_heading(text, "payment terms"),
            ),
            "delivery_terms": self._first_value(
                self._entity_values(entities.get("delivery_terms", [])),
                self._line_after_heading(text, "delivery terms"),
                self._find_line(text, ["delivery", "deliver", "lead time"]),
            ),
            "contract_duration": self._find_line(text, ["contract duration", "term of contract", "agreement term", "duration"]),
            "warranty_period": self._first_value(
                self._entity_values(entities.get("warranties", [])),
                self._find_line(text, ["warranty", "guarantee"]),
            ),
            "renewal_terms": self._find_line(text, ["renewal", "renew", "extension"]),
            "termination_terms": self._find_line(text, ["termination", "terminate", "termination for convenience", "termination for cause"]),
        }
        normalized = {
            key: self._normalize_term_value(value)
            for key, value in terms.items()
        }
        normalized["payment_terms"] = self._normalize_payment_terms(
            normalized.get("payment_terms")
        )
        return normalized

    def _missing_contract_information(
        self,
        key_terms: Dict[str, str],
        text: str,
        document: Dict[str, Any],
    ) -> List[str]:
        missing = []
        required_terms = {
            "contract_value": "Contract value is not clearly stated.",
            "currency": "Currency is not clearly stated.",
            "payment_terms": "Payment terms are not clearly stated.",
            "delivery_terms": "Delivery terms are not clearly stated.",
            "contract_duration": "Contract duration or term is not clearly stated.",
            "warranty_period": "Warranty or guarantee period is not clearly stated.",
            "renewal_terms": "Renewal or extension terms are not clearly stated.",
            "termination_terms": "Termination terms are not clearly stated.",
        }

        for field, message in required_terms.items():
            if key_terms.get(field) in ["", "Not stated"]:
                missing.append(message)

        requirements = document.get("detected_requirements", {}) or {}
        if not requirements.get("has_penalty_terms") and "penalty" not in text.lower():
            missing.append("Penalty or liability position is not clearly stated.")

        return self._unique_text(missing)

    def _legal_obligations(self, text: str, entities: Dict[str, Any]) -> List[str]:
        obligations = []
        obligations.extend(self._lines_for_keywords(text, ["shall", "must", "required to", "responsible for"], limit=12))
        document_obligation = self._required_document_obligation(entities)
        if document_obligation:
            obligations.append(document_obligation)
        obligations.extend(self._entity_value_list(entities.get("warranties", [])))
        return self._clean_obligation_list(obligations)[:12]

    def _commercial_obligations(
        self,
        text: str,
        entities: Dict[str, Any],
        commercial: Dict[str, Any],
    ) -> List[str]:
        obligations = []
        payment_obligation = self._payment_obligation_from_terms(commercial.get("payment_terms"))
        if not payment_obligation:
            payment_obligation = self._payment_obligation_from_terms(
                self._entity_values(entities.get("payment_terms", []))
            )
        if payment_obligation:
            obligations.append(payment_obligation)
        obligations.extend(self._entity_value_list(entities.get("delivery_terms", [])))
        for obligation in self._lines_for_keywords(text, ["invoice", "retention", "advance", "delivery"], limit=10):
            if payment_obligation and self._looks_like_payment_timing(obligation):
                continue
            obligations.append(obligation)

        if commercial.get("contract_value") not in ["", "Unknown", "Not stated", None]:
            obligations.append(f"Contract value: {commercial.get('contract_value')}")
        return self._dedupe_normalized_obligations(
            self._clean_obligation_list(obligations)
        )[:12]

    def _critical_clauses(
        self,
        text: str,
        entities: Dict[str, Any],
        risk_register: Dict[str, Any],
    ) -> List[Dict[str, str]]:
        clauses = []
        clause_keywords = {
            "Penalty": ["penalty", "liquidated damages", "delay damages", "fine"],
            "Liability": ["liability", "limitation of liability", "damages"],
            "Warranty": ["warranty", "guarantee", "defect", "replacement"],
            "Indemnity": ["indemnity", "indemnify"],
            "Confidentiality": ["confidentiality", "confidential", "non-disclosure", "nda"],
            "Termination": ["termination", "terminate"],
            "Force Majeure": ["force majeure", "act of god"],
            "Performance Security": ["performance bond", "bank guarantee", "security deposit"],
        }

        for clause_type, keywords in clause_keywords.items():
            line = self._find_line(text, keywords)
            if self._is_meaningful_clause_summary(line):
                clauses.append(
                    {
                        "clause_type": clause_type,
                        "risk_level": self._clause_risk_level(clause_type, line),
                        "summary": line,
                    }
                )

        for penalty in entities.get("penalties", []) or []:
            value = str(penalty.get("value", "")).strip()
            if self._is_meaningful_clause_summary(value):
                clauses.append(
                    {
                        "clause_type": "Penalty",
                        "risk_level": "High",
                        "summary": self._clean_sentence(value),
                    }
                )

        for risk in risk_register.get("risks", []) or []:
            if risk.get("severity") in ["Critical", "High"] and risk.get("category") in ["Legal", "Warranty", "Financial"]:
                clauses.append(
                    {
                        "clause_type": str(risk.get("category", "Critical Clause")),
                        "risk_level": str(risk.get("severity", "High")),
                        "summary": str(risk.get("title") or risk.get("description") or "Critical clause requires review."),
                    }
                )

        return self._dedupe_clause_dicts(clauses)[:10]

    def _overall_contract_risk(
        self,
        risk_register: Dict[str, Any],
        commercial: Dict[str, Any],
        critical_clauses: List[Dict[str, str]],
        missing_information: List[str],
    ) -> str:
        levels = [
            risk_register.get("overall_risk_level"),
            commercial.get("overall_commercial_risk"),
        ]
        levels.extend(clause.get("risk_level") for clause in critical_clauses)

        if "Critical" in levels:
            return "Critical"
        if "High" in levels:
            return "High"
        if len(missing_information) >= 5:
            return "High"
        if "Medium-High" in levels or "Medium" in levels:
            return "Medium"
        return "Low"

    def _confidence_label(
        self,
        document: Dict[str, Any],
        entities: Dict[str, Any],
        risk_register: Dict[str, Any],
        missing_information: List[str],
    ) -> str:
        values = [
            self._number_or_default(document.get("confidence_score"), default=None),
            self._number_or_default(entities.get("confidence_score"), default=None),
        ]
        values = [value for value in values if value is not None]
        confidence = round(sum(values) / len(values)) if values else 55

        confidence -= min(len(missing_information) * 5, 35)
        if not risk_register:
            confidence -= 10

        if confidence >= 75:
            return "High"
        if confidence >= 45:
            return "Medium"
        return "Low"

    def _contract_summary(
        self,
        contract_type: str,
        overall_risk: str,
        key_terms: Dict[str, str],
        critical_clauses: List[Dict[str, str]],
    ) -> str:
        return (
            f"{contract_type} reviewed for contractual obligations and commercial/legal terms. "
            f"Overall contract risk is {overall_risk}. "
            f"Payment terms are {str(key_terms.get('payment_terms') or 'Not stated').rstrip('.')}. "
            f"Critical clauses identified: {len(critical_clauses)}."
        )

    def _executive_assessment(
        self,
        overall_risk: str,
        confidence: str,
        commercial: Dict[str, Any],
        missing_information: List[str],
        executive_decision: Dict[str, Any],
        memory_count: int,
        knowledge_count: int,
    ) -> str:
        decision_context = executive_decision.get("recommendation")

        if overall_risk in ["Critical", "High"]:
            return (
                f"Contract risk is {overall_risk}. Executive approval should remain on hold until "
                f"material risks are reviewed and {len(missing_information)} contract information gap(s) are closed."
            )

        return (
            f"Contract terms appear manageable subject to closure of missing information. "
            f"Confidence is {confidence}; commercial exposure is {commercial.get('overall_commercial_risk', 'Unknown')}."
        )

    def _recommended_actions(
        self,
        overall_risk: str,
        missing_information: List[str],
        critical_clauses: List[Dict[str, str]],
        commercial: Dict[str, Any],
    ) -> List[str]:
        actions = []

        if missing_information:
            actions.append("Close missing contract information before executive approval.")
        if critical_clauses:
            actions.append("Assign owners to review critical clauses and quantify exposure.")
        if commercial.get("contract_value") in ["", "Unknown", "Not stated", None] or not commercial.get("currency"):
            actions.append("Confirm contract value, pricing basis, and currency.")
        if commercial.get("penalty_exposure"):
            actions.append("Review penalty exposure and confirm whether it is acceptable or negotiable.")
        if overall_risk in ["Critical", "High"]:
            actions.append("Hold approval until legal, commercial, and operational risks are reviewed by management.")

        if not actions:
            actions.append("Proceed with final contract review and management approval.")

        return self._unique_text(actions)[:8]

    def _contract_type(
        self,
        text: str,
        document_type: Optional[str],
        document: Dict[str, Any],
    ) -> str:
        lower = text.lower()
        if "framework agreement" in lower:
            return "Framework Agreement"
        if "service agreement" in lower:
            return "Service Agreement"
        if "purchase order" in lower:
            return "Purchase Order"
        if "tender" in lower:
            return "Tender / Contract-Like Document"
        if "contract" in lower or "agreement" in lower:
            return "Contract"
        return document.get("document_type") or document_type or "Contract-Like Document"

    def _executive_decision_context(self, text: str) -> Dict[str, Any]:
        tender_reference = self._extract_tender_reference(text)
        if not tender_reference:
            return {}

        try:
            return self.executive_decision_engine.evaluate_tender(tender_reference)
        except Exception:
            return {}

    def _business_memory_count(
        self,
        text: str,
        document_type: Optional[str],
        document: Dict[str, Any],
    ) -> int:
        subjects = [
            self._extract_tender_reference(text),
            document_type,
            document.get("document_type"),
        ]

        for subject in subjects:
            if not subject:
                continue
            try:
                return len(self.business_memory_engine.recall(str(subject)))
            except Exception:
                continue
        return 0

    def _knowledge_count(self, document_type: Optional[str]) -> int:
        if not document_type:
            return 0
        try:
            return len(self.knowledge_engine.search_documents(document_type, limit=5))
        except Exception:
            return 0

    def _clean_text(self, text: str) -> str:
        text = str(text or "").replace("\x00", " ")
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def _entity_values(self, items: List[Dict[str, Any]]) -> str:
        return "; ".join(self._entity_value_list(items))

    def _entity_value_list(self, items: List[Dict[str, Any]]) -> List[str]:
        values = []
        for item in items or []:
            value = str(item.get("value", "")).strip()
            if value:
                values.append(value)
        return self._unique_text(values)

    def _lines_for_keywords(self, text: str, keywords: List[str], limit: int) -> List[str]:
        results = []
        for line in text.splitlines():
            clean = line.strip().lstrip("-").strip()
            lower = clean.lower()
            if clean and any(keyword in lower for keyword in keywords):
                results.append(clean)
        return self._unique_text(results)[:limit]

    def _find_line(self, text: str, keywords: List[str]) -> str:
        for line in text.splitlines():
            clean = line.strip().lstrip("-").strip()
            lower = clean.lower()
            if clean and any(keyword in lower for keyword in keywords):
                return clean
        return ""

    def _line_after_heading(self, text: str, heading: str) -> str:
        lines = [line.strip() for line in text.splitlines()]
        heading = heading.lower().strip()

        for index, line in enumerate(lines):
            if line.lower().rstrip(":") == heading:
                for next_line in lines[index + 1:]:
                    if next_line.strip():
                        return next_line.strip().lstrip("-").strip()

        return ""

    def _contract_amount_from_text(self, text: str) -> str:
        for line in text.splitlines():
            lower = line.lower()
            if any(word in lower for word in ["penalty", "warranty", "days", "delivery", "closing date"]):
                continue

            if not any(word in lower for word in ["value", "amount", "price", "total", "contract sum"]):
                continue

            match = re.search(
                r"(?:AED|USD|EUR|SAR|\$)\s?\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?|\d{1,3}(?:,\d{3})+(?:\.\d{1,2})?",
                line,
                flags=re.IGNORECASE,
            )
            if match:
                return match.group(0).strip()

        return ""

    def _currency_from_text(self, text: str) -> str:
        lower = text.lower()
        if "aed" in lower or "dirham" in lower:
            return "AED"
        if "usd" in lower or "$" in text:
            return "USD"
        if "eur" in lower:
            return "EUR"
        if "sar" in lower:
            return "SAR"
        return ""

    def _clause_risk_level(self, clause_type: str, value: str) -> str:
        lower = value.lower()
        if clause_type in ["Penalty", "Liability", "Performance Security"] or "liquidated damages" in lower:
            return "High"
        if clause_type in ["Warranty", "Termination", "Indemnity"]:
            return "Medium"
        return "Low"

    def _dedupe_clause_dicts(self, clauses: List[Dict[str, str]]) -> List[Dict[str, str]]:
        grouped: Dict[str, Dict[str, str]] = {}

        for clause in clauses:
            key = self._clause_group_key(clause)
            current = grouped.get(key)
            if current is None or self._clause_informativeness(clause) > self._clause_informativeness(current):
                grouped[key] = clause

        return list(grouped.values())

    def _clause_group_key(self, clause: Dict[str, str]) -> str:
        clause_type = str(clause.get("clause_type") or "").lower()
        summary = str(clause.get("summary") or "").lower()
        text = f"{clause_type} {summary}"

        if any(word in text for word in ["penalty", "liquidated damages", "delay damages"]):
            return "penalty"
        if any(word in text for word in ["warranty", "guarantee", "defect", "replacement"]):
            return "warranty"
        if "termination" in text or "terminate" in text:
            return "termination"
        if "indemn" in text:
            return "indemnity"
        if "confidential" in text or "non-disclosure" in text:
            return "confidentiality"
        if "force majeure" in text:
            return "force_majeure"
        if any(word in text for word in ["performance bond", "bank guarantee", "security deposit"]):
            return "performance_security"

        return clause_type or summary[:40]

    def _clause_informativeness(self, clause: Dict[str, str]) -> int:
        summary = str(clause.get("summary") or "")
        score = len(summary.split())

        if any(char.isdigit() for char in summary):
            score += 6
        if clause.get("risk_level") == "Critical":
            score += 2
        if summary.lower().endswith("exposure") or summary.lower().endswith("liability"):
            score -= 4

        return score

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

    def _first_value(self, *values) -> str:
        for value in values:
            if value not in (None, "", [], {}, "Unknown"):
                return str(value)
        return ""

    def _normalize_term_value(self, value: Any) -> str:
        text = str(value or "").strip()
        if not text or text == "Unknown":
            return "Not stated"
        return self._clean_sentence(text)

    def _normalize_payment_terms(self, value: Any) -> str:
        text = str(value or "").strip().rstrip(".")
        if not text or text == "Not stated":
            return "Not stated"

        days = self._days_from_text(text)
        lower = text.lower()
        if days and "delivery" in lower and "acceptance" in lower:
            return f"Payment to be made {days} days after delivery and acceptance."
        if days:
            return f"Payment to be made within {days} days."
        if lower.startswith("payment "):
            return self._clean_sentence(text)
        return self._clean_sentence(f"Payment terms: {text}")

    def _payment_obligation_from_terms(self, value: Any) -> str:
        payment_terms = self._normalize_payment_terms(value)
        if payment_terms == "Not stated":
            return ""

        days = self._days_from_text(payment_terms)
        lower = payment_terms.lower()
        if days and "delivery" in lower and "acceptance" in lower:
            return f"Payment is due {days} days after delivery and acceptance."
        if days:
            return f"Payment is due within {days} days."
        return payment_terms

    def _looks_like_payment_timing(self, value: Any) -> bool:
        text = str(value or "").lower()
        return bool(self._days_from_text(text)) and "delivery" in text and "acceptance" in text

    def _days_from_text(self, value: Any) -> int:
        match = re.search(r"\b(\d+)\s*days?\b", str(value or ""), flags=re.IGNORECASE)
        if match:
            return int(match.group(1))
        return 0

    def _required_document_obligation(self, entities: Dict[str, Any]) -> str:
        documents = self._entity_value_list(entities.get("certificates", []))
        documents = [
            document
            for document in documents
            if not self._is_heading_only(document)
        ]

        if not documents:
            return ""

        return f"Submit {self._join_human_list(documents)}."

    def _clean_obligation_list(self, obligations: List[str]) -> List[str]:
        cleaned = []

        for obligation in obligations:
            text = self._clean_sentence(obligation)
            if not text or self._is_heading_only(text):
                continue
            if self._is_standalone_document_name(text):
                continue
            cleaned.append(text)

        return self._unique_text(cleaned)

    def _dedupe_normalized_obligations(self, obligations: List[str]) -> List[str]:
        results = []
        seen = set()

        for obligation in obligations:
            key = obligation.lower()
            key = re.sub(r"^(payment terms|delivery terms|contract value)\s*:\s*", "", key)
            key = key.strip(" .")

            if key in seen:
                continue

            seen.add(key)
            results.append(obligation)

        return results

    def _is_standalone_document_name(self, value: str) -> bool:
        text = str(value or "").strip().rstrip(".").lower()
        document_names = {
            "trade license",
            "vat certificate",
            "iso certificate",
            "technical compliance sheet",
            "product test report",
            "test report",
        }
        return text in document_names

    def _is_heading_only(self, value: str) -> bool:
        text = str(value or "").strip().rstrip(":").rstrip(".").lower()
        headings = {
            "penalty",
            "payment terms",
            "delivery terms",
            "required documents",
            "technical specifications",
            "submission",
            "warranty",
            "guarantee",
        }
        return text in headings

    def _is_meaningful_clause_summary(self, value: str) -> bool:
        text = str(value or "").strip()
        if not text or self._is_heading_only(text):
            return False
        return len(text.split()) >= 4

    def _clean_sentence(self, value: Any) -> str:
        text = " ".join(str(value or "").split()).strip(" ;:")
        if not text:
            return ""
        if text.endswith("."):
            return text
        return text + "."

    def _join_human_list(self, values: List[str]) -> str:
        cleaned = [str(value).strip().rstrip(".") for value in values if value]
        if len(cleaned) <= 1:
            return "".join(cleaned)
        if len(cleaned) == 2:
            return f"{cleaned[0]} and {cleaned[1]}"
        return ", ".join(cleaned[:-1]) + f", and {cleaned[-1]}"

    def _number_or_default(self, value: Any, default: Any) -> Any:
        try:
            return int(value)
        except Exception:
            return default

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
