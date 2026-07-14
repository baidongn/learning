import json

import httpx
import pytest

from highway_agent.config import Settings
from highway_agent.models import DeepSeekChatClient


@pytest.mark.asyncio
async def test_deepseek_client_uses_current_model_and_openai_compatible_endpoint() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": '{"status":"ok"}'}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 3, "total_tokens": 13},
            },
        )

    settings = Settings(model_mode="live", deepseek_api_key="test-key")
    client = DeepSeekChatClient(settings, transport=httpx.MockTransport(handler))

    response = await client.complete_json("system", "user")

    assert captured["url"] == "https://api.deepseek.com/chat/completions"
    assert captured["body"]["model"] == "deepseek-v4-flash"
    assert captured["body"]["thinking"] == {"type": "disabled"}
    assert response.content == {"status": "ok"}
    assert response.total_tokens == 13


def test_deepseek_live_client_requires_api_key() -> None:
    settings = Settings(model_mode="live", deepseek_api_key="")

    with pytest.raises(ValueError, match="DEEPSEEK_API_KEY"):
        DeepSeekChatClient(settings)

