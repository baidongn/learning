"""PostgreSQL/pgvector 生产检索适配与本地确定性向量器。"""

from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Sequence

import psycopg

from agent_lab.retrieval import Document, SearchHit


class HashingEmbedder:
    """课堂和离线测试使用的无模型向量器，不用于生产语义质量评估。"""

    def __init__(self, dimensions: int = 256) -> None:
        if dimensions < 2:
            raise ValueError("向量维度至少为 2")
        self.dimensions = dimensions

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        tokens = re.findall(r"[a-z0-9_]+|[\u4e00-\u9fff]", text.lower())
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign
        norm = math.sqrt(sum(value * value for value in vector))
        if not norm:
            return vector
        return [value / norm for value in vector]


class PgVectorRetriever:
    """最小 pgvector 检索器；真实项目应换成语义 Embedding 服务。"""

    def __init__(
        self,
        database_url: str,
        embedder: HashingEmbedder | None = None,
        table: str = "knowledge_documents",
    ) -> None:
        if not table.replace("_", "").isalnum():
            raise ValueError("表名只能包含字母、数字和下划线")
        self.database_url = database_url
        self.embedder = embedder or HashingEmbedder()
        self.table = table

    @staticmethod
    def vector_literal(vector: list[float]) -> str:
        """显式生成 pgvector 文本格式，避免驱动把 list 推断为 SQL 数组。"""
        return "[" + ",".join(format(value, ".12g") for value in vector) + "]"

    def initialize(self) -> None:
        """创建扩展和演示表。"""
        with (
            psycopg.connect(self.database_url) as connection,
            connection.cursor() as cursor,
        ):
            cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
            cursor.execute(
                f"""CREATE TABLE IF NOT EXISTS {self.table} (
                    id TEXT PRIMARY KEY,
                    text TEXT NOT NULL,
                    source TEXT NOT NULL,
                    embedding vector({self.embedder.dimensions}) NOT NULL
                )"""
            )

    def add(self, document: Document) -> None:
        vector = self.vector_literal(self.embedder.embed(document.text))
        with (
            psycopg.connect(self.database_url) as connection,
            connection.cursor() as cursor,
        ):
            cursor.execute(
                f"""INSERT INTO {self.table} (id, text, source, embedding)
                VALUES (%s, %s, %s, %s::vector)
                ON CONFLICT (id) DO UPDATE SET
                text = EXCLUDED.text, source = EXCLUDED.source,
                embedding = EXCLUDED.embedding""",
                (document.id, document.text, document.source, vector),
            )

    def retrieve(self, query: str, top_k: int = 4) -> list[SearchHit]:
        vector = self.vector_literal(self.embedder.embed(query))
        with (
            psycopg.connect(self.database_url) as connection,
            connection.cursor() as cursor,
        ):
            cursor.execute(
                f"""SELECT id, text, source, 1 - (embedding <=> %s::vector) AS score
                FROM {self.table} ORDER BY embedding <=> %s::vector LIMIT %s""",
                (vector, vector, top_k),
            )
            rows: Sequence[tuple[str, str, str, float]] = cursor.fetchall()
        return [
            SearchHit(
                document=Document(id=row[0], text=row[1], source=row[2]),
                score=float(row[3]),
            )
            for row in rows
        ]
