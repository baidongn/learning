# 第 4 周：双 Agent LangGraph 工作流

> 学习方式：5 天，每天 2～3 小时。继承第 3 周的预案专家、事件研判 Agent 和三个只读 Tool。
>
> 本周终点：使用 LangGraph 创建固定双 Agent 工作流；信息完整时“事件研判 → 预案检索”，信息缺失时强制停止，不让模型猜测。

## 1. 本周学习地图与最终成果

前三周的 Agent 都是独立运行：

```text
预案专家 Agent
事件研判 Agent
```

本周第一次把它们编排成图：

```text
START
  |
  v
analyze_incident
  |
  +-- missing_fields 非空 --> needs_input --> END
  |
  +-- missing_fields 为空 --> retrieve_plan --> END
```

这仍然不是 Supervisor。节点顺序和分支规则由程序固定，模型不能自行改变流程。

五天安排：

| Day | 核心内容 | 当天成果 |
|---|---|---|
| Day 1 | LangGraph、State、依赖锁定 | 定义可序列化 IncidentWorkflowState |
| Day 2 | Agent 节点 | 封装 analyze_incident 和 retrieve_plan |
| Day 3 | 条件边与停止节点 | 信息缺失时不调用预案专家 |
| Day 4 | 编译、调用与图测试 | 两条路径节点顺序可断言 |
| Day 5 | 工作流 API 与验收 | 通过 HTTP 运行双 Agent 图 |

本周必做：

- 使用真实 `StateGraph`，不是手写 if/else 伪装成图。
- State 只保存可序列化字典。
- 每个专业 Agent 仍可独立测试。
- 缺失信息时 `plan is None`。
- 事件列表能反映实际节点顺序。
- 通过 `make test`、`make eval`、`make verify`。

本周选做：

- 打印 Mermaid 图。
- 为更多缺失字段组合增加测试。
- 在终端美化 events 输出。

## 2. 前置知识、环境准备和本周起点

先验收第 3 周：

```bash
cd weeks/week-03
make test
make eval
make verify
```

进入第 4 周：

```bash
cd ../week-04
cp .env.example .env
make setup
```

从本周开始，Makefile 改用课程目录内的标准 Python venv 和锁定依赖文件：

```make
PYTHON ?= python3
VENV ?= .venv
COMPOSE ?= docker compose

setup:
	$(PYTHON) -m venv $(VENV)
	$(VENV)/bin/python -m pip install -r backend/requirements.lock.txt
```

这么做的原因：

- 每周目录可独立安装。
- CI 和本机使用同一份直接依赖版本。
- 避免学习者没有全局 uv 时无法继续。
- LangGraph 等核心包版本明确，不使用浮动最新版。

新增依赖 `backend/requirements.lock.txt` 包含：

```text
langgraph==1.2.9
```

本周新增目录：

```text
backend/src/highway_agent/workflows/
├── __init__.py
└── incident_response.py

backend/tests/
└── test_workflow.py
```

默认仍为 Mock 模式；工作流会装配 Mock 预案专家，不需要 DeepSeek Key。

## 3. 本周架构、目录变化与完整调用链

LangGraph 的三个基本概念：

| 概念 | 本周对应 |
|---|---|
| State | `IncidentWorkflowState` |
| Node | analyze_incident、needs_input、retrieve_plan |
| Edge | START、普通边、条件边、END |

State 流转示例：

```text
输入：
{
  request: {...},
  events: []
}

研判后：
{
  request: {...},
  assessment: {...},
  status: "analyzed",
  events: ["incident_analyzed"]
}

预案后：
{
  request: {...},
  assessment: {...},
  plan: {...},
  status: "plan_ready",
  events: ["incident_analyzed", "plan_retrieved"]
}
```

为什么 State 使用字典而不是直接保存 Pydantic 对象？

- 后续 Checkpointer 要序列化状态。
- HTTP 返回需要 JSON。
- TypedDict 能给开发期类型提示。
- 每个节点边界显式调用 `model_validate` 和 `model_dump(mode="json")`。

图只负责：

- 顺序。
- 条件。
- 状态合并。
- 停止。

图不负责：

- 事件风险判断。
- RAG 检索。
- Tool HTTP。
- DeepSeek 请求。

这些仍由已经独立测试过的组件负责。

## 4. Day 1：安装 LangGraph 并定义工作流 State

### 今天目标

1. 理解 StateGraph 的职责。
2. 锁定 LangGraph 版本。
3. 创建 workflows 包。
4. 用 TypedDict 定义状态。
5. 区分输入、过程状态和输出。
6. 保证 State 可 JSON 序列化。

### 上一节衔接

第 3 周已经有两个独立 Agent，但 API 调用者需要自己决定先调用谁、何时停止。

今天先定义一个统一状态，让多个节点围绕同一份事件上下文工作。

### 先说结论

工作流 State 不是“全局随便放东西的字典”。

本周只允许：

```text
request
assessment
plan
status
events
```

字段越少，节点契约越容易理解和测试。

### 第 1 步：锁定依赖

创建 `backend/requirements.lock.txt`。其中核心运行依赖为：

```text
alembic==1.18.5
asyncpg==0.31.0
fastapi==0.139.0
httpx==0.28.1
langgraph==1.2.9
pgvector==0.5.0
pydantic-settings==2.14.2
SQLAlchemy==2.0.51
uvicorn==0.51.0
```

开发依赖：

```text
pytest==8.4.2
pytest-asyncio==1.4.0
pytest-cov==7.1.0
PyYAML==6.0.3
```

安装：

```bash
make setup
.venv/bin/python -c "import langgraph; print('langgraph import ok')"
```

### 第 2 步：更新 Makefile

本周 `Makefile` 完整命令入口：

```make
PYTHON ?= python3
VENV ?= .venv
COMPOSE ?= docker compose

.PHONY: setup infra-up infra-down migrate run test eval verify reset

setup:
	$(PYTHON) -m venv $(VENV)
	$(VENV)/bin/python -m pip install -r backend/requirements.lock.txt

infra-up:
	$(COMPOSE) -f compose.dev.yaml up -d

infra-down:
	$(COMPOSE) -f compose.dev.yaml down

migrate:
	cd backend && ../$(VENV)/bin/alembic upgrade head

run:
	$(VENV)/bin/uvicorn highway_agent.main:app --app-dir backend/src --reload

test:
	$(VENV)/bin/python -m pytest backend/tests -q

eval:
	$(VENV)/bin/python -m pytest backend/tests -q -k "workflow"

verify: test
	$(COMPOSE) -f compose.dev.yaml config --quiet

reset:
	$(COMPOSE) -f compose.dev.yaml down -v
```

从今天起课程命令优先用 `.venv/bin/python`，避免不同环境混用。

### 第 3 步：创建 workflows 包

新建空文件：

```text
backend/src/highway_agent/workflows/__init__.py
```

新建 `backend/src/highway_agent/workflows/incident_response.py`，先写导入：

```python
"""Week 4 的固定双 Agent 工作流。

图只负责编排和分支；专业判断仍由边界清晰的 Agent 完成。
"""

from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from highway_agent.agents.incident_analysis import (
    IncidentAnalysisAgent,
    IncidentAnalysisRequest,
)
from highway_agent.agents.plan_expert import (
    DeepSeekPlanExpertAgent,
    PlanExpertAgent,
    PlanQuery,
)
from highway_agent.tools import MockApiToolClient
```

### 第 4 步：定义 State

继续添加：

```python
class IncidentWorkflowState(
    TypedDict,
    total=False,
):
    """工作流跨节点传递的可序列化状态。"""

    request: dict[str, Any]
    assessment: dict[str, Any]
    plan: dict[str, Any] | None
    status: str
    events: list[str]
```

`total=False` 表示中间状态不要求同时拥有全部字段。例如进入图时还没有 assessment 和 plan。

### 第 5 步：理解各字段生命周期

字段表：

| 字段 | 写入节点 | 读取节点 |
|---|---|---|
| request | 图入口 | analyze、retrieve |
| assessment | analyze_incident | route、后续节点 |
| plan | retrieve_plan | API/调用方 |
| status | 每个业务节点 | API/测试 |
| events | 每个节点追加 | API/测试/审计 |

`events` 不是完整日志，只是本周用于理解节点顺序的轻量事件列表。

### 第 6 步：验证 State 可序列化

临时运行：

```bash
PYTHONPATH=backend/src .venv/bin/python -c "import json; from highway_agent.workflows.incident_response import IncidentWorkflowState; state=IncidentWorkflowState(request={'raw_text':'追尾'},events=[]); print(json.dumps(state,ensure_ascii=False))"
```

### 运行与预期输出

预期：

```json
{"request": {"raw_text": "追尾"}, "events": []}
```

导入测试：

```bash
PYTHONPATH=backend/src .venv/bin/python -c "from highway_agent.workflows.incident_response import IncidentWorkflowState; print(IncidentWorkflowState.__name__)"
```

输出：

```text
IncidentWorkflowState
```

### 对应测试

今天先运行已有组件回归：

```bash
.venv/bin/python -m pytest backend/tests/test_incident_agent.py backend/tests/test_plan_agent.py -q
```

State 还没有图行为，Day 4 再写完整工作流测试。

### 常见错误

错误 1：无法导入 langgraph

确认执行了 `make setup`，并使用 `.venv/bin/python`。

错误 2：把 Agent 实例放进 State

Agent、HTTP Client 等运行对象不可序列化，应放在 `EmergencyWorkflow` 实例属性中。

错误 3：State 保存 datetime 对象

Agent 输出使用 `model_dump(mode="json")`，把时间转成 JSON 字符串。

错误 4：把所有字段设为必需

中间节点不一定已经产生 plan，所以使用 `total=False`。

错误 5：用 State 做业务模型

State 是流程载体，具体业务仍使用 Pydantic 模型校验。

### 当天小练习

给一个完整请求构造初始 State，并用 `json.dumps(..., ensure_ascii=False)` 打印。

要求初始 State 只有 request 和 events，不要提前填充虚假的 assessment 或 plan。

### 今日总结与明日预告

今天完成了依赖、目录和状态契约。

明天实现两个 Agent 节点：事件研判节点与预案检索节点，并在边界完成 Pydantic/JSON 转换。

## 5. Day 2：把两个独立 Agent 封装成图节点

### 今天目标

1. 创建 EmergencyWorkflow 构造函数。
2. 注入 Tool 和预案 Agent。
3. 实现 analyze_incident 节点。
4. 实现 retrieve_plan 节点。
5. 兼容 Mock 和 DeepSeek 预案专家。
6. 追加节点事件。
7. 不在节点内复制 Agent 业务逻辑。

### 上一节衔接

Day 1 定义了 State，但图还没有节点。

今天只实现节点方法，先不完成分支和编译。

### 先说结论

节点是“适配器”：

```text
State 字典
  -> Pydantic 输入
  -> 调用已测试 Agent
  -> Pydantic 输出
  -> JSON State 更新
```

节点不重新判断风险，也不重新写 RAG。

### 第 1 步：创建工作流类和依赖

在 State 后添加：

```python
class EmergencyWorkflow:
    """串联事件研判和预案专家，不包含自主路由。"""

    def __init__(
        self,
        tools: MockApiToolClient,
        plan_agent: (
            PlanExpertAgent
            | DeepSeekPlanExpertAgent
        ),
    ) -> None:
        self.incident_agent = IncidentAnalysisAgent(
            tools
        )
        self.plan_agent = plan_agent
```

依赖由外部注入：

- Tool Client 可以用 ASGITransport。
- Plan Agent 可以是 Mock 或 Live。
- 工作流本身不读取环境变量。

### 第 2 步：实现事件研判节点

在类内添加：

```python
    async def _analyze_incident(
        self,
        state: IncidentWorkflowState,
    ) -> IncidentWorkflowState:
        """运行第二个 Agent，并把 Pydantic 结果转换为可持久化字典。"""

        request = (
            IncidentAnalysisRequest.model_validate(
                state["request"]
            )
        )
        assessment = await self.incident_agent.ainvoke(
            request
        )

        return {
            "assessment": assessment.model_dump(
                mode="json"
            ),
            "status": "analyzed",
            "events": ["incident_analyzed"],
        }
```

返回的是“状态更新”，LangGraph 会与已有 request 合并。

### 第 3 步：准备预案查询

预案专家只需要事件摘要：

```python
        request_text = str(
            state["request"]["raw_text"]
        )
        query = PlanQuery(
            event_summary=request_text
        )
```

不要把整个 state 序列化后塞给预案专家；最小输入更容易控制和评测。

### 第 4 步：兼容同步和异步 Agent

继续实现完整 `_retrieve_plan`：

```python
    async def _retrieve_plan(
        self,
        state: IncidentWorkflowState,
    ) -> IncidentWorkflowState:
        """信息完整后才调用预案专家。"""

        request_text = str(
            state["request"]["raw_text"]
        )
        query = PlanQuery(
            event_summary=request_text
        )

        if isinstance(
            self.plan_agent,
            DeepSeekPlanExpertAgent,
        ):
            plan = await self.plan_agent.ainvoke(
                query
            )
        else:
            plan = self.plan_agent.invoke(
                query
            )

        return {
            "plan": plan.model_dump(mode="json"),
            "status": (
                "plan_ready"
                if plan.status == "ready"
                else plan.status
            ),
            "events": [
                *state.get("events", []),
                "plan_retrieved",
            ],
        }
```

### 第 5 步：解释状态更新

`_analyze_incident` 返回：

```python
{
    "assessment": ...,
    "status": "analyzed",
    "events": ["incident_analyzed"],
}
```

`_retrieve_plan` 返回：

```python
{
    "plan": ...,
    "status": "plan_ready",
    "events": [
        "incident_analyzed",
        "plan_retrieved",
    ],
}
```

第二个节点必须从 state 读取已有 events 再追加。

### 第 6 步：不要直接调用私有节点做最终功能

私有节点是图的内部实现。今天可以通过小型临时测试观察，但正式调用必须等图编译后使用 `ainvoke`。

静态检查：

```bash
PYTHONPATH=backend/src .venv/bin/python -m py_compile backend/src/highway_agent/workflows/incident_response.py
```

### 运行与预期输出

语法检查成功时无输出，退出码为 0。

回归 Agent：

```bash
.venv/bin/python -m pytest backend/tests/test_incident_agent.py backend/tests/test_plan_agent.py -q
```

预期两个 Agent 仍全部通过，说明节点代码没有修改其内部行为。

### 对应测试

今天重点是回归：

```bash
.venv/bin/python -m pytest backend/tests/test_incident_agent.py backend/tests/test_plan_agent.py -q
```

Day 4 会通过图的公开入口断言节点结果。

### 常见错误

错误 1：返回完整 State 丢失 request

节点只返回更新即可，LangGraph 负责合并。不要手动复制所有字段。

错误 2：Pydantic 对象无法持久化

使用：

```python
model_dump(mode="json")
```

错误 3：Mock Agent 被 await

Mock 的 `invoke` 是同步函数；Live 的 `ainvoke` 才需要 await。

错误 4：节点内直接创建 DeepSeek 客户端

模型选择应在 API 装配层完成，工作流只接收 Agent。

错误 5：复制风险判断代码

风险属于 `IncidentAnalysisAgent`，节点只调用它。

### 当天小练习

在纸上写出两个节点各自读取和写入的 State 字段：

- analyze_incident 读什么、写什么？
- retrieve_plan 读什么、写什么？

然后对照代码检查，不新增无用状态字段。

### 今日总结与明日预告

两个专业 Agent 已被封装成节点适配器。

明天实现条件路由和 needs_input 停止节点，建立“缺信息就不继续”的流程边界。

## 6. Day 3：添加条件边和 needs_input 停止节点

### 今天目标

1. 从 assessment 读取 missing_fields。
2. 返回稳定路由名称。
3. 创建 needs_input 节点。
4. 缺信息时直接 END。
5. 完整信息时进入 retrieve_plan。
6. 保证未调用的 plan 不存在。
7. 理解业务条件与模型自主路由差别。

### 上一节衔接

Day 2 已经有 analyze 和 retrieve 两个节点，但尚未决定它们如何连接。

今天用一个纯函数路由，明确控制流程。

### 先说结论

路由规则只有一条：

```text
missing_fields 非空
  -> needs_input

missing_fields 为空
  -> retrieve_plan
```

这个判断由结构化字段完成，不让 LLM 选择。

### 第 1 步：实现路由函数

在 `EmergencyWorkflow` 内添加：

```python
    @staticmethod
    def _route_after_analysis(
        state: IncidentWorkflowState,
    ) -> str:
        """信息不完整时强制停止，避免带着猜测继续生成方案。"""

        missing_fields = (
            state["assessment"]["missing_fields"]
        )

        return (
            "needs_input"
            if missing_fields
            else "retrieve_plan"
        )
```

返回值必须与条件边映射键一致。

### 第 2 步：实现停止节点

继续添加：

```python
    @staticmethod
    def _needs_input(
        state: IncidentWorkflowState,
    ) -> IncidentWorkflowState:
        return {
            "status": "needs_input",
            "events": [
                *state.get("events", []),
                "needs_input",
            ],
        }
```

它不创建 plan，不调用外部服务，只更新状态和事件。

### 第 3 步：理解为什么不是异常

信息缺失是正常业务结果，不是系统异常。

因此返回：

```json
{
  "status": "needs_input",
  "assessment": {
    "missing_fields": [
      "casualties",
      "lane_occupancy"
    ]
  }
}
```

而不是 HTTP 500。

### 第 4 步：理解 plan 的缺失语义

由于 `IncidentWorkflowState(total=False)`，停止分支可以完全没有 `plan` 键。

调用方使用：

```python
result.get("plan") is None
```

不要填一个伪造的空建议。

### 第 5 步：设计两条测试输入

完整输入：

```text
秦岭隧道追尾并出现烟雾，占用两条车道，无人伤亡
```

缺失输入：

```text
高速发生追尾
```

第二条缺少：

```text
casualties
lane_occupancy
```

### 第 6 步：检查路由是纯逻辑

路由函数不应该：

- 调用 Tool。
- 调用模型。
- 修改数据库。
- 创建 Agent。
- 追加随机结果。

它只读取已有 assessment 并返回节点名。

### 运行与预期输出

今天先执行语法检查：

```bash
PYTHONPATH=backend/src .venv/bin/python -m py_compile backend/src/highway_agent/workflows/incident_response.py
```

预期无输出、退出码 0。

完整流程将在 Day 4 编译后运行。

### 对应测试

可以先检查 Agent 对两条输入生成的 missing_fields：

```bash
.venv/bin/python -m pytest backend/tests/test_incident_agent.py -q
```

确认 Agent 层的缺失字段测试全绿。

### 常见错误

错误 1：路由键与节点名不一致

返回值只能是 `needs_input` 或 `retrieve_plan`。

错误 2：判断 raw_text 而不是 assessment

缺失识别已由 Agent 完成，图应读取结构化结果。

错误 3：needs_input 仍调用预案专家

停止节点必须直接连接 END。

错误 4：把 needs_input 当异常

这是可预期业务状态，应返回 200 和结构化结果。

错误 5：events 覆盖已有值

使用列表解包追加，不要只返回 `["needs_input"]`。

### 当天小练习

构造两个假的 State，直接调用静态路由函数：

```python
complete_state = {
    "assessment": {
        "missing_fields": []
    }
}

incomplete_state = {
    "assessment": {
        "missing_fields": ["casualties"]
    }
}
```

确认分别返回 `retrieve_plan` 和 `needs_input`。

### 今日总结与明日预告

条件路由已经明确。

明天把节点和边注册到 StateGraph、编译公开入口，并用自动测试证明两个分支的节点顺序。

## 7. Day 4：构建、编译并测试完整 StateGraph

### 今天目标

1. 创建 `StateGraph(IncidentWorkflowState)`。
2. 注册三个节点。
3. 添加 START 边。
4. 添加条件边映射。
5. 添加两个 END 边。
6. 编译图。
7. 暴露统一 ainvoke。
8. 测试完整和停止分支。

### 上一节衔接

Day 1～3 已经准备 State、节点和路由。

今天把它们真正连接为 LangGraph。

### 先说结论

图的构建只在 `EmergencyWorkflow.__init__` 完成一次：

```text
builder
  -> add_node
  -> add_edge
  -> add_conditional_edges
  -> compile
```

运行时统一调用编译后的 `self.graph`。

### 第 1 步：注册节点

在构造函数设置两个 Agent 后继续添加：

```python
        builder = StateGraph(
            IncidentWorkflowState
        )

        builder.add_node(
            "analyze_incident",
            self._analyze_incident,
        )
        builder.add_node(
            "needs_input",
            self._needs_input,
        )
        builder.add_node(
            "retrieve_plan",
            self._retrieve_plan,
        )
```

节点名会进入图结构和调试信息，应使用稳定 snake_case。

### 第 2 步：添加入口和条件边

继续添加：

```python
        builder.add_edge(
            START,
            "analyze_incident",
        )

        builder.add_conditional_edges(
            "analyze_incident",
            self._route_after_analysis,
            {
                "needs_input": "needs_input",
                "retrieve_plan": "retrieve_plan",
            },
        )
```

分析完成后只允许进入两个白名单节点。

### 第 3 步：添加结束边并编译

继续添加：

```python
        builder.add_edge(
            "needs_input",
            END,
        )
        builder.add_edge(
            "retrieve_plan",
            END,
        )

        self.graph = builder.compile()
```

第 4 周暂不传 Checkpointer；第 5 周再增加。

### 第 4 步：创建公开运行入口

在类末尾添加：

```python
    async def ainvoke(
        self,
        request: dict[str, Any],
    ) -> IncidentWorkflowState:
        """以统一入口运行图，调用方不直接接触 LangGraph 配置。"""

        initial_state: IncidentWorkflowState = {
            "request": request,
            "events": [],
        }

        return await self.graph.ainvoke(
            initial_state
        )
```

API 和测试只调用 `workflow.ainvoke`。

### 第 5 步：创建测试工厂

新建 `backend/tests/test_workflow.py`：

```python
import httpx
import pytest

from highway_agent.agents.plan_expert import (
    PlanExpertAgent,
)
from highway_agent.api import create_app
from highway_agent.rag import (
    InMemoryPlanRetriever,
    load_demo_documents,
)
from highway_agent.tools import MockApiToolClient
from highway_agent.workflows.incident_response import (
    EmergencyWorkflow,
)


def build_workflow() -> EmergencyWorkflow:
    app = create_app()
    tools = MockApiToolClient(
        transport=httpx.ASGITransport(app=app)
    )
    plan_agent = PlanExpertAgent(
        InMemoryPlanRetriever(
            load_demo_documents()
        )
    )

    return EmergencyWorkflow(
        tools=tools,
        plan_agent=plan_agent,
    )
```

### 第 6 步：测试正常分支

继续添加：

```python
@pytest.mark.asyncio
async def test_complete_event_reaches_plan_ready() -> None:
    workflow = build_workflow()

    result = await workflow.ainvoke(
        {
            "raw_text": (
                "秦岭隧道追尾并出现烟雾，"
                "占用两条车道，无人伤亡"
            ),
            "road_code": "G65",
            "section_id": "QINLING-01",
            "camera_id": "CAM-QINLING-01",
        }
    )

    assert result["status"] == "plan_ready"
    assert result["events"] == [
        "incident_analyzed",
        "plan_retrieved",
    ]
    assert result["plan"]["citations"]
```

### 第 7 步：测试停止分支

继续添加：

```python
@pytest.mark.asyncio
async def test_incomplete_event_stops_before_plan_agent() -> None:
    workflow = build_workflow()

    result = await workflow.ainvoke(
        {
            "raw_text": "高速发生追尾",
            "road_code": "G5",
            "section_id": "HANTAI-01",
        }
    )

    assert result["status"] == "needs_input"
    assert result["events"] == [
        "incident_analyzed",
        "needs_input",
    ]
    assert result.get("plan") is None
    assert result["assessment"]["missing_fields"] == [
        "casualties",
        "lane_occupancy",
    ]
```

### 运行与预期输出

执行：

```bash
.venv/bin/python -m pytest backend/tests/test_workflow.py -q -k "complete or incomplete"
```

预期：

```text
..                                                                       [100%]
2 passed
```

正常事件 events：

```json
["incident_analyzed", "plan_retrieved"]
```

缺失事件 events：

```json
["incident_analyzed", "needs_input"]
```

### 对应测试

今天的核心：

```bash
.venv/bin/python -m pytest backend/tests/test_workflow.py -q
```

API 测试将在 Day 5 添加后变为三条。

### 常见错误

错误 1：compile 前漏注册节点

边引用的所有节点都必须先 `add_node`。

错误 2：把字符串 END 当成节点

使用从 `langgraph.graph` 导入的 `END` 常量。

错误 3：events 顺序错误

检查 retrieve/needs_input 是否从 state 追加已有 events。

错误 4：停止分支仍有 plan

检查条件边映射和 needs_input 到 END 的边。

错误 5：直接调用 builder.ainvoke

需要先 `builder.compile()`，运行 compiled graph。

### 当天小练习

在测试中打印：

```python
print(result["events"])
print(result["status"])
```

分别运行两条测试，手工画出走过的节点。练习完成后可删除打印，保持测试输出整洁。

### 今日总结与明日预告

固定双 Agent 图已经可以独立运行和测试。

明天接入 API，演示完整和停止分支，并完成本周验收。

## 8. Day 5：接入工作流 API 并完成本周验收

### 今天目标

1. 在应用装配层选择 Mock/Live Plan Agent。
2. 创建工作流 HTTP 路由。
3. 使用现有 IncidentAnalysisRequest 校验输入。
4. 测试 API 正常分支。
5. 手动演示 needs_input。
6. 运行全量测试和工作流评测。
7. 验证 Compose。

### 上一节衔接

Day 4 已经通过 Python 入口运行 StateGraph。

今天把图接回 FastAPI，同时保留两个独立 Agent API。

### 先说结论

独立 Agent API 和工作流 API同时存在：

```text
/api/agents/incident-analysis/invoke
/api/agents/plan-expert/invoke
/api/workflows/incident-response/run
```

这样满足“每个 Agent 先独立测试，再接工作流”。

### 第 1 步：选择预案 Agent

在 `create_app` 已有 Mock/Live Agent 初始化后添加：

```python
    selected_plan_agent = (
        live_plan_agent
        or plan_agent
    )
```

工作流只接收最终选择，不自行读取 MODEL_MODE。

### 第 2 步：导入工作流

在 `api.py` 导入区添加：

```python
from highway_agent.workflows.incident_response import (
    EmergencyWorkflow,
)
```

### 第 3 步：增加工作流路由

在两个独立 Agent 路由之后添加：

```python
    @app.post(
        "/api/workflows/incident-response/run"
    )
    async def run_incident_response(
        request: IncidentAnalysisRequest,
    ) -> dict[str, object]:
        """运行固定双 Agent 图；Week 4 不允许模型自行改变节点顺序。"""

        tools = MockApiToolClient(
            transport=httpx.ASGITransport(app=app)
        )
        workflow = EmergencyWorkflow(
            tools=tools,
            plan_agent=selected_plan_agent,
        )

        return await workflow.ainvoke(
            request.model_dump(mode="json")
        )
```

### 第 4 步：增加 API 测试

在 `test_workflow.py` 添加：

```python
def test_workflow_api_runs_fixed_two_agent_graph() -> None:
    from fastapi.testclient import TestClient

    client = TestClient(create_app())
    response = client.post(
        "/api/workflows/incident-response/run",
        json={
            "raw_text": (
                "秦岭隧道追尾并出现烟雾，"
                "占用两条车道，无人伤亡"
            ),
            "road_code": "G65",
            "section_id": "QINLING-01",
            "camera_id": "CAM-QINLING-01",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "plan_ready"
```

### 第 5 步：手动演示两条路径

启动：

```bash
make run
```

正常路径：

```bash
curl -X POST http://127.0.0.1:8000/api/workflows/incident-response/run -H "Content-Type: application/json" -d '{"raw_text":"秦岭隧道追尾并出现烟雾，占用两条车道，无人伤亡","road_code":"G65","section_id":"QINLING-01","camera_id":"CAM-QINLING-01"}'
```

停止路径：

```bash
curl -X POST http://127.0.0.1:8000/api/workflows/incident-response/run -H "Content-Type: application/json" -d '{"raw_text":"高速发生追尾","road_code":"G5","section_id":"HANTAI-01"}'
```

### 第 6 步：运行统一验收

执行：

```bash
make test
make eval
make verify
```

本周 `make eval` 只选择 workflow 测试，验证两条关键分支。

### 运行与预期输出

完整后端测试：

```text
.....................................                                    [100%]
37 passed
```

正常响应关键字段：

```json
{
  "status": "plan_ready",
  "events": [
    "incident_analyzed",
    "plan_retrieved"
  ],
  "plan": {
    "status": "ready",
    "citations": [
      {
        "document_id": "PLAN-TUNNEL-001"
      }
    ]
  }
}
```

停止响应：

```json
{
  "status": "needs_input",
  "events": [
    "incident_analyzed",
    "needs_input"
  ],
  "assessment": {
    "missing_fields": [
      "casualties",
      "lane_occupancy"
    ]
  }
}
```

### 对应测试

最终运行：

```bash
.venv/bin/python -m pytest backend/tests/test_workflow.py -q
make test
make eval
make verify
```

全部通过才通关。

### 常见错误

错误 1：API 每次创建图太慢

本周图很小，先保证依赖和行为清晰。第 5 周引入 lifespan 和持久化资源管理。

错误 2：Live 模式选择错误

使用 `selected_plan_agent = live_plan_agent or plan_agent`。

错误 3：工作流返回 Pydantic 序列化错误

节点必须使用 `model_dump(mode="json")`。

错误 4：needs_input 返回 500

它是正常图状态，路由直接返回字典即可。

错误 5：工作流测试污染真实网络

测试使用 mock 设置和 ASGITransport，不需要 DeepSeek Key。

### 当天小练习

增加一条 API 测试，提交缺失输入，断言：

- HTTP 200。
- status 为 needs_input。
- plan 不存在或为 null。
- events 最后是 needs_input。

### 今日总结与明日预告

本周完成第一个 LangGraph 双 Agent 工作流。

第 5 周将在同一图上增加 Checkpoint、thread_id、工作记忆和人工审批。

## 9. 本周唯一实战作业

任务：新增“冰雪事件完整路径”和“冰雪事件缺失路径”两条工作流测试。

完整输入：

```text
G65秦岭路段降雪结冰，占用1条车道，无人员伤亡
```

缺失输入：

```text
G65秦岭路段降雪结冰
```

要求：

1. 完整输入走 `plan_ready`。
2. 完整输入第一引用是 `PLAN-SNOW-001`。
3. 完整输入 events 是 analyze + plan。
4. 缺失输入走 `needs_input`。
5. 缺失输入不产生 plan。
6. 两条测试都通过公开 `workflow.ainvoke`。
7. 不直接调用私有节点。
8. 不修改路由规则以硬编码冰雪场景。
9. 三个统一命令全部通过。

验收：

```bash
make test
make eval
make verify
```

## 10. 测试、常见错误与系统排查

诊断顺序：

```text
工作流结果错误
  -> 看 events 确认走过节点
  -> 看 assessment.missing_fields
  -> 单测 IncidentAnalysisAgent
  -> 单测 PlanExpertAgent
  -> 单测 Tool
  -> 最后检查图边
```

常用命令：

```bash
.venv/bin/python -m pytest backend/tests/test_workflow.py -vv
.venv/bin/python -m pytest backend/tests/test_incident_agent.py -q
.venv/bin/python -m pytest backend/tests/test_plan_agent.py -q
make test
```

症状表：

| 症状 | 可能原因 |
|---|---|
| 没有 assessment | analyze 节点未连接 START |
| 总是 needs_input | Agent 缺失字段识别或测试输入不完整 |
| 总是 retrieve_plan | route 没读取 missing_fields |
| events 被覆盖 | 节点没追加已有列表 |
| plan 不可序列化 | 未使用 mode=json |
| Live Agent 被错误调用 | 应用模式装配错误 |
| graph 没有 ainvoke | 忘记 compile |
| API 422 | 输入不满足 IncidentAnalysisRequest |

不要在第 4 周添加：

- Checkpointer。
- interrupt。
- 人工审批。
- Supervisor。
- 动态模型路由。
- 自动资源调度。

这些能力会逐周增加，保持每个概念可以单独测试。

## 11. 通关清单与三道面试题

- [ ] 能解释 State、Node、Edge。
- [ ] 能定义 total=False TypedDict。
- [ ] 能把 Pydantic 输出转成 JSON State。
- [ ] 能把独立 Agent 封装成节点。
- [ ] 能写纯路由函数。
- [ ] 能添加条件边映射。
- [ ] 能解释 needs_input 是业务状态。
- [ ] 能证明停止分支没有调用预案 Agent。
- [ ] 能断言节点 events 顺序。
- [ ] 能通过公开 ainvoke 运行图。
- [ ] 能保留独立 Agent API。
- [ ] 能让 `make test`、`make eval`、`make verify` 通过。

### 面试题 1

为什么要用 LangGraph，而不是在一个函数里连续调用两个 Agent？

回答要点：

简单串联可以用普通函数，但图提供显式状态、节点、条件边和可扩展的持久化/中断能力。当前图让“缺信息停止”和“信息完整继续”可观察、可测试，并为后续 Checkpoint、HITL 和 Supervisor 留出清晰扩展点。

### 面试题 2

为什么工作流 State 应保存 JSON 字典，而不是 Agent 或 Pydantic 实例？

回答要点：

状态需要跨节点传递并在后续持久化。JSON 结构更容易序列化、查看和恢复；Agent/Client 属于运行依赖，应由工作流对象持有。节点边界用 Pydantic 校验输入输出即可。

### 面试题 3

如何证明信息不完整时预案专家没有被调用？

回答要点：

断言最终 status 为 needs_input、events 只有 incident_analyzed 和 needs_input、plan 不存在；还可以注入会在调用时抛错的 Plan Agent 替身，验证停止分支不会触发它。

## 12. 本周总结与下一周衔接

本周将两个独立 Agent 连接成固定图：

```text
事件研判
  -> 条件路由
  -> 需要补充信息 / 预案建议
```

进入第 5 周前执行：

```bash
make test
make eval
make verify
```

第 5 周继续在当前图上增加：

- MemorySaver 开发 Checkpointer。
- PostgreSQL Checkpointer 正式接口。
- thread_id。
- 人工审批 interrupt。
- approve/reject/edit。
- 恢复执行。
- FastAPI lifespan。
- 未审批高风险动作不得执行。

不会新增第三个 Agent，学习重点是状态持久化与人在回路。
