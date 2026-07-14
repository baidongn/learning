from fastapi.testclient import TestClient

import httpx
import pytest

from highway_agent.agents.plan_expert import (
    DeepSeekPlanExpertAgent,
    PlanExpertAgent,
    PlanQuery,
)
from highway_agent.api import create_app
from highway_agent.config import Settings
from highway_agent.models import ModelJsonResponse
from highway_agent.rag import InMemoryPlanRetriever, load_demo_documents


def test_plan_expert_returns_actions_with_citations() -> None:
    agent = PlanExpertAgent(InMemoryPlanRetriever(load_demo_documents()))

    result = agent.invoke(PlanQuery(event_summary="隧道内发生追尾并出现烟雾"))

    assert result.status == "ready"
    assert result.actions
    assert result.citations[0].document_id == "PLAN-TUNNEL-001"
    assert result.citations[0].source.startswith("synthetic://")


def test_plan_expert_refuses_when_evidence_is_missing() -> None:
    agent = PlanExpertAgent(InMemoryPlanRetriever(load_demo_documents()))

    result = agent.invoke(PlanQuery(event_summary="服务区餐饮价格投诉"))

    assert result.status == "insufficient_evidence"
    assert result.actions == []
    assert "未检索到" in result.summary


def test_plan_expert_api_is_available_in_mock_mode() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/agents/plan-expert/invoke",
        json={"event_summary": "秦岭隧道追尾并出现烟雾"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "ready"
    assert response.json()["citations"]


@pytest.mark.asyncio
async def test_live_plan_agent_uses_deepseek_but_binds_retrieved_citations() -> None:
    """模型可以生成建议，但不能自行决定引用来源。"""

    class FakeDeepSeekClient:
        def __init__(self) -> None:
            self.user_prompt = ""

        async def complete_json(
            self, system_prompt: str, user_prompt: str
        ) -> ModelJsonResponse:
            assert "只能依据提供的预案证据" in system_prompt
            self.user_prompt = user_prompt
            return ModelJsonResponse(
                content={
                    "summary": "建议先核实隧道烟雾与伤亡。",
                    "actions": ["核实火情", "通知医疗资源待命"],
                    "citations": ["MODEL-INVENTED-CITATION"],
                },
                total_tokens=36,
            )

    client = FakeDeepSeekClient()
    agent = DeepSeekPlanExpertAgent(
        InMemoryPlanRetriever(load_demo_documents()),
        client,  # type: ignore[arg-type]
    )

    result = await agent.ainvoke(PlanQuery(event_summary="秦岭隧道出现烟雾"))

    assert "PLAN-TUNNEL-001" in client.user_prompt
    assert result.actions == ["核实火情", "通知医疗资源待命"]
    assert result.citations[0].document_id == "PLAN-TUNNEL-001"
    assert all(citation.document_id != "MODEL-INVENTED-CITATION" for citation in result.citations)


def test_plan_expert_api_calls_deepseek_in_live_mode() -> None:
    """Live 配置必须穿过真实 DeepSeek HTTP 适配层。"""

    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": '{"summary":"DeepSeek 建议","actions":["核实火情"]}'
                        }
                    }
                ],
                "usage": {"total_tokens": 20},
            },
        )

    app = create_app(
        Settings(model_mode="live", deepseek_api_key="test-key"),
        model_transport=httpx.MockTransport(handler),
    )
    response = TestClient(app).post(
        "/api/agents/plan-expert/invoke",
        json={"event_summary": "秦岭隧道出现烟雾"},
    )

    assert response.status_code == 200
    assert calls["count"] == 1
    assert response.json()["summary"] == "DeepSeek 建议"
    assert response.json()["citations"][0]["document_id"] == "PLAN-TUNNEL-001"
