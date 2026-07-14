"""气象 MCP 服务。"""

from typing import Any

from mcp.server.fastmcp import FastMCP

from highway_agent.mcp_servers.common import serialize_result
from highway_agent.tools import MockApiToolClient


def create_weather_server(client: MockApiToolClient | None = None) -> FastMCP:
    """创建只包含气象预警查询工具的 MCP 服务。"""

    tool_client = client or MockApiToolClient(base_url="http://127.0.0.1:8000")
    server = FastMCP(
        "shaanxi-highway-weather-tools",
        instructions="只读查询陕西高速模拟气象预警。",
        host="127.0.0.1",
        port=8102,
    )

    @server.tool(description="查询指定路段的模拟气象预警")
    async def query_weather_warning(
        section_id: str, scenario: str | None = None
    ) -> dict[str, Any]:
        result = await tool_client.query_weather_warning(section_id, scenario)
        return serialize_result(result)

    return server
