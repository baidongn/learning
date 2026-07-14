# Week 7：MCP 工具服务

本周不增加 Agent，只把前六周已经测试过的 REST Tool 暴露为三个 MCP 服务：路况/摄像头、气象、资源/路线。

## 快速开始

```bash
cp .env.example .env
make setup
make run
```

另开终端启动一个 MCP 服务：

```bash
PYTHONPATH=backend/src .venv/bin/python mcp-servers/road_server.py
```

运行 `make test`、`make eval`、`make verify` 验证 5 个 MCP Tool 的发现和调用。课程正文见 `WEEK-07-COURSE.md`，协议说明见根目录 `MCP.md`。
