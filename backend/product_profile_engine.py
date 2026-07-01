import re
from typing import Dict, List

from entity_database import EntityDatabase


class ProductProfileEngine:
    def __init__(self):
        self.entity_database = EntityDatabase()

    def get_profile(self, product_name: str) -> Dict:
        product_entities = self.entity_database.search_entities(
            query=product_name,
            limit=100,
        )

        source_documents = []
        related_entities = []

        for entity in product_entities:
            if entity.get("entity_type") == "product":
                related_entities.append(entity)

            source_filename = entity.get("source_filename")
            if source_filename and source_filename not in source_documents:
                source_documents.append(source_filename)

        all_entities = self.entity_database.list_entities(limit=500)

        document_entities = [
            entity
            for entity in all_entities
            if entity.get("source_filename") in source_documents
        ]

        profile = {
            "product_name": product_name,
            "category": None,
            "quantities": [],
            "delivery_terms": [],
            "warranties": [],
            "payment_terms": [],
            "penalties": [],
            "locations": [],
            "source_documents": source_documents,
            "related_entities": related_entities,
        }

        for entity in document_entities:
            entity_type = entity.get("entity_type")
            normalized_value = entity.get("normalized_value")
            value = entity.get("value")
            category = entity.get("category")
            source_line = entity.get("source_line") or ""

            if entity_type == "product":
                profile["category"] = category or profile["category"]

                quantity = self._extract_quantity(source_line)
                if quantity:
                    self._append_unique(profile["quantities"], quantity)

            elif entity_type == "delivery_term":
                self._append_unique(profile["delivery_terms"], normalized_value or value)

            elif entity_type == "warranty":
                self._append_unique(profile["warranties"], normalized_value or value)

            elif entity_type == "payment_term":
                self._append_unique(profile["payment_terms"], normalized_value or value)

            elif entity_type == "penalty":
                self._append_unique(profile["penalties"], normalized_value or value)

            elif entity_type == "location":
                self._append_unique(profile["locations"], normalized_value or value)

        return {
            "status": "success",
            "profile": profile,
            "source_document_count": len(source_documents),
            "document_entity_count": len(document_entities),
        }

    def _extract_quantity(self, text: str):
        match = re.search(r"\b\d{2,}\b", text)
        if match:
            return int(match.group(0))
        return None

    def _append_unique(self, target: List, value):
        if value and value not in target:
            target.append(value)