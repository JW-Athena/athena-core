from entity_database import EntityDatabase
from knowledge_engine import KnowledgeEngine


class DashboardEngine:
    def __init__(self):
        self.entity_database = EntityDatabase()
        self.knowledge_engine = KnowledgeEngine()

    def get_summary(self):
        documents = self.knowledge_engine.list_documents(limit=1000)
        entities = self.entity_database.list_entities(limit=1000)
        relationships = self.entity_database.list_relationships(limit=1000)

        products = [
            entity for entity in entities
            if entity.get("entity_type") == "product"
        ]

        risks = [
            entity for entity in entities
            if entity.get("entity_type") in ["penalty", "warranty"]
        ]

        tenders = [
            entity for entity in entities
            if entity.get("entity_type") == "tender_reference"
        ]

        primary_product = products[0].get("normalized_value") if products else "None"

        return {
            "documents_processed": len(documents),
            "entities_stored": len(entities),
            "relationships": len(relationships),
            "products_identified": len(products),
            "open_risks": len(risks),
            "tenders_identified": len(tenders),
            "primary_product": primary_product,
        }