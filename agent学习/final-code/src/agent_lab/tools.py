"""工具注册、校验、权限、重试、超时与幂等控制。"""

from __future__ import annotations

import asyncio
import inspect
from collections.abc import Awaitable, Callable
from typing import Any

from pydantic import BaseModel, Field, ValidationError


class ToolError(RuntimeError):
    """工具执行的统一异常。"""


class ToolNotFoundError(ToolError):
    """请求了未注册工具。"""


class ToolPermissionError(ToolError):
    """当前上下文无权调用工具。"""


class ToolValidationError(ToolError):
    """工具参数不符合 Schema。"""


class ToolContext(BaseModel):
    """模型不可伪造的运行时上下文。"""

    user_id: str
    allowed_tools: set[str] | None = None
    idempotency_key: str | None = None


class ToolResult(BaseModel):
    """规范化工具结果。"""

    name: str
    output: Any
    attempts: int = 1
    cached: bool = False


ToolHandler = Callable[..., Any | Awaitable[Any]]


class ToolSpec(BaseModel):
    """工具契约。"""

    model_config = {"arbitrary_types_allowed": True}

    name: str
    description: str
    input_model: type[BaseModel]
    handler: ToolHandler
    timeout_seconds: float = 5.0
    retries: int = 0
    risky: bool = False
    tags: set[str] = Field(default_factory=set)

    def openai_schema(self) -> dict[str, Any]:
        """生成 DeepSeek Tool Calling 使用的 JSON Schema。"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.input_model.model_json_schema(),
            },
        }


class ToolRegistry:
    """集中管理工具，避免模型直接执行任意函数。"""

    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}
        self._idempotency_cache: dict[str, ToolResult] = {}

    def register(self, spec: ToolSpec) -> None:
        self._tools[spec.name] = spec

    def get(self, name: str) -> ToolSpec:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise ToolNotFoundError(f"工具 {name!r} 未注册") from exc

    def schemas(self) -> list[dict[str, Any]]:
        return [spec.openai_schema() for spec in self._tools.values()]

    async def invoke(
        self, name: str, arguments: dict[str, Any], context: ToolContext
    ) -> ToolResult:
        spec = self.get(name)
        if context.allowed_tools is not None and name not in context.allowed_tools:
            raise ToolPermissionError(f"用户无权调用工具 {name!r}")

        cache_key = None
        if context.idempotency_key:
            cache_key = f"{name}:{context.user_id}:{context.idempotency_key}"
            if cache_key in self._idempotency_cache:
                return self._idempotency_cache[cache_key].model_copy(update={"cached": True})

        try:
            payload = spec.input_model.model_validate(arguments)
        except ValidationError as exc:
            raise ToolValidationError(f"工具 {name!r} 参数错误：{exc}") from exc

        last_error: Exception | None = None
        for attempt in range(1, spec.retries + 2):
            try:
                arguments = payload.model_dump()
                if inspect.iscoroutinefunction(spec.handler):
                    value = await asyncio.wait_for(
                        spec.handler(**arguments), timeout=spec.timeout_seconds
                    )
                else:
                    # 同步工具放入线程，避免阻塞事件循环；超时不能强制终止线程本身。
                    value = await asyncio.wait_for(
                        asyncio.to_thread(spec.handler, **arguments),
                        timeout=spec.timeout_seconds,
                    )
                    if inspect.isawaitable(value):
                        value = await asyncio.wait_for(value, timeout=spec.timeout_seconds)
                result = ToolResult(name=name, output=value, attempts=attempt)
                if cache_key:
                    self._idempotency_cache[cache_key] = result
                return result
            except (TimeoutError, RuntimeError) as exc:
                last_error = exc
        raise ToolError(f"工具 {name!r} 在重试后仍失败：{last_error}") from last_error
