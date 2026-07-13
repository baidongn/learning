"""DeepSeek 模型网关与零密钥测试替身。"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Sequence
from typing import Any, Protocol, TypeVar

from openai import AsyncOpenAI
from pydantic import BaseModel, Field

T = TypeVar("T", bound=BaseModel)


class TokenUsage(BaseModel):
    """一次模型调用的 Token 使用量。"""

    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


class ToolCall(BaseModel):
    """与厂商无关的工具调用结构。"""

    id: str
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class ModelReply(BaseModel):
    """统一后的模型回复。"""

    content: str = ""
    tool_calls: list[ToolCall] = Field(default_factory=list)
    usage: TokenUsage = Field(default_factory=TokenUsage)


class ModelGateway(Protocol):
    """Agent 依赖的最小模型接口。"""

    mode: str

    async def chat(
        self,
        messages: Sequence[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> ModelReply: ...

    async def structured_output(
        self, messages: Sequence[dict[str, Any]], schema: type[T]
    ) -> T: ...

    async def tool_call(
        self,
        messages: Sequence[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> list[ToolCall]: ...

    async def stream(self, messages: Sequence[dict[str, Any]]) -> AsyncIterator[str]: ...

    async def reasoning(self, prompt: str) -> str: ...


class DeepSeekClient:
    """通过 OpenAI-compatible API 调用 DeepSeek。"""

    mode = "deepseek"

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.deepseek.com",
        chat_model: str = "deepseek-chat",
        reasoning_model: str = "deepseek-reasoner",
        timeout: float = 30.0,
    ) -> None:
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url, timeout=timeout)
        self.chat_model = chat_model
        self.reasoning_model = reasoning_model

    async def chat(
        self,
        messages: Sequence[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> ModelReply:
        response = await self._client.chat.completions.create(
            model=self.chat_model,
            messages=list(messages),  # type: ignore[arg-type]
            tools=tools,  # type: ignore[arg-type]
        )
        message = response.choices[0].message
        tool_calls = []
        for call in message.tool_calls or []:
            tool_calls.append(
                ToolCall(
                    id=call.id,
                    name=call.function.name,
                    arguments=json.loads(call.function.arguments or "{}"),
                )
            )
        usage = response.usage
        return ModelReply(
            content=message.content or "",
            tool_calls=tool_calls,
            usage=TokenUsage(
                prompt_tokens=usage.prompt_tokens if usage else 0,
                completion_tokens=usage.completion_tokens if usage else 0,
            ),
        )

    async def structured_output(
        self, messages: Sequence[dict[str, Any]], schema: type[T]
    ) -> T:
        schema_instruction = (
            "请只返回 JSON，并严格满足以下 JSON Schema：\n"
            + json.dumps(schema.model_json_schema(), ensure_ascii=False)
        )
        augmented = [*messages, {"role": "system", "content": schema_instruction}]
        response = await self._client.chat.completions.create(
            model=self.chat_model,
            messages=augmented,  # type: ignore[arg-type]
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or "{}"
        return schema.model_validate_json(content)

    async def tool_call(
        self,
        messages: Sequence[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> list[ToolCall]:
        """显式请求一次工具选择；执行仍由 ToolRegistry 负责。"""
        reply = await self.chat(messages, tools=tools)
        return reply.tool_calls

    async def stream(self, messages: Sequence[dict[str, Any]]) -> AsyncIterator[str]:
        stream = await self._client.chat.completions.create(
            model=self.chat_model,
            messages=list(messages),  # type: ignore[arg-type]
            stream=True,
        )
        async for chunk in stream:
            text = chunk.choices[0].delta.content
            if text:
                yield text

    async def reasoning(self, prompt: str) -> str:
        response = await self._client.chat.completions.create(
            model=self.reasoning_model,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content or ""


class FakeDeepSeekClient:
    """确定性模型替身，供测试、课堂演示和离线运行使用。"""

    mode = "fake"

    def __init__(
        self,
        replies: list[ModelReply] | None = None,
        structured_payloads: list[dict[str, Any]] | None = None,
    ) -> None:
        self._replies = list(replies or [])
        self._structured_payloads = list(structured_payloads or [])

    async def chat(
        self,
        messages: Sequence[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> ModelReply:
        del tools
        if self._replies:
            return self._replies.pop(0)
        content = str(messages[-1].get("content", "")) if messages else ""
        marker = "【检索资料】"
        if marker in content:
            material = content.split(marker, 1)[1].strip().splitlines()[0]
            return ModelReply(content=f"根据资料：{material}")
        return ModelReply(content=f"Fake DeepSeek 回复：{content}")

    async def structured_output(
        self, messages: Sequence[dict[str, Any]], schema: type[T]
    ) -> T:
        del messages
        payload = self._structured_payloads.pop(0) if self._structured_payloads else {}
        return schema.model_validate(payload)

    async def tool_call(
        self,
        messages: Sequence[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> list[ToolCall]:
        reply = await self.chat(messages, tools=tools)
        return reply.tool_calls

    async def stream(self, messages: Sequence[dict[str, Any]]) -> AsyncIterator[str]:
        reply = await self.chat(messages)
        for index in range(0, len(reply.content), 6):
            yield reply.content[index : index + 6]

    async def reasoning(self, prompt: str) -> str:
        return f"Fake 推理：{prompt}"
