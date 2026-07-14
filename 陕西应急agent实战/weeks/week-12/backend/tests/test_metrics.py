"""Prometheus 可观测性端点测试。"""

from fastapi.testclient import TestClient

from highway_agent.api import create_app


def test_metrics_endpoint_records_supervisor_status() -> None:
    client = TestClient(create_app())
    response = client.post(
        "/api/agents/supervisor/invoke",
        json={
            "incident_id": "INC-METRIC-001",
            "raw_text": "秦岭隧道追尾出现烟雾，2人受伤，占用2车道",
            "road_code": "G65",
            "section_id": "QINLING-01",
            "camera_id": "CAM-QINLING-01",
            "required_resources": ["ambulance"],
        },
    )
    assert response.status_code == 200

    metrics = client.get("/metrics")

    assert metrics.status_code == 200
    assert "highway_supervisor_invocations_total" in metrics.text
    assert 'status="awaiting_approval"' in metrics.text
