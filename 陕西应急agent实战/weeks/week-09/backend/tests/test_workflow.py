import httpx
import pytest

from highway_agent.agents.plan_expert import PlanExpertAgent
from highway_agent.api import create_app
from highway_agent.rag import InMemoryPlanRetriever, load_demo_documents
from highway_agent.tools import MockApiToolClient
from highway_agent.workflows.incident_response import EmergencyWorkflow


def build_workflow() -> EmergencyWorkflow:
    app = create_app()
    tools = MockApiToolClient(transport=httpx.ASGITransport(app=app))
    plan_agent = PlanExpertAgent(InMemoryPlanRetriever(load_demo_documents()))
    return EmergencyWorkflow(tools=tools, plan_agent=plan_agent)


@pytest.mark.asyncio
async def test_complete_event_reaches_plan_ready() -> None:
    workflow = build_workflow()

    result = await workflow.ainvoke(
        {
            "raw_text": "秦岭隧道追尾并出现烟雾，占用两条车道，无人伤亡",
            "road_code": "G65",
            "section_id": "QINLING-01",
            "camera_id": "CAM-QINLING-01",
        }
    )

    assert result["status"] == "plan_ready"
    assert result["events"] == ["incident_analyzed", "plan_retrieved"]
    assert result["plan"]["citations"]


@pytest.mark.asyncio
async def test_incomplete_event_stops_before_plan_agent() -> None:
    workflow = build_workflow()

    result = await workflow.ainvoke(
        {
            "raw_text": "高速发生追尾",
            "road_code": "G5",
            "section_id": "HANTAI-01",
        }
    )

    assert result["status"] == "needs_input"
    assert result["events"] == ["incident_analyzed", "needs_input"]
    assert result.get("plan") is None
    assert result["assessment"]["missing_fields"] == ["casualties", "lane_occupancy"]


def test_workflow_api_runs_fixed_two_agent_graph() -> None:
    from fastapi.testclient import TestClient

    client = TestClient(create_app())
    response = client.post(
        "/api/workflows/incident-response/run",
        json={
            "raw_text": "秦岭隧道追尾并出现烟雾，占用两条车道，无人伤亡",
            "road_code": "G65",
            "section_id": "QINLING-01",
            "camera_id": "CAM-QINLING-01",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "plan_ready"

