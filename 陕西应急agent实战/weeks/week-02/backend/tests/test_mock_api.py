from fastapi.testclient import TestClient

from highway_agent.api import create_app


client = TestClient(create_app())


def test_health_reports_mock_mode() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "model_mode": "mock"}


def test_road_status_returns_deterministic_fixture() -> None:
    response = client.get("/mock/roads/G65/sections/QINLING-01/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["road_code"] == "G65"
    assert payload["traffic_status"] == "congested"
    assert payload["closed_lanes"] == 2
    assert payload["source"] == "synthetic-demo-data"


def test_mock_scenario_can_return_stale_data() -> None:
    response = client.get(
        "/mock/roads/G65/sections/QINLING-01/status",
        headers={"X-Mock-Scenario": "stale"},
    )

    assert response.status_code == 200
    assert response.json()["data_freshness"] == "stale"


def test_unknown_road_section_returns_404() -> None:
    response = client.get("/mock/roads/G999/sections/UNKNOWN/status")

    assert response.status_code == 404
    assert response.json()["detail"]["error_code"] == "ROAD_SECTION_NOT_FOUND"


def test_weather_warning_returns_synthetic_snow_alert() -> None:
    response = client.get("/mock/weather/warnings", params={"section_id": "QINLING-01"})

    assert response.status_code == 200
    assert response.json()["warning_type"] == "snow"
    assert response.json()["source"] == "synthetic-demo-data"


def test_resource_query_filters_by_type() -> None:
    response = client.get(
        "/mock/resources/nearby",
        params={"section_id": "QINLING-01", "resource_type": "ambulance"},
    )

    assert response.status_code == 200
    resources = response.json()["items"]
    assert len(resources) == 1
    assert resources[0]["resource_type"] == "ambulance"


def test_failure_scenario_is_explicit_and_deterministic() -> None:
    response = client.get(
        "/mock/weather/warnings",
        params={"section_id": "QINLING-01"},
        headers={"X-Mock-Scenario": "unavailable"},
    )

    assert response.status_code == 503
    assert response.json()["detail"]["error_code"] == "MOCK_SERVICE_UNAVAILABLE"

