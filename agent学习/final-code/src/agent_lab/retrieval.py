"""可替换的检索接口与零依赖内存实现。"""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Protocol

from pydantic import BaseModel, Field


class Document(BaseModel):
    """进入知识库的规范化文档。"""

    id: str
    text: str
    source: str
    metadata: dict[str, str] = Field(default_factory=dict)


class SearchHit(BaseModel):
    """带分数和引用的检索结果。"""

    document: Document
    score: float

    @property
    def citation(self) -> str:
        return self.document.source


class Retriever(Protocol):
    def retrieve(self, query: str, top_k: int = 4) -> list[SearchHit]: ...


def _tokens(text: str) -> list[str]:
    """同时支持中文双字片段和英文单词的轻量分词。"""
    lowered = text.lower()
    words = re.findall(r"[a-z0-9_]+", lowered)
    chinese = "".join(re.findall(r"[\u4e00-\u9fff]", lowered))
    bigrams = [chinese[index : index + 2] for index in range(max(0, len(chinese) - 1))]
    return words + bigrams


def _cosine(left: Counter[str], right: Counter[str]) -> float:
    common = set(left) & set(right)
    numerator = sum(left[token] * right[token] for token in common)
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    if not left_norm or not right_norm:
        return 0.0
    return numerator / (left_norm * right_norm)


class InMemoryRetriever:
    """用于课堂和测试的混合检索器。"""

    def __init__(self, documents: list[Document] | None = None, min_score: float = 0.1) -> None:
        self.documents = list(documents or [])
        self.min_score = min_score

    def add(self, document: Document) -> None:
        self.documents.append(document)

    def retrieve(self, query: str, top_k: int = 4) -> list[SearchHit]:
        query_vector = Counter(_tokens(query))
        hits = []
        for document in self.documents:
            body = f"{document.text} {document.source}"
            score = _cosine(query_vector, Counter(_tokens(body)))
            if score >= self.min_score:
                hits.append(SearchHit(document=document, score=round(score, 4)))
        return sorted(hits, key=lambda item: item.score, reverse=True)[:top_k]

