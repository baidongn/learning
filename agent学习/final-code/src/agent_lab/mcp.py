"""将受信任的 MCP 工具转换为内部 ToolSpec。"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, create_model

from agent_lab.tools import ToolRegistry, ToolSpec


class MCPServerNotAllowedError(PermissionError):
    """MCP 服务没有进入白名单。"""


class MCPTool(BaseModel):
    """从 MCP ListTools 响应提取出的最小工具描述。"""

    name: str
    description: str
    input_schema: dict[str, Any]


_TYPE_MAP: dict[str, type[Any]] = {
    "string": str,
    "integer": int,
    "number": float,
    "boolean": bool,
    "array": list,
    "object": dict,
}


def _schema_to_model(name: str, schema: dict[str, Any]) -> type[BaseModel]:
    """把常用 JSON Schema 字段转为 Pydantic 模型。

    完整 JSON Schema 很复杂；生产环境可改用 jsonschema 预校验。这里覆盖
    MCP 工具最常见的基础类型，并让额外字段保持拒绝策略。
    """

    required = set(schema.get("required", []))
    fields: dict[str, tuple[Any, Any]] = {}
    for field_name, definition in schema.get("properties", {}).items():
        python_type = _TYPE_MAP.get(definition.get("type", "string"), Any)
        default = ... if field_name in required else None
        if default is None:
            python_type = python_type | None
        fields[field_name] = (python_type, default)
    model_name = "".join(part.title() for part in name.split("_")) + "Input"
    return create_model(model_name, __config__={"extra": "forbid"}, **fields)


class MCPAdapter:
    """只暴露白名单 MCP 服务中的显式工具。"""

    def __init__(self, registry: ToolRegistry, allowed_servers: set[str]) -> None:
        self.registry = registry
        self.allowed_servers = allowed_servers

    def register_tool(
        self, server: str, tool: MCPTool, handler: Callable[..., Any]
    ) -> str:
        if server not in self.allowed_servers:
            raise MCPServerNotAllowedError(f"MCP 服务 {server!r} 不在白名单")
        safe_server = re.sub(r"[^a-zA-Z0-9_]", "_", server)
        safe_tool = re.sub(r"[^a-zA-Z0-9_]", "_", tool.name)
        name = f"mcp_{safe_server}_{safe_tool}"
        self.registry.register(
            ToolSpec(
                name=name,
                description=f"来自 MCP 服务 {server}：{tool.description}",
                input_model=_schema_to_model(name, tool.input_schema),
                handler=handler,
                tags={"mcp", f"server:{server}"},
            )
        )
        return name
