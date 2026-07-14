"""应急资源 MCP 服务。"""

from typing import Any

from mcp.server.fastmcp import FastMCP

from highway_agent.mcp_servers.common import serialize_result
from highway_agent.tools import MockApiToolClient


def create_resource_server(client: MockApiToolClient | None = None) -> FastMCP:
    """创建资源查询与路线估算 MCP 服务。"""

    tool_client = client or MockApiToolClient(base_url="http://127.0.0.1:8000")
    server = FastMCP(
        "shaanxi-highway-resource-tools",
        instructions="只读查询模拟救援资源并估算到场时间。",
        host="127.0.0.1",
        port=8103,
    )

    @server.tool(description="查询指定路段附近的可用模拟救援资源")
    async def query_nearby_resources(
        section_id: str, resource_type: str | None = None
    ) -> dict[str, Any]:
        result = await tool_client.query_nearby_resources(section_id, resource_type)
        return serialize_result(result)

    @server.tool(description="估算救援资源到事件路段的模拟行车时间")
    async def estimate_route(
        origin: str, destination: str, distance_km: float
    ) -> dict[str, Any]:
        result = await tool_client.estimate_route(origin, destination, distance_km)
        return serialize_result(result)

    return server
