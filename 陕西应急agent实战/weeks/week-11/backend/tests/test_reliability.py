"""外部 Tool 熔断器测试。"""

import pytest

from highway_agent.reliability import CircuitBreaker, CircuitOpenError


@pytest.mark.asyncio
async def test_circuit_opens_after_three_consecutive_failures() -> None:
    breaker = CircuitBreaker(failure_threshold=3, recovery_seconds=30)

    async def failing_operation() -> str:
        raise RuntimeError("模拟上游故障")

    for _ in range(3):
        with pytest.raises(RuntimeError):
            await breaker.call(failing_operation)

    assert breaker.state == "open"
    with pytest.raises(CircuitOpenError):
        await breaker.call(failing_operation)


@pytest.mark.asyncio
async def test_half_open_probe_recovers_after_cooldown() -> None:
    now = [100.0]
    breaker = CircuitBreaker(
        failure_threshold=1,
        recovery_seconds=10,
        clock=lambda: now[0],
    )

    async def failing_operation() -> str:
        raise RuntimeError("模拟失败")

    with pytest.raises(RuntimeError):
        await breaker.call(failing_operation)
    now[0] = 111.0

    result = await breaker.call(lambda: _successful("恢复成功"))

    assert result == "恢复成功"
    assert breaker.state == "closed"


@pytest.mark.asyncio
async def test_failure_result_can_open_circuit_without_raising() -> None:
    """ToolResult 风格的显式失败也应累计，而不只统计异常。"""

    breaker = CircuitBreaker[bool](
        failure_threshold=2,
        is_failure=lambda result: result is False,
    )

    assert await breaker.call(lambda: _successful(False)) is False
    assert await breaker.call(lambda: _successful(False)) is False
    assert breaker.state == "open"

    with pytest.raises(CircuitOpenError):
        await breaker.call(lambda: _successful(True))


async def _successful(value: str) -> str:
    return value
