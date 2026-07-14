import httpx
import pytest
from fastapi.testclient import TestClient
from langgraph.checkpoint.memory import InMemorySaver

from highway_agent.agents.plan_expert import PlanExpertAgent
from highway_agent.api import create_app
from highway_agent.checkpoints import configured_checkpointer, to_psycopg_uri
from highway_agent.config import Settings
from highway_agent.rag import InMemoryPlanRetriever, load_demo_documents
from highway_agent.tools import MockApiToolClient
from highway_agent.workflows.approval_flow import ApprovalEmergencyWorkflow


def build_workflow() -> ApprovalEmergencyWorkflow:
    app = create_app()
    tools = MockApiToolClient(transport=httpx.ASGITransport(app=app))
    plan_agent = PlanExpertAgent(InMemoryPlanRetriever(load_demo_documents()))
    return ApprovalEmergencyWorkflow(tools, plan_agent, checkpointer=InMemorySaver())


REQUEST = {
    "raw_text": "秦岭隧道追尾并出现烟雾，占用两条车道，无人伤亡",
    "road_code": "G65",
    "section_id": "QINLING-01",
    "camera_id": "CAM-QINLING-01",
}


@pytest.mark.asyncio
async def test_workflow_interrupts_before_any_high_risk_action() -> None:
    workflow = build_workflow()

    result = await workflow.start(REQUEST, thread_id="approval-1")

    assert result["status"] == "awaiting_approval"
    assert result["executed_actions"] == []
    assert result["interrupt"]["allowed_decisions"] == ["approve", "edit", "reject"]


@pytest.mark.asyncio
async def test_approve_resumes_same_thread_and_records_simulated_action() -> None:
    workflow = build_workflow()
    await workflow.start(REQUEST, thread_id="approval-2")

    result = await workflow.resume("approval-2", {"decision": "approve"})

    assert result["status"] == "approved"
    assert result["executed_actions"] == ["simulate_traffic_control"]
    assert result["approval"]["decision"] == "approve"


@pytest.mark.asyncio
async def test_reject_never_records_simulated_action() -> None:
    workflow = build_workflow()
    await workflow.start(REQUEST, thread_id="approval-3")

    result = await workflow.resume("approval-3", {"decision": "reject", "comment": "信息不足"})

    assert result["status"] == "rejected"
    assert result["executed_actions"] == []


@pytest.mark.asyncio
async def test_edit_requests_revision_without_recording_an_action() -> None:
    """编辑代表退回修改，不能被当作批准执行。"""

    workflow = build_workflow()
    await workflow.start(REQUEST, thread_id="approval-edit")

    result = await workflow.resume(
        "approval-edit",
        {"decision": "edit", "comment": "请补充封道范围"},
    )

    assert result["status"] == "needs_revision"
    assert result["executed_actions"] == []
    assert result["events"][-1] == "human_edited"


def test_asyncpg_url_is_converted_for_postgres_checkpointer() -> None:
    assert (
        to_psycopg_uri("postgresql+asyncpg://highway:highway@localhost/highway_agent")
        == "postgresql://highway:highway@localhost/highway_agent"
    )


@pytest.mark.asyncio
async def test_configured_checkpointer_defaults_to_memory() -> None:
    """Mock/测试默认不需要数据库，部署时再显式切换 PostgreSQL。"""

    async with configured_checkpointer(Settings()) as saver:
        assert isinstance(saver, InMemorySaver)


def test_postgres_checkpointer_can_be_selected_by_environment() -> None:
    settings = Settings(checkpoint_backend="postgres")

    assert settings.checkpoint_backend == "postgres"


def test_app_lifespan_installs_configured_checkpointer() -> None:
    app = create_app(Settings(checkpoint_backend="memory"))

    with TestClient(app):
        assert isinstance(app.state.approval_checkpointer, InMemorySaver)
