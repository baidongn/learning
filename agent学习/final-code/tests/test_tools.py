import pytest
from pydantic import BaseModel

from agent_lab.tools import (
    ToolContext,
    ToolError,
    ToolNotFoundError,
    ToolRegistry,
    ToolSpec,
    ToolValidationError,
)


class ValueInput(BaseModel):
    value: int


async def test_unknown_tool_is_rejected() -> None:
    registry = ToolRegistry()

    with pytest.raises(ToolNotFoundError, match="未注册"):
        await registry.invoke("missing", {}, ToolContext(user_id="u1"))


async def test_transient_failure_is_retried() -> None:
    attempts = 0

    async def unstable(value: int) -> str:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise RuntimeError("临时失败")
        return str(value)

    registry = ToolRegistry()
    registry.register(
        ToolSpec(
            name="unstable",
            description="测试重试",
            input_model=ValueInput,
            handler=unstable,
            retries=2,
        )
    )

    result = await registry.invoke("unstable", {"value": 7}, ToolContext(user_id="u1"))

    assert result.output == "7"
    assert result.attempts == 3


async def test_idempotency_key_prevents_duplicate_side_effect() -> None:
    executions = 0

    async def side_effect(value: int) -> str:
        nonlocal executions
        executions += 1
        return f"完成:{value}"

    registry = ToolRegistry()
    registry.register(
        ToolSpec(
            name="side_effect",
            description="测试幂等",
            input_model=ValueInput,
            handler=side_effect,
        )
    )
    context = ToolContext(user_id="u1", idempotency_key="same-request")

    first = await registry.invoke("side_effect", {"value": 1}, context)
    second = await registry.invoke("side_effect", {"value": 1}, context)

    assert first.output == second.output
    assert executions == 1
    assert second.cached is True


async def test_invalid_tool_arguments_are_rejected() -> None:
    registry = ToolRegistry()
    registry.register(
        ToolSpec(
            name="typed",
            description="测试参数校验",
            input_model=ValueInput,
            handler=lambda value: value,
        )
    )

    with pytest.raises(ToolValidationError, match="参数错误"):
        await registry.invoke("typed", {"value": "不是数字"}, ToolContext(user_id="u1"))


async def test_timeout_is_retried_and_normalized() -> None:
    async def slow(value: int) -> int:
        await __import__("asyncio").sleep(0.02)
        return value

    registry = ToolRegistry()
    registry.register(
        ToolSpec(
            name="slow",
            description="测试超时",
            input_model=ValueInput,
            handler=slow,
            timeout_seconds=0.001,
            retries=1,
        )
    )

    with pytest.raises(ToolError, match="重试后仍失败"):
        await registry.invoke("slow", {"value": 1}, ToolContext(user_id="u1"))


async def test_sync_tool_also_honors_timeout() -> None:
    import time

    def blocking(value: int) -> int:
        time.sleep(0.02)
        return value

    registry = ToolRegistry()
    registry.register(
        ToolSpec(
            name="blocking",
            description="测试同步工具超时",
            input_model=ValueInput,
            handler=blocking,
            timeout_seconds=0.001,
        )
    )

    with pytest.raises(ToolError, match="重试后仍失败"):
        await registry.invoke("blocking", {"value": 1}, ToolContext(user_id="u1"))
