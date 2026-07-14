"""验证第 7 周 MCP 服务暴露的工具契约。"""

import httpx
import pytest

from highway_agent.api import create_app
from highway_agent.mcp_servers import (
    create_resource_server,
    create_road_server,
    create_weather_server,
)
from highway_agent.tools import MockApiToolClient


@pytest.fixture
def tool_client() -> MockApiToolClient:
    """使用 ASGITransport 调用本地模拟 API，不依赖外部网络。"""

    transport = httpx.ASGITransport(app=create_app())
    return MockApiToolClient(transport=transport)


@pytest.mark.asyncio
async def test_road_mcp_server_exposes_and_calls_road_tools(
    tool_client: MockApiToolClient,
) -> None:
    server = create_road_server(tool_client)

    tool_names = {tool.name for tool in await server.list_tools()}
    assert tool_names == {"query_road_status", "query_camera_analysis"}

    content = await server.call_tool(
        "query_road_status",
        {"road_code": "G65", "section_id": "QINLING-01"},
    )
    # FastMCP 返回“文本内容列表 + 结构化结果”的二元组。
    payload = content[1]
    assert payload["success"] is True
    assert payload["data"]["road_code"] == "G65"


@pytest.mark.asyncio
async def test_weather_mcp_server_exposes_weather_tool(
    tool_client: MockApiToolClient,
) -> None:
    server = create_weather_server(tool_client)

    tool_names = {tool.name for tool in await server.list_tools()}
    assert tool_names == {"query_weather_warning"}


@pytest.mark.asyncio
async def test_resource_mcp_server_exposes_resource_tools(
    tool_client: MockApiToolClient,
) -> None:
    server = create_resource_server(tool_client)

    tool_names = {tool.name for tool in await server.list_tools()}
    assert tool_names == {"query_nearby_resources", "estimate_route"}

    content = await server.call_tool(
        "estimate_route",
        {"origin": "西安绕城基地", "destination": "QINLING-01", "distance_km": 12.0},
    )
    payload = content[1]
    assert payload["success"] is True
    assert payload["data"]["eta_minutes"] > 0


def test_mcp_servers_do_not_conflict_with_api_or_each_other(
    tool_client: MockApiToolClient,
) -> None:
    ports = {
        create_road_server(tool_client).settings.port,
        create_weather_server(tool_client).settings.port,
        create_resource_server(tool_client).settings.port,
    }

    assert ports == {8101, 8102, 8103}
    assert 8000 not in ports
