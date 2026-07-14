import httpx
import pytest
from fastapi.testclient import TestClient
from datetime import UTC

from highway_agent.agents.incident_analysis import IncidentAnalysisAgent, IncidentAnalysisRequest
from highway_agent.api import create_app
from highway_agent.tools import MockApiToolClient


@pytest.mark.asyncio
async def test_incident_agent_calls_three_read_only_tools_and_marks_critical_risk() -> None:
    app = create_app()
    tools = MockApiToolClient(transport=httpx.ASGITransport(app=app))
    agent = IncidentAnalysisAgent(tools)

    result = await agent.ainvoke(
        IncidentAnalysisRequest(
            raw_text="秦岭隧道两车追尾，现场有烟，占用两条车道，无人伤亡",
            road_code="G65",
            section_id="QINLING-01",
            camera_id="CAM-QINLING-01",
        )
    )

    assert result.incident_type == "tunnel_smoke"
    assert result.risk_level == "critical"
    assert result.missing_fields == []
    assert [trace.tool_name for trace in result.tool_trace] == [
        "query_road_status",
        "query_weather_warning",
        "query_camera_analysis",
    ]
    assert all(trace.source == "synthetic-demo-data" for trace in result.tool_trace)
    assert all(trace.observed_at.tzinfo == UTC for trace in result.tool_trace)


@pytest.mark.asyncio
async def test_incident_agent_marks_unreported_casualties_as_missing() -> None:
    app = create_app()
    tools = MockApiToolClient(transport=httpx.ASGITransport(app=app))
    agent = IncidentAnalysisAgent(tools)

    result = await agent.ainvoke(
        IncidentAnalysisRequest(
            raw_text="高速发生追尾",
            road_code="G5",
            section_id="HANTAI-01",
        )
    )

    assert "casualties" in result.missing_fields
    assert "lane_occupancy" in result.missing_fields
    assert "无人员伤亡" not in result.known_facts


@pytest.mark.asyncio
async def test_incident_agent_recognizes_light_injury_as_casualty_information() -> None:
    app = create_app()
    tools = MockApiToolClient(transport=httpx.ASGITransport(app=app))
    agent = IncidentAnalysisAgent(tools)

    result = await agent.ainvoke(
        IncidentAnalysisRequest(
            raw_text="汉台路段追尾，1人轻伤，占用1车道",
            road_code="G5",
            section_id="HANTAI-01",
        )
    )

    assert "casualties" not in result.missing_fields


def test_incident_agent_api_returns_structured_assessment() -> None:
    # FastAPI TestClient 负责同步驱动异步 Agent。
    api_client = TestClient(create_app())
    response = api_client.post(
        "/api/agents/incident-analysis/invoke",
        json={
            "raw_text": "秦岭隧道追尾，有烟，占用两条车道，无人伤亡",
            "road_code": "G65",
            "section_id": "QINLING-01",
            "camera_id": "CAM-QINLING-01",
        },
    )

    assert response.status_code == 200
    assert response.json()["risk_level"] == "critical"
