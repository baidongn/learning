# 第 3 周：HTTP Tool 与事件研判 Agent

> 学习方式：5 天，每天 2～3 小时。直接继承第 2 周完整代码。
>
> 本周终点：把第 1 周的模拟 REST API 包装成三个只读 Tool，新增可独立运行的事件研判 Agent，并输出事实、缺失字段、风险等级和完整 Tool 调用轨迹。

## 1. 本周学习地图与最终成果

第 2 周的预案专家只调用本地 Retriever。第 3 周开始让 Agent 获取“系统外部”的实时上下文。

本周完整调用链：

```text
事件上报
  -> IncidentAnalysisRequest
  -> IncidentAnalysisAgent
       -> query_road_status
       -> query_weather_warning
       -> query_camera_analysis（可选）
  -> ToolResult 统一成功/失败
  -> 事件类型和风险规则
  -> IncidentAssessment
       -> known_facts
       -> missing_fields
       -> tool_trace
```

五天安排：

| Day | 核心内容 | 当天产出 |
|---|---|---|
| Day 1 | ToolResult 与 HTTP 适配器 | 一个统一封装 HTTP 成功/失败的工具客户端 |
| Day 2 | 三个只读 Tool 与异常测试 | 路况、天气、摄像头 Tool 可独立调用 |
| Day 3 | 摄像头模拟 API 与结构化结果 | 不处理真实视频的视觉结果接口 |
| Day 4 | 事件研判 Agent | 固定顺序调用 Tool 并生成结构化研判 |
| Day 5 | API、评测与验收 | 完成 Agent HTTP 演示和可靠性测试 |

本周新增第二个 Agent：

```text
IncidentAnalysisAgent（事件研判 Agent）
```

已有预案专家继续保留，但两个 Agent 暂不互相调用。第 4 周才使用 LangGraph 把它们串成双 Agent 工作流。

本周 Tool 是什么？

```text
模拟 REST API
  -> MockApiToolClient
  -> async Python 方法
  -> ToolResult
```

它不是 LangChain `@tool`，也不是 MCP。这样安排是为了先学清楚最基础的工具边界：输入、HTTP、超时、错误映射、来源、时间戳和 trace_id。第 7 周再把成熟的工具协议升级为 MCP。

本周必做：

- 三个只读 Tool。
- 统一 ToolResult。
- 事件研判 Agent。
- 工具调用轨迹。
- 404/503/断连/stale 测试。
- `make test`、`make eval`、`make verify` 全部通过。

本周选做：

- 给 Tool 增加一个显式 timeout 测试。
- 为更多 camera_id 定义固定结果。
- 将工具轨迹以表格方式打印到终端。

## 2. 前置知识、环境准备和本周起点

先验收第 2 周：

```bash
cd weeks/week-02
make test
make eval
make verify
```

进入第 3 周：

```bash
cd ../week-03
cp .env.example .env
make setup
```

本周默认仍然是：

```dotenv
MODEL_MODE=mock
DEEPSEEK_API_KEY=
```

第 3 周完整目录相对上周新增：

```text
backend/src/highway_agent/
├── agents/
│   ├── plan_expert.py
│   └── incident_analysis.py   # 新增
├── api.py                     # 新增 camera 和 incident API
├── domain.py                  # 新增 CameraAnalysis
├── rag.py
├── models.py
└── tools.py                   # 新增
```

你需要先理解两条边界：

1. 模拟 API 是被调用系统，返回 HTTP 状态码和 JSON。
2. Tool 是适配层，把 HTTP 细节转换成 Agent 能稳定处理的 `ToolResult`。

本周使用 `httpx.ASGITransport(app=app)` 做进程内 HTTP 调用。它仍经过 ASGI 路由、参数解析、响应模型和状态码，但不需要额外启动 8000 端口，非常适合自动测试。

## 3. 本周架构、目录变化与完整调用链

Tool 边界：

```text
Agent
  只理解 ToolResult
       |
       v
MockApiToolClient
  负责 URL、参数、Header、超时和错误映射
       |
       v
FastAPI 模拟外部系统
  返回 200 / 404 / 503
```

统一 ToolResult：

```text
success
data
error_code
message
source
observed_at
trace_id
```

为什么一定要统一？

如果 Agent 直接处理 httpx：

```text
路况 404 的 JSON
天气 503 的 JSON
连接异常 Python Exception
超时 Python Exception
正常响应 JSON
```

每个分支都不同。经过 ToolResult 后：

```text
成功：success=True + data
失败：success=False + error_code
```

Agent 的业务逻辑会简单很多。

本周安全范围：

- 所有 Tool 只读。
- 摄像头接口只返回模拟结构化结果。
- 不接触真实视频流。
- 不执行封路、派车、通知。
- 不把工具失败伪装成成功事实。
- 工具来源和时间戳必须保留。

## 4. Day 1：创建统一 ToolResult 和 HTTP 调用适配层

### 今天目标

1. 定义所有 Tool 共用的结果 Schema。
2. 保留 source、observed_at 和 trace_id。
3. 创建可注入 Transport 的 HTTP 客户端。
4. 统一捕获超时和连接异常。
5. 统一映射 HTTP 错误。
6. 测试每次 ToolResult 都有独立时间戳。

### 上一节衔接

第 2 周 Agent 只依赖本地 Retriever，不需要处理外部系统错误。

今天先做工具底座，不急着写事件研判规则。Tool 自己必须先可独立调用和测试。

### 先说结论

Agent 不应该看到：

```python
httpx.Response
httpx.TimeoutException
httpx.ConnectError
```

Agent 只应该看到：

```python
ToolResult(success=True, data={...})
ToolResult(success=False, error_code="TOOL_TIMEOUT")
```

### 第 1 步：创建 ToolResult

新建 `backend/src/highway_agent/tools.py`：

```python
"""普通 HTTP Tool 适配层。

Agent 只接收 ToolResult，不需要理解 HTTP 状态码、Header 或供应商错误格式。
"""

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import httpx
from pydantic import BaseModel, Field


class ToolResult(BaseModel):
    """所有工具共享的成功/失败契约。"""

    success: bool
    data: dict[str, Any] | None = None
    error_code: str | None = None
    message: str = ""
    source: str = ""
    observed_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC)
    )
    trace_id: str
```

重点：

- `data` 只在成功时有业务内容。
- `error_code` 用于稳定分支，不依赖中文 message。
- `source` 说明证据来自哪里。
- `observed_at` 是上游数据观察时间。
- `trace_id` 是本次工具调用流水号。

### 第 2 步：为什么时间必须使用 default_factory

不推荐：

```python
observed_at: datetime = datetime.now(UTC)
```

上面会在模块导入时计算一次，长运行进程的每个实例可能拿到同一个旧时间。

推荐：

```python
observed_at: datetime = Field(
    default_factory=lambda: datetime.now(UTC)
)
```

每次构造 ToolResult 都会重新计算。

### 第 3 步：创建客户端构造函数

继续添加：

```python
class MockApiToolClient:
    """把课程模拟 REST API 包装成 Agent 可调用的只读工具。"""

    def __init__(
        self,
        base_url: str = "http://mock.local",
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = base_url
        self.transport = transport
```

生产调用可传真实 `base_url`；测试传 `ASGITransport` 或 `MockTransport`。

### 第 4 步：实现统一 _get 的请求部分

在类内添加：

```python
    async def _get(
        self,
        path: str,
        *,
        params: dict[str, str] | None = None,
        scenario: str | None = None,
    ) -> ToolResult:
        """统一处理 HTTP 错误，确保 Agent 的分支逻辑保持简单。"""

        trace_id = str(uuid4())
        headers = (
            {"X-Mock-Scenario": scenario}
            if scenario
            else {}
        )

        try:
            async with httpx.AsyncClient(
                base_url=self.base_url,
                transport=self.transport,
                timeout=5.0,
            ) as client:
                response = await client.get(
                    path,
                    params=params,
                    headers=headers,
                )
        except httpx.TimeoutException:
            return ToolResult(
                success=False,
                error_code="TOOL_TIMEOUT",
                message="模拟工具调用超时",
                trace_id=trace_id,
            )
        except httpx.RequestError:
            return ToolResult(
                success=False,
                error_code="TOOL_CONNECTION_ERROR",
                message="模拟工具连接失败",
                trace_id=trace_id,
            )
```

这里故意不向 Agent 抛出 httpx 异常。

### 第 5 步：实现 HTTP 错误和成功映射

继续在 `_get` 内添加：

```python
        if response.is_error:
            detail = response.json().get("detail", {})
            return ToolResult(
                success=False,
                error_code=detail.get(
                    "error_code",
                    f"HTTP_{response.status_code}",
                ),
                message=detail.get(
                    "message",
                    "工具调用失败",
                ),
                trace_id=trace_id,
            )

        data = response.json()
        return ToolResult(
            success=True,
            data=data,
            source=data.get(
                "source",
                "synthetic-demo-data",
            ),
            observed_at=data.get(
                "observed_at",
                datetime.now(UTC),
            ),
            trace_id=trace_id,
        )
```

关键安全点：上游如果提供 `observed_at`，必须保留它，不能用本机请求完成时间覆盖，否则后续无法识别 stale 数据。

### 第 6 步：测试时间戳工厂

新建 `backend/tests/test_tools.py`：

```python
from highway_agent.tools import ToolResult


def test_tool_result_timestamp_uses_per_instance_factory() -> None:
    """时间戳不能在模块导入时固定，长运行进程也要记录真实调用时间。"""

    field = ToolResult.model_fields["observed_at"]

    assert field.default_factory is not None
```

运行：

```bash
uv run --project backend pytest backend/tests/test_tools.py::test_tool_result_timestamp_uses_per_instance_factory -q
```

### 运行与预期输出

预期：

```text
.                                                                        [100%]
1 passed
```

手动构造结果：

```bash
uv run --project backend python -c "from highway_agent.tools import ToolResult; print(ToolResult(success=False,error_code='DEMO',trace_id='trace-demo').model_dump(mode='json'))"
```

预期包含 UTC 格式时间和 `trace-demo`。

### 对应测试

今天执行：

```bash
uv run --project backend pytest backend/tests/test_tools.py -q -k timestamp
```

暂时没有具体业务 Tool 方法，下一天补齐。

### 常见错误

错误 1：`trace_id` 使用固定字符串

每次请求应调用 `uuid4()`，否则无法区分多次工具调用。

错误 2：捕获 `Exception`

过宽捕获会隐藏编程错误。本节只捕获 `TimeoutException` 和 `RequestError`。

错误 3：失败结果仍放 data

失败时 `data=None`，业务分支读取前必须看 `success`。

错误 4：覆盖上游时间

成功结果优先使用 `data["observed_at"]`。

错误 5：用 message 做流程判断

message 给人看；程序使用稳定 `error_code`。

### 当天小练习

连续构造两个 ToolResult，打印 `observed_at` 和 `trace_id`。

要求：

- 两个 trace_id 不相同。
- 时间带时区。
- 不需要人为 sleep。

### 今日总结与明日预告

今天完成了 Tool 的统一结果边界和 HTTP 通用调用。

明天添加三个正式只读方法，并用 ASGITransport/MockTransport 测试成功、503、断连和 stale。

## 5. Day 2：实现路况、天气和摄像头三个只读 Tool

### 今天目标

1. 为路况查询定义清晰参数。
2. 为天气查询定义清晰参数。
3. 为摄像头结构化分析定义清晰参数。
4. 用 ASGITransport 测试真实路由边界。
5. 用 MockTransport 模拟连接失败。
6. 验证 503 和 stale 时间保留。
7. 理解 Tool 描述与权限边界。

### 上一节衔接

Day 1 的 `_get` 已经统一了 HTTP、超时、错误和成功结果。

今天具体 Tool 方法只负责构造路径和参数，不重复错误处理。

### 先说结论

三个 Tool：

| 方法 | 输入 | 输出 | 权限 |
|---|---|---|---|
| `query_road_status` | road_code、section_id | ToolResult | 只读 |
| `query_weather_warning` | section_id | ToolResult | 只读 |
| `query_camera_analysis` | camera_id | ToolResult | 只读模拟结果 |

它们不会操作数据库，不会执行高风险动作。

### 第 1 步：实现路况 Tool

在 `MockApiToolClient` 内添加：

```python
    async def query_road_status(
        self,
        road_code: str,
        section_id: str,
        scenario: str | None = None,
    ) -> ToolResult:
        """查询指定路段的模拟通行状态。"""

        return await self._get(
            (
                f"/mock/roads/{road_code}"
                f"/sections/{section_id}/status"
            ),
            scenario=scenario,
        )
```

调用方不需要知道 URL 结构。

### 第 2 步：实现天气 Tool

继续添加：

```python
    async def query_weather_warning(
        self,
        section_id: str,
        scenario: str | None = None,
    ) -> ToolResult:
        """查询指定路段的模拟气象预警。"""

        return await self._get(
            "/mock/weather/warnings",
            params={"section_id": section_id},
            scenario=scenario,
        )
```

### 第 3 步：实现摄像头 Tool

继续添加：

```python
    async def query_camera_analysis(
        self,
        camera_id: str,
        scenario: str | None = None,
    ) -> ToolResult:
        """查询已经完成的模拟摄像头结构化分析，不处理真实视频。"""

        return await self._get(
            f"/mock/cameras/{camera_id}/analysis",
            scenario=scenario,
        )
```

这不是视频识别。Tool 只查询一个已经结构化的模拟结果。

### 第 4 步：测试正常路况调用

在 `test_tools.py` 增加导入：

```python
import httpx
import pytest

from highway_agent.api import create_app
from highway_agent.tools import MockApiToolClient
```

增加测试：

```python
@pytest.mark.asyncio
async def test_road_tool_wraps_http_api_in_standard_result() -> None:
    app = create_app()
    tools = MockApiToolClient(
        transport=httpx.ASGITransport(app=app)
    )

    result = await tools.query_road_status(
        "G65",
        "QINLING-01",
    )

    assert result.success is True
    assert result.data["closed_lanes"] == 2
    assert result.source == "synthetic-demo-data"
    assert result.trace_id
```

### 第 5 步：测试连接失败和 503

连接失败测试：

```python
@pytest.mark.asyncio
async def test_tool_converts_connection_error_to_standard_result() -> None:
    """外部系统断连不能让 Agent 收到未处理的 httpx 异常。"""

    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        raise httpx.ConnectError(
            "模拟断连",
            request=request,
        )

    tools = MockApiToolClient(
        transport=httpx.MockTransport(handler)
    )
    result = await tools.query_road_status(
        "G65",
        "QINLING-01",
    )

    assert result.success is False
    assert result.error_code == "TOOL_CONNECTION_ERROR"
```

503 测试：

```python
@pytest.mark.asyncio
async def test_tool_converts_service_failure_to_error_result() -> None:
    app = create_app()
    tools = MockApiToolClient(
        transport=httpx.ASGITransport(app=app)
    )

    result = await tools.query_weather_warning(
        "QINLING-01",
        scenario="unavailable",
    )

    assert result.success is False
    assert result.error_code == "MOCK_SERVICE_UNAVAILABLE"
    assert result.data is None
```

### 第 6 步：测试 stale 上游时间不被覆盖

补充导入：

```python
from datetime import UTC, datetime, timedelta
```

增加测试：

```python
@pytest.mark.asyncio
async def test_tool_preserves_upstream_observation_time() -> None:
    """安全复核必须看到数据源时间，不能用本地请求时间覆盖过期证据。"""

    app = create_app()
    tools = MockApiToolClient(
        transport=httpx.ASGITransport(app=app)
    )

    result = await tools.query_road_status(
        "G65",
        "QINLING-01",
        scenario="stale",
    )

    stale_limit = datetime.now(UTC) - timedelta(minutes=60)
    assert result.observed_at < stale_limit
```

### 运行与预期输出

执行：

```bash
uv run --project backend pytest backend/tests/test_tools.py -q
```

在 Day 3 摄像头接口完成前，可以先选择非 camera 测试：

```text
.....                                                                    [100%]
5 passed, 1 deselected
```

正常 ToolResult 关键字段：

```json
{
  "success": true,
  "data": {
    "road_code": "G65",
    "closed_lanes": 2
  },
  "source": "synthetic-demo-data",
  "trace_id": "每次不同的 UUID"
}
```

### 对应测试

今天运行：

```bash
uv run --project backend pytest backend/tests/test_tools.py -q -k "not camera"
```

覆盖成功、断连、503、stale 和时间工厂。

### 常见错误

错误 1：测试中访问 `result.data["closed_lanes"]` 报类型提示

先断言 `result.success` 和 `result.data is not None`。课程测试运行时 fixture 确保它存在。

错误 2：ASGITransport 没有 app

必须传：

```python
httpx.ASGITransport(app=create_app())
```

错误 3：scenario 没传到 Header

`_get` 负责转换为 `X-Mock-Scenario`，具体 Tool 不直接拼 Header。

错误 4：503 被抛成异常

httpx 默认不会对状态码自动抛错。代码通过 `response.is_error` 映射。

错误 5：404 没有稳定错误码

模拟 API detail 中已有 `ROAD_SECTION_NOT_FOUND`，`_get` 会保留。

### 当天小练习

调用不存在路段：

```python
result = await tools.query_road_status(
    "G999",
    "UNKNOWN",
)
```

预测并验证：

- `success=False`
- `error_code=ROAD_SECTION_NOT_FOUND`
- `data=None`
- `trace_id` 非空

### 今日总结与明日预告

今天三个只读 Tool 的客户端接口已经完成。

明天补摄像头模拟 API 和 `CameraAnalysis`，让第三个 Tool 也能通过完整 HTTP 边界测试。

## 6. Day 3：增加摄像头结构化模拟 API

### 今天目标

1. 定义 `CameraAnalysis` 领域结构。
2. 明确不处理真实视频。
3. 增加固定摄像头分析 API。
4. 支持 unavailable 故障注入。
5. 用摄像头 Tool 调用 API。
6. 验证 smoke_detected 和 vehicle_count。

### 上一节衔接

Day 2 已经写好 `query_camera_analysis`，但被调用的 API 还没有加入。

今天先完成被调用系统，再让 Tool 测试闭环。

### 先说结论

本课程不做真实视频识别。

摄像头接口代表：

```text
外部视觉系统已经完成分析
  -> 本项目只读取结构化结果
```

这样可以练习多源信息融合，而不会把课程扩展成计算机视觉项目。

### 第 1 步：创建 CameraAnalysis

在 `backend/src/highway_agent/domain.py` 的 `ResourceList` 后添加：

```python
class CameraAnalysis(BaseModel):
    """真实视觉模型的模拟结构化输出。"""

    camera_id: str
    smoke_detected: bool
    stopped_vehicle_detected: bool
    vehicle_count: int = Field(ge=0)
    source: str = "synthetic-demo-data"
    observed_at: datetime
```

`vehicle_count` 不能为负，来源默认明确为模拟数据。

### 第 2 步：在 API 导入新模型

修改 `backend/src/highway_agent/api.py` 的 domain 导入，包含：

```python
from highway_agent.domain import (
    CameraAnalysis,
    EmergencyResource,
    ResourceList,
    RoadStatus,
    WeatherWarning,
)
```

### 第 3 步：增加摄像头路由

在资源路由之后、Agent 路由之前添加：

```python
    @app.get(
        "/mock/cameras/{camera_id}/analysis",
        response_model=CameraAnalysis,
    )
    async def camera_analysis(
        camera_id: str,
        x_mock_scenario: str | None = Header(default=None),
    ) -> CameraAnalysis:
        """返回模拟视觉分析结果；课程不会读取或保存真实视频。"""

        _raise_if_unavailable(x_mock_scenario)

        return CameraAnalysis(
            camera_id=camera_id,
            smoke_detected=(
                camera_id == "CAM-QINLING-01"
            ),
            stopped_vehicle_detected=True,
            vehicle_count=7,
            observed_at=datetime.now(UTC),
        )
```

固定规则：

- `CAM-QINLING-01` 检测到烟雾。
- 其他摄像头默认没有烟雾。
- 所有结果都是 synthetic。

### 第 4 步：测试摄像头 Tool

在 `test_tools.py` 添加：

```python
@pytest.mark.asyncio
async def test_camera_tool_returns_structured_analysis() -> None:
    app = create_app()
    tools = MockApiToolClient(
        transport=httpx.ASGITransport(app=app)
    )

    result = await tools.query_camera_analysis(
        "CAM-QINLING-01"
    )

    assert result.success is True
    assert result.data["smoke_detected"] is True
    assert result.data["vehicle_count"] == 7
```

### 第 5 步：手动调用接口

启动：

```bash
make run
```

调用：

```bash
curl http://127.0.0.1:8000/mock/cameras/CAM-QINLING-01/analysis
curl http://127.0.0.1:8000/mock/cameras/CAM-HANTAI-01/analysis
```

模拟不可用：

```bash
curl -i -H "X-Mock-Scenario: unavailable" http://127.0.0.1:8000/mock/cameras/CAM-QINLING-01/analysis
```

### 第 6 步：运行完整 Tool 测试

执行：

```bash
uv run --project backend pytest backend/tests/test_tools.py -q
```

此时摄像头测试也应通过。

### 运行与预期输出

秦岭摄像头：

```json
{
  "camera_id": "CAM-QINLING-01",
  "smoke_detected": true,
  "stopped_vehicle_detected": true,
  "vehicle_count": 7,
  "source": "synthetic-demo-data"
}
```

汉台摄像头：

```json
{
  "camera_id": "CAM-HANTAI-01",
  "smoke_detected": false,
  "stopped_vehicle_detected": true,
  "vehicle_count": 7,
  "source": "synthetic-demo-data"
}
```

测试预期：

```text
......                                                                   [100%]
6 passed
```

### 对应测试

执行：

```bash
uv run --project backend pytest backend/tests/test_tools.py -q
```

六条测试全部通过后，Tool 才算独立完成。

### 常见错误

错误 1：把 camera_id 当成真实流地址

它只是模拟标识，接口不读取 RTSP、文件或图片。

错误 2：observed_at 没有时区

使用 `datetime.now(UTC)`。

错误 3：source 为空

领域模型默认是 `synthetic-demo-data`，Tool 会保留。

错误 4：unavailable 没生效

路由开头必须调用 `_raise_if_unavailable`。

错误 5：真实视频识别范围膨胀

不要安装 OpenCV，不要增加目标检测模型。课程范围只到结构化结果消费。

### 当天小练习

增加一条 API 测试：

- 请求 `CAM-HANTAI-01`。
- 断言 `smoke_detected=False`。
- 断言 `vehicle_count=7`。
- 断言 `source=synthetic-demo-data`。

练习完成后运行 `test_mock_api.py` 和 `test_tools.py`。

### 今日总结与明日预告

三个 Tool 现在都能独立运行和测试。

明天创建事件研判 Agent，固定调用顺序，综合文本、路况、天气和可选摄像头结果。

## 7. Day 4：创建事件研判 Agent 和 Tool 调用轨迹

### 今天目标

1. 定义事件研判输入。
2. 定义可审计 ToolTrace。
3. 定义 IncidentAssessment。
4. 固定调用两个必需 Tool 和一个可选 Tool。
5. 根据文本与工具结果判断事件类型。
6. 计算风险等级。
7. 标记缺失的伤亡和车道信息。

### 上一节衔接

Day 1～3 已经完成三个只读 Tool。

今天先让 Agent 使用固定顺序。暂不让大模型自由选 Tool，避免同时学习“工具协议”和“自主循环”导致难度跳跃。

### 先说结论

Agent 的职责：

```text
补充上下文
+ 整理已知事实
+ 标记缺失信息
+ 给出风险建议
```

Agent 不负责：

```text
派车
封路
通知
真实调度
```

### 第 1 步：定义输入与轨迹

新建 `backend/src/highway_agent/agents/incident_analysis.py`：

```python
"""事件研判 Agent：负责抽取事实、补充上下文和提出风险建议。"""

from datetime import datetime

from pydantic import BaseModel, Field

from highway_agent.tools import (
    MockApiToolClient,
    ToolResult,
)


class IncidentAnalysisRequest(BaseModel):
    """人工上报和已知定位信息。"""

    raw_text: str = Field(
        min_length=2,
        max_length=2000,
    )
    road_code: str
    section_id: str
    camera_id: str | None = None


class ToolTrace(BaseModel):
    """可展示、可评测的工具调用摘要。"""

    tool_name: str
    success: bool
    trace_id: str
    error_code: str | None = None
    source: str = ""
    observed_at: datetime
```

### 第 2 步：定义输出与轨迹转换

继续添加：

```python
class IncidentAssessment(BaseModel):
    """事件研判 Agent 的稳定输出。"""

    incident_type: str
    risk_level: str
    known_facts: list[str]
    missing_fields: list[str]
    tool_trace: list[ToolTrace]


def _trace(
    tool_name: str,
    result: ToolResult,
) -> ToolTrace:
    """从完整 ToolResult 中提取适合状态和前端展示的轨迹。"""

    return ToolTrace(
        tool_name=tool_name,
        success=result.success,
        trace_id=result.trace_id,
        error_code=result.error_code,
        source=result.source,
        observed_at=result.observed_at,
    )
```

工具轨迹不直接暴露整个 data，避免状态无限膨胀；保留审计所需摘要。

### 第 3 步：调用必需和可选 Tool

继续添加类和方法开头：

```python
class IncidentAnalysisAgent:
    """最多调用三个只读工具，不执行任何真实业务动作。"""

    def __init__(
        self,
        tools: MockApiToolClient,
    ) -> None:
        self.tools = tools

    async def ainvoke(
        self,
        request: IncidentAnalysisRequest,
    ) -> IncidentAssessment:
        """按固定顺序补充路况、气象和可选摄像头上下文。"""

        road = await self.tools.query_road_status(
            request.road_code,
            request.section_id,
        )
        weather = await self.tools.query_weather_warning(
            request.section_id
        )

        results: list[tuple[str, ToolResult]] = [
            ("query_road_status", road),
            ("query_weather_warning", weather),
        ]

        camera: ToolResult | None = None
        if request.camera_id:
            camera = await self.tools.query_camera_analysis(
                request.camera_id
            )
            results.append(
                ("query_camera_analysis", camera)
            )
```

有 camera_id 才调用摄像头；没有时只调用两个 Tool。

### 第 4 步：判断事件类型

继续在方法内添加：

```python
        text = request.raw_text
        smoke_detected = (
            "烟" in text
            or bool(
                camera
                and camera.data
                and camera.data.get("smoke_detected")
            )
        )

        if smoke_detected:
            incident_type = "tunnel_smoke"
        elif "滑坡" in text or "落石" in text:
            incident_type = "landslide"
        elif "积水" in text:
            incident_type = "flooding"
        elif "雪" in text or "结冰" in text:
            incident_type = "snow_ice"
        else:
            incident_type = "collision"
```

烟雾优先级最高，因为它会将风险直接提升到 critical。

### 第 5 步：计算风险并识别缺失字段

继续添加：

```python
        closed_lanes = int(
            (road.data or {}).get(
                "closed_lanes",
                0,
            )
        )
        severe_weather = (
            (weather.data or {}).get("level")
            in {"orange", "red"}
        )

        if smoke_detected:
            risk_level = "critical"
        elif closed_lanes >= 2 or severe_weather:
            risk_level = "high"
        else:
            risk_level = "medium"

        missing_fields: list[str] = []
        casualty_keywords = (
            "伤亡",
            "受伤",
            "轻伤",
            "重伤",
            "死亡",
        )
        if not any(
            keyword in text
            for keyword in casualty_keywords
        ):
            missing_fields.append("casualties")

        if not any(
            keyword in text
            for keyword in ("车道", "占用")
        ):
            missing_fields.append("lane_occupancy")
```

不要因为文本没提伤亡就推断“无人伤亡”。正确做法是标记 `casualties` 缺失。

### 第 6 步：构造事实和最终输出

继续完成方法：

```python
        known_facts = [text]

        if road.success:
            known_facts.append(
                f"模拟路况关闭车道数：{closed_lanes}"
            )

        if weather.success:
            warning_type = (
                (weather.data or {}).get(
                    "warning_type",
                    "none",
                )
            )
            known_facts.append(
                f"模拟气象预警：{warning_type}"
            )

        return IncidentAssessment(
            incident_type=incident_type,
            risk_level=risk_level,
            known_facts=known_facts,
            missing_fields=missing_fields,
            tool_trace=[
                _trace(name, result)
                for name, result in results
            ],
        )
```

### 运行与预期输出

运行 Agent 测试：

```bash
uv run --project backend pytest backend/tests/test_incident_agent.py -q -k "not api"
```

预期三个异步测试通过。

关键研判：

```json
{
  "incident_type": "tunnel_smoke",
  "risk_level": "critical",
  "missing_fields": [],
  "tool_trace": [
    {"tool_name": "query_road_status"},
    {"tool_name": "query_weather_warning"},
    {"tool_name": "query_camera_analysis"}
  ]
}
```

### 对应测试

`backend/tests/test_incident_agent.py` 必须覆盖：

1. 三工具调用顺序。
2. 烟雾事件为 critical。
3. 未提伤亡时 `casualties` 缺失。
4. “轻伤”被识别为已提供伤亡信息。
5. trace source 和 UTC 时间有效。

### 常见错误

错误 1：路况 Tool 失败时访问 None

使用 `(road.data or {})` 读取默认值。

错误 2：没有 camera_id 仍调用 camera

只在 `if request.camera_id` 分支调用。

错误 3：文本未提伤亡就写“无人伤亡”

必须放入 missing_fields，不能编造。

错误 4：“1人轻伤”仍被标记缺失

关键词列表必须包含 `轻伤`、`重伤`、`死亡` 等明确表述。

错误 5：工具轨迹顺序不稳定

本周固定顺序为路况、天气、可选摄像头，为第 4 周工作流做准备。

### 当天小练习

调用：

```text
汉台路段追尾，1人轻伤，占用1车道
```

输入 G5/HANTAI-01，不传 camera_id。

确认：

- incident_type 是 collision。
- risk_level 是 medium。
- missing_fields 不含 casualties。
- tool_trace 只有两个项目。

### 今日总结与明日预告

事件研判 Agent 已经能够独立运行、调用 Tool 和输出轨迹。

明天接入 FastAPI，运行完整评测，并演示 Tool 成功和失败边界。

## 8. Day 5：接入 Agent API、运行评测与完成验收

### 今天目标

1. 用 ASGITransport 把 Agent 接回同一应用的模拟 API。
2. 增加事件研判 HTTP 路由。
3. 测试同步 TestClient 驱动异步 Agent。
4. 运行 Tool 和 Agent 核心评测。
5. 演示三工具调用轨迹。
6. 完成本周统一验收。

### 上一节衔接

Day 4 已经能在 Python 中直接调用事件研判 Agent。

今天将它接入现有 FastAPI，并保持预案专家和 Week 1 模拟接口全部可用。

### 先说结论

应用内调用链：

```text
TestClient / curl
  -> incident-analysis 路由
  -> Agent
  -> MockApiToolClient
  -> ASGITransport
  -> 同一个 FastAPI 的 /mock 路由
```

这不是直接调用 Python fixture，仍然经过 HTTP/ASGI 协议边界。

### 第 1 步：增加 API 导入

在 `backend/src/highway_agent/api.py` 导入：

```python
from highway_agent.agents.incident_analysis import (
    IncidentAnalysisAgent,
    IncidentAnalysisRequest,
    IncidentAssessment,
)
from highway_agent.tools import MockApiToolClient
```

保留现有 `import httpx`。

### 第 2 步：增加 Agent 路由

在预案专家路由之后、`return app` 之前添加：

```python
    @app.post(
        "/api/agents/incident-analysis/invoke",
        response_model=IncidentAssessment,
    )
    async def invoke_incident_analysis(
        request: IncidentAnalysisRequest,
    ) -> IncidentAssessment:
        """通过真实 HTTP ASGI 边界调用本应用提供的三个模拟 Tool。"""

        tools = MockApiToolClient(
            transport=httpx.ASGITransport(app=app)
        )
        agent = IncidentAnalysisAgent(tools)

        return await agent.ainvoke(request)
```

每次请求创建一个轻量 Tool Client 和 Agent，便于当前课程理解依赖。后续可通过 FastAPI dependency/lifespan 复用。

### 第 3 步：增加 API 测试

在 `test_incident_agent.py` 添加：

```python
from fastapi.testclient import TestClient


def test_incident_agent_api_returns_structured_assessment() -> None:
    # FastAPI TestClient 负责同步驱动异步 Agent。
    api_client = TestClient(create_app())

    response = api_client.post(
        "/api/agents/incident-analysis/invoke",
        json={
            "raw_text": (
                "秦岭隧道追尾，有烟，"
                "占用两条车道，无人伤亡"
            ),
            "road_code": "G65",
            "section_id": "QINLING-01",
            "camera_id": "CAM-QINLING-01",
        },
    )

    assert response.status_code == 200
    assert response.json()["risk_level"] == "critical"
```

### 第 4 步：启动并调用

启动：

```bash
make run
```

调用：

```bash
curl -X POST http://127.0.0.1:8000/api/agents/incident-analysis/invoke -H "Content-Type: application/json" -d '{"raw_text":"秦岭隧道两车追尾，现场有烟，占用两条车道，无人伤亡","road_code":"G65","section_id":"QINLING-01","camera_id":"CAM-QINLING-01"}'
```

再测试缺失字段：

```bash
curl -X POST http://127.0.0.1:8000/api/agents/incident-analysis/invoke -H "Content-Type: application/json" -d '{"raw_text":"高速发生追尾","road_code":"G5","section_id":"HANTAI-01"}'
```

### 第 5 步：检查完整轨迹

第一条响应中，按顺序检查：

```text
query_road_status
query_weather_warning
query_camera_analysis
```

每条都应包含：

- `success`
- `trace_id`
- `source`
- `observed_at`
- 可选 `error_code`

### 第 6 步：运行统一验收

执行：

```bash
make test
make eval
make verify
```

本周 `make eval` 聚焦测试名包含 `tools` 或 `incident_agent` 的场景。

### 运行与预期输出

完整测试预期：

```text
..................................                                       [100%]
34 passed
```

核心响应：

```json
{
  "incident_type": "tunnel_smoke",
  "risk_level": "critical",
  "known_facts": [
    "秦岭隧道两车追尾，现场有烟，占用两条车道，无人伤亡",
    "模拟路况关闭车道数：2",
    "模拟气象预警：snow"
  ],
  "missing_fields": [],
  "tool_trace": [
    {
      "tool_name": "query_road_status",
      "success": true,
      "source": "synthetic-demo-data"
    },
    {
      "tool_name": "query_weather_warning",
      "success": true,
      "source": "synthetic-demo-data"
    },
    {
      "tool_name": "query_camera_analysis",
      "success": true,
      "source": "synthetic-demo-data"
    }
  ]
}
```

### 对应测试

最终运行：

```bash
uv run --project backend pytest backend/tests/test_tools.py -q
uv run --project backend pytest backend/tests/test_incident_agent.py -q
make test
make eval
make verify
```

全部成功才进入第 4 周。

### 常见错误

错误 1：递归调用 incident API

Tool 的路径必须是 `/mock/...`，不能指向 `/api/agents/incident-analysis/invoke`。

错误 2：curl JSON 引号错误

macOS/Linux 外层使用单引号，JSON 字段使用双引号。

错误 3：API 结果没有 tool_trace

确保 Agent 最终通过 `_trace` 转换全部 results。

错误 4：模型 Key 为空导致失败

本周事件研判是确定性规则，不需要 DeepSeek。保持 mock 模式。

错误 5：评测结果不稳定

检查是否加入随机数或当前时间业务判断。本周时间只用于轨迹，不决定类型和风险。

### 当天小练习

从 API 调用一个滑坡场景：

```text
连续降雨导致落石占用两条车道，无人伤亡
```

使用 G65/QINLING-01。

确认：

- incident_type 为 landslide。
- 风险至少 high。
- missing_fields 为空。
- Tool 顺序稳定。

### 今日总结与明日预告

第 3 周完成：

```text
模拟 API
  -> HTTP Tool
  -> ToolResult
  -> 事件研判 Agent
  -> ToolTrace
  -> FastAPI
  -> 测试和评测
```

第 4 周会把事件研判 Agent 和预案专家 Agent 接入 LangGraph 双 Agent 工作流。

## 9. 本周唯一实战作业

任务：增加“道路积水”事件研判场景，并验证工具轨迹。

输入：

```text
G30宝鸡路段暴雨后严重积水，占用1条车道，暂无人员伤亡
```

如果你完成了 Week 1 的 G30 作业，使用 G30/BAOJI-01；否则先在模拟路况 fixture 中补该路段。

验收要求：

1. incident_type 为 `flooding`。
2. casualties 不在 missing_fields。
3. lane_occupancy 不在 missing_fields。
4. 不传 camera_id，因此只调用两个 Tool。
5. Tool 顺序是路况、天气。
6. 所有成功轨迹有 source 和 trace_id。
7. 增加 Agent 单元测试。
8. 增加 API 测试。
9. `make test`、`make eval`、`make verify` 全部通过。

建议先写测试：

```python
@pytest.mark.asyncio
async def test_incident_agent_recognizes_flooding() -> None:
    app = create_app()
    tools = MockApiToolClient(
        transport=httpx.ASGITransport(app=app)
    )
    agent = IncidentAnalysisAgent(tools)

    result = await agent.ainvoke(
        IncidentAnalysisRequest(
            raw_text=(
                "G30宝鸡路段暴雨后严重积水，"
                "占用1条车道，暂无人员伤亡"
            ),
            road_code="G30",
            section_id="BAOJI-01",
        )
    )

    assert result.incident_type == "flooding"
    assert "casualties" not in result.missing_fields
    assert "lane_occupancy" not in result.missing_fields
    assert len(result.tool_trace) == 2
```

不要为完成作业增加真实气象或摄像头服务。

## 10. 测试、常见错误与系统排查

按层排查：

```text
API 研判错误
  -> 直接调用 Agent
  -> 查看 tool_trace
  -> 直接调用单个 Tool
  -> 查看 ToolResult
  -> 直接调用 /mock API
```

调试命令：

```bash
uv run --project backend pytest backend/tests/test_tools.py -vv
uv run --project backend pytest backend/tests/test_incident_agent.py -vv
uv run --project backend pytest backend/tests/test_mock_api.py -vv
make test
```

故障映射：

| 现象 | 可能层 | 首查 |
|---|---|---|
| HTTP 404 | 模拟数据 | road_code/section_id |
| TOOL_CONNECTION_ERROR | Tool HTTP | transport/base_url |
| MOCK_SERVICE_UNAVAILABLE | 显式故障 | scenario Header |
| stale 未保留 | Tool 映射 | observed_at |
| 事件类型不对 | Agent 规则 | 关键词优先级 |
| 缺失字段不对 | 信息抽取 | 伤亡/车道关键词 |
| trace 少一条 | Agent 编排 | camera_id 条件 |
| source 为空 | ToolResult | 上游 data source |

调试原则：

- 先看 ToolResult，再看 Agent。
- 不要把工具失败当成零车道这一事实；当前规则用默认值只是保持流程可运行，轨迹仍明确失败。
- 不要在 Agent 里重新写 HTTP 请求。
- 不要在 Tool 中写事件类型判断。
- 不要为了测试通过移除 source、observed_at 或 trace_id。

## 11. 通关清单与三道面试题

- [ ] 能解释 API 与 Tool 的差别。
- [ ] 能定义统一 ToolResult。
- [ ] 能说明 error_code 与 message 的用途差别。
- [ ] 能解释 default_factory 时间戳。
- [ ] 能使用 ASGITransport。
- [ ] 能使用 MockTransport 模拟断连。
- [ ] 能保留上游 observed_at。
- [ ] 能独立调用三个只读 Tool。
- [ ] 能解释 camera API 为什么不是视频识别。
- [ ] 能让事件研判 Agent 标记信息缺失。
- [ ] 能输出可审计 ToolTrace。
- [ ] 能让 `make test`、`make eval`、`make verify` 通过。

### 面试题 1

为什么 Agent 不应该直接处理 httpx 的各种响应和异常？

回答要点：

HTTP 状态、供应商错误格式、超时和连接异常属于工具适配层。统一转换为 ToolResult 后，Agent 只处理 success、data 和 error_code，业务分支更简单，也便于替换 REST 为 MCP 或其他实现。

### 面试题 2

为什么 ToolResult 同时需要 observed_at 和 trace_id？

回答要点：

observed_at 表示业务证据何时被上游观测，用于判断数据新鲜度；trace_id 标识本次调用，用于串联日志和排查错误。二者含义不同，不能用请求时间代替上游观测时间。

### 面试题 3

事件上报没有伤亡信息时，为什么不能默认“无人伤亡”？

回答要点：

未提及不等于否定。应急研判必须区分已知事实和缺失信息。把它放入 missing_fields 可以触发后续补充或人工确认，避免模型或规则制造危险事实。

## 12. 本周总结与下一周衔接

本周新增了第二个独立 Agent，并第一次使用模拟 API Tool：

```text
HTTP 边界
+ 统一 ToolResult
+ 明确错误码
+ 来源与时间
+ 调用轨迹
+ 缺失信息
+ 结构化研判
```

进入第 4 周前执行：

```bash
make test
make eval
make verify
```

第 4 周将继续继承两个 Agent，并新增：

- LangGraph State。
- incident_analysis 节点。
- plan_expert 节点。
- finalize 节点。
- 条件边。
- 正常与 stop 分支。
- 工作流 API。
- 图结构与节点顺序测试。

第 4 周仍不会加入人工审批和 Checkpointer；这些放到第 5 周，保持学习曲线平滑。
