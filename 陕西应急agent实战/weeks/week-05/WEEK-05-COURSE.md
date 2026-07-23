# 第 5 周：Checkpoint、工作记忆与人工审批

> 学习方式：5 天，每天 2～3 小时。继承第 4 周固定双 Agent 图。
>
> 本周终点：为工作流加入可恢复 Checkpoint、thread_id 和 LangGraph interrupt；方案生成后必须暂停，只有人工 approve 才能记录模拟高风险动作，edit/reject 均不得执行。

## 1. 本周学习地图与最终成果

第 4 周的图一次运行到底：

```text
研判 -> 预案 -> END
```

本周修改为：

```text
研判
  -> 预案
  -> human_approval
  -> interrupt
       |
       +-- approve -> approved + 模拟动作
       +-- edit    -> needs_revision + 无动作
       +-- reject  -> rejected + 无动作
```

暂停与恢复依赖：

```text
thread_id
+ Checkpointer
+ Command(resume=decision)
```

五天安排：

| Day | 核心内容 | 当天成果 |
|---|---|---|
| Day 1 | State 扩展与 InMemorySaver | 理解线程、快照和开发记忆 |
| Day 2 | PostgreSQL Checkpointer | 正式环境可持久化恢复 |
| Day 3 | interrupt 审批节点 | 方案生成后强制暂停 |
| Day 4 | approve/edit/reject 恢复 | 三种人工决定行为清晰 |
| Day 5 | FastAPI lifespan 与审批 API | 完成 start/resume HTTP 闭环 |

本周不新增 Agent。学习重点是工作流可靠性和人在回路。

安全验收底线：

```text
未审批高风险操作执行率 = 0
```

课程中的 `simulate_traffic_control` 只是记录一个字符串，不连接真实交通控制系统。

本周必做：

- MemorySaver 测试。
- PostgreSQL Checkpointer 工厂。
- thread_id。
- interrupt。
- Command resume。
- approve/edit/reject。
- FastAPI lifespan。
- 未审批动作为空的测试。
- `make test`、`make eval`、`make verify`。

本周选做：

- 启动 PostgreSQL 后观察 checkpoint 表。
- 为 comment 增加长度校验。
- 测试不存在 thread_id 的恢复错误。

## 2. 前置知识、环境准备和本周起点

验收第 4 周：

```bash
cd weeks/week-04
make test
make eval
make verify
```

进入第 5 周：

```bash
cd ../week-05
cp .env.example .env
make setup
```

本周增加配置：

```dotenv
CHECKPOINT_BACKEND=memory
```

开发和测试默认 memory，不需要数据库。

本地持久化练习：

```dotenv
CHECKPOINT_BACKEND=postgres
DATABASE_URL=postgresql+asyncpg://highway:highway@localhost:5432/highway_agent
```

新增直接依赖：

```text
langgraph-checkpoint-postgres==3.1.0
psycopg[binary]==3.3.4
```

新增文件：

```text
backend/src/highway_agent/
├── checkpoints.py
└── workflows/
    └── approval_flow.py

backend/tests/
└── test_approval_workflow.py
```

已有 `incident_response.py` 仍保留无审批图，方便对比和回归。

## 3. 本周架构、目录变化与完整调用链

开始请求：

```text
POST /api/workflows/incident-response/{thread_id}/start
  -> ApprovalEmergencyWorkflow.start
  -> StateGraph
  -> analyze_incident
  -> retrieve_plan
  -> human_approval
  -> interrupt(payload)
  -> Checkpointer 保存线程状态
  -> 返回 awaiting_approval
```

恢复请求：

```text
POST /api/workflows/incident-response/{thread_id}/resume
  -> ApprovalDecision 校验
  -> Command(resume=decision)
  -> Checkpointer 按 thread_id 恢复
  -> human_approval 从 interrupt 继续
  -> approved / needs_revision / rejected
```

Checkpointer 的两个实现：

| 环境 | 实现 | 特点 |
|---|---|---|
| 单元测试/默认 Mock | `InMemorySaver` | 快、无需数据库、进程退出丢失 |
| 本地/生产显式选择 | `AsyncPostgresSaver` | 跨请求、可持久化、需连接管理 |

为什么必须有 thread_id？

同一服务可能同时处理多个事件。Checkpointer 要用 thread_id 区分：

```text
approval-001 -> 事件 A 的暂停状态
approval-002 -> 事件 B 的暂停状态
```

如果 start 和 resume 的 thread_id 不一致，就无法恢复同一个工作流。

## 4. Day 1：扩展 State 并使用 InMemorySaver 保存线程

### 今天目标

1. 理解 Checkpoint 与普通变量的差别。
2. 扩展审批相关 State。
3. 使用 `InMemorySaver`。
4. 编译带 Checkpointer 的图。
5. 通过 thread_id 隔离线程。
6. 保留旧工作流回归能力。

### 上一节衔接

第 4 周图没有 Checkpointer，调用结束后中间状态不会被用于恢复。

今天先使用内存实现，把“保存哪个线程”的结构搭好。

### 先说结论

Checkpoint 保存的是图状态快照，不是聊天历史字符串。

本周需要保存：

```text
request
assessment
plan
status
events
approval
executed_actions
```

### 第 1 步：增加配置项

修改 `backend/src/highway_agent/config.py`：

```python
from typing import Literal

from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)


class Settings(BaseSettings):
    """课程项目的统一配置入口。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )

    app_name: str = "陕西高速路网应急指挥 Agent"
    model_mode: Literal["mock", "live"] = "mock"
    checkpoint_backend: Literal[
        "memory",
        "postgres",
    ] = "memory"
    database_url: str = (
        "postgresql+asyncpg://highway:highway"
        "@localhost:5432/highway_agent"
    )
    redis_url: str = "redis://localhost:6379/0"
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_api_key: str = ""
    deepseek_model: str = "deepseek-v4-flash"
```

### 第 2 步：扩展工作流 State

在 `incident_response.py` 的 `IncidentWorkflowState` 增加：

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
    approval: dict[str, Any]
    executed_actions: list[str]
```

`executed_actions` 用来验证审批前后是否记录动作。

### 第 3 步：创建审批工作流文件

新建 `backend/src/highway_agent/workflows/approval_flow.py`，先写导入：

```python
"""带持久化中断和人工审批的 Week 5 工作流。"""

from typing import Any

from langgraph.checkpoint.base import (
    BaseCheckpointSaver,
)
from langgraph.graph import (
    END,
    START,
    StateGraph,
)
from langgraph.types import (
    Command,
    interrupt,
)

from highway_agent.agents.incident_analysis import (
    IncidentAnalysisAgent,
)
from highway_agent.agents.plan_expert import (
    DeepSeekPlanExpertAgent,
    PlanExpertAgent,
)
from highway_agent.tools import MockApiToolClient
from highway_agent.workflows.incident_response import (
    EmergencyWorkflow,
    IncidentWorkflowState,
)
```

### 第 4 步：创建带 Checkpointer 的图骨架

继续添加：

```python
class ApprovalEmergencyWorkflow(
    EmergencyWorkflow
):
    """在方案生成后暂停，只有人工决定才能继续。"""

    def __init__(
        self,
        tools: MockApiToolClient,
        plan_agent: (
            PlanExpertAgent
            | DeepSeekPlanExpertAgent
        ),
        checkpointer: BaseCheckpointSaver,
    ) -> None:
        # 复用父类节点函数，但重新编译一张包含审批节点的图。
        self.incident_agent = IncidentAnalysisAgent(
            tools
        )
        self.plan_agent = plan_agent

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

human_approval 在 Day 3 实现后再注册。

### 第 5 步：理解 InMemorySaver

测试中实例化：

```python
from langgraph.checkpoint.memory import (
    InMemorySaver,
)

checkpointer = InMemorySaver()
```

它只适合：

- 单元测试。
- 单进程演示。
- 不要求重启恢复。

它不适合生产多实例部署。

### 第 6 步：设计 thread config

LangGraph 配置格式：

```python
config = {
    "configurable": {
        "thread_id": thread_id,
    }
}
```

start 和 resume 必须使用完全相同的 `thread_id`。

### 运行与预期输出

检查配置：

```bash
PYTHONPATH=backend/src .venv/bin/python -c "from highway_agent.config import Settings; print(Settings().checkpoint_backend)"
```

预期：

```text
memory
```

运行旧工作流回归：

```bash
.venv/bin/python -m pytest backend/tests/test_workflow.py -q
```

预期 3 条旧图测试仍通过。

### 对应测试

今天先运行：

```bash
.venv/bin/python -m pytest backend/tests/test_config.py backend/tests/test_workflow.py -q
```

审批图将在 Day 3 完成后测试。

### 常见错误

错误 1：把 Checkpointer 放进 State

它是图运行依赖，应传给 `compile(checkpointer=...)`。

错误 2：thread_id 放进业务 request

thread_id 属于 LangGraph config，不是 IncidentAnalysisRequest 字段。

错误 3：认为 MemorySaver 能跨重启

进程退出后内存状态丢失；生产使用 PostgreSQL。

错误 4：删除 Week 4 工作流

保留 `EmergencyWorkflow` 便于回归和对比。

错误 5：executed_actions 默认放模拟动作

初始必须是空列表，只有 approve 分支能添加。

### 当天小练习

设计两个 thread_id：

```text
approval-demo-a
approval-demo-b
```

写出它们各自的 config 字典，确认结构完全独立。

### 今日总结与明日预告

今天完成 State 和线程结构。

明天实现 Checkpointer 工厂，让 memory/postgres 通过配置选择，并处理 asyncpg 与 psycopg 连接字符串差异。

## 5. Day 2：实现 Memory/PostgreSQL Checkpointer 工厂

### 今天目标

1. 理解 Checkpointer 为什么使用 psycopg。
2. 转换 SQLAlchemy asyncpg URL。
3. 创建 AsyncPostgresSaver。
4. 自动执行 saver.setup。
5. 用 asynccontextmanager 管理连接。
6. 根据配置选择 memory/postgres。
7. 用测试验证默认不依赖数据库。

### 上一节衔接

Day 1 设计了可持久化 State 和 thread config。

今天实现正式 Checkpointer 资源管理，但测试仍默认 memory。

### 先说结论

系统有两套 PostgreSQL 客户端用途：

```text
SQLAlchemy 业务 ORM
  -> postgresql+asyncpg://

LangGraph PostgreSQL Checkpointer
  -> psycopg3
  -> postgresql://
```

同一数据库可以使用，不同库要求的 URL 驱动标识不同。

### 第 1 步：锁定依赖

确认 `backend/requirements.lock.txt` 包含：

```text
langgraph-checkpoint-postgres==3.1.0
psycopg[binary]==3.3.4
```

重新安装：

```bash
make setup
```

### 第 2 步：创建 URL 转换函数

新建 `backend/src/highway_agent/checkpoints.py`：

```python
"""LangGraph Checkpointer 工厂。

单元测试使用内存实现；本地和生产运行使用 PostgreSQL 实现。
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from langgraph.checkpoint.memory import (
    InMemorySaver,
)
from langgraph.checkpoint.postgres.aio import (
    AsyncPostgresSaver,
)

from highway_agent.config import Settings


def to_psycopg_uri(
    database_url: str,
) -> str:
    """Checkpointer 使用 psycopg3，移除 SQLAlchemy 的 asyncpg 驱动标识。"""

    return database_url.replace(
        "postgresql+asyncpg://",
        "postgresql://",
        1,
    )
```

只替换第一次，避免误改密码或参数内容。

### 第 3 步：创建 PostgreSQL context manager

继续添加：

```python
@asynccontextmanager
async def postgres_checkpointer(
    database_url: str,
) -> AsyncIterator[AsyncPostgresSaver]:
    """创建并初始化 PostgreSQL Checkpointer 表。"""

    checkpoint_uri = to_psycopg_uri(
        database_url
    )

    async with (
        AsyncPostgresSaver.from_conn_string(
            checkpoint_uri
        )
    ) as saver:
        await saver.setup()
        yield saver
```

`setup()` 创建 Checkpointer 所需表。context manager 负责关闭连接资源。

### 第 4 步：创建配置工厂

继续添加：

```python
@asynccontextmanager
async def configured_checkpointer(
    settings: Settings,
) -> AsyncIterator[
    AsyncPostgresSaver | InMemorySaver
]:
    """Mock 默认内存；部署显式选择 postgres 后保存可恢复状态。"""

    if (
        settings.checkpoint_backend
        == "postgres"
    ):
        async with postgres_checkpointer(
            settings.database_url
        ) as saver:
            yield saver
        return

    yield InMemorySaver()
```

### 第 5 步：测试 URL 转换

在 `backend/tests/test_approval_workflow.py` 添加：

```python
from highway_agent.checkpoints import (
    configured_checkpointer,
    to_psycopg_uri,
)


def test_asyncpg_url_is_converted_for_postgres_checkpointer() -> None:
    source = (
        "postgresql+asyncpg://highway:highway"
        "@localhost/highway_agent"
    )

    assert to_psycopg_uri(source) == (
        "postgresql://highway:highway"
        "@localhost/highway_agent"
    )
```

### 第 6 步：测试默认 MemorySaver

继续添加：

```python
import pytest
from langgraph.checkpoint.memory import (
    InMemorySaver,
)

from highway_agent.config import Settings


@pytest.mark.asyncio
async def test_configured_checkpointer_defaults_to_memory() -> None:
    """Mock/测试默认不需要数据库，部署时再显式切换 PostgreSQL。"""

    async with configured_checkpointer(
        Settings()
    ) as saver:
        assert isinstance(
            saver,
            InMemorySaver,
        )
```

### 运行与预期输出

执行：

```bash
.venv/bin/python -m pytest backend/tests/test_approval_workflow.py -q -k "asyncpg or configured"
```

预期：

```text
..                                                                       [100%]
2 passed
```

不需要启动 PostgreSQL。

### 对应测试

今天还要验证配置可选择 postgres，但不真正连接：

```python
def test_postgres_checkpointer_can_be_selected_by_environment() -> None:
    settings = Settings(
        checkpoint_backend="postgres"
    )

    assert settings.checkpoint_backend == "postgres"
```

运行对应三条测试。

### 常见错误

错误 1：把 asyncpg URL 直接给 psycopg

会出现不识别驱动或连接配置错误。先转为 `postgresql://`。

错误 2：忘记 await saver.setup()

首次使用时缺少 checkpoint 表。

错误 3：单元测试默认连接真实数据库

默认必须 `memory`，确保无 Docker 也能测试。

错误 4：每次请求都打开和关闭 Postgres Saver

正式应用使用 lifespan 持有资源，Day 5 实现。

错误 5：在 context manager 外继续使用 saver

离开上下文后连接可能关闭，必须在应用生命周期内使用。

### 当天小练习

启动基础设施：

```bash
make infra-up
make migrate
```

临时将 `CHECKPOINT_BACKEND=postgres`，Day 5 完成 lifespan 后再运行 API。今天不要单独复制内部连接代码。

### 今日总结与明日预告

Checkpointer 工厂已经支持内存和 PostgreSQL。

明天把 human_approval 节点接入图，并用 interrupt 强制暂停。

## 6. Day 3：创建 human_approval 节点并触发 interrupt

### 今天目标

1. 理解 interrupt 的返回与恢复语义。
2. 向人展示 plan 和允许的决定。
3. 在预案节点后进入审批节点。
4. 带 Checkpointer 编译图。
5. start 时传 thread_id。
6. 把 LangGraph interrupt 转为友好 API 结构。
7. 证明暂停前 executed_actions 为空。

### 上一节衔接

Day 2 已有 Checkpointer，但图还没有真正中断。

今天在 retrieve_plan 后增加 human_approval。

### 先说结论

`interrupt(payload)` 会暂停当前节点：

```text
第一次执行 interrupt
  -> 保存 checkpoint
  -> 返回 __interrupt__

resume
  -> interrupt(...) 表达式得到 decision
  -> 从节点后续逻辑继续
```

因此 interrupt 之前的代码可能在恢复时重新进入，审批节点中不要放不可重复副作用。

### 第 1 步：注册审批节点

在 `ApprovalEmergencyWorkflow.__init__` 添加：

```python
        builder.add_node(
            "human_approval",
            self._human_approval,
        )
```

完整边：

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
        builder.add_edge(
            "needs_input",
            END,
        )
        builder.add_edge(
            "retrieve_plan",
            "human_approval",
        )
        builder.add_edge(
            "human_approval",
            END,
        )
```

### 第 2 步：带 Checkpointer 编译

构造函数最后：

```python
        self.graph = builder.compile(
            checkpointer=checkpointer
        )
```

没有 Checkpointer 的 interrupt 无法可靠跨请求恢复。

### 第 3 步：创建审批 payload

在类内添加节点开头：

```python
    @staticmethod
    def _human_approval(
        state: IncidentWorkflowState,
    ) -> IncidentWorkflowState:
        """暂停图并等待 approve/edit/reject；暂停期间绝不记录执行动作。"""

        decision = interrupt(
            {
                "type": "approval_required",
                "allowed_decisions": [
                    "approve",
                    "edit",
                    "reject",
                ],
                "plan": state.get("plan"),
            }
        )
```

返回给审批人的信息包含计划，但不包含真实控制接口。

### 第 4 步：实现 start

类末尾添加：

```python
    async def start(
        self,
        request: dict[str, Any],
        thread_id: str,
    ) -> dict[str, Any]:
        """启动新线程，并把 LangGraph Interrupt 转换为友好响应。"""

        config = {
            "configurable": {
                "thread_id": thread_id,
            }
        }

        result = await self.graph.ainvoke(
            {
                "request": request,
                "events": [],
                "executed_actions": [],
            },
            config=config,
        )

        if "__interrupt__" in result:
            value = result[
                "__interrupt__"
            ][0].value

            return {
                "thread_id": thread_id,
                "status": "awaiting_approval",
                "interrupt": value,
                "executed_actions": [],
            }

        return result
```

### 第 5 步：创建测试工厂和请求

在测试文件中：

```python
import httpx

from highway_agent.agents.plan_expert import (
    PlanExpertAgent,
)
from highway_agent.api import create_app
from highway_agent.rag import (
    InMemoryPlanRetriever,
    load_demo_documents,
)
from highway_agent.tools import MockApiToolClient
from highway_agent.workflows.approval_flow import (
    ApprovalEmergencyWorkflow,
)


def build_workflow() -> ApprovalEmergencyWorkflow:
    app = create_app()
    tools = MockApiToolClient(
        transport=httpx.ASGITransport(app=app)
    )
    plan_agent = PlanExpertAgent(
        InMemoryPlanRetriever(
            load_demo_documents()
        )
    )

    return ApprovalEmergencyWorkflow(
        tools,
        plan_agent,
        checkpointer=InMemorySaver(),
    )


REQUEST = {
    "raw_text": (
        "秦岭隧道追尾并出现烟雾，"
        "占用两条车道，无人伤亡"
    ),
    "road_code": "G65",
    "section_id": "QINLING-01",
    "camera_id": "CAM-QINLING-01",
}
```

### 第 6 步：测试未审批不执行

增加：

```python
@pytest.mark.asyncio
async def test_workflow_interrupts_before_any_high_risk_action() -> None:
    workflow = build_workflow()

    result = await workflow.start(
        REQUEST,
        thread_id="approval-1",
    )

    assert result["status"] == "awaiting_approval"
    assert result["executed_actions"] == []
    assert result["interrupt"]["allowed_decisions"] == [
        "approve",
        "edit",
        "reject",
    ]
```

### 运行与预期输出

执行：

```bash
.venv/bin/python -m pytest backend/tests/test_approval_workflow.py -q -k interrupts
```

预期：

```text
.                                                                        [100%]
1 passed
```

start 结果：

```json
{
  "thread_id": "approval-1",
  "status": "awaiting_approval",
  "interrupt": {
    "type": "approval_required",
    "allowed_decisions": [
      "approve",
      "edit",
      "reject"
    ],
    "plan": {
      "status": "ready"
    }
  },
  "executed_actions": []
}
```

### 对应测试

今天最重要的断言：

```python
assert result["executed_actions"] == []
```

它证明图暂停期间没有记录高风险动作。

### 常见错误

错误 1：没有传 thread_id

带 Checkpointer 的图需要 config 中的 thread_id。

错误 2：interrupt 后仍执行动作

第一次运行时 interrupt 会暂停，任何副作用都必须放在 decision 分支之后。

错误 3：把审批节点接到 START

正确顺序是 retrieve_plan 后审批，让人看到完整计划。

错误 4：缺失信息也进入审批

analyze 的条件边仍然需要 needs_input 直接 END。

错误 5：测试共享 thread_id

每条测试使用不同 thread_id，避免状态相互影响。

### 当天小练习

启动两个不同 thread_id 的工作流，确认两者都返回 awaiting_approval，并且 executed_actions 均为空。

### 今日总结与明日预告

工作流现在会在计划生成后持久化暂停。

明天实现三种恢复决定，并严格限定只有 approve 才记录模拟动作。

## 7. Day 4：用 Command 恢复 approve、edit 和 reject

### 今天目标

1. 使用 `Command(resume=decision)`。
2. 使用相同 thread_id。
3. 实现 approve。
4. 实现 edit。
5. 实现 reject。
6. 限制 executed_actions。
7. 测试三条分支和 events。
8. 理解 edit 为什么不是 approve。

### 上一节衔接

Day 3 能暂停并返回审批 payload，但还不能恢复。

今天让人工决定成为 interrupt 表达式的返回值。

### 先说结论

决定矩阵：

| decision | status | executed_actions | event |
|---|---|---|---|
| approve | approved | simulate_traffic_control | human_approved |
| edit | needs_revision | 空 | human_edited |
| reject | rejected | 空 | human_rejected |

任何未知值按 reject 处理；API 层还会用 Literal 拒绝非法输入。

### 第 1 步：实现 approve 分支

在 `_human_approval` 的 interrupt 后添加：

```python
        action = str(
            decision.get(
                "decision",
                "reject",
            )
        )

        if action == "approve":
            return {
                "status": "approved",
                "approval": decision,
                # 这里只记录模拟动作，课程永远不会连接真实交通控制系统。
                "executed_actions": [
                    "simulate_traffic_control"
                ],
                "events": [
                    *state.get("events", []),
                    "human_approved",
                ],
            }
```

### 第 2 步：实现 edit 分支

继续添加：

```python
        if action == "edit":
            return {
                "status": "needs_revision",
                "approval": decision,
                "executed_actions": [],
                "events": [
                    *state.get("events", []),
                    "human_edited",
                ],
            }
```

edit 只表示退回修改，本周不自动回跳到 retrieve_plan，避免扩大图复杂度。

### 第 3 步：实现 reject 分支

节点末尾：

```python
        return {
            "status": "rejected",
            "approval": decision,
            "executed_actions": [],
            "events": [
                *state.get("events", []),
                "human_rejected",
            ],
        }
```

默认走最保守的拒绝分支。

### 第 4 步：实现 resume

类末尾添加：

```python
    async def resume(
        self,
        thread_id: str,
        decision: dict[str, Any],
    ) -> dict[str, Any]:
        """从相同 Checkpoint 继续，不重新执行已经成功的前置节点。"""

        config = {
            "configurable": {
                "thread_id": thread_id,
            }
        }

        return await self.graph.ainvoke(
            Command(resume=decision),
            config=config,
        )
```

### 第 5 步：测试 approve

```python
@pytest.mark.asyncio
async def test_approve_resumes_same_thread_and_records_simulated_action() -> None:
    workflow = build_workflow()
    await workflow.start(
        REQUEST,
        thread_id="approval-2",
    )

    result = await workflow.resume(
        "approval-2",
        {"decision": "approve"},
    )

    assert result["status"] == "approved"
    assert result["executed_actions"] == [
        "simulate_traffic_control"
    ]
    assert result["approval"]["decision"] == "approve"
```

### 第 6 步：测试 reject

```python
@pytest.mark.asyncio
async def test_reject_never_records_simulated_action() -> None:
    workflow = build_workflow()
    await workflow.start(
        REQUEST,
        thread_id="approval-3",
    )

    result = await workflow.resume(
        "approval-3",
        {
            "decision": "reject",
            "comment": "信息不足",
        },
    )

    assert result["status"] == "rejected"
    assert result["executed_actions"] == []
```

### 第 7 步：测试 edit

```python
@pytest.mark.asyncio
async def test_edit_requests_revision_without_recording_an_action() -> None:
    """编辑代表退回修改，不能被当作批准执行。"""

    workflow = build_workflow()
    await workflow.start(
        REQUEST,
        thread_id="approval-edit",
    )

    result = await workflow.resume(
        "approval-edit",
        {
            "decision": "edit",
            "comment": "请补充封道范围",
        },
    )

    assert result["status"] == "needs_revision"
    assert result["executed_actions"] == []
    assert result["events"][-1] == "human_edited"
```

### 运行与预期输出

执行：

```bash
.venv/bin/python -m pytest backend/tests/test_approval_workflow.py -q -k "approve or reject or edit"
```

预期三条通过。

approve 关键结果：

```json
{
  "status": "approved",
  "approval": {
    "decision": "approve"
  },
  "executed_actions": [
    "simulate_traffic_control"
  ]
}
```

reject/edit 的 executed_actions 必须是空列表。

### 对应测试

运行：

```bash
.venv/bin/python -m pytest backend/tests/test_approval_workflow.py -q
```

此时应覆盖中断、三决定、工厂和配置测试。

### 常见错误

错误 1：resume 用了新 thread_id

必须和 start 一致，否则找不到暂停状态。

错误 2：直接再次调用 start

恢复要传 `Command(resume=...)`，不是重新提交 request。

错误 3：edit 添加执行动作

edit 不是批准，必须为空。

错误 4：reject 保留上次 approve 的列表

每个线程独立；分支显式返回空列表。

错误 5：把模拟字符串当真实执行

本课程从不连接真实交通控制系统，字符串仅用于测试审批边界。

### 当天小练习

新增非法决定的单元测试，直接调用底层 resume 传 `{"decision": "unknown"}`，确认保守地进入 rejected 且无动作。

API 层非法决定会在 Day 5 被 Pydantic 返回 422。

### 今日总结与明日预告

三种人工决定已经明确，未批准永不记录动作。

明天用 FastAPI lifespan 管理 Checkpointer，并增加 start/resume API。

## 8. Day 5：使用 FastAPI lifespan 管理 Checkpointer 和审批 API

### 今天目标

1. 用 lifespan 持有 Checkpointer。
2. 把资源放入 app.state。
3. 延迟创建共享审批工作流。
4. 定义 ApprovalDecision。
5. 增加 start API。
6. 增加 resume API。
7. 测试 lifespan 注入。
8. 完成本周验收。

### 上一节衔接

Day 4 的审批图可以在 Python 中完整暂停和恢复。

今天把 Checkpointer 生命周期与 Web 应用绑定，避免 PostgreSQL Saver 在请求结束后失效。

### 先说结论

资源生命周期：

```text
FastAPI 启动
  -> configured_checkpointer enter
  -> app.state.approval_checkpointer
  -> 接受 start/resume 请求
FastAPI 关闭
  -> context manager exit
  -> 关闭 PostgreSQL 连接
```

### 第 1 步：定义审批 API 输入

在 `api.py` 导入：

```python
from contextlib import asynccontextmanager
from typing import Literal

from pydantic import BaseModel
```

增加：

```python
class ApprovalDecision(BaseModel):
    """人工审批 API 的输入。"""

    decision: Literal[
        "approve",
        "edit",
        "reject",
    ]
    comment: str = ""
```

非法 decision 会返回 422。

### 第 2 步：创建 lifespan

在 `create_app` 内、创建 FastAPI 前添加：

```python
    @asynccontextmanager
    async def lifespan(
        application: FastAPI,
    ):
        """部署时在应用生命周期内保持 PostgreSQL Checkpointer 连接。"""

        async with configured_checkpointer(
            app_settings
        ) as checkpointer:
            application.state.approval_checkpointer = (
                checkpointer
            )
            yield
```

创建应用时传入：

```python
    app = FastAPI(
        title=app_settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
    )
```

### 第 3 步：创建延迟工作流工厂

在 `create_app` 内 Agent 初始化后添加：

```python
    def get_approval_workflow(
    ) -> ApprovalEmergencyWorkflow:
        """开发模式共享内存 Checkpointer；生产模式由生命周期注入 PostgreSQL。"""

        if not hasattr(
            app.state,
            "approval_workflow",
        ):
            tools = MockApiToolClient(
                transport=httpx.ASGITransport(
                    app=app
                )
            )
            checkpointer = getattr(
                app.state,
                "approval_checkpointer",
                InMemorySaver(),
            )
            app.state.approval_workflow = (
                ApprovalEmergencyWorkflow(
                    tools,
                    selected_plan_agent,
                    checkpointer=checkpointer,
                )
            )

        return app.state.approval_workflow
```

TestClient 未进入上下文时仍有 InMemorySaver 回退；正式启动由 lifespan 注入。

### 第 4 步：增加 start API

在旧工作流 API 后添加：

```python
    @app.post(
        "/api/workflows/incident-response/{thread_id}/start"
    )
    async def start_approval_flow(
        thread_id: str,
        request: IncidentAnalysisRequest,
    ) -> dict[str, object]:
        """启动带人工审批的可恢复线程。"""

        workflow = get_approval_workflow()

        return await workflow.start(
            request.model_dump(mode="json"),
            thread_id,
        )
```

### 第 5 步：增加 resume API

继续添加：

```python
    @app.post(
        "/api/workflows/incident-response/{thread_id}/resume"
    )
    async def resume_approval_flow(
        thread_id: str,
        decision: ApprovalDecision,
    ) -> dict[str, object]:
        """用人工决定恢复指定线程。"""

        workflow = get_approval_workflow()

        return await workflow.resume(
            thread_id,
            decision.model_dump(),
        )
```

### 第 6 步：测试 lifespan

测试：

```python
from fastapi.testclient import TestClient


def test_app_lifespan_installs_configured_checkpointer() -> None:
    app = create_app(
        Settings(
            checkpoint_backend="memory"
        )
    )

    with TestClient(app):
        assert isinstance(
            app.state.approval_checkpointer,
            InMemorySaver,
        )
```

使用 `with TestClient(app)` 才会明确进入 lifespan。

### 第 7 步：手动 API 演示

启动：

```bash
make run
```

开始：

```bash
curl -X POST http://127.0.0.1:8000/api/workflows/incident-response/demo-001/start -H "Content-Type: application/json" -d '{"raw_text":"秦岭隧道追尾并出现烟雾，占用两条车道，无人伤亡","road_code":"G65","section_id":"QINLING-01","camera_id":"CAM-QINLING-01"}'
```

批准：

```bash
curl -X POST http://127.0.0.1:8000/api/workflows/incident-response/demo-001/resume -H "Content-Type: application/json" -d '{"decision":"approve","comment":"同意模拟处置"}'
```

必须使用同一个 `demo-001`。

### 运行与预期输出

完整测试：

```text
.............................................                            [100%]
45 passed
```

start：

```json
{
  "thread_id": "demo-001",
  "status": "awaiting_approval",
  "executed_actions": []
}
```

resume approve：

```json
{
  "status": "approved",
  "approval": {
    "decision": "approve",
    "comment": "同意模拟处置"
  },
  "executed_actions": [
    "simulate_traffic_control"
  ]
}
```

### 对应测试

最终执行：

```bash
make test
make eval
make verify
```

本周 `make eval` 选择 approval 测试，必须覆盖：

- 未审批无动作。
- approve 有且只有模拟动作。
- reject 无动作。
- edit 无动作。
- Checkpointer 默认 memory。
- lifespan 正确安装。

### 常见错误

错误 1：TestClient 不触发生命周期

使用 `with TestClient(app):`。

错误 2：start 和 resume 使用不同服务实例

内存 Checkpointer 只在同一进程有效。本地演示保持 Uvicorn 不重启。

错误 3：Postgres 模式启动失败

先 `make infra-up`，确认 DATABASE_URL，并检查 psycopg URL 转换。

错误 4：重复创建 workflow 丢失 MemorySaver

通过 `app.state.approval_workflow` 共享同一实例。

错误 5：非法 decision 返回 500

ApprovalDecision Literal 会在进入路由前返回 422。

### 当天小练习

分别使用三个新 thread_id 调用 approve、edit、reject。

记录 status、events 最后一项和 executed_actions，确认完全符合决定矩阵。

### 今日总结与明日预告

第 5 周完成持久化状态和人工审批闭环。

第 6 周会新增资源调度 Agent，但仍然只生成调度草案，不绕过审批执行。

## 9. 本周唯一实战作业

任务：为同一完整事件创建三个独立审批线程，分别 approve、edit、reject，并写 API 自动测试。

线程：

```text
assignment-approve
assignment-edit
assignment-reject
```

要求：

1. 三个 start 都返回 awaiting_approval。
2. start 阶段 executed_actions 全为空。
3. approve 最终仅包含 `simulate_traffic_control`。
4. edit status 为 needs_revision 且无动作。
5. reject status 为 rejected 且无动作。
6. comment 被保留在 approval。
7. 三个线程互不污染。
8. 非法 decision API 返回 422。
9. `make test`、`make eval`、`make verify` 全部通过。

不要在作业中新增真实控制、通知或数据库写动作。

## 10. 测试、常见错误与系统排查

诊断流程：

```text
resume 失败
  -> start 是否返回 awaiting_approval？
  -> thread_id 是否完全相同？
  -> workflow/Checkpointer 是否同一实例？
  -> 是否使用 Command(resume=...)？
  -> interrupt payload 是否存在？
  -> decision 是否通过 Literal？
```

调试命令：

```bash
.venv/bin/python -m pytest backend/tests/test_approval_workflow.py -vv
make test
docker compose -f compose.dev.yaml ps
docker compose -f compose.dev.yaml logs postgres
```

PostgreSQL 模式检查：

```bash
make infra-up
CHECKPOINT_BACKEND=postgres make run
```

症状表：

| 症状 | 可能原因 |
|---|---|
| Missing thread_id | config 结构错误 |
| 恢复找不到状态 | thread_id 不一致或 Saver 已丢失 |
| start 已执行动作 | 副作用放在 interrupt 前 |
| edit 也有动作 | 分支边界错误 |
| Memory 重启丢失 | 预期行为，改用 postgres |
| psycopg 不认 URL | 未移除 +asyncpg |
| checkpoint 表不存在 | 未 await setup |
| lifespan 未运行 | TestClient 未用上下文 |

安全复核：

- 未审批：0 个动作。
- reject：0 个动作。
- edit：0 个动作。
- approve：仅课程模拟字符串。
- 不存在真实业务执行 Tool。

## 11. 通关清单与三道面试题

- [ ] 能解释 Checkpoint 和普通内存变量。
- [ ] 能说明 thread_id 的作用。
- [ ] 能使用 InMemorySaver。
- [ ] 能创建 AsyncPostgresSaver。
- [ ] 能转换 asyncpg/psycopg URL。
- [ ] 能解释 asynccontextmanager。
- [ ] 能使用 interrupt。
- [ ] 能使用 Command(resume=...)。
- [ ] 能实现 approve/edit/reject。
- [ ] 能证明未审批动作执行率为 0。
- [ ] 能用 FastAPI lifespan 持有 Saver。
- [ ] 能让 `make test`、`make eval`、`make verify` 通过。

### 面试题 1

LangGraph interrupt 为什么必须配合 Checkpointer 和 thread_id？

回答要点：

interrupt 会暂停图，后续请求需要恢复暂停时的 State 和节点位置。Checkpointer 保存快照，thread_id 定位具体线程；缺少任一项都无法可靠地把人工决定送回正确事件。

### 面试题 2

为什么开发测试使用 InMemorySaver，生产使用 PostgreSQL Saver？

回答要点：

InMemorySaver 速度快、无外部依赖，适合单测，但不能跨进程重启和多实例共享。PostgreSQL Saver 提供持久化与跨请求恢复，适合部署；应用还需用 lifespan 管理连接。

### 面试题 3

如何保证 edit 和 reject 不会误执行高风险动作？

回答要点：

动作只在显式 approve 分支构造；edit/reject 都显式返回空 executed_actions，并有自动测试断言。start 中断结果也断言为空，API decision 用 Literal 限制输入。

## 12. 本周总结与下一周衔接

本周新增的是可靠性能力，不是新 Agent：

```text
Checkpoint
+ thread_id
+ interrupt
+ resume
+ 人工审批
+ 生命周期管理
+ 零未审批执行
```

进入第 6 周前执行：

```bash
make test
make eval
make verify
```

第 6 周会新增第三个 Agent：资源调度 Agent。

它会：

- 查询附近救援资源。
- 根据距离与可用性排序。
- 生成 DispatchProposal。
- 处理资源不足。
- 保留只读/模拟边界。
- 先独立测试，再接入已有工作流。
- 继续要求高风险动作人工审批。
