# MCP 设计与启动

Week 7 开始提供三个 FastMCP Server，MCP 层只做协议适配，业务仍由已测试的 REST Tool Client 完成。

| 服务 | Tool |
|---|---|
| `shaanxi-highway-road-tools` | `query_road_status`、`query_camera_analysis` |
| `shaanxi-highway-weather-tools` | `query_weather_warning` |
| `shaanxi-highway-resource-tools` | `query_nearby_resources`、`estimate_route` |

启动示例：

```bash
cd weeks/week-07
make setup
make run                       # 终端 1：模拟 REST API
make run-mcp-road              # 终端 2：Road MCP
```

默认 Transport 是 Streamable HTTP。单元测试使用工厂注入 ASGITransport，直接验证 `list_tools` 与 `call_tool`，无需开启网络端口。
