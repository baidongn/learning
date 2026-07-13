import pytest

from agent_lab.agent import AgentResult, ToolTrace
from agent_lab.evaluator import EvaluationCase, Evaluator
from agent_lab.mcp import MCPAdapter, MCPServerNotAllowedError, MCPTool
from agent_lab.tools import ToolContext, ToolRegistry


async def test_mcp_adapter_only_exposes_whitelisted_server() -> None:
    registry = ToolRegistry()
    adapter = MCPAdapter(registry, allowed_servers={"trusted"})

    with pytest.raises(MCPServerNotAllowedError, match="不在白名单"):
        adapter.register_tool(
            "unknown",
            MCPTool(name="weather", description="查询天气", input_schema={"type": "object"}),
            lambda **_: "晴",
        )


async def test_mcp_tool_is_namespaced_and_invokable() -> None:
    registry = ToolRegistry()
    adapter = MCPAdapter(registry, allowed_servers={"trusted"})
    adapter.register_tool(
        "trusted",
        MCPTool(
            name="weather",
            description="查询天气",
            input_schema={
                "type": "object",
                "properties": {"city": {"type": "string"}},
                "required": ["city"],
            },
        ),
        lambda city: f"{city}:晴",
    )

    result = await registry.invoke(
        "mcp_trusted_weather", {"city": "杭州"}, ToolContext(user_id="u1")
    )

    assert result.output == "杭州:晴"


def test_evaluator_scores_grounding_and_tool_trajectory() -> None:
    evaluator = Evaluator()
    result = AgentResult(
        answer="年假需要提前三天申请",
        citations=["员工手册"],
        route="rag",
        tool_trace=[ToolTrace(name="rag_search", arguments={"query": "年假"})],
    )
    case = EvaluationCase(
        query="年假怎么申请",
        expected_keywords=["提前三天"],
        expected_tools=["rag_search"],
        require_citations=True,
        expected_citations=["员工手册"],
    )

    score = evaluator.evaluate(case, result)

    assert score.correctness == 1.0
    assert score.groundedness == 1.0
    assert score.trajectory == 1.0


def test_evaluator_rejects_wrong_citation() -> None:
    result = AgentResult(answer="需要提前三天", citations=["未知博客"])
    case = EvaluationCase(
        query="年假怎么申请",
        expected_keywords=["提前三天"],
        require_citations=True,
        expected_citations=["员工手册"],
    )

    assert Evaluator().evaluate(case, result).groundedness == 0.0
