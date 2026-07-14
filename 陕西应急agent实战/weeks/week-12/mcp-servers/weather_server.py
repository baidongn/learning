"""启动气象 MCP 服务：python mcp-servers/weather_server.py。"""

from highway_agent.mcp_servers import create_weather_server


if __name__ == "__main__":
    create_weather_server().run(transport="streamable-http")
