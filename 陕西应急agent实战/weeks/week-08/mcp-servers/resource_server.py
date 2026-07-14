"""启动资源 MCP 服务：python mcp-servers/resource_server.py。"""

from highway_agent.mcp_servers import create_resource_server


if __name__ == "__main__":
    create_resource_server().run(transport="streamable-http")
