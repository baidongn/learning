import asyncio

from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from agent_lab.agent import CustomerServiceAgent
from agent_lab.api import create_app
from agent_lab.deepseek import FakeDeepSeekClient
from agent_lab.retrieval import InMemoryRetriever


def make_client() -> TestClient:
    return TestClient(
        create_app(CustomerServiceAgent(FakeDeepSeekClient(), InMemoryRetriever()))
    )


def test_knowledge_endpoint_adds_searchable_document() -> None:
    client = make_client()

    created = client.post(
        "/api/v1/knowledge",
        json={"id": "policy", "text": "年假提前三天申请", "source": "员工手册"},
    )
    answer = client.post(
        "/api/v1/chat",
        json={"message": "年假怎么申请", "user_id": "u1", "thread_id": "knowledge-thread"},
    )

    assert created.status_code == 201
    assert answer.json()["citations"] == ["员工手册"]


def test_metrics_endpoint_counts_requests() -> None:
    client = make_client()
    client.post(
        "/api/v1/chat",
        json={"message": "你好", "user_id": "u1", "thread_id": "metrics-thread"},
    )

    response = client.get("/api/v1/metrics")

    assert response.status_code == 200
    assert response.json()["chat_requests"] == 1


async def test_cancel_endpoint_stops_active_request_not_next_request() -> None:
    class SlowFakeDeepSeekClient(FakeDeepSeekClient):
        async def chat(self, messages, tools=None):
            await asyncio.sleep(10)
            return await super().chat(messages, tools)

    app = create_app(CustomerServiceAgent(SlowFakeDeepSeekClient(), InMemoryRetriever()))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        running = asyncio.create_task(
            client.post(
                "/api/v1/chat",
                json={"message": "你好", "user_id": "u1", "thread_id": "cancel-thread"},
            )
        )
        await asyncio.sleep(0.02)
        cancelled = await client.post("/api/v1/cancel", json={"thread_id": "cancel-thread"})
        result = await running

    assert cancelled.json() == {"thread_id": "cancel-thread", "cancelled": True}
    assert result.json()["answer"] == "执行已取消。"


def test_session_endpoint_returns_latest_state() -> None:
    client = make_client()
    client.post(
        "/api/v1/chat",
        json={"message": "查询订单1002", "user_id": "u1", "thread_id": "session-thread"},
    )

    response = client.get("/api/v1/sessions/session-thread")

    assert response.status_code == 200
    assert response.json()["thread_id"] == "session-thread"
    assert response.json()["route"] == "tool"


def test_missing_approval_returns_stable_client_error() -> None:
    response = make_client().post(
        "/api/v1/approve",
        json={"thread_id": "missing", "user_id": "u1", "approved": True},
    )

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_operation"
