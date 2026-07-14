"""Tool 边界的轻量熔断器。"""

from collections.abc import Awaitable, Callable
from time import monotonic
from typing import Generic, Literal, TypeVar

T = TypeVar("T")


class CircuitOpenError(RuntimeError):
    """熔断期间拒绝继续压垮故障上游。"""


class CircuitBreaker(Generic[T]):
    """连续失败后打开，冷却后允许一次半开探测。"""

    def __init__(
        self,
        *,
        failure_threshold: int = 3,
        recovery_seconds: float = 30.0,
        clock: Callable[[], float] = monotonic,
        is_failure: Callable[[T], bool] | None = None,
    ) -> None:
        if failure_threshold < 1:
            raise ValueError("failure_threshold 必须大于等于 1")
        self.failure_threshold = failure_threshold
        self.recovery_seconds = recovery_seconds
        self.clock = clock
        self.is_failure = is_failure or (lambda _result: False)
        self.failure_count = 0
        self.opened_at: float | None = None
        self.state: Literal["closed", "open", "half_open"] = "closed"

    async def call(self, operation: Callable[[], Awaitable[T]]) -> T:
        """在熔断状态机保护下执行一次异步 Tool 调用。"""

        if self.state == "open":
            assert self.opened_at is not None
            if self.clock() - self.opened_at < self.recovery_seconds:
                raise CircuitOpenError("上游工具处于熔断冷却期")
            self.state = "half_open"

        try:
            result = await operation()
        except Exception:
            self.failure_count += 1
            if self.state == "half_open" or self.failure_count >= self.failure_threshold:
                self.state = "open"
                self.opened_at = self.clock()
            raise

        if self.is_failure(result):
            self._record_failure()
            return result
        self._record_success()
        return result

    def _record_failure(self) -> None:
        """累计显式失败，并在达到门槛或半开失败时打开熔断。"""

        self.failure_count += 1
        if self.state == "half_open" or self.failure_count >= self.failure_threshold:
            self.state = "open"
            self.opened_at = self.clock()

    def _record_success(self) -> None:
        """成功调用关闭熔断并清空连续失败计数。"""

        self.failure_count = 0
        self.opened_at = None
        self.state = "closed"
