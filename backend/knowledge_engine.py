import json
import os
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional


class KnowledgeEngine:
    def __init__(self, database_path: str = "database/athena_knowledge.db"):
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
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT NOT NULL,
                    document_type TEXT,
                    title TEXT,
                    summary TEXT,
                    full_text TEXT,
                    intelligence_json TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )

            conn.commit()

    def save_document(
        self,
        filename: str,
        document_type: Optional[str],
        full_text: str,
        intelligence: Dict[str, Any],
    ) -> Dict[str, Any]:
        title = (
            intelligence.get("executive_title")
            or intelligence.get("document_reference")
            or filename
        )

        summary = (
            intelligence.get("executive_summary")
            or intelligence.get("decision_summary_for_ceo")
            or ""
        )

        created_at = datetime.utcnow().isoformat()

        with self._connect() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO documents (
                    filename,
                    document_type,
                    title,
                    summary,
                    full_text,
                    intelligence_json,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    filename,
                    document_type,
                    title,
                    summary,
                    full_text,
                    json.dumps(intelligence, ensure_ascii=False),
                    created_at,
                ),
            )

            document_id = cursor.lastrowid
            conn.commit()

        return {
            "saved": True,
            "document_id": document_id,
            "filename": filename,
            "document_type": document_type,
            "title": title,
            "created_at": created_at,
        }

    def list_documents(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT id, filename, document_type, title, summary, created_at
                FROM documents
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            )

            rows = cursor.fetchall()

        return [
            {
                "id": row[0],
                "filename": row[1],
                "document_type": row[2],
                "title": row[3],
                "summary": row[4],
                "created_at": row[5],
            }
            for row in rows
        ]

    def get_document(self, document_id: int) -> Dict[str, Any]:
        with self._connect() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT id, filename, document_type, title, summary, full_text, intelligence_json, created_at
                FROM documents
                WHERE id = ?
                """,
                (document_id,),
            )

            row = cursor.fetchone()

        if not row:
            return {
                "found": False,
                "message": "Document not found",
            }

        return {
            "found": True,
            "id": row[0],
            "filename": row[1],
            "document_type": row[2],
            "title": row[3],
            "summary": row[4],
            "full_text": row[5],
            "intelligence": json.loads(row[6]) if row[6] else {},
            "created_at": row[7],
        }

    def search_documents(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        search_term = f"%{query}%"

        with self._connect() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT id, filename, document_type, title, summary, created_at
                FROM documents
                WHERE filename LIKE ?
                   OR document_type LIKE ?
                   OR title LIKE ?
                   OR summary LIKE ?
                   OR full_text LIKE ?
                   OR intelligence_json LIKE ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (
                    search_term,
                    search_term,
                    search_term,
                    search_term,
                    search_term,
                    search_term,
                    limit,
                ),
            )

            rows = cursor.fetchall()

        return [
            {
                "id": row[0],
                "filename": row[1],
                "document_type": row[2],
                "title": row[3],
                "summary": row[4],
                "created_at": row[5],
            }
            for row in rows
        ]