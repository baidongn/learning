"""应用配置：所有外部依赖都通过环境变量注入。"""

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """课程项目的统一配置入口。

    Mock 是默认模式，确保没有模型 Key 时仍可运行全部基础测试。
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "陕西高速路网应急指挥 Agent"
    model_mode: Literal["mock", "live"] = "mock"
    database_url: str = "postgresql+asyncpg://highway:highway@localhost:5432/highway_agent"
    redis_url: str = "redis://localhost:6379/0"
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_api_key: str = ""
    deepseek_model: str = "deepseek-v4-flash"
