"""预案专家 Agent：Mock 确定性实现与 DeepSeek Live 实现。"""

import json
from typing import Protocol

from pydantic import BaseModel, Field

from highway_agent.models import ModelJsonResponse
from highway_agent.rag import InMemoryPlanRetriever, SearchMatch


class PlanQuery(BaseModel):
    """预案专家的最小输入。"""

    event_summary: str = Field(min_length=2, max_length=2000)


class Citation(BaseModel):
    """让每条建议可以追溯到具体预案切片。"""

    document_id: str
    title: str
    section: str
    source: str
    score: float


class PlanRecommendation(BaseModel):
    """预案专家的稳定结构化输出。"""

    status: str
    summary: str
    actions: list[str]
    citations: list[Citation]


class JsonModelClient(Protocol):
    """Live Agent 只依赖 JSON 模型接口，便于测试注入替身。"""

    async def complete_json(
        self, system_prompt: str, user_prompt: str
    ) -> ModelJsonResponse: ...


def _build_citations(matches: list[SearchMatch]) -> list[Citation]:
    """引用只能来自检索结果，不能接受模型自行生成的来源。"""

    return [
        Citation(
            document_id=match.document.id,
            title=match.document.title,
            section=match.document.section,
            source=match.document.source,
            score=match.score,
        )
        for match in matches
    ]


class PlanExpertAgent:
    """只允许调用一个检索工具，控制第一位 Agent 的学习难度。"""

    def __init__(self, retriever: InMemoryPlanRetriever) -> None:
        self.retriever = retriever

    def invoke(self, query: PlanQuery) -> PlanRecommendation:
        """检索证据后生成确定性的 Mock 建议；无证据时明确拒答。"""

        matches = self.retriever.search(query.event_summary, limit=2)
        if not matches:
            return PlanRecommendation(
                status="insufficient_evidence",
                summary="未检索到与当前事件相关的课程预案，不能生成处置建议。",
                actions=[],
                citations=[],
            )

        top_document = matches[0].document
        actions = [item.strip() for item in top_document.content.split("；") if item.strip()]
        citations = _build_citations(matches)
        return PlanRecommendation(
            status="ready",
            summary=f"已基于《{top_document.title}》生成初步建议。",
            actions=actions,
            citations=citations,
        )


class DeepSeekPlanExpertAgent:
    """Live 模式的预案专家：先检索，再让 DeepSeek 基于证据生成建议。"""

    def __init__(self, retriever: InMemoryPlanRetriever, model: JsonModelClient) -> None:
        self.retriever = retriever
        self.model = model

    async def ainvoke(self, query: PlanQuery) -> PlanRecommendation:
        """调用 DeepSeek，但由代码绑定真实检索引用并校验结构。"""

        matches = self.retriever.search(query.event_summary, limit=2)
        if not matches:
            return PlanRecommendation(
                status="insufficient_evidence",
                summary="未检索到与当前事件相关的课程预案，不能生成处置建议。",
                actions=[],
                citations=[],
            )

        evidence = [
            {
                "document_id": match.document.id,
                "title": match.document.title,
                "section": match.document.section,
                "content": match.document.content,
            }
            for match in matches
        ]
        response = await self.model.complete_json(
            "你是高速应急预案助手。只能依据提供的预案证据，输出 JSON："
            '{"summary":"...","actions":["..."]}。不得生成引用或声称已经执行。',
            json.dumps(
                {"event_summary": query.event_summary, "evidence": evidence},
                ensure_ascii=False,
            ),
        )
        summary = response.content.get("summary")
        actions = response.content.get("actions")
        if not isinstance(summary, str) or not isinstance(actions, list) or not all(
            isinstance(item, str) for item in actions
        ):
            raise ValueError("DeepSeek 返回的预案建议不符合结构化契约")
        return PlanRecommendation(
            status="ready",
            summary=summary,
            actions=actions,
            citations=_build_citations(matches),
        )
