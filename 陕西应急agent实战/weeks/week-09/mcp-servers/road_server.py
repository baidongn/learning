"""启动路况 MCP 服务：python mcp-servers/road_server.py。"""

from highway_agent.mcp_servers import create_road_server


if __name__ == "__main__":
    create_road_server().run(transport="streamable-http")
