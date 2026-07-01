from typing import Dict

from entity_database import EntityDatabase


class TenderProfileEngine:

    def __init__(self):
        self.entity_database = EntityDatabase()

    def get_profile(self, tender_reference: str) -> Dict:

        tender_entities = self.entity_database.search_entities(
            query=tender_reference,
            limit=100,
        )

        if not tender_entities:
            return {
                "status": "not_found",
                "profile": {},
            }

        source_documents = []

        for entity in tender_entities:
            source = entity.get("source_filename")

            if source and source not in source_documents:
                source_documents.append(source)

        all_entities = self.entity_database.list_entities(limit=500)

        profile = {
            "tender_reference": tender_reference,
            "products": [],
            "delivery_terms": [],
            "payment_terms": [],
            "warranties": [],
            "penalties": [],
            "certificates": [],
            "deadlines": [],
            "locations": [],
            "source_documents": source_documents,
        }

        for entity in all_entities:

            if entity.get("source_filename") not in source_documents:
                continue

            value = entity.get("normalized_value") or entity.get("value")
            entity_type = entity.get("entity_type")

            if entity_type == "product":
                if value not in profile["products"]:
                    profile["products"].append(value)

            elif entity_type == "delivery_term":
                if value not in profile["delivery_terms"]:
                    profile["delivery_terms"].append(value)

            elif entity_type == "payment_term":
                if value not in profile["payment_terms"]:
                    profile["payment_terms"].append(value)

            elif entity_type == "warranty":
                if value not in profile["warranties"]:
                    profile["warranties"].append(value)

            elif entity_type == "penalty":
                if value not in profile["penalties"]:
                    profile["penalties"].append(value)

            elif entity_type == "certificate_or_required_document":
                if value not in profile["certificates"]:
                    profile["certificates"].append(value)

            elif entity_type == "deadline_or_date":
                if value not in profile["deadlines"]:
                    profile["deadlines"].append(value)

            elif entity_type == "location":
                if value not in profile["locations"]:
                    profile["locations"].append(value)

        return {
            "status": "success",
            "profile": profile,
        }