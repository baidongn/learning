# Week 3 架构

Agent → Tool Adapter → HTTP API 是唯一调用路径。Agent 只读 `ToolResult`；失败不抛到业务层，便于 Week 4 用图分支处理。

