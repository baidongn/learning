"""Agent 结果与执行轨迹的轻量确定性评测。"""

from __future__ import annotations

from pydantic import BaseModel, Field

from agent_lab.agent import AgentResult


class EvaluationCase(BaseModel):
    """一条可进入回归测试集的样例。"""

    query: str
    expected_keywords: list[str] = Field(default_factory=list)
    expected_tools: list[str] = Field(default_factory=list)
    require_citations: bool = False
    expected_citations: list[str] = Field(default_factory=list)


class EvaluationScore(BaseModel):
    """分别衡量答案、依据和行为轨迹。"""

    correctness: float
    groundedness: float
    trajectory: float


class Evaluator:
    """无需额外模型即可运行的基础评测器。"""

    @staticmethod
    def _ratio(expected: list[str], actual: list[str] | str) -> float:
        if not expected:
            return 1.0
        matched = sum(item in actual for item in expected)
        return round(matched / len(expected), 4)

    def evaluate(self, case: EvaluationCase, result: AgentResult) -> EvaluationScore:
        tools = [trace.name for trace in result.tool_trace]
        if case.expected_citations:
            groundedness = self._ratio(case.expected_citations, result.citations)
        elif case.require_citations:
            groundedness = float(bool(result.citations))
        else:
            groundedness = 1.0
        return EvaluationScore(
            correctness=self._ratio(case.expected_keywords, result.answer),
            groundedness=groundedness,
            trajectory=self._ratio(case.expected_tools, tools),
        )
