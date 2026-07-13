"""Celery 后台任务：演示文档清洗与分块。"""

from __future__ import annotations

import re

from celery import Celery

from agent_lab.config import get_settings

settings = get_settings()
worker = Celery("agent_lab", broker=settings.redis_url, backend=settings.redis_url)


@worker.task(name="agent_lab.ingest_document")
def ingest_document(document_id: str, text: str, chunk_size: int = 500) -> dict[str, object]:
    """清洗文本并切块；生产环境在此处调用 Embedding 和 pgvector。"""
    normalized = re.sub(r"\s+", " ", text).strip()
    chunks = [
        normalized[index : index + chunk_size]
        for index in range(0, len(normalized), chunk_size)
    ]
    return {"document_id": document_id, "chunks": chunks, "chunk_count": len(chunks)}
