"""环境变量配置；敏感信息不进入代码仓库。"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    deepseek_api_key: str | None = None
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_chat_model: str = "deepseek-chat"
    deepseek_reasoning_model: str = "deepseek-reasoner"
    database_url: str = "postgresql://agent:agent@postgres:5432/agent"
    redis_url: str = "redis://redis:6379/0"
    cors_origins: str = "*"


@lru_cache
def get_settings() -> Settings:
    """缓存配置，测试时可清除缓存后覆盖环境变量。"""
    return Settings()
