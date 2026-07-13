from fastapi.testclient import TestClient

from agent_lab.agent import CustomerServiceAgent
from agent_lab.api import create_app
from agent_lab.deepseek import FakeDeepSeekClient
from agent_lab.retrieval import Document, InMemoryRetriever


def make_client() -> TestClient:
    agent = CustomerServiceAgent(
        model=FakeDeepSeekClient(),
        retriever=InMemoryRetriever(
            [Document(id="leave", text="年假需要提前三天申请。", source="员工手册")]
        ),
    )
    return TestClient(create_app(agent))


def test_health_endpoint() -> None:
    response = make_client().get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["mode"] == "fake"


def test_chat_endpoint_returns_citations() -> None:
    response = make_client().post(
        "/api/v1/chat",
        json={"message": "年假怎么申请", "user_id": "u1", "thread_id": "api-thread"},
    )

    assert response.status_code == 200
    assert response.json()["citations"] == ["员工手册"]


def test_stream_endpoint_emits_sse_events() -> None:
    response = make_client().post(
        "/api/v1/chat/stream",
        json={"message": "年假怎么申请", "user_id": "u1", "thread_id": "stream-thread"},
    )

    assert response.status_code == 200
    assert "event: token" in response.text
    assert "event: done" in response.text
