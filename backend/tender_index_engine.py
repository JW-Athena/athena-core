from typing import Dict, List

from entity_database import EntityDatabase


class TenderIndexEngine:

    def __init__(self):
        self.entity_database = EntityDatabase()

    def list_tenders(self) -> List[Dict]:

        entities = self.entity_database.list_entities(limit=10000)

        tenders = {}

        for entity in entities:

            if entity.get("entity_type") != "tender_reference":
                continue

            tender = entity.get("normalized_value") or entity.get("value")

            filename = entity.get("source_filename")

            if tender not in tenders:

                tenders[tender] = {
                    "tender_reference": tender,
                    "source_document": filename,
                }

        return list(tenders.values())