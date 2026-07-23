# 第 6 周：资源调度 Agent 与确定性调度草案

> 学习方式：5 天，每天 2～3 小时。继承第 5 周双 Agent、Checkpoint 和人工审批。
>
> 本周终点：新增第三个独立 Agent——资源调度 Agent。它查询附近资源和路线估算，生成可审计、可幂等重放的调度草案；不会执行真实派车，也暂不接入主工作流。

## 1. 本周学习地图与最终成果

本周新增：

```text
ResourceDispatchAgent（资源调度 Agent）
```

完整调用链：

```text
DispatchRequest
  -> query_nearby_resources Tool
  -> 按 required_types 选择可用资源
  -> estimate_route Tool
  -> 计算向上取整 ETA
  -> 按 ETA 排序
  -> UUID5 稳定 proposal_id
  -> DispatchProposal
       -> ready
       -> partial + unmet_requirements
```

五天安排：

| Day | 核心内容 | 当天成果 |
|---|---|---|
| Day 1 | 路线领域模型与模拟 API | 确定性 ETA 接口 |
| Day 2 | 资源与路线 Tool | 两个 Tool 独立可测 |
| Day 3 | 调度输入输出与 Agent | 能选择 ambulance/tow_truck |
| Day 4 | 资源缺口与幂等 | 不虚构直升机，相同请求 ID 稳定 |
| Day 5 | 独立 API、评测和验收 | 第三个 Agent 独立完成 |

为什么第 6 周不把它直接接入 LangGraph？

课程原则是：

```text
每个 Agent
  -> 先独立运行
  -> 再独立测试
  -> 再独立评测
  -> 后续才接工作流
```

这样出现问题时，可以确定是资源 Agent 自身、Tool 还是图编排。

本周必做：

- RouteEstimateRequest/RouteEstimate。
- 路线模拟 API。
- query_nearby_resources。
- estimate_route。
- DispatchRequest。
- DispatchProposal。
- ready/partial。
- 稳定 proposal_id。
- 独立 Agent API。
- `make test`、`make eval`、`make verify`。

本周选做：

- 增加第二辆同类型资源并比较 ETA。
- 为 route Tool 增加 timeout 测试。
- 设计资源已占用的 fixture。

## 2. 前置知识、环境准备和本周起点

先验收第 5 周：

```bash
cd weeks/week-05
make test
make eval
make verify
```

进入第 6 周：

```bash
cd ../week-06
cp .env.example .env
make setup
```

默认继续：

```dotenv
MODEL_MODE=mock
CHECKPOINT_BACKEND=memory
```

第 6 周完整工程保留：

- 预案专家 Agent。
- 事件研判 Agent。
- 固定双 Agent 图。
- 审批图。
- Checkpointer。
- 所有既有模拟 API 和 Tool。

本周新增：

```text
backend/src/highway_agent/
├── agents/
│   └── resource_dispatch.py
├── domain.py     # RouteEstimate 模型
├── tools.py      # resource/route Tool
└── api.py        # route mock + resource Agent API

backend/tests/
└── test_resource_agent.py
```

本周资源数据仍使用第 1 周的固定 `RESOURCE_FIXTURES`：

```text
RES-AMB-001  ambulance  8.5 km  available
RES-TOW-001  tow_truck 5.2 km  available
```

没有 helicopter，因此 helicopter 请求必须明确报告缺口。

## 3. 本周架构、目录变化与完整调用链

调度 Agent 的权限：

| 能力 | 是否允许 |
|---|---|
| 查询附近资源 | 允许，只读 |
| 估算路线 ETA | 允许，无副作用计算 |
| 生成调度草案 | 允许 |
| 调用真实派车系统 | 不允许 |
| 修改资源状态 | 不允许 |
| 绕过人工审批 | 不允许 |

路线 API 使用 POST，但仍然是无副作用计算。HTTP 方法不是判断副作用的唯一依据，业务语义才是关键。

确定性 ETA 规则：

```text
教学速度 = 60 km/h
distance_km 数值 = eta_minutes 数值
```

例如：

```text
5.2 km -> 5.2 分钟 -> Agent math.ceil -> 6 分钟
8.5 km -> 8.5 分钟 -> Agent math.ceil -> 9 分钟
```

因此 assignments 按 ETA 排序后：

```text
tow_truck
ambulance
```

幂等 proposal_id：

```text
stable_key
  = incident_id
  + 排序后的 required_types

UUID5(namespace, stable_key)
  -> 同样请求得到同样 ID
```

它不是数据库幂等锁，但为后续 Redis/持久化幂等提供稳定业务键。

## 4. Day 1：定义路线模型并创建确定性路线 API

### 今天目标

1. 定义路线估算请求。
2. 校验 distance_km 必须大于 0。
3. 定义路线响应。
4. 创建无副作用 POST API。
5. 使用 60 km/h 简化 ETA。
6. 手动验证确定性结果。
7. 保留 synthetic 来源。

### 上一节衔接

第 5 周已有资源查询 API，但没有预计到达时间。

今天先创建一个确定性的路线服务，第二天再包装为 Tool。

### 先说结论

路线服务输入：

```json
{
  "origin": "RES-TOW-001",
  "destination": "QINLING-01",
  "distance_km": 5.2
}
```

输出：

```json
{
  "eta_minutes": 5.2,
  "source": "synthetic-demo-data"
}
```

### 第 1 步：创建 RouteEstimateRequest

在 `backend/src/highway_agent/domain.py` 的 CameraAnalysis 后添加：

```python
class RouteEstimateRequest(BaseModel):
    """模拟路线服务的输入。"""

    origin: str
    destination: str
    distance_km: float = Field(gt=0)
```

`gt=0` 会拒绝 0 和负数。

### 第 2 步：创建 RouteEstimate

继续添加：

```python
class RouteEstimate(BaseModel):
    """路线服务返回的确定性 ETA。"""

    origin: str
    destination: str
    distance_km: float
    eta_minutes: float
    source: str = "synthetic-demo-data"
```

Route API 和 Agent 的 ResourceAssignment 分开：

- RouteEstimate 保留浮点分钟。
- ResourceAssignment 对外给整数分钟。

### 第 3 步：在 API 导入模型

修改 `api.py` 的 domain 导入：

```python
from highway_agent.domain import (
    CameraAnalysis,
    EmergencyResource,
    ResourceList,
    RoadStatus,
    RouteEstimate,
    RouteEstimateRequest,
    WeatherWarning,
)
```

### 第 4 步：增加路线 API

在 camera 路由后添加：

```python
    @app.post(
        "/mock/routes/estimate",
        response_model=RouteEstimate,
    )
    async def estimate_route(
        request: RouteEstimateRequest,
    ) -> RouteEstimate:
        """按 60 km/h 教学速度生成确定性 ETA。"""

        return RouteEstimate(
            origin=request.origin,
            destination=request.destination,
            distance_km=request.distance_km,
            eta_minutes=request.distance_km,
        )
```

为什么 `eta_minutes=distance_km`？

60 km/h 等于每公里 1 分钟。本课程只为练习调度数据流，不开发真实导航引擎。

### 第 5 步：启动并调用

启动：

```bash
make run
```

调用：

```bash
curl -X POST http://127.0.0.1:8000/mock/routes/estimate -H "Content-Type: application/json" -d '{"origin":"RES-TOW-001","destination":"QINLING-01","distance_km":5.2}'
```

非法距离：

```bash
curl -i -X POST http://127.0.0.1:8000/mock/routes/estimate -H "Content-Type: application/json" -d '{"origin":"RES-TOW-001","destination":"QINLING-01","distance_km":0}'
```

### 第 6 步：检查接口契约

正常应 HTTP 200；0 公里应 HTTP 422。

Swagger：

```text
http://127.0.0.1:8000/docs
```

找到 `POST /mock/routes/estimate`，确认 Schema 中 distance_km 是大于 0 的数字。

### 运行与预期输出

正常响应：

```json
{
  "origin": "RES-TOW-001",
  "destination": "QINLING-01",
  "distance_km": 5.2,
  "eta_minutes": 5.2,
  "source": "synthetic-demo-data"
}
```

非法响应状态：

```text
HTTP/1.1 422 Unprocessable Entity
```

### 对应测试

运行领域和模拟 API 回归：

```bash
.venv/bin/python -m pytest backend/tests/test_domain.py backend/tests/test_mock_api.py -q
```

下一天会通过 Tool 间接测试路线 API。

### 常见错误

错误 1：distance=0 仍成功

检查是否使用 `Field(gt=0)`。

错误 2：直接返回字典缺字段

使用 `RouteEstimate`，让响应模型校验来源和 ETA。

错误 3：加入随机交通系数

本周必须确定性，评测才能稳定。

错误 4：误以为 POST 一定有副作用

本接口只计算并返回，不写数据库、不调度资源。

错误 5：把路线服务当真实地图

source 必须是 synthetic，不用于现实路线决策。

### 当天小练习

分别请求 5.2、8.5、12.0 km，记录 eta_minutes，确认与 distance_km 数值相同。

### 今日总结与明日预告

路线领域契约和模拟 API 已完成。

明天给 Tool Client 增加资源查询和路线估算方法，统一处理 HTTP 错误。

## 5. Day 2：实现资源查询与路线估算 Tool

### 今天目标

1. 复用 Week 3 的 `_get`。
2. 创建 query_nearby_resources。
3. 支持可选 resource_type。
4. 创建 estimate_route。
5. 处理 POST 超时和连接失败。
6. 返回统一 ToolResult。
7. 独立手动调用两个 Tool。

### 上一节衔接

Day 1 已有路线 API，第 1 周已有附近资源 API。

今天让 Agent 只面对两个 Python Tool 方法，不理解 URL 或 httpx。

### 先说结论

资源 Agent 的工具箱只有：

```text
query_nearby_resources
estimate_route
```

它没有写资源状态、确认派车或通知人员的 Tool。

### 第 1 步：实现资源查询 Tool

在 `MockApiToolClient` 类末尾添加：

```python
    async def query_nearby_resources(
        self,
        section_id: str,
        resource_type: str | None = None,
    ) -> ToolResult:
        """查询可用救援资源。"""

        params = {
            "section_id": section_id,
        }

        if resource_type:
            params["resource_type"] = (
                resource_type
            )

        return await self._get(
            "/mock/resources/nearby",
            params=params,
        )
```

它复用 `_get`，自动获得 trace_id、source 和错误映射。

### 第 2 步：实现路线 Tool 的请求

继续添加：

```python
    async def estimate_route(
        self,
        origin: str,
        destination: str,
        distance_km: float,
    ) -> ToolResult:
        """调用模拟路线 API；写成 POST 但仍是无副作用计算。"""

        trace_id = str(uuid4())

        try:
            async with httpx.AsyncClient(
                base_url=self.base_url,
                transport=self.transport,
                timeout=5.0,
            ) as client:
                response = await client.post(
                    "/mock/routes/estimate",
                    json={
                        "origin": origin,
                        "destination": destination,
                        "distance_km": distance_km,
                    },
                )
```

### 第 3 步：处理路线网络异常

继续：

```python
        except httpx.TimeoutException:
            return ToolResult(
                success=False,
                error_code="TOOL_TIMEOUT",
                message="路线估算超时",
                trace_id=trace_id,
            )
        except httpx.RequestError:
            return ToolResult(
                success=False,
                error_code="TOOL_CONNECTION_ERROR",
                message="路线工具连接失败",
                trace_id=trace_id,
            )
```

### 第 4 步：处理 HTTP 错误与成功

继续完成：

```python
        if response.is_error:
            return ToolResult(
                success=False,
                error_code=(
                    f"HTTP_{response.status_code}"
                ),
                message="路线估算失败",
                trace_id=trace_id,
            )

        data = response.json()

        return ToolResult(
            success=True,
            data=data,
            source=data["source"],
            observed_at=data.get(
                "observed_at",
                datetime.now(UTC),
            ),
            trace_id=trace_id,
        )
```

路线 API 没有 observed_at，因此使用工具调用时间；来源仍来自上游响应。

### 第 5 步：手动调用资源 Tool

创建一次性异步演示可以直接在测试中完成。先运行已有资源 API：

```bash
curl "http://127.0.0.1:8000/mock/resources/nearby?section_id=QINLING-01"
```

预期两条资源。

### 第 6 步：通过 Agent 测试间接验证 Tool

第 3 天创建资源 Agent 后，正式测试会同时覆盖这两个 Tool。

今天先做语法检查：

```bash
PYTHONPATH=backend/src .venv/bin/python -m py_compile backend/src/highway_agent/tools.py
```

### 运行与预期输出

资源 API：

```json
{
  "items": [
    {
      "id": "RES-AMB-001",
      "resource_type": "ambulance",
      "distance_km": 8.5,
      "available": true
    },
    {
      "id": "RES-TOW-001",
      "resource_type": "tow_truck",
      "distance_km": 5.2,
      "available": true
    }
  ],
  "source": "synthetic-demo-data"
}
```

语法检查无输出、退出码 0。

### 对应测试

运行 Tool 回归：

```bash
.venv/bin/python -m pytest backend/tests/test_tools.py -q
```

旧 Tool 必须全部保持正常。

### 常见错误

错误 1：resource_type 为 None 仍传字符串 "None"

只有存在值时才加入 params。

错误 2：路线 Tool 没生成新 trace_id

每次 POST 调用都要 `uuid4()`。

错误 3：POST 异常未转换

保持与 `_get` 相同的 timeout/connection 语义。

错误 4：Agent 直接调用 API

Agent 只能依赖 `MockApiToolClient`。

错误 5：新增“确认派车”Tool

本周不允许任何真实写操作。

### 当天小练习

为 `query_nearby_resources("QINLING-01", "ambulance")` 写一个异步测试，断言结果只有一条且类型正确。

### 今日总结与明日预告

两个调度只读 Tool 已完成。

明天定义 DispatchRequest、ResourceAssignment、DispatchProposal，并实现资源选择和 ETA 排序。

## 6. Day 3：创建资源调度 Agent 和 ETA 排序

### 今天目标

1. 定义调度请求。
2. required_types 至少一项。
3. 定义单项资源建议。
4. 定义完整调度 Proposal。
5. 查询可用资源。
6. 按类型选择候选。
7. 调用路线 Tool。
8. 对 ETA 向上取整并排序。

### 上一节衔接

Day 2 已经能查询资源和估算路线。

今天创建第三个专业 Agent。它只生成建议，不执行派车。

### 先说结论

输入：

```json
{
  "incident_id": "INC-DISPATCH-001",
  "section_id": "QINLING-01",
  "required_types": [
    "ambulance",
    "tow_truck"
  ]
}
```

输出 assignments 按 ETA：

```text
tow_truck 6 分钟
ambulance 9 分钟
```

### 第 1 步：创建输入模型

新建 `backend/src/highway_agent/agents/resource_dispatch.py`：

```python
"""资源调度 Agent：查询约束并生成建议，不执行真实调度。"""

import math
from uuid import (
    NAMESPACE_URL,
    uuid5,
)

from pydantic import (
    BaseModel,
    Field,
)

from highway_agent.tools import (
    MockApiToolClient,
)


class DispatchRequest(BaseModel):
    """调度建议所需的最小输入。"""

    incident_id: str
    section_id: str
    required_types: list[str] = Field(
        min_length=1
    )
```

### 第 2 步：创建输出模型

继续添加：

```python
class ResourceAssignment(BaseModel):
    """单个资源的建议和预计到达时间。"""

    resource_id: str
    name: str
    resource_type: str
    distance_km: float
    eta_minutes: int


class DispatchProposal(BaseModel):
    """可审计、可幂等重放的调度建议。"""

    proposal_id: str
    incident_id: str
    status: str
    assignments: list[ResourceAssignment]
    unmet_requirements: list[str]
```

### 第 3 步：创建 Agent 并查询资源

继续添加：

```python
class ResourceDispatchAgent:
    """第三个专业 Agent；只有只读 Tool 权限。"""

    def __init__(
        self,
        tools: MockApiToolClient,
    ) -> None:
        self.tools = tools

    async def ainvoke(
        self,
        request: DispatchRequest,
    ) -> DispatchProposal:
        """查询资源和路线，无法满足时明确列出缺口。"""

        result = await (
            self.tools.query_nearby_resources(
                request.section_id
            )
        )

        available = (
            list(
                (result.data or {}).get(
                    "items",
                    [],
                )
            )
            if result.success
            else []
        )

        assignments: list[
            ResourceAssignment
        ] = []
        unmet: list[str] = []
```

工具失败时 available 为空，所有需求都会进入 unmet，而不是编造资源。

### 第 4 步：按类型选择可用候选

继续添加循环：

```python
        for resource_type in (
            request.required_types
        ):
            candidate = next(
                (
                    item
                    for item in available
                    if (
                        item["resource_type"]
                        == resource_type
                        and item["available"]
                    )
                ),
                None,
            )

            if candidate is None:
                unmet.append(resource_type)
                continue
```

当前 fixture 每类型只有一个资源；后续生产系统可升级为按距离、能力和状态综合排序。

### 第 5 步：估算路线并创建 Assignment

继续：

```python
            route = await (
                self.tools.estimate_route(
                    origin=candidate["id"],
                    destination=request.section_id,
                    distance_km=float(
                        candidate["distance_km"]
                    ),
                )
            )

            if not route.success:
                unmet.append(resource_type)
                continue

            route_data = route.data or {}
            assignments.append(
                ResourceAssignment(
                    resource_id=candidate["id"],
                    name=candidate["name"],
                    resource_type=resource_type,
                    distance_km=float(
                        candidate["distance_km"]
                    ),
                    eta_minutes=math.ceil(
                        float(
                            route_data[
                                "eta_minutes"
                            ]
                        )
                    ),
                )
            )
```

路线 Tool 失败等价于当前无法形成可靠 Assignment，因此进入 unmet。

### 第 6 步：按 ETA 排序

循环后：

```python
        assignments.sort(
            key=lambda item: item.eta_minutes
        )
```

最早到达的建议排在前面。

### 运行与预期输出

Day 4 完成返回逻辑后运行完整 Agent。今天先语法检查：

```bash
PYTHONPATH=backend/src .venv/bin/python -m py_compile backend/src/highway_agent/agents/resource_dispatch.py
```

预期无输出。

可以先确认模型拒绝空需求：

```bash
PYTHONPATH=backend/src .venv/bin/python -c "from highway_agent.agents.resource_dispatch import DispatchRequest; DispatchRequest(incident_id='INC',section_id='QINLING-01',required_types=[])"
```

预期抛出 Pydantic ValidationError。

### 对应测试

今天创建 `backend/tests/test_resource_agent.py` 的构造器：

```python
import httpx
import pytest

from highway_agent.agents.resource_dispatch import (
    DispatchRequest,
    ResourceDispatchAgent,
)
from highway_agent.api import create_app
from highway_agent.tools import MockApiToolClient


def build_agent() -> ResourceDispatchAgent:
    app = create_app()
    tools = MockApiToolClient(
        transport=httpx.ASGITransport(app=app)
    )
    return ResourceDispatchAgent(tools)
```

Day 4 添加三条行为测试。

### 常见错误

错误 1：选择 unavailable 资源

候选条件必须同时匹配类型和 `available=True`。

错误 2：ETA 使用 int 截断

使用 `math.ceil`，5.2 变 6，而不是 5。

错误 3：排序使用 distance 而非 ETA

当前二者等价，但业务含义应按 `eta_minutes` 排序。

错误 4：资源 API 失败仍生成 assignment

失败时 available 为空，明确 unmet。

错误 5：Agent 内出现真实派车函数

本 Agent 只返回 DispatchProposal。

### 当天小练习

在纸上推演 ambulance + tow_truck：

- 哪个 Tool 先调用？
- 一共调用几次路线 Tool？
- 最终 assignments 顺序？
- ETA 各是多少？

再等 Day 4 测试验证。

### 今日总结与明日预告

资源选择与 ETA 计算主体已完成。

明天补齐 ready/partial、稳定 proposal_id，并写三条核心测试。

## 7. Day 4：实现资源缺口、稳定 Proposal ID 与幂等测试

### 今天目标

1. 无资源时写入 unmet_requirements。
2. 全满足时 status=ready。
3. 部分/完全不满足时 status=partial。
4. 使用 UUID5。
5. required_types 排序后构造稳定键。
6. 相同输入得到相同 Proposal。
7. 不虚构 helicopter。
8. 写三条核心测试。

### 上一节衔接

Day 3 已能查询和构造 assignments，但还没有返回 Proposal。

今天完成结果状态和幂等标识。

### 先说结论

状态规则：

```text
unmet 为空
  -> ready

unmet 非空
  -> partial
```

即使一个 assignment 都没有，仍返回 partial 和明确缺口，而不是异常或虚构资源。

### 第 1 步：构造稳定业务键

在循环和排序后添加：

```python
        stable_key = (
            f"{request.incident_id}:"
            f"{','.join(sorted(request.required_types))}"
        )
```

对 required_types 排序，保证：

```text
["ambulance", "tow_truck"]
["tow_truck", "ambulance"]
```

产生相同 stable_key。

### 第 2 步：生成 UUID5 并返回

完成方法：

```python
        return DispatchProposal(
            proposal_id=str(
                uuid5(
                    NAMESPACE_URL,
                    stable_key,
                )
            ),
            incident_id=request.incident_id,
            status=(
                "ready"
                if not unmet
                else "partial"
            ),
            assignments=assignments,
            unmet_requirements=unmet,
        )
```

UUID5 是基于命名空间和文本的确定性 UUID；不要用 uuid4 生成 proposal_id。

### 第 3 步：测试资源全部满足

在 `test_resource_agent.py` 添加：

```python
@pytest.mark.asyncio
async def test_dispatch_agent_selects_available_resources_with_eta() -> None:
    agent = build_agent()

    proposal = await agent.ainvoke(
        DispatchRequest(
            incident_id="INC-DISPATCH-001",
            section_id="QINLING-01",
            required_types=[
                "ambulance",
                "tow_truck",
            ],
        )
    )

    assert proposal.status == "ready"
    assert [
        item.resource_type
        for item in proposal.assignments
    ] == [
        "tow_truck",
        "ambulance",
    ]
    assert all(
        item.eta_minutes > 0
        for item in proposal.assignments
    )
    assert proposal.unmet_requirements == []
```

### 第 4 步：测试资源缺口

继续添加：

```python
@pytest.mark.asyncio
async def test_dispatch_agent_reports_missing_resource_instead_of_inventing_one() -> None:
    agent = build_agent()

    proposal = await agent.ainvoke(
        DispatchRequest(
            incident_id="INC-DISPATCH-002",
            section_id="QINLING-01",
            required_types=[
                "helicopter"
            ],
        )
    )

    assert proposal.assignments == []
    assert proposal.unmet_requirements == [
        "helicopter"
    ]
    assert proposal.status == "partial"
```

### 第 5 步：测试幂等

继续添加：

```python
@pytest.mark.asyncio
async def test_same_incident_request_is_idempotent() -> None:
    agent = build_agent()
    request = DispatchRequest(
        incident_id="INC-DISPATCH-003",
        section_id="QINLING-01",
        required_types=["ambulance"],
    )

    first = await agent.ainvoke(request)
    second = await agent.ainvoke(request)

    assert (
        first.proposal_id
        == second.proposal_id
    )
    assert first == second
```

由于 fixture、路线和 UUID 都确定，完整 Proposal 相同。

### 第 6 步：运行 Agent 测试

执行：

```bash
.venv/bin/python -m pytest backend/tests/test_resource_agent.py -q
```

### 运行与预期输出

预期：

```text
...                                                                      [100%]
3 passed
```

ready Proposal：

```json
{
  "status": "ready",
  "assignments": [
    {
      "resource_type": "tow_truck",
      "distance_km": 5.2,
      "eta_minutes": 6
    },
    {
      "resource_type": "ambulance",
      "distance_km": 8.5,
      "eta_minutes": 9
    }
  ],
  "unmet_requirements": []
}
```

partial Proposal：

```json
{
  "status": "partial",
  "assignments": [],
  "unmet_requirements": [
    "helicopter"
  ]
}
```

### 对应测试

本周核心评测就是：

```bash
.venv/bin/python -m pytest backend/tests/test_resource_agent.py -q
```

覆盖正确选择、缺口和幂等。

### 常见错误

错误 1：proposal_id 每次不同

检查是否误用 uuid4；必须使用 uuid5。

错误 2：required_types 顺序改变 ID

构造 stable_key 前排序。

错误 3：没有 helicopter 时仍生成对象

不能补“默认直升机”，必须进入 unmet。

错误 4：partial 被写成 failed

资源不足不代表系统异常；仍可返回已有建议和缺口。

错误 5：同 incident 不同需求 ID 相同

stable_key 同时包含排序后的 required_types。

### 当天小练习

用同一个 incident_id，分别请求：

```text
["ambulance", "tow_truck"]
["tow_truck", "ambulance"]
```

确认 proposal_id 相同。再请求只包含 ambulance，确认 proposal_id 不同。

### 今日总结与明日预告

调度 Proposal 现在具备资源缺口和稳定标识。

明天接入独立 Agent API，完成本周评测和验收。

## 8. Day 5：接入资源 Agent API 并完成独立验收

### 今天目标

1. 在 API 导入调度模型和 Agent。
2. 增加独立 invoke 路由。
3. 使用 ASGITransport 装配 Tool。
4. 手动调用 ready。
5. 手动调用 partial。
6. 运行 Agent 评测。
7. 回归审批边界。
8. 明确暂不接主图。

### 上一节衔接

Day 4 的 Agent 已通过独立 Python 测试。

今天增加 HTTP 入口，但不修改第 4/5 周工作流拓扑。

### 先说结论

新增 API：

```text
POST /api/agents/resource-dispatch/invoke
```

工作流 API保持不变。第 6 周只证明第三个 Agent 自己可靠。

### 第 1 步：导入资源 Agent

在 `api.py` 增加：

```python
from highway_agent.agents.resource_dispatch import (
    DispatchProposal,
    DispatchRequest,
    ResourceDispatchAgent,
)
```

### 第 2 步：增加独立路由

在 incident Agent 路由后添加：

```python
    @app.post(
        "/api/agents/resource-dispatch/invoke",
        response_model=DispatchProposal,
    )
    async def invoke_resource_dispatch(
        request: DispatchRequest,
    ) -> DispatchProposal:
        """生成模拟调度建议；接口不会产生真实副作用。"""

        tools = MockApiToolClient(
            transport=httpx.ASGITransport(
                app=app
            )
        )
        agent = ResourceDispatchAgent(tools)

        return await agent.ainvoke(request)
```

### 第 3 步：调用 ready 场景

启动：

```bash
make run
```

调用：

```bash
curl -X POST http://127.0.0.1:8000/api/agents/resource-dispatch/invoke -H "Content-Type: application/json" -d '{"incident_id":"INC-DISPATCH-DEMO","section_id":"QINLING-01","required_types":["ambulance","tow_truck"]}'
```

### 第 4 步：调用 partial 场景

```bash
curl -X POST http://127.0.0.1:8000/api/agents/resource-dispatch/invoke -H "Content-Type: application/json" -d '{"incident_id":"INC-DISPATCH-MISSING","section_id":"QINLING-01","required_types":["helicopter"]}'
```

### 第 5 步：检查无副作用

结果中只有 Proposal。

确认代码没有：

- 更新 RESOURCE_FIXTURES。
- 写数据库。
- 调用真实通知。
- 添加 executed_actions。
- 绕过 ApprovalEmergencyWorkflow。

### 第 6 步：运行统一验收

执行：

```bash
make test
make eval
make verify
```

本周 `make eval` 只选择 `resource_agent` 测试。

### 运行与预期输出

完整测试：

```text
.................................................                        [100%]
49 passed
```

ready 响应 assignments 顺序：

```text
tow_truck -> ambulance
```

partial 响应：

```json
{
  "status": "partial",
  "assignments": [],
  "unmet_requirements": [
    "helicopter"
  ]
}
```

### 对应测试

最终执行：

```bash
.venv/bin/python -m pytest backend/tests/test_resource_agent.py -q
.venv/bin/python -m pytest backend/tests/test_approval_workflow.py -q
make test
make eval
make verify
```

审批回归确保新增 Agent 没破坏安全边界。

### 常见错误

错误 1：API 返回 422

required_types 不能为空；distance 不由用户传入，而来自资源数据。

错误 2：assignments 顺序与输入相同

结果按 ETA 排序，不按 required_types 顺序。

错误 3：helicopter 返回 500

资源不足是 partial 业务状态。

错误 4：proposal_id 是随机值

检查 uuid5 和 stable_key。

错误 5：把 Agent 接到审批前自动执行

本周不接主图，更不执行真实调度。

### 当天小练习

为资源 Agent 增加 API TestClient 测试：

- HTTP 200。
- status=ready。
- 两条 assignment。
- 第一条 tow_truck。
- unmet_requirements 为空。

### 今日总结与明日预告

第三个专业 Agent 已独立完成。

第 7 周不会新增 Agent，而是把成熟的 REST Tool 能力暴露成 MCP 工具服务。

## 9. 本周唯一实战作业

任务：增加 `fire_engine` 消防车资源，并验证 ready/partial 和 ETA 排序。

要求：

1. 新资源 ID：`RES-FIRE-001`。
2. resource_type：`fire_engine`。
3. section_id：`QINLING-01`。
4. distance_km：6.4。
5. available：true。
6. 请求 tow_truck + fire_engine + ambulance。
7. 排序应是 tow_truck(6)、fire_engine(7)、ambulance(9)。
8. 同样请求 proposal_id 稳定。
9. 未知类型仍进入 unmet。
10. 三个统一命令通过。

先写测试，再添加 fixture。不要修改 Agent 为特判 fire_engine，通用类型匹配应该自动工作。

## 10. 测试、常见错误与系统排查

诊断顺序：

```text
Proposal 不正确
  -> 看 query_nearby_resources ToolResult
  -> 看 available 列表
  -> 看 candidate 是否匹配 type/available
  -> 看 estimate_route ToolResult
  -> 看 eta ceil
  -> 看排序
  -> 看 unmet
  -> 看 stable_key
```

调试命令：

```bash
.venv/bin/python -m pytest backend/tests/test_resource_agent.py -vv
.venv/bin/python -m pytest backend/tests/test_tools.py -q
.venv/bin/python -m pytest backend/tests/test_mock_api.py -q
make test
```

症状表：

| 症状 | 可能原因 |
|---|---|
| assignments 为空 | 路段不匹配或 Tool 失败 |
| 少一种资源 | type 拼写或 unavailable |
| ETA 为 5 而非 6 | 使用 int 而非 ceil |
| 顺序错误 | 未按 eta_minutes sort |
| ID 每次变化 | 使用 uuid4 |
| 输入换序 ID 变化 | stable_key 未排序 |
| 缺资源时报错 | 未使用 partial |
| 资源状态被修改 | 违反只读边界 |

不要在本周加入：

- 真实地图 API。
- 真实救援站数据。
- 资源数据库写入。
- 自动派车。
- Supervisor。
- MCP。

MCP 放到下一周，资源 Agent 先完成独立验证。

## 11. 通关清单与三道面试题

- [ ] 能定义路线输入输出模型。
- [ ] 能解释 60 km/h 教学 ETA。
- [ ] 能创建无副作用路线 API。
- [ ] 能实现资源查询 Tool。
- [ ] 能实现 POST 路线 Tool。
- [ ] 能按类型和 available 选择资源。
- [ ] 能对 ETA 使用 math.ceil。
- [ ] 能按 ETA 排序。
- [ ] 能报告 unmet_requirements。
- [ ] 能用 UUID5 生成稳定 ID。
- [ ] 能说明为什么暂不接主工作流。
- [ ] 能让 `make test`、`make eval`、`make verify` 通过。

### 面试题 1

为什么资源不足时返回 partial，而不是让模型补一个资源？

回答要点：

资源属于外部事实，不能由模型生成。partial 可以同时返回已找到的 assignments 和明确 unmet_requirements，让人工或后续系统处理缺口；虚构资源会造成严重调度风险。

### 面试题 2

为什么 proposal_id 使用 UUID5 而不是 UUID4？

回答要点：

UUID5 基于稳定业务键生成，相同 incident_id 和需求集合得到相同 ID，便于幂等重试和审计。UUID4 每次随机，无法识别重复 Proposal。

### 面试题 3

资源调度 Agent 为什么只生成 Proposal，不直接派车？

回答要点：

派车是高风险外部写操作，需要权限、幂等、审批和审计。当前 Agent 只使用只读资源查询与无副作用路线估算，先保证建议正确；真实执行必须放在 HITL 之后的受控 Tool 中。

## 12. 本周总结与下一周衔接

本周完成第三个独立 Agent：

```text
资源事实
  -> 两个 Tool
  -> ETA
  -> 排序
  -> 缺口
  -> 幂等 Proposal
  -> 独立 API
```

进入第 7 周前执行：

```bash
make test
make eval
make verify
```

第 7 周不新增 Agent，而是学习 MCP：

- 为 road、weather、resources 创建 MCP Server。
- 定义工具名称、描述和参数 Schema。
- 使用 JSON-RPC/stdio 风格测试。
- 保持原 REST Tool 作为底层能力。
- 比较普通 Tool 与 MCP Tool。
- 让成熟工具可被标准客户端发现和调用。

学习曲线保持：先有可靠工具，再升级协议。
