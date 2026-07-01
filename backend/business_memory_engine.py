import json
import os
import sqlite3
from datetime import datetime
from typing import Dict, List


class BusinessMemoryEngine:

    def __init__(self):
        self.database = "database/business_memory.db"
        self._initialize()

    def _connect(self):
        return sqlite3.connect(self.database)

    def _initialize(self):

        os.makedirs("database", exist_ok=True)

        with self._connect() as conn:

            cursor = conn.cursor()

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS business_memory (

                    id INTEGER PRIMARY KEY AUTOINCREMENT,

                    memory_type TEXT NOT NULL,

                    subject TEXT NOT NULL,

                    title TEXT NOT NULL,

                    summary TEXT,

                    metadata_json TEXT,

                    created_at TEXT NOT NULL

                )
                """
            )

            conn.commit()

    def remember(
        self,
        memory_type: str,
        subject: str,
        title: str,
        summary: str,
        metadata: Dict,
    ):

        with self._connect() as conn:

            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO business_memory (

                    memory_type,
                    subject,
                    title,
                    summary,
                    metadata_json,
                    created_at

                )

                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    memory_type,
                    subject,
                    title,
                    summary,
                    json.dumps(metadata),
                    datetime.utcnow().isoformat(),
                ),
            )

            conn.commit()

        return {
            "status": "success",
            "memory_created": True,
        }

    def recall(
        self,
        subject: str,
    ) -> List[Dict]:

        with self._connect() as conn:

            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT

                    memory_type,
                    subject,
                    title,
                    summary,
                    metadata_json,
                    created_at

                FROM business_memory

                WHERE subject LIKE ?

                ORDER BY id DESC
                """,
                (
                    f"%{subject}%",
                ),
            )

            rows = cursor.fetchall()

        results = []

        for row in rows:

            results.append(
                {
                    "memory_type": row[0],
                    "subject": row[1],
                    "title": row[2],
                    "summary": row[3],
                    "metadata": json.loads(row[4]),
                    "created_at": row[5],
                }
            )

        return results
