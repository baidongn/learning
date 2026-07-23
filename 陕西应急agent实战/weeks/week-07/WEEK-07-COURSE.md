# 第 7 周：把成熟 REST Tool 升级为 MCP 工具服务

> 学习方式：5 天，每天 2～3 小时。继承第 6 周三个专业 Agent 和普通 HTTP Tool。
>
> 本周终点：使用 FastMCP 把路况、气象、摄像头、资源和路线能力分成三个可发现、可调用的 MCP Server；本周不新增 Agent，不改变已有业务规则。

## 1. 本周学习地图与最终成果

前六周的 Tool 是 Python 方法：

```text
Agent
  -> MockApiToolClient.query_road_status(...)
  -> REST API
```

本周增加标准协议层：

```text
MCP Client
  -> tools/list
  -> tools/call
  -> FastMCP Server
  -> MockApiToolClient
  -> REST API
```

三个 Server：

| Server | 端口 | 工具 |
|---|---:|---|
| road | 8101 | query_road_status、query_camera_analysis |
| weather | 8102 | query_weather_warning |
| resource | 8103 | query_nearby_resources、estimate_route |

五天安排：

| Day | 核心内容 | 当天成果 |
|---|---|---|
| Day 1 | MCP 边界、FastMCP 与序列化 | 公共 serialize_result |
| Day 2 | Road MCP Server | 两个路况相关工具可发现 |
| Day 3 | Weather/Resource Server | 三个 Server 共五个工具 |
| Day 4 | list_tools/call_tool 合约测试 | 不启动网络也能测试 MCP |
| Day 5 | Streamable HTTP 启动与验收 | API + MCP Server 本地演示 |

本周明确不做：

- 不新增 Agent。
- 不把所有 Tool 塞进一个 Server。
- 不删除原来的 REST Tool。
- 不连接真实陕西高速接口。
- 不新增写操作。
- 不让 MCP 绕过审批。

MCP 的价值不是“让 Tool 变聪明”，而是提供标准的：

```text
工具发现
参数 Schema
工具调用
结果传输
服务边界
```

本周必做：

- 锁定 `mcp==1.28.1`。
- 公共序列化。
- 三个 FastMCP 工厂。
- 五个只读工具。
- 三个独立入口脚本。
- 工具列表和调用测试。
- 端口冲突测试。
- `make test`、`make eval`、`make verify`。

本周选做：

- 使用 MCP Inspector 连接本地 Server。
- 给每个 Server 增加健康说明文档。
- 为 MCP unavailable 场景增加测试。

## 2. 前置知识、环境准备和本周起点

先验收第 6 周：

```bash
cd weeks/week-06
make test
make eval
make verify
```

进入第 7 周：

```bash
cd ../week-07
cp .env.example .env
make setup
```

本周依赖增加：

```text
mcp==1.28.1
```

新增目录：

```text
backend/src/highway_agent/mcp_servers/
├── __init__.py
├── common.py
├── road.py
├── weather.py
└── resources.py

mcp-servers/
├── road_server.py
├── weather_server.py
└── resource_server.py

backend/tests/
└── test_mcp_servers.py
```

为什么有两层目录？

- `backend/src/highway_agent/mcp_servers`：可导入、可注入、可测试的服务工厂。
- `mcp-servers`：极薄的进程启动入口。

业务实现仍在：

```text
highway_agent.tools.MockApiToolClient
```

MCP Server 只做协议适配，不复制 HTTP 请求和错误处理。

## 3. 本周架构、目录变化与完整调用链

分层：

```text
MCP 协议层
  FastMCP / @server.tool
       |
       v
Tool 适配层
  MockApiToolClient / ToolResult
       |
       v
模拟业务 API
  FastAPI /mock/*
```

为什么分三个 Server？

1. 权限最小化：客户端只连接需要的能力域。
2. 故障隔离：气象服务异常不影响资源服务进程。
3. 独立部署：端口和扩缩容可以不同。
4. 面试展示：能说明工具域和服务边界。

MCP 工具 Schema 来自：

```text
Python 函数名
+ 类型注解
+ 参数默认值
+ description
```

例如：

```python
async def query_road_status(
    road_code: str,
    section_id: str,
    scenario: str | None = None,
) -> dict[str, Any]:
```

客户端可以发现：

- 工具名。
- 必需参数 road_code/section_id。
- 可选参数 scenario。
- 返回 JSON 对象。
- 工具描述。

MCP 结果继续保留 ToolResult：

```text
success
data
error_code
message
source
observed_at
trace_id
```

协议升级不能丢掉前几周建立的可靠性字段。

## 4. Day 1：理解 MCP 并创建公共序列化边界

### 今天目标

1. 区分普通 Tool、REST API 和 MCP。
2. 安装固定版本 MCP SDK。
3. 创建 mcp_servers 包。
4. 将 Pydantic ToolResult 序列化为 JSON。
5. 保留时间和 trace_id。
6. 设计三个 Server 边界。
7. 不修改已有 Agent。

### 上一节衔接

第 6 周已有成熟的 `MockApiToolClient`。如果没有这一层就直接写 MCP，网络异常、来源和时间处理会散落到每个 Server。

今天先复用成熟 ToolResult，建立薄协议层。

### 先说结论

三者关系：

| 层 | 作用 |
|---|---|
| REST API | 被调用业务系统 |
| Python Tool Client | 统一 HTTP 与错误 |
| MCP Server | 让标准客户端发现和调用 Tool |

MCP 不替代业务系统，也不自动创建 Agent。

### 第 1 步：锁定 MCP 依赖

确认 `backend/requirements.lock.txt` 增加：

```text
mcp==1.28.1
```

安装：

```bash
make setup
.venv/bin/python -c "import mcp; print('mcp import ok')"
```

### 第 2 步：创建包入口

创建 `backend/src/highway_agent/mcp_servers/__init__.py`：

```python
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
```

今天另外三个模块还没创建，暂时不要导入包入口做运行测试；完成 Day 3 后统一验证。

### 第 3 步：创建序列化函数

新建 `backend/src/highway_agent/mcp_servers/common.py`：

```python
"""MCP 服务共用的序列化辅助函数。"""

from typing import Any

from highway_agent.tools import ToolResult


def serialize_result(
    result: ToolResult,
) -> dict[str, Any]:
    """把内部 ToolResult 转换为 MCP 可传输的 JSON 对象。"""

    return result.model_dump(
        mode="json"
    )
```

### 第 4 步：为什么使用 mode=json

ToolResult 中的 `observed_at` 是 datetime。

普通 `model_dump()` 可能保留 datetime 对象；`mode="json"` 会得到 ISO 时间字符串，适合 MCP 传输。

示例：

```json
{
  "observed_at": "2026-07-13T08:00:00Z"
}
```

### 第 5 步：设计服务边界

先写下分组：

```text
road
  query_road_status
  query_camera_analysis

weather
  query_weather_warning

resources
  query_nearby_resources
  estimate_route
```

为什么 camera 放 road？

本课程将路况和摄像头视为道路现场信息域；气象与资源分别独立。

### 第 6 步：测试公共函数

执行：

```bash
PYTHONPATH=backend/src .venv/bin/python -c "from highway_agent.mcp_servers.common import serialize_result; from highway_agent.tools import ToolResult; print(serialize_result(ToolResult(success=False,error_code='DEMO',trace_id='trace-1')))"
```

### 运行与预期输出

预期字典包含：

```text
'success': False
'error_code': 'DEMO'
'trace_id': 'trace-1'
'observed_at': ISO 字符串
```

语法检查：

```bash
PYTHONPATH=backend/src .venv/bin/python -m py_compile backend/src/highway_agent/mcp_servers/common.py
```

无输出、退出码 0。

### 对应测试

今天回归原 Tool：

```bash
.venv/bin/python -m pytest backend/tests/test_tools.py -q
```

确保协议层没有改变 ToolResult。

### 常见错误

错误 1：直接返回 Pydantic 对象

MCP 工具返回 JSON 友好字典，使用 `mode="json"`。

错误 2：序列化时删除 trace_id

后续排查需要保留完整统一契约。

错误 3：在 common.py 创建 HTTP Client

common 只负责序列化。

错误 4：修改 Agent 改用 MCP

本周先开发 Server，不改 Agent 依赖。

错误 5：把真实接口凭证放进 Server

底层仍指向本地模拟 API。

### 当天小练习

构造成功 ToolResult，data 包含 `{"road_code": "G65"}`，序列化后确认 data、source 和 trace_id 均存在。

### 今日总结与明日预告

今天明确了协议分层和公共结果边界。

明天创建 Road FastMCP Server，学习 Server 元数据、`@server.tool`、类型 Schema 和依赖注入。

## 5. Day 2：创建 Road MCP Server 和两个工具

### 今天目标

1. 创建 FastMCP 实例。
2. 设置名称、说明、host 和 port。
3. 注入 MockApiToolClient。
4. 使用 `@server.tool`。
5. 暴露路况工具。
6. 暴露摄像头工具。
7. 保持工具只读。
8. 创建进程入口。

### 上一节衔接

Day 1 已有 `serialize_result`，可以把 ToolResult 安全传给 MCP 客户端。

今天创建第一个 Server。

### 先说结论

Road Server 自身不写业务逻辑：

```text
MCP 参数
  -> 调已有 tool_client 方法
  -> serialize_result
  -> 返回
```

### 第 1 步：创建 road.py 导入

新建 `backend/src/highway_agent/mcp_servers/road.py`：

```python
"""路况 MCP 服务。"""

from typing import Any

from mcp.server.fastmcp import FastMCP

from highway_agent.mcp_servers.common import (
    serialize_result,
)
from highway_agent.tools import (
    MockApiToolClient,
)
```

### 第 2 步：创建 Server 工厂

继续添加：

```python
def create_road_server(
    client: MockApiToolClient | None = None,
) -> FastMCP:
    """创建只包含路况与摄像头分析工具的 MCP 服务。"""

    tool_client = (
        client
        or MockApiToolClient(
            base_url="http://127.0.0.1:8000"
        )
    )

    server = FastMCP(
        "shaanxi-highway-road-tools",
        instructions=(
            "只读查询陕西高速模拟路况与"
            "摄像头结构化分析。"
        ),
        host="127.0.0.1",
        port=8101,
    )
```

依赖注入：

- 正式启动 client 为 None，调用 8000 API。
- 测试注入 ASGITransport Client，不启动网络。

### 第 3 步：暴露路况工具

在工厂内继续：

```python
    @server.tool(
        description="查询指定高速路段的模拟通行状态"
    )
    async def query_road_status(
        road_code: str,
        section_id: str,
        scenario: str | None = None,
    ) -> dict[str, Any]:
        result = await (
            tool_client.query_road_status(
                road_code,
                section_id,
                scenario,
            )
        )

        return serialize_result(result)
```

函数名成为 MCP 工具名，类型注解成为参数 Schema。

### 第 4 步：暴露摄像头工具

继续：

```python
    @server.tool(
        description=(
            "查询摄像头已经完成的模拟结构化分析结果"
        )
    )
    async def query_camera_analysis(
        camera_id: str,
        scenario: str | None = None,
    ) -> dict[str, Any]:
        result = await (
            tool_client.query_camera_analysis(
                camera_id,
                scenario,
            )
        )

        return serialize_result(result)

    return server
```

工厂最后必须返回 server，测试才能 list/call。

### 第 5 步：理解工具 Schema

预计路况输入 Schema 的关键字段：

```json
{
  "type": "object",
  "properties": {
    "road_code": {"type": "string"},
    "section_id": {"type": "string"},
    "scenario": {
      "type": ["string", "null"],
      "default": null
    }
  },
  "required": [
    "road_code",
    "section_id"
  ]
}
```

描述帮助客户端或模型理解何时使用。

### 第 6 步：创建启动脚本

新建 `mcp-servers/road_server.py`：

```python
"""启动路况 MCP 服务：python mcp-servers/road_server.py。"""

from highway_agent.mcp_servers import (
    create_road_server,
)


if __name__ == "__main__":
    create_road_server().run(
        transport="streamable-http"
    )
```

### 运行与预期输出

先不启动网络，直接列工具：

```bash
PYTHONPATH=backend/src .venv/bin/python -c "import asyncio; from highway_agent.mcp_servers.road import create_road_server; print(asyncio.run(create_road_server().list_tools()))"
```

输出中应出现：

```text
query_road_status
query_camera_analysis
```

### 对应测试

Day 4 会写完整测试。今天执行语法检查：

```bash
PYTHONPATH=backend/src .venv/bin/python -m py_compile backend/src/highway_agent/mcp_servers/road.py mcp-servers/road_server.py
```

### 常见错误

错误 1：工厂里直接 `server.run()`

会让导入时阻塞，无法单测。工厂只返回 Server，入口脚本负责 run。

错误 2：工具内重复写 httpx

调用现有 MockApiToolClient。

错误 3：忘记 return server

测试无法拿到实例。

错误 4：端口使用 8000

8000 已是 FastAPI，Road MCP 使用 8101。

错误 5：工具描述写“执行交通控制”

本 Server 只有只读查询。

### 当天小练习

打印两个 Tool 的 name 和 description，检查描述能否让不了解代码的人知道何时调用。

### 今日总结与明日预告

Road MCP Server 已完成。

明天创建 Weather 和 Resource Server，并建立三个独立进程入口。

## 6. Day 3：创建 Weather 与 Resource MCP Server

### 今天目标

1. 创建 Weather Server。
2. 暴露气象工具。
3. 创建 Resource Server。
4. 暴露资源查询工具。
5. 暴露路线估算工具。
6. 为三个 Server 分配独立端口。
7. 完成包统一导出。
8. 创建两个入口脚本。

### 上一节衔接

Day 2 已掌握 FastMCP 工厂模式。

今天按同样边界完成另外两个服务，但每份代码都要亲自写完。

### 先说结论

端口：

```text
FastAPI   8000
Road MCP  8101
Weather   8102
Resource  8103
```

端口不能冲突。

### 第 1 步：创建 Weather Server

新建 `backend/src/highway_agent/mcp_servers/weather.py`：

```python
"""气象 MCP 服务。"""

from typing import Any

from mcp.server.fastmcp import FastMCP

from highway_agent.mcp_servers.common import (
    serialize_result,
)
from highway_agent.tools import (
    MockApiToolClient,
)


def create_weather_server(
    client: MockApiToolClient | None = None,
) -> FastMCP:
    """创建只包含气象预警查询工具的 MCP 服务。"""

    tool_client = (
        client
        or MockApiToolClient(
            base_url="http://127.0.0.1:8000"
        )
    )

    server = FastMCP(
        "shaanxi-highway-weather-tools",
        instructions=(
            "只读查询陕西高速模拟气象预警。"
        ),
        host="127.0.0.1",
        port=8102,
    )

    @server.tool(
        description="查询指定路段的模拟气象预警"
    )
    async def query_weather_warning(
        section_id: str,
        scenario: str | None = None,
    ) -> dict[str, Any]:
        result = await (
            tool_client.query_weather_warning(
                section_id,
                scenario,
            )
        )

        return serialize_result(result)

    return server
```

### 第 2 步：创建 Resource Server 导入和工厂

新建 `backend/src/highway_agent/mcp_servers/resources.py`：

```python
"""应急资源 MCP 服务。"""

from typing import Any

from mcp.server.fastmcp import FastMCP

from highway_agent.mcp_servers.common import (
    serialize_result,
)
from highway_agent.tools import (
    MockApiToolClient,
)


def create_resource_server(
    client: MockApiToolClient | None = None,
) -> FastMCP:
    """创建资源查询与路线估算 MCP 服务。"""

    tool_client = (
        client
        or MockApiToolClient(
            base_url="http://127.0.0.1:8000"
        )
    )

    server = FastMCP(
        "shaanxi-highway-resource-tools",
        instructions=(
            "只读查询模拟救援资源并估算到场时间。"
        ),
        host="127.0.0.1",
        port=8103,
    )
```

### 第 3 步：暴露资源查询工具

继续：

```python
    @server.tool(
        description=(
            "查询指定路段附近的可用模拟救援资源"
        )
    )
    async def query_nearby_resources(
        section_id: str,
        resource_type: str | None = None,
    ) -> dict[str, Any]:
        result = await (
            tool_client.query_nearby_resources(
                section_id,
                resource_type,
            )
        )

        return serialize_result(result)
```

### 第 4 步：暴露路线估算工具

继续：

```python
    @server.tool(
        description=(
            "估算救援资源到事件路段的模拟行车时间"
        )
    )
    async def estimate_route(
        origin: str,
        destination: str,
        distance_km: float,
    ) -> dict[str, Any]:
        result = await (
            tool_client.estimate_route(
                origin,
                destination,
                distance_km,
            )
        )

        return serialize_result(result)

    return server
```

### 第 5 步：创建入口脚本

`mcp-servers/weather_server.py`：

```python
"""启动气象 MCP 服务：python mcp-servers/weather_server.py。"""

from highway_agent.mcp_servers import (
    create_weather_server,
)


if __name__ == "__main__":
    create_weather_server().run(
        transport="streamable-http"
    )
```

`mcp-servers/resource_server.py`：

```python
"""启动资源 MCP 服务：python mcp-servers/resource_server.py。"""

from highway_agent.mcp_servers import (
    create_resource_server,
)


if __name__ == "__main__":
    create_resource_server().run(
        transport="streamable-http"
    )
```

### 第 6 步：完成包统一导出

确认 `mcp_servers/__init__.py` 导出三个工厂：

```python
from .resources import create_resource_server
from .road import create_road_server
from .weather import create_weather_server

__all__ = [
    "create_resource_server",
    "create_road_server",
    "create_weather_server",
]
```

### 运行与预期输出

列 Weather 工具：

```bash
PYTHONPATH=backend/src .venv/bin/python -c "import asyncio; from highway_agent.mcp_servers import create_weather_server; print([t.name for t in asyncio.run(create_weather_server().list_tools())])"
```

预期：

```text
['query_weather_warning']
```

列 Resource 工具，预期包含：

```text
query_nearby_resources
estimate_route
```

### 对应测试

语法检查全部模块：

```bash
PYTHONPATH=backend/src .venv/bin/python -m py_compile backend/src/highway_agent/mcp_servers/common.py backend/src/highway_agent/mcp_servers/road.py backend/src/highway_agent/mcp_servers/weather.py backend/src/highway_agent/mcp_servers/resources.py mcp-servers/road_server.py mcp-servers/weather_server.py mcp-servers/resource_server.py
```

### 常见错误

错误 1：Resource Server 与 Weather 使用同端口

确认分别是 8103 和 8102。

错误 2：入口导入具体文件路径错误

统一从 `highway_agent.mcp_servers` 导入工厂。

错误 3：estimate_route 变成写操作

它只计算模拟 ETA。

错误 4：工具参数没有类型注解

FastMCP 需要注解生成 Schema。

错误 5：包入口循环导入

common 只依赖 tools；三个 server 再依赖 common。

### 当天小练习

对三个 Server 执行 `list_tools()`，制作一张“服务名—端口—工具名”表，与本周第 1 章核对。

### 今日总结与明日预告

三个 MCP Server、五个工具和三个入口已经齐全。

明天不启动网络，使用 FastMCP 的 list_tools/call_tool 直接测试协议契约。

## 7. Day 4：测试 MCP 工具发现、调用和端口隔离

### 今天目标

1. 创建可注入的 Tool Client fixture。
2. 调用 `server.list_tools()`。
3. 验证精确工具集合。
4. 调用 `server.call_tool()`。
5. 解析 FastMCP 结构化结果。
6. 验证底层 ToolResult 字段。
7. 验证三个端口不冲突。
8. 保持测试无外部网络。

### 上一节衔接

Day 3 已完成所有 Server 工厂。

今天用进程内 ASGITransport 调用 FastAPI 模拟系统，再通过 FastMCP API 调工具。

### 先说结论

测试链：

```text
pytest
  -> create_*_server(injected client)
  -> call_tool
  -> MockApiToolClient
  -> ASGITransport
  -> FastAPI mock API
```

不启动 8000、8101、8102、8103，也不访问互联网。

### 第 1 步：创建测试 fixture

新建 `backend/tests/test_mcp_servers.py`：

```python
"""验证第 7 周 MCP 服务暴露的工具契约。"""

import httpx
import pytest

from highway_agent.api import create_app
from highway_agent.mcp_servers import (
    create_resource_server,
    create_road_server,
    create_weather_server,
)
from highway_agent.tools import MockApiToolClient


@pytest.fixture
def tool_client() -> MockApiToolClient:
    """使用 ASGITransport 调用本地模拟 API，不依赖外部网络。"""

    transport = httpx.ASGITransport(
        app=create_app()
    )

    return MockApiToolClient(
        transport=transport
    )
```

### 第 2 步：测试 Road 工具发现

继续添加：

```python
@pytest.mark.asyncio
async def test_road_mcp_server_exposes_and_calls_road_tools(
    tool_client: MockApiToolClient,
) -> None:
    server = create_road_server(
        tool_client
    )

    tools = await server.list_tools()
    tool_names = {
        tool.name
        for tool in tools
    }

    assert tool_names == {
        "query_road_status",
        "query_camera_analysis",
    }
```

使用集合断言精确权限清单，避免误暴露其他工具。

### 第 3 步：调用 Road 工具

在同一测试继续：

```python
    content = await server.call_tool(
        "query_road_status",
        {
            "road_code": "G65",
            "section_id": "QINLING-01",
        },
    )

    # FastMCP 返回“文本内容列表 + 结构化结果”的二元组。
    payload = content[1]

    assert payload["success"] is True
    assert payload["data"]["road_code"] == "G65"
```

`payload` 就是 serialize_result 的 JSON 结构。

### 第 4 步：测试 Weather 工具集合

```python
@pytest.mark.asyncio
async def test_weather_mcp_server_exposes_weather_tool(
    tool_client: MockApiToolClient,
) -> None:
    server = create_weather_server(
        tool_client
    )

    tool_names = {
        tool.name
        for tool in await server.list_tools()
    }

    assert tool_names == {
        "query_weather_warning"
    }
```

### 第 5 步：测试 Resource 工具与调用

```python
@pytest.mark.asyncio
async def test_resource_mcp_server_exposes_resource_tools(
    tool_client: MockApiToolClient,
) -> None:
    server = create_resource_server(
        tool_client
    )

    tool_names = {
        tool.name
        for tool in await server.list_tools()
    }

    assert tool_names == {
        "query_nearby_resources",
        "estimate_route",
    }

    content = await server.call_tool(
        "estimate_route",
        {
            "origin": "西安绕城基地",
            "destination": "QINLING-01",
            "distance_km": 12.0,
        },
    )
    payload = content[1]

    assert payload["success"] is True
    assert payload["data"]["eta_minutes"] > 0
```

### 第 6 步：测试端口隔离

继续添加同步测试：

```python
def test_mcp_servers_do_not_conflict_with_api_or_each_other(
    tool_client: MockApiToolClient,
) -> None:
    ports = {
        create_road_server(
            tool_client
        ).settings.port,
        create_weather_server(
            tool_client
        ).settings.port,
        create_resource_server(
            tool_client
        ).settings.port,
    }

    assert ports == {
        8101,
        8102,
        8103,
    }
    assert 8000 not in ports
```

### 运行与预期输出

执行：

```bash
.venv/bin/python -m pytest backend/tests/test_mcp_servers.py -q
```

预期：

```text
....                                                                     [100%]
4 passed
```

### 对应测试

今天核心测试覆盖：

- 工具发现。
- 精确权限集合。
- Road 调用。
- Resource 调用。
- 结构化结果。
- 端口隔离。

### 常见错误

错误 1：`call_tool` 结果当成普通字典

当前 FastMCP 返回二元组，结构化 payload 在索引 1。

错误 2：测试启动真实 Server

直接使用工厂 API，不调用 `run()`。

错误 3：工具集合用 `<=` 宽松断言

使用精确相等，防止意外暴露危险工具。

错误 4：测试访问 127.0.0.1:8000

注入 ASGITransport Client。

错误 5：端口测试包含 8000

MCP Server 必须避开 FastAPI 端口。

### 当天小练习

增加 unavailable MCP 测试：

调用 Road Server 的 `query_road_status`，scenario 传 `unavailable`，断言：

- success=False。
- error_code=MOCK_SERVICE_UNAVAILABLE。
- trace_id 非空。

### 今日总结与明日预告

MCP 工具发现和调用合约已经自动验证。

明天启动真实 Streamable HTTP Server，完成 API + MCP 本地演示和统一验收。

## 8. Day 5：启动 Streamable HTTP MCP Server 并完成验收

### 今天目标

1. 先启动底层 FastAPI。
2. 再启动 Road MCP。
3. 理解两个进程的依赖关系。
4. 确认端口监听。
5. 了解 Streamable HTTP 入口。
6. 运行 MCP 评测。
7. 回归所有 Agent。
8. 完成统一验收。

### 上一节衔接

Day 4 已在进程内验证 Server 行为。

今天实际启动网络服务，观察协议层是独立进程。

### 先说结论

Road MCP 默认客户端访问：

```text
http://127.0.0.1:8000
```

因此必须先启动 FastAPI，再启动 MCP。

### 第 1 步：终端 A 启动 FastAPI

```bash
make run
```

检查：

```bash
curl http://127.0.0.1:8000/health
```

预期 status=ok。

### 第 2 步：终端 B 启动 Road MCP

```bash
make run-mcp-road
```

Makefile 目标：

```make
run-mcp-road:
	PYTHONPATH=backend/src $(VENV)/bin/python mcp-servers/road_server.py
```

Server 使用 Streamable HTTP 并监听 8101。

### 第 3 步：启动 Weather 和 Resource

终端 C：

```bash
PYTHONPATH=backend/src .venv/bin/python mcp-servers/weather_server.py
```

终端 D：

```bash
PYTHONPATH=backend/src .venv/bin/python mcp-servers/resource_server.py
```

开发时也可以只启动当前要调试的 Server。

### 第 4 步：检查端口

macOS/Linux：

```bash
lsof -iTCP:8000 -sTCP:LISTEN
lsof -iTCP:8101 -sTCP:LISTEN
lsof -iTCP:8102 -sTCP:LISTEN
lsof -iTCP:8103 -sTCP:LISTEN
```

应是四个监听端口。

### 第 5 步：理解客户端连接

FastMCP 的 Streamable HTTP 客户端会连接对应 Server 的 MCP endpoint，先 initialize，再 tools/list 或 tools/call。

本课程自动测试直接调用 Server API，避免把客户端命令行工具版本差异引入必做路径。

### 第 6 步：运行统一验收

停止手动 Server 后执行：

```bash
make test
make eval
make verify
```

本周 `make eval` 选择 `mcp_servers` 测试。

### 运行与预期输出

完整后端测试：

```text
.....................................................                    [100%]
53 passed
```

MCP 核心测试：

```text
....                                                                     [100%]
4 passed
```

FastAPI 健康检查：

```json
{
  "status": "ok",
  "model_mode": "mock"
}
```

### 对应测试

最终执行：

```bash
.venv/bin/python -m pytest backend/tests/test_mcp_servers.py -q
make test
make eval
make verify
```

全部通过后通关。

### 常见错误

错误 1：MCP 能启动但调用失败

确认 FastAPI 8000 正在运行，因为默认 Tool Client 依赖它。

错误 2：端口已占用

用 lsof 找到旧进程，正常停止；不要随意改端口而忘记更新测试。

错误 3：直接 curl MCP 当普通 REST

MCP Streamable HTTP 有协议握手，不等同于业务 REST 路由。

错误 4：PYTHONPATH 错误

入口脚本需要 `PYTHONPATH=backend/src`，Make 目标已配置。

错误 5：只测工具列表不测调用

Road 和 Resource 测试必须至少实际 call_tool 一次。

### 当天小练习

分别启动三个 Server，记录每个启动日志中的服务名和端口。然后正常停止，执行 `make test`，确认没有遗留端口影响测试。

### 今日总结与明日预告

第 7 周完成了从普通 Tool 到 MCP 服务的协议升级。

第 8 周会新增第四个 Agent：安全复核 Agent，对证据新鲜度、工具失败、资源缺口和审批要求进行独立审查。

## 9. 本周唯一实战作业

任务：为 Road MCP Server 增加一个只读工具 `get_road_context`，组合调用路况和摄像头 Tool。

输入：

```text
road_code
section_id
camera_id
```

输出：

```json
{
  "road": {
    "success": true
  },
  "camera": {
    "success": true
  }
}
```

要求：

1. 工具仍然只读。
2. 复用 MockApiToolClient。
3. 两个结果都使用 serialize_result。
4. 不修改底层 REST API。
5. Road Server 工具精确集合测试更新为 3 个。
6. 增加正常调用测试。
7. 增加 camera unavailable 测试。
8. 端口保持 8101。
9. 三个统一命令通过。

注意：这个组合作业只做工具聚合，不新增 Agent。

## 10. 测试、常见错误与系统排查

诊断顺序：

```text
MCP 调用失败
  -> list_tools 是否能看到工具？
  -> 参数 Schema 是否正确？
  -> call_tool 返回结构是什么？
  -> serialize_result 是否保留字段？
  -> MockApiToolClient 是否成功？
  -> FastAPI /mock API 是否成功？
```

调试命令：

```bash
.venv/bin/python -m pytest backend/tests/test_mcp_servers.py -vv
.venv/bin/python -m pytest backend/tests/test_tools.py -q
curl http://127.0.0.1:8000/health
lsof -iTCP:8101 -sTCP:LISTEN
```

症状表：

| 症状 | 可能原因 |
|---|---|
| 工具列表为空 | 装饰器未在工厂执行 |
| 工具名错误 | Python 函数名错误 |
| 参数缺 Schema | 缺类型注解 |
| call_tool 解析错误 | payload 在结果索引 1 |
| connection error | FastAPI 未启动 |
| datetime 序列化失败 | 未 mode=json |
| 端口冲突 | Server 配置重复 |
| 测试访问网络 | 未注入 ASGITransport |

安全边界：

- MCP 工具精确集合必须测试。
- 所有工具只读或无副作用。
- 不暴露审批 resume 为 MCP Tool。
- 不暴露真实控制接口。
- 不把 MCP 当授权机制；权限仍需应用层实现。

## 11. 通关清单与三道面试题

- [ ] 能区分 REST、Python Tool 和 MCP。
- [ ] 能解释 MCP 工具发现。
- [ ] 能用 FastMCP 创建 Server。
- [ ] 能用类型注解生成 Schema。
- [ ] 能写清晰工具 description。
- [ ] 能注入 Tool Client。
- [ ] 能用 mode=json 序列化。
- [ ] 能 list_tools。
- [ ] 能 call_tool。
- [ ] 能精确测试权限集合。
- [ ] 能启动 Streamable HTTP。
- [ ] 能让 `make test`、`make eval`、`make verify` 通过。

### 面试题 1

已经有 REST API，为什么还要增加 MCP Server？

回答要点：

REST 是业务系统接口；MCP 提供面向 AI 客户端的标准工具发现、参数 Schema 和调用协议。MCP Server 可以复用 REST Tool，不复制业务逻辑，并让不同客户端以统一方式使用能力。

### 面试题 2

为什么把 MCP Server 写成工厂，而不是模块导入时直接运行？

回答要点：

工厂允许依赖注入 ASGITransport Client，便于无网络测试；导入不会阻塞；同一工厂既能被入口脚本运行，也能被测试 list_tools/call_tool。

### 面试题 3

MCP 是否自动解决工具权限和安全问题？

回答要点：

不会。MCP 标准化发现和调用，但工具是否只读、谁能连接、参数如何校验、高风险操作是否审批，仍需应用设计。本课程通过服务拆分、精确工具集合测试和不暴露写工具控制风险。

## 12. 本周总结与下一周衔接

本周没有新增 Agent，而是把既有能力标准化：

```text
可靠 REST Tool
  -> FastMCP 工厂
  -> 三个能力域 Server
  -> 五个工具 Schema
  -> 工具发现
  -> 工具调用
  -> 独立进程
```

进入第 8 周前执行：

```bash
make test
make eval
make verify
```

第 8 周新增安全复核 Agent：

- 审查工具是否失败。
- 审查证据 observed_at 是否过期。
- 审查资源是否不足。
- 审查高风险动作是否要求人工批准。
- 输出 pass/review/block。
- 先独立测试，不开发 Supervisor。

MCP 服务继续保留，但安全 Agent 关注业务证据和动作边界。
