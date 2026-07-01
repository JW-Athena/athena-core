import json
import os
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional


class EntityDatabase:
    def __init__(self, database_path: str = "database/athena_entities.db"):
        self.database_path = database_path
        self._ensure_database_folder()
        self._create_tables()

    def _ensure_database_folder(self) -> None:
        folder = os.path.dirname(self.database_path)
        if folder and not os.path.exists(folder):
            os.makedirs(folder)

    def _connect(self):
        return sqlite3.connect(self.database_path)

    def _create_tables(self) -> None:
        with self._connect() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS entities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entity_type TEXT NOT NULL,
                    value TEXT NOT NULL,
                    category TEXT,
                    source_filename TEXT,
                    source_document_type TEXT,
                    source_line TEXT,
                    metadata_json TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS relationships (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    relationship_type TEXT NOT NULL,
                    from_entity TEXT NOT NULL,
                    to_entity TEXT NOT NULL,
                    source_filename TEXT,
                    metadata_json TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )

            conn.commit()

    def save_extraction(
        self,
        filename: str,
        document_type: Optional[str],
        extraction: Dict,
    ) -> Dict:
        entities_saved = []
        relationships_saved = []

        entities = extraction.get("entities", {})

        for group_name, group_items in entities.items():
            for item in group_items:
                saved = self.save_entity(
                    entity_type=item.get("type") or group_name,
                    value=item.get("value", ""),
                    category=item.get("category"),
                    source_filename=filename,
                    source_document_type=document_type,
                    source_line=item.get("source_line"),
                    metadata=item,
                )
                entities_saved.append(saved)

        for relationship in extraction.get("relationships", []):
            saved_relationship = self.save_relationship(
                relationship_type=relationship.get("relationship", ""),
                from_entity=relationship.get("from", ""),
                to_entity=relationship.get("to", ""),
                source_filename=filename,
                metadata=relationship,
            )
            relationships_saved.append(saved_relationship)

        return {
            "saved": True,
            "filename": filename,
            "entities_saved_count": len(entities_saved),
            "relationships_saved_count": len(relationships_saved),
            "entities_saved": entities_saved,
            "relationships_saved": relationships_saved,
        }

    def save_entity(
        self,
        entity_type: str,
        value: str,
        category: Optional[str],
        source_filename: Optional[str],
        source_document_type: Optional[str],
        source_line: Optional[str],
        metadata: Optional[Dict],
    ) -> Dict:
        value = value.strip()

        if not value:
            return {
                "saved": False,
                "reason": "Empty entity value",
            }

        created_at = datetime.utcnow().isoformat()

        with self._connect() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO entities (
                    entity_type,
                    value,
                    category,
                    source_filename,
                    source_document_type,
                    source_line,
                    metadata_json,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entity_type,
                    value,
                    category,
                    source_filename,
                    source_document_type,
                    source_line,
                    json.dumps(metadata or {}, ensure_ascii=False),
                    created_at,
                ),
            )

            entity_id = cursor.lastrowid
            conn.commit()

        return {
            "saved": True,
            "entity_id": entity_id,
            "entity_type": entity_type,
            "value": value,
            "category": category,
        }

    def save_relationship(
        self,
        relationship_type: str,
        from_entity: str,
        to_entity: str,
        source_filename: Optional[str],
        metadata: Optional[Dict],
    ) -> Dict:
        created_at = datetime.utcnow().isoformat()

        with self._connect() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO relationships (
                    relationship_type,
                    from_entity,
                    to_entity,
                    source_filename,
                    metadata_json,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    relationship_type,
                    from_entity,
                    to_entity,
                    source_filename,
                    json.dumps(metadata or {}, ensure_ascii=False),
                    created_at,
                ),
            )

            relationship_id = cursor.lastrowid
            conn.commit()

        return {
            "saved": True,
            "relationship_id": relationship_id,
            "relationship_type": relationship_type,
            "from": from_entity,
            "to": to_entity,
        }

    def list_entities(self, limit: int = 50) -> List[Dict]:
        with self._connect() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT id, entity_type, value, category, source_filename, source_document_type, source_line, created_at
                FROM entities
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            )

            rows = cursor.fetchall()

        return [
            {
                "id": row[0],
                "entity_type": row[1],
                "value": row[2],
                "category": row[3],
                "source_filename": row[4],
                "source_document_type": row[5],
                "source_line": row[6],
                "created_at": row[7],
            }
            for row in rows
        ]

    def search_entities(self, query: str, limit: int = 50) -> List[Dict]:
        search = f"%{query}%"

        with self._connect() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT id, entity_type, value, category, source_filename, source_document_type, source_line, created_at
                FROM entities
                WHERE entity_type LIKE ?
                   OR value LIKE ?
                   OR category LIKE ?
                   OR source_filename LIKE ?
                   OR source_line LIKE ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (search, search, search, search, search, limit),
            )

            rows = cursor.fetchall()

        return [
            {
                "id": row[0],
                "entity_type": row[1],
                "value": row[2],
                "category": row[3],
                "source_filename": row[4],
                "source_document_type": row[5],
                "source_line": row[6],
                "created_at": row[7],
            }
            for row in rows
        ]

    def list_relationships(self, limit: int = 50) -> List[Dict]:
        with self._connect() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT id, relationship_type, from_entity, to_entity, source_filename, created_at
                FROM relationships
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            )

            rows = cursor.fetchall()

        return [
            {
                "id": row[0],
                "relationship_type": row[1],
                "from": row[2],
                "to": row[3],
                "source_filename": row[4],
                "created_at": row[5],
            }
            for row in rows
        ]