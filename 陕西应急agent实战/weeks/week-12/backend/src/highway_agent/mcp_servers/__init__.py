"""MCP 工具服务工厂。

第 7 周只把已有 REST Tool 暴露为标准 MCP 工具，不新增业务 Agent。
"""

from .resources import create_resource_server
from .road import create_road_server
from .weather import create_weather_server

__all__ = [
    "create_resource_server",
    "create_road_server",
    "create_weather_server",
]
