from typing import Dict

from entity_database import EntityDatabase


class SupplierProfileEngine:

    def __init__(self):
        self.entity_database = EntityDatabase()

    def get_profile(
        self,
        supplier_name: str,
    ) -> Dict:

        entities = self.entity_database.search_entities(
            query=supplier_name,
            limit=500,
        )

        profile = {
            "supplier_name": supplier_name,
            "products": [],
            "contracts": [],
            "locations": [],
            "certificates": [],
            "documents": [],
        }

        for entity in entities:

            entity_type = entity.get("entity_type")

            value = entity.get("normalized_value") or entity.get("value")

            if entity_type == "product":
                if value not in profile["products"]:
                    profile["products"].append(value)

            elif entity_type == "certificate_or_required_document":
                if value not in profile["certificates"]:
                    profile["certificates"].append(value)

            elif entity_type == "location":
                if value not in profile["locations"]:
                    profile["locations"].append(value)

            source = entity.get("source_filename")

            if source and source not in profile["documents"]:
                profile["documents"].append(source)

        return {
            "status": "success",
            "profile": profile,
        }