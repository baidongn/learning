"""模型供应商适配层；Agent 不直接依赖 DeepSeek HTTP 细节。"""

import json
from dataclasses import dataclass

import httpx

from highway_agent.config import Settings


@dataclass(frozen=True)
class ModelJsonResponse:
    """统一模型响应，保留课程需要的 Token 统计。"""

    content: dict[str, object]
    total_tokens: int


class DeepSeekChatClient:
    """DeepSeek OpenAI-compatible Chat Completions 客户端。"""

    def __init__(
        self,
        settings: Settings,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if not settings.deepseek_api_key:
            raise ValueError("Live 模式必须配置 DEEPSEEK_API_KEY")
        self.settings = settings
        self.transport = transport

    async def complete_json(self, system_prompt: str, user_prompt: str) -> ModelJsonResponse:
        """请求 JSON 输出；工具型 Agent 默认关闭思考模式以降低延迟。"""

        payload = {
            "model": self.settings.deepseek_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "thinking": {"type": "disabled"},
            "response_format": {"type": "json_object"},
            "stream": False,
        }
        headers = {"Authorization": f"Bearer {self.settings.deepseek_api_key}"}
        async with httpx.AsyncClient(
            base_url=self.settings.deepseek_base_url,
            headers=headers,
            transport=self.transport,
            timeout=30.0,
        ) as client:
            response = await client.post("/chat/completions", json=payload)
            response.raise_for_status()
        body = response.json()
        content = json.loads(body["choices"][0]["message"]["content"])
        return ModelJsonResponse(
            content=content,
            total_tokens=int(body.get("usage", {}).get("total_tokens", 0)),
        )

