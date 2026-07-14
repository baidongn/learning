"""路况 MCP 服务。"""

from typing import Any

from mcp.server.fastmcp import FastMCP

from highway_agent.mcp_servers.common import serialize_result
from highway_agent.tools import MockApiToolClient


def create_road_server(client: MockApiToolClient | None = None) -> FastMCP:
    """创建只包含路况与摄像头分析工具的 MCP 服务。"""

    tool_client = client or MockApiToolClient(base_url="http://127.0.0.1:8000")
    server = FastMCP(
        "shaanxi-highway-road-tools",
        instructions="只读查询陕西高速模拟路况与摄像头结构化分析。",
        host="127.0.0.1",
        port=8101,
    )

    @server.tool(description="查询指定高速路段的模拟通行状态")
    async def query_road_status(
        road_code: str, section_id: str, scenario: str | None = None
    ) -> dict[str, Any]:
        result = await tool_client.query_road_status(road_code, section_id, scenario)
        return serialize_result(result)

    @server.tool(description="查询摄像头已经完成的模拟结构化分析结果")
    async def query_camera_analysis(
        camera_id: str, scenario: str | None = None
    ) -> dict[str, Any]:
        result = await tool_client.query_camera_analysis(camera_id, scenario)
        return serialize_result(result)

    return server
