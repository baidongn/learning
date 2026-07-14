"""Week 2 的最小 RAG 实现。

Mock 模式使用确定性字符二元组，既能处理中文，又不依赖外部 Embedding API。
"""

from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass

from pydantic import BaseModel


class PlanDocument(BaseModel):
    """可检索的课程模拟预案切片。"""

    id: str
    title: str
    section: str
    content: str
    source: str


@dataclass(frozen=True)
class SearchMatch:
    """检索结果及可用于评测的相关度分数。"""

    document: PlanDocument
    score: float


def _terms(text: str) -> set[str]:
    """提取英文单词和中文二元组，避免依赖额外分词库。"""

    normalized = re.sub(r"\s+", "", text.lower())
    ascii_words = set(re.findall(r"[a-z0-9]+", normalized))
    chinese = "".join(re.findall(r"[\u4e00-\u9fff]", normalized))
    bigrams = {chinese[index : index + 2] for index in range(max(0, len(chinese) - 1))}
    return ascii_words | bigrams


class InMemoryPlanRetriever:
    """与 pgvector Repository 共享语义的本地确定性检索器。"""

    def __init__(self, documents: list[PlanDocument], threshold: float = 0.08) -> None:
        self.documents = documents
        self.threshold = threshold

    def embed(self, text: str) -> list[float]:
        """生成 16 维教学向量；仅用于 Mock 和单元测试。"""

        vector = [0.0] * 16
        for term in _terms(text):
            digest = hashlib.sha256(term.encode("utf-8")).digest()
            vector[digest[0] % len(vector)] += 1.0
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [round(value / norm, 8) for value in vector]

    def search(self, query: str, limit: int = 3) -> list[SearchMatch]:
        """按查询词覆盖率排序，并丢弃低于阈值的弱相关文档。"""

        query_terms = _terms(query)
        if not query_terms:
            return []
        matches: list[SearchMatch] = []
        for document in self.documents:
            document_terms = _terms(f"{document.title}{document.section}{document.content}")
            score = len(query_terms & document_terms) / len(query_terms)
            if score >= self.threshold:
                matches.append(SearchMatch(document=document, score=round(score, 4)))
        return sorted(matches, key=lambda item: item.score, reverse=True)[:limit]


def load_demo_documents() -> list[PlanDocument]:
    """返回明确标注为 synthetic 的课程预案，避免冒充官方文件。"""

    return [
        PlanDocument(
            id="PLAN-TUNNEL-001",
            title="课程模拟隧道交通事件预案",
            section="追尾与烟雾告警",
            content="核实火情与伤亡；确认车道占用；准备交通管制；通知消防和医疗资源待命。",
            source="synthetic://plans/tunnel-incident",
        ),
        PlanDocument(
            id="PLAN-SNOW-001",
            title="课程模拟冰雪保畅预案",
            section="降雪和道路结冰",
            content="巡查路面结冰；准备融雪物资；降低通行速度；必要时分流车辆。",
            source="synthetic://plans/snow-ice",
        ),
        PlanDocument(
            id="PLAN-LANDSLIDE-001",
            title="课程模拟边坡灾害预案",
            section="滑坡和落石",
            content="封控危险区域；核实阻断范围；联系抢险队伍；评估次生灾害风险。",
            source="synthetic://plans/landslide",
        ),
    ]

