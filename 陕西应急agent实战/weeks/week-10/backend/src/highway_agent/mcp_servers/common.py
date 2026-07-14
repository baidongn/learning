"""MCP 服务共用的序列化辅助函数。"""

from typing import Any

from highway_agent.tools import ToolResult


def serialize_result(result: ToolResult) -> dict[str, Any]:
    """把内部 ToolResult 转换为 MCP 可传输的 JSON 对象。"""

    return result.model_dump(mode="json")
