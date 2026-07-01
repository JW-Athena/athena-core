import re
from typing import Dict, Optional


class EntityNormalizer:
    """
    Entity Normalizer

    Converts raw extracted entity text into cleaner business values.
    """

    def normalize_entity(
        self,
        entity_type: str,
        value: str,
        category: Optional[str] = None,
    ) -> Dict:

        clean_value = value.strip().lstrip("-").strip()

        if entity_type == "product":
            return self._normalize_product(clean_value, category)

        if entity_type == "location":
            return self._normalize_location(clean_value)

        if entity_type == "delivery_term":
            return self._normalize_delivery(clean_value)

        if entity_type == "warranty":
            return self._normalize_warranty(clean_value)

        if entity_type == "penalty":
            return self._normalize_penalty(clean_value)

        if entity_type == "payment_term":
            return self._normalize_payment(clean_value)

        return {
            "normalized_type": entity_type,
            "normalized_value": clean_value,
            "details": {},
        }

    def _normalize_product(self, value: str, category: Optional[str]) -> Dict:
        lower = value.lower()

        product_name = value

        if "tactical boots" in lower:
            product_name = "Tactical Boots"
        elif "boots" in lower:
            product_name = "Boots"
        elif "footwear" in lower:
            product_name = "Footwear"
        elif "fabric" in lower:
            product_name = "Fabric"
        elif "uniform" in lower:
            product_name = "Uniform"

        quantity = self._extract_quantity(value)

        return {
            "normalized_type": "product",
            "normalized_value": product_name,
            "details": {
                "category": category,
                "quantity": quantity,
            },
        }

    def _normalize_location(self, value: str) -> Dict:
        lower = value.lower()

        if "abu dhabi" in lower:
            location = "Abu Dhabi"
        elif "dubai" in lower:
            location = "Dubai"
        elif "sharjah" in lower:
            location = "Sharjah"
        elif "united arab emirates" in lower or "uae" in lower:
            location = "United Arab Emirates"
        else:
            location = value

        return {
            "normalized_type": "location",
            "normalized_value": location,
            "details": {},
        }

    def _normalize_delivery(self, value: str) -> Dict:
        delivery_days = self._extract_days(value)

        return {
            "normalized_type": "delivery_term",
            "normalized_value": f"{delivery_days} days" if delivery_days else value,
            "details": {
                "delivery_days": delivery_days,
            },
        }

    def _normalize_warranty(self, value: str) -> Dict:
        years = self._extract_years(value)

        return {
            "normalized_type": "warranty",
            "normalized_value": f"{years} years" if years else value,
            "details": {
                "warranty_years": years,
                "coverage": "manufacturing defects" if "defect" in value.lower() else None,
            },
        }

    def _normalize_penalty(self, value: str) -> Dict:
        percentage = self._extract_percentage(value)

        return {
            "normalized_type": "penalty",
            "normalized_value": f"{percentage}% per week" if percentage else value,
            "details": {
                "percentage": percentage,
                "frequency": "per week" if "week" in value.lower() else None,
            },
        }

    def _normalize_payment(self, value: str) -> Dict:
        days = self._extract_days(value)

        return {
            "normalized_type": "payment_term",
            "normalized_value": f"{days} days after delivery and acceptance" if days else value,
            "details": {
                "payment_days": days,
                "trigger": "after delivery and acceptance" if "delivery and acceptance" in value.lower() else None,
            },
        }

    def _extract_quantity(self, value: str) -> Optional[int]:
        match = re.search(r"\b\d{2,}\b", value)
        if match:
            return int(match.group(0))
        return None

    def _extract_days(self, value: str) -> Optional[int]:
        match = re.search(r"\b(\d+)\s*days?\b", value, re.IGNORECASE)
        if match:
            return int(match.group(1))
        return None

    def _extract_years(self, value: str) -> Optional[int]:
        match = re.search(r"\b(\d+)\s*years?\b|\b(\d+)\s*year\b", value, re.IGNORECASE)
        if match:
            return int(match.group(1) or match.group(2))
        return None

    def _extract_percentage(self, value: str) -> Optional[float]:
        match = re.search(r"(\d+(?:\.\d+)?)\s*%", value)
        if match:
            return float(match.group(1))
        return None