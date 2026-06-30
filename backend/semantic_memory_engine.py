import json
import math
import os
import re
import sqlite3
from collections import Counter
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    from openai import OpenAI
except Exception:
    OpenAI = None


class SemanticMemoryEngine:
    def __init__(self, database_path: str = "database/athena_knowledge.db"):
        self.database_path = database_path
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=self.api_key) if OpenAI and self.api_key else None
        self.embedding_model = "text-embedding-3-small"

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
                CREATE TABLE IF NOT EXISTS semantic_memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_id INTEGER,
                    filename TEXT NOT NULL,
                    document_type TEXT,
                    title TEXT,
                    summary TEXT,
                    memory_text TEXT NOT NULL,
                    keywords_json TEXT,
                    embedding_json TEXT,
                    embedding_model TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )

            existing_columns = self._get_table_columns(cursor, "semantic_memory")

            if "embedding_json" not in existing_columns:
                cursor.execute("ALTER TABLE semantic_memory ADD COLUMN embedding_json TEXT")

            if "embedding_model" not in existing_columns:
                cursor.execute("ALTER TABLE semantic_memory ADD COLUMN embedding_model TEXT")

            conn.commit()

    def _get_table_columns(self, cursor, table_name: str) -> List[str]:
        cursor.execute(f"PRAGMA table_info({table_name})")
        return [row[1] for row in cursor.fetchall()]

    def save_memory(
        self,
        document_id: Optional[int],
        filename: str,
        document_type: Optional[str],
        title: Optional[str],
        summary: Optional[str],
        full_text: str,
        intelligence: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        intelligence = intelligence or {}

        memory_text = self._build_memory_text(
            filename=filename,
            document_type=document_type,
            title=title,
            summary=summary,
            full_text=full_text,
            intelligence=intelligence,
        )

        keywords = self._extract_keywords(memory_text)
        embedding = self._create_embedding(memory_text)
        created_at = datetime.utcnow().isoformat()

        with self._connect() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO semantic_memory (
                    document_id,
                    filename,
                    document_type,
                    title,
                    summary,
                    memory_text,
                    keywords_json,
                    embedding_json,
                    embedding_model,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    document_id,
                    filename,
                    document_type,
                    title,
                    summary,
                    memory_text,
                    json.dumps(keywords, ensure_ascii=False),
                    json.dumps(embedding) if embedding else None,
                    self.embedding_model if embedding else "keyword_fallback",
                    created_at,
                ),
            )

            memory_id = cursor.lastrowid
            conn.commit()

        return {
            "saved": True,
            "memory_id": memory_id,
            "document_id": document_id,
            "filename": filename,
            "document_type": document_type,
            "title": title,
            "created_at": created_at,
            "embedding_enabled": embedding is not None,
            "embedding_model": self.embedding_model if embedding else "keyword_fallback",
            "top_keywords": keywords[:20],
        }

    def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        query_embedding = self._create_embedding(query)

        with self._connect() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT id, document_id, filename, document_type, title, summary,
                       memory_text, keywords_json, embedding_json, embedding_model, created_at
                FROM semantic_memory
                ORDER BY id DESC
                """
            )

            rows = cursor.fetchall()

        scored_results = []

        for row in rows:
            memory_id = row[0]
            document_id = row[1]
            filename = row[2]
            document_type = row[3]
            title = row[4]
            summary = row[5]
            memory_text = row[6]
            keywords_json = row[7]
            embedding_json = row[8]
            embedding_model = row[9]
            created_at = row[10]

            score = 0.0
            search_method = "keyword_fallback"

            if query_embedding and embedding_json:
                try:
                    memory_embedding = json.loads(embedding_json)
                    score = self._cosine_similarity(query_embedding, memory_embedding)
                    search_method = "embedding"
                except Exception:
                    score = self._keyword_score(query=query, memory_text=memory_text)
            else:
                score = self._keyword_score(query=query, memory_text=memory_text)

            if score > 0:
                try:
                    keywords = json.loads(keywords_json) if keywords_json else []
                except Exception:
                    keywords = []

                scored_results.append(
                    {
                        "memory_id": memory_id,
                        "document_id": document_id,
                        "filename": filename,
                        "document_type": document_type,
                        "title": title,
                        "summary": summary,
                        "semantic_score": round(score, 4),
                        "search_method": search_method,
                        "embedding_model": embedding_model,
                        "top_keywords": keywords[:15],
                        "created_at": created_at,
                    }
                )

        scored_results.sort(key=lambda item: item["semantic_score"], reverse=True)
        return scored_results[:limit]

    def find_similar(self, document_id: int, limit: int = 10) -> Dict[str, Any]:
        source_memory = self._get_memory_by_document_id(document_id)

        if not source_memory:
            return {
                "found": False,
                "message": "Source document not found in semantic memory",
                "results": [],
            }

        source_embedding = None
        if source_memory.get("embedding_json"):
            try:
                source_embedding = json.loads(source_memory["embedding_json"])
            except Exception:
                source_embedding = None

        with self._connect() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT id, document_id, filename, document_type, title, summary,
                       memory_text, keywords_json, embedding_json, embedding_model, created_at
                FROM semantic_memory
                WHERE document_id != ?
                ORDER BY id DESC
                """,
                (document_id,),
            )

            rows = cursor.fetchall()

        scored_results = []

        for row in rows:
            score = 0.0
            search_method = "keyword_fallback"

            if source_embedding and row[8]:
                try:
                    target_embedding = json.loads(row[8])
                    score = self._cosine_similarity(source_embedding, target_embedding)
                    search_method = "embedding"
                except Exception:
                    score = self._keyword_score(
                        query=source_memory["memory_text"],
                        memory_text=row[6],
                    )
            else:
                score = self._keyword_score(
                    query=source_memory["memory_text"],
                    memory_text=row[6],
                )

            if score > 0:
                try:
                    keywords = json.loads(row[7]) if row[7] else []
                except Exception:
                    keywords = []

                scored_results.append(
                    {
                        "memory_id": row[0],
                        "document_id": row[1],
                        "filename": row[2],
                        "document_type": row[3],
                        "title": row[4],
                        "summary": row[5],
                        "semantic_score": round(score, 4),
                        "search_method": search_method,
                        "embedding_model": row[9],
                        "top_keywords": keywords[:15],
                        "created_at": row[10],
                    }
                )

        scored_results.sort(key=lambda item: item["semantic_score"], reverse=True)

        return {
            "found": True,
            "source_document_id": document_id,
            "source_filename": source_memory["filename"],
            "count": len(scored_results[:limit]),
            "results": scored_results[:limit],
        }

    def rebuild_from_knowledge(self) -> Dict[str, Any]:
        with self._connect() as conn:
            cursor = conn.cursor()

            cursor.execute("DELETE FROM semantic_memory")

            cursor.execute(
                """
                SELECT id, filename, document_type, title, summary, full_text, intelligence_json
                FROM documents
                ORDER BY id ASC
                """
            )

            rows = cursor.fetchall()
            conn.commit()

        rebuilt = []

        for row in rows:
            document_id = row[0]
            filename = row[1]
            document_type = row[2]
            title = row[3]
            summary = row[4]
            full_text = row[5] or ""

            try:
                intelligence = json.loads(row[6]) if row[6] else {}
            except Exception:
                intelligence = {}

            saved = self.save_memory(
                document_id=document_id,
                filename=filename,
                document_type=document_type,
                title=title,
                summary=summary,
                full_text=full_text,
                intelligence=intelligence,
            )

            rebuilt.append(saved)

        return {
            "status": "success",
            "rebuilt_count": len(rebuilt),
            "embedding_enabled": self.client is not None,
            "embedding_model": self.embedding_model if self.client else "keyword_fallback",
            "rebuilt": rebuilt,
        }

    def _create_embedding(self, text: str) -> Optional[List[float]]:
        if not self.client:
            return None

        clean_text = text[:12000]

        try:
            response = self.client.embeddings.create(
                model=self.embedding_model,
                input=clean_text,
            )
            return response.data[0].embedding
        except Exception:
            return None

    def _get_memory_by_document_id(self, document_id: int) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT id, document_id, filename, document_type, title, summary,
                       memory_text, keywords_json, embedding_json, embedding_model, created_at
                FROM semantic_memory
                WHERE document_id = ?
                LIMIT 1
                """,
                (document_id,),
            )

            row = cursor.fetchone()

        if not row:
            return None

        return {
            "memory_id": row[0],
            "document_id": row[1],
            "filename": row[2],
            "document_type": row[3],
            "title": row[4],
            "summary": row[5],
            "memory_text": row[6],
            "keywords_json": row[7],
            "embedding_json": row[8],
            "embedding_model": row[9],
            "created_at": row[10],
        }

    def _build_memory_text(
        self,
        filename: str,
        document_type: Optional[str],
        title: Optional[str],
        summary: Optional[str],
        full_text: str,
        intelligence: Dict[str, Any],
    ) -> str:
        important_parts = [
            filename or "",
            document_type or "",
            title or "",
            summary or "",
            json.dumps(intelligence, ensure_ascii=False),
            full_text or "",
        ]

        return "\n".join(part for part in important_parts if part).strip()

    def _keyword_score(self, query: str, memory_text: str) -> float:
        query_tokens = self._expand_tokens(self._tokenize(query))
        memory_tokens = self._expand_tokens(self._tokenize(memory_text))
        return self._cosine_counter_similarity(query_tokens, memory_tokens)

    def _tokenize(self, text: str) -> List[str]:
        text = text.lower()
        text = re.sub(r"[^a-z0-9\u0600-\u06FF]+", " ", text)
        tokens = [token.strip() for token in text.split() if len(token.strip()) >= 2]

        stopwords = {
            "the", "and", "for", "with", "from", "this", "that",
            "shall", "must", "will", "are", "was", "were", "been",
            "into", "after", "before", "all", "any", "per", "each",
            "في", "من", "على", "إلى", "الى", "عن", "مع",
            "هذا", "هذه", "ذلك", "تلك", "كل", "أن", "او", "أو",
        }

        return [token for token in tokens if token not in stopwords]

    def _expand_tokens(self, tokens: List[str]) -> List[str]:
        synonym_map = {
            "warranty": ["guarantee", "defect", "replacement"],
            "guarantee": ["warranty", "defect", "replacement"],
            "boots": ["shoes", "footwear", "tactical"],
            "shoes": ["boots", "footwear"],
            "footwear": ["boots", "shoes"],
            "tender": ["bid", "submission"],
            "bid": ["tender", "submission"],
            "deadline": ["closing", "submission", "expiry"],
            "payment": ["invoice", "commercial", "terms"],
            "delivery": ["lead", "timeline", "location"],
            "certificate": ["certification", "iso", "compliance"],
            "technical": ["specification", "compliance", "standard"],
            "penalty": ["fine", "liability", "damages", "delay"],
            "fabric": ["textile", "material", "cloth"],
            "leather": ["upper", "material"],
            "vat": ["tax", "trn"],
            "supplier": ["vendor", "contractor", "seller"],
            "مناقصة": ["tender", "bid", "submission"],
            "توريد": ["supply", "delivery"],
            "ضمان": ["warranty", "guarantee"],
            "غرامة": ["penalty", "fine"],
            "شهادة": ["certificate", "certification"],
            "فني": ["technical", "specification"],
            "الدفع": ["payment"],
            "تسليم": ["delivery"],
        }

        expanded = list(tokens)

        for token in tokens:
            if token in synonym_map:
                expanded.extend(synonym_map[token])

        return expanded

    def _extract_keywords(self, text: str) -> List[str]:
        tokens = self._tokenize(text)
        expanded = self._expand_tokens(tokens)
        counter = Counter(expanded)
        common = counter.most_common(50)
        return [word for word, count in common if count >= 1]

    def _cosine_similarity(self, vector_a: List[float], vector_b: List[float]) -> float:
        if not vector_a or not vector_b:
            return 0.0

        if len(vector_a) != len(vector_b):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vector_a, vector_b))
        norm_a = math.sqrt(sum(a * a for a in vector_a))
        norm_b = math.sqrt(sum(b * b for b in vector_b))

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot_product / (norm_a * norm_b)

    def _cosine_counter_similarity(self, query_tokens: List[str], memory_tokens: List[str]) -> float:
        if not query_tokens or not memory_tokens:
            return 0.0

        query_counter = Counter(query_tokens)
        memory_counter = Counter(memory_tokens)

        dot_product = 0.0

        for token, query_count in query_counter.items():
            dot_product += query_count * memory_counter.get(token, 0)

        query_norm = math.sqrt(sum(count * count for count in query_counter.values()))
        memory_norm = math.sqrt(sum(count * count for count in memory_counter.values()))

        if query_norm == 0 or memory_norm == 0:
            return 0.0

        return dot_product / (query_norm * memory_norm)