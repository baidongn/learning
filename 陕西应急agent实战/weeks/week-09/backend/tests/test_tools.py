import httpx
import pytest
from datetime import UTC, datetime, timedelta

from highway_agent.api import create_app
from highway_agent.tools import MockApiToolClient, ToolResult


def test_tool_result_timestamp_uses_per_instance_factory() -> None:
    """时间戳不能在模块导入时固定，长运行进程也要记录真实调用时间。"""

    assert ToolResult.model_fields["observed_at"].default_factory is not None


@pytest.mark.asyncio
async def test_tool_converts_connection_error_to_standard_result() -> None:
    """外部系统断连不能让 Agent 收到未处理的 httpx 异常。"""

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("模拟断连", request=request)

    tools = MockApiToolClient(transport=httpx.MockTransport(handler))
    result = await tools.query_road_status("G65", "QINLING-01")

    assert result.success is False
    assert result.error_code == "TOOL_CONNECTION_ERROR"


@pytest.mark.asyncio
async def test_road_tool_wraps_http_api_in_standard_result() -> None:
    app = create_app()
    tools = MockApiToolClient(transport=httpx.ASGITransport(app=app))

    result = await tools.query_road_status("G65", "QINLING-01")

    assert result.success is True
    assert result.data["closed_lanes"] == 2
    assert result.source == "synthetic-demo-data"
    assert result.trace_id


@pytest.mark.asyncio
async def test_tool_converts_service_failure_to_error_result() -> None:
    app = create_app()
    tools = MockApiToolClient(transport=httpx.ASGITransport(app=app))

    result = await tools.query_weather_warning("QINLING-01", scenario="unavailable")

    assert result.success is False
    assert result.error_code == "MOCK_SERVICE_UNAVAILABLE"
    assert result.data is None


@pytest.mark.asyncio
async def test_tool_preserves_upstream_observation_time() -> None:
    """安全复核必须看到数据源时间，不能用本地请求时间覆盖过期证据。"""

    app = create_app()
    tools = MockApiToolClient(transport=httpx.ASGITransport(app=app))

    result = await tools.query_road_status("G65", "QINLING-01", scenario="stale")

    assert result.observed_at < datetime.now(UTC) - timedelta(minutes=60)


@pytest.mark.asyncio
async def test_camera_tool_returns_structured_analysis() -> None:
    app = create_app()
    tools = MockApiToolClient(transport=httpx.ASGITransport(app=app))

    result = await tools.query_camera_analysis("CAM-QINLING-01")

    assert result.success is True
    assert result.data["smoke_detected"] is True
    assert result.data["vehicle_count"] == 7


@pytest.mark.asyncio
async def test_route_tool_converts_timeout_to_standard_result() -> None:
    """POST 路线工具与 GET 工具必须遵循同一错误契约。"""

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("模拟超时", request=request)

    tools = MockApiToolClient(transport=httpx.MockTransport(handler))
    result = await tools.estimate_route("RES-001", "QINLING-01", 8.0)

    assert result.success is False
    assert result.error_code == "TOOL_TIMEOUT"
