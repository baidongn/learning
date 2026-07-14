"""Supervisor 的路由、重试、步数上限和审批边界测试。"""

from datetime import UTC, datetime, timedelta

import httpx
import pytest
from fastapi.testclient import TestClient

from highway_agent.agents.incident_analysis import (
    IncidentAnalysisAgent,
    IncidentAssessment,
    ToolTrace,
)
from highway_agent.agents.plan_expert import PlanExpertAgent
from highway_agent.agents.resource_dispatch import ResourceDispatchAgent
from highway_agent.agents.safety_review import SafetyReviewAgent
from highway_agent.agents.supervisor import SupervisorAgent, SupervisorRequest
from highway_agent.api import create_app
from highway_agent.config import Settings
from highway_agent.rag import InMemoryPlanRetriever, load_demo_documents
from highway_agent.tools import MockApiToolClient


def build_supervisor(
    incident_agent: IncidentAnalysisAgent | None = None,
    *,
    max_steps: int = 8,
) -> SupervisorAgent:
    """组装真实的前四个专业 Agent，测试完整路由。"""

    app = create_app()
    tools = MockApiToolClient(transport=httpx.ASGITransport(app=app))
    return SupervisorAgent(
        incident_agent=incident_agent or IncidentAnalysisAgent(tools),
        plan_agent=PlanExpertAgent(InMemoryPlanRetriever(load_demo_documents())),
        dispatch_agent=ResourceDispatchAgent(tools),
        safety_agent=SafetyReviewAgent(),
        max_steps=max_steps,
        max_retries=1,
    )


def high_risk_request(**overrides: object) -> SupervisorRequest:
    payload: dict[str, object] = {
        "incident_id": "INC-SUP-001",
        "raw_text": "秦岭隧道追尾出现烟雾，2人受伤，占用2车道",
        "road_code": "G65",
        "section_id": "QINLING-01",
        "camera_id": "CAM-QINLING-01",
        "required_resources": ["ambulance", "tow_truck"],
        "human_approved": False,
    }
    payload.update(overrides)
    return SupervisorRequest.model_validate(payload)


@pytest.mark.asyncio
async def test_supervisor_routes_to_specialists_but_waits_for_approval() -> None:
    result = await build_supervisor().ainvoke(high_risk_request())

    assert result.incident and result.incident.risk_level == "critical"
    assert result.plan and result.plan.citations
    assert result.dispatch and len(result.dispatch.assignments) == 2
    assert result.safety and result.safety.verdict == "BLOCK"
    assert result.status == "awaiting_approval"
    assert result.awaiting_human_approval is True
    assert result.executed_actions == []
    assert [step.agent_name for step in result.route_trace] == [
        "incident_analysis",
        "plan_expert",
        "resource_dispatch",
        "safety_review",
    ]


@pytest.mark.asyncio
async def test_supervisor_never_bypasses_human_approval() -> None:
    result = await build_supervisor().ainvoke(high_risk_request())

    assert "HUMAN_APPROVAL_REQUIRED" in result.safety.reason_codes
    assert "dispatch_resource" not in result.executed_actions


@pytest.mark.asyncio
async def test_supervisor_stops_when_required_incident_fields_are_missing() -> None:
    """基础事实不完整时只返回追问，不继续生成方案或调度资源。"""

    result = await build_supervisor().ainvoke(
        high_risk_request(
            raw_text="高速发生追尾",
            camera_id=None,
            required_resources=[],
        )
    )

    assert result.status == "needs_input"
    assert result.incident and set(result.incident.missing_fields) == {
        "casualties",
        "lane_occupancy",
    }
    assert result.plan is None
    assert result.dispatch is None
    assert result.safety is None
    assert [step.agent_name for step in result.route_trace] == ["incident_analysis"]
    assert result.executed_actions == []


@pytest.mark.asyncio
async def test_supervisor_retries_transient_agent_failure_once() -> None:
    app = create_app()
    tools = MockApiToolClient(transport=httpx.ASGITransport(app=app))
    real_agent = IncidentAnalysisAgent(tools)

    class FlakyIncidentAgent:
        """第一次失败、第二次成功的可控替身。"""

        def __init__(self) -> None:
            self.calls = 0

        async def ainvoke(self, request):  # type: ignore[no-untyped-def]
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError("模拟瞬时故障")
            return await real_agent.ainvoke(request)

    flaky = FlakyIncidentAgent()
    result = await build_supervisor(incident_agent=flaky).ainvoke(high_risk_request())  # type: ignore[arg-type]

    attempts = [
        step.attempt
        for step in result.route_trace
        if step.agent_name == "incident_analysis"
    ]
    assert flaky.calls == 2
    assert attempts == [1, 2]


@pytest.mark.asyncio
async def test_supervisor_stops_at_configured_step_limit() -> None:
    result = await build_supervisor(max_steps=2).ainvoke(high_risk_request())

    assert result.status == "step_limit"
    assert len(result.route_trace) == 2
    assert result.executed_actions == []


@pytest.mark.asyncio
async def test_supervisor_routes_stale_tool_evidence_to_revision() -> None:
    """任一关键 Tool 证据过期时，安全复核必须要求重新查询。"""

    class StaleIncidentAgent:
        async def ainvoke(self, request):  # type: ignore[no-untyped-def]
            return IncidentAssessment(
                incident_type="collision",
                risk_level="medium",
                known_facts=[request.raw_text],
                missing_fields=[],
                tool_trace=[
                    ToolTrace(
                        tool_name="query_road_status",
                        success=True,
                        trace_id="stale-trace",
                        source="synthetic-demo-data",
                        observed_at=datetime.now(UTC) - timedelta(hours=2),
                    ),
                    ToolTrace(
                        tool_name="query_weather_warning",
                        success=True,
                        trace_id="fresh-trace",
                        source="synthetic-demo-data",
                        observed_at=datetime.now(UTC),
                    ),
                ],
            )

    result = await build_supervisor(incident_agent=StaleIncidentAgent()).ainvoke(  # type: ignore[arg-type]
        high_risk_request(required_resources=[], camera_id=None)
    )

    assert result.status == "needs_revision"
    assert result.safety and "STALE_EVIDENCE" in result.safety.reason_codes


def test_supervisor_api_uses_deepseek_plan_agent_in_live_mode() -> None:
    """最终编排的预案节点也必须遵循 MODEL_MODE=live。"""

    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": '{"summary":"DeepSeek 现场建议","actions":["核实火情"]}'
                        }
                    }
                ],
                "usage": {"total_tokens": 24},
            },
        )

    app = create_app(
        Settings(model_mode="live", deepseek_api_key="test-key"),
        model_transport=httpx.MockTransport(handler),
    )
    response = TestClient(app).post(
        "/api/agents/supervisor/invoke",
        json=high_risk_request().model_dump(mode="json"),
    )

    assert response.status_code == 200
    assert calls["count"] == 1
    assert response.json()["plan"]["summary"] == "DeepSeek 现场建议"
    assert response.json()["status"] == "awaiting_approval"
