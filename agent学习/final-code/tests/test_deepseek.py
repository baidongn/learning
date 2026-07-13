import pytest
from pydantic import BaseModel, ValidationError

from agent_lab.deepseek import FakeDeepSeekClient, ModelReply, TokenUsage, ToolCall


class Intent(BaseModel):
    route: str


async def test_fake_client_supports_structured_output() -> None:
    client = FakeDeepSeekClient(structured_payloads=[{"route": "rag"}])

    result = await client.structured_output([{"role": "user", "content": "查询制度"}], Intent)

    assert result == Intent(route="rag")


async def test_fake_client_reports_usage() -> None:
    client = FakeDeepSeekClient(
        replies=[ModelReply(content="你好", usage=TokenUsage(prompt_tokens=4, completion_tokens=2))]
    )

    reply = await client.chat([{"role": "user", "content": "你好"}])

    assert reply.content == "你好"
    assert reply.usage.total_tokens == 6


async def test_invalid_structured_output_is_rejected() -> None:
    client = FakeDeepSeekClient(structured_payloads=[{"unknown": "rag"}])

    with pytest.raises(ValidationError):
        await client.structured_output([{"role": "user", "content": "查询制度"}], Intent)


async def test_fake_client_has_explicit_tool_call_interface() -> None:
    expected = ToolCall(id="call-1", name="query_order", arguments={"order_id": "1002"})
    client = FakeDeepSeekClient(replies=[ModelReply(tool_calls=[expected])])

    calls = await client.tool_call(
        [{"role": "user", "content": "查询订单1002"}],
        [{"type": "function", "function": {"name": "query_order", "parameters": {}}}],
    )

    assert calls == [expected]
