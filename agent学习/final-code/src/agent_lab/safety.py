"""输入安全、敏感信息与执行预算。"""

from __future__ import annotations

import re

from pydantic import BaseModel


class SafetyDecision(BaseModel):
    allowed: bool
    reason: str = ""


class BudgetExceededError(RuntimeError):
    """Agent 超出运行预算。"""


class ExecutionBudget:
    """限制失控循环、工具次数和费用。"""

    def __init__(
        self,
        max_iterations: int = 8,
        max_tool_calls: int = 5,
        max_tokens: int = 12_000,
    ) -> None:
        self.max_iterations = max_iterations
        self.max_tool_calls = max_tool_calls
        self.max_tokens = max_tokens
        self.iterations = 0
        self.tool_calls = 0
        self.tokens = 0

    def record_iteration(self) -> None:
        self.iterations += 1
        if self.iterations > self.max_iterations:
            raise BudgetExceededError("超过允许的循环次数")

    def record_tool_call(self) -> None:
        self.tool_calls += 1
        if self.tool_calls > self.max_tool_calls:
            raise BudgetExceededError("超过允许的工具调用次数")

    def record_tokens(self, value: int) -> None:
        self.tokens += value
        if self.tokens > self.max_tokens:
            raise BudgetExceededError("超过允许的 Token 数")


class SafetyPolicy:
    """演示版安全策略；生产环境应叠加专业审核服务。"""

    _injection_patterns = (
        r"忽略.{0,8}(之前|以上).{0,8}指令",
        r"输出.{0,8}(系统提示|system prompt)",
        r"ignore.{0,8}(previous|all).{0,8}instructions",
    )
    _blocked_terms = ("制作炸弹", "盗取密码")

    def check_input(self, text: str) -> SafetyDecision:
        lowered = text.lower()
        if any(re.search(pattern, lowered, re.IGNORECASE) for pattern in self._injection_patterns):
            return SafetyDecision(allowed=False, reason="检测到提示词注入")
        if any(term in lowered for term in self._blocked_terms):
            return SafetyDecision(allowed=False, reason="内容不符合安全策略")
        return SafetyDecision(allowed=True)

    @staticmethod
    def redact_pii(text: str) -> str:
        text = re.sub(r"\b1[3-9]\d{9}\b", "[手机号已隐藏]", text)
        return re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[邮箱已隐藏]", text)

