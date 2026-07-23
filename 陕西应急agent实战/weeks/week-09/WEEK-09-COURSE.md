# 第 9 周：受限 Supervisor Agent 与有界多 Agent 编排

> 学习方式：5 天，每天 2～3 小时。继承四个已经独立运行、测试和评测的专业 Agent。
>
> 本周终点：最后开发第五个 Agent——Supervisor。它按固定安全顺序调用事件研判、预案、资源调度和安全复核，具备一次重试、步数上限、证据年龄计算和人工审批等待状态，但永远不执行真实动作。

## 1. 本周学习地图与最终成果

Supervisor 最后开发，因为它依赖前四个 Agent 的稳定契约。

固定顺序：

```text
IncidentAnalysisAgent
  |
  +-- missing_fields -> needs_input -> STOP
  |
  v
PlanExpertAgent
  |
  +-- high/critical 且有资源需求
  |      -> ResourceDispatchAgent
  |
  v
SafetyReviewAgent
  |
  +-- PASS   -> ready
  +-- REVISE -> needs_revision
  +-- BLOCK only approval -> awaiting_approval
  +-- BLOCK other -> blocked
```

每次专业 Agent 调用：

```text
最多重试 1 次
每次尝试消耗 1 个 step
每次留下 SupervisorTrace
```

五天安排：

| Day | 核心内容 | 当天成果 |
|---|---|---|
| Day 1 | Supervisor 输入输出与 Trace | 统一聚合契约 |
| Day 2 | 有界重试与步数上限 | 异常重试一次，防无限循环 |
| Day 3 | 四专业 Agent 固定路由 | 缺字段提前停止，高风险才调度 |
| Day 4 | 真实证据年龄与安全状态映射 | stale、审批、阻断正确分流 |
| Day 5 | API、DeepSeek Live 与验收 | 最终后端编排可演示 |

本周新增第五个 Agent：

```text
SupervisorAgent
```

它是受限编排器，不让模型自由决定任意节点或工具。第 9 周先追求可控、可测试、可审计。

本周必做：

- SupervisorRequest/Result。
- SupervisorTrace。
- max_steps。
- max_retries=1。
- missing_fields 立即停止。
- 条件调用资源 Agent。
- 从 ToolTrace 计算 evidence_age_minutes。
- 调用安全 Agent。
- 状态映射。
- executed_actions 始终为空。
- Mock/Live 预案 Agent兼容。
- `make test`、`make eval`、`make verify`。

本周选做：

- 为每个专业 Agent 增加可控失败替身。
- 给 Trace 增加 duration_ms。
- 把 Supervisor 路由迁入一张新的 LangGraph。

## 2. 前置知识、环境准备和本周起点

验收第 8 周：

```bash
cd weeks/week-08
make test
make eval
make verify
```

进入第 9 周：

```bash
cd ../week-09
cp .env.example .env
make setup
```

本周不增加第三方依赖。新增：

```text
backend/src/highway_agent/agents/
└── supervisor.py

backend/tests/
└── test_supervisor_agent.py
```

四个专业 Agent 必须先保持独立测试：

```bash
.venv/bin/python -m pytest backend/tests/test_incident_agent.py -q
.venv/bin/python -m pytest backend/tests/test_plan_agent.py -q
.venv/bin/python -m pytest backend/tests/test_resource_agent.py -q
.venv/bin/python -m pytest backend/tests/test_safety_agent.py -q
```

默认：

```dotenv
MODEL_MODE=mock
```

Live 模式只替换预案专家为 DeepSeek 版本；其他三个专业 Agent 仍为确定性实现。

## 3. 本周架构、目录变化与完整调用链

Supervisor 依赖注入：

```text
incident_agent
plan_agent
dispatch_agent
safety_agent
max_steps
max_retries
```

它不自行创建 Tool Client，也不读取全局环境变量。API 装配层负责选择具体实现。

Trace 示例：

```json
[
  {
    "agent_name": "incident_analysis",
    "attempt": 1,
    "success": true
  },
  {
    "agent_name": "plan_expert",
    "attempt": 1,
    "success": true
  },
  {
    "agent_name": "resource_dispatch",
    "attempt": 1,
    "success": true
  },
  {
    "agent_name": "safety_review",
    "attempt": 1,
    "success": true
  }
]
```

状态集合：

| status | 触发条件 |
|---|---|
| needs_input | 研判缺少关键字段 |
| awaiting_approval | 唯一 BLOCK 原因为人工审批 |
| blocked | 注入/未知动作等其他阻断 |
| needs_revision | 引用缺失或证据过期 |
| ready | 安全 PASS |
| step_limit | 尝试次数达到上限 |
| failed | 重试后仍异常 |

为什么 executed_actions 永远为空？

Supervisor 只组织建议和安全结论。即使 `human_approved=True`，本周仍不连接执行层；真实副作用必须由独立、受控、可审计的执行服务完成。

## 4. Day 1：定义 Supervisor 统一输入、轨迹和聚合输出

### 今天目标

1. 定义 SupervisorRequest。
2. 默认高风险动作未审批。
3. 定义每次 Agent 尝试轨迹。
4. 定义七种 Supervisor 状态。
5. 聚合四个专业结果。
6. 单独标记 awaiting_human_approval。
7. executed_actions 默认空。
8. 创建内部步数异常。

### 上一节衔接

第 8 周已完成最后一个专业 Agent。

今天先定义 Supervisor 契约，不急着调用任何 Agent。

### 先说结论

SupervisorRequest 统一包含：

```text
事件 ID
事件文本和定位
可选摄像头
资源需求
审批状态
```

SupervisorResult 保留每个专业 Agent 的原始结构，不把它们压扁成一段不可测试的自然语言。

### 第 1 步：创建模块导入

新建 `backend/src/highway_agent/agents/supervisor.py`：

```python
"""受限 Supervisor Agent：按固定安全边界编排四个专业 Agent。"""

from collections.abc import Callable
from datetime import (
    UTC,
    datetime,
)
from inspect import isawaitable
from typing import (
    Any,
    Literal,
    TypeVar,
)

from pydantic import (
    BaseModel,
    Field,
)

from highway_agent.agents.incident_analysis import (
    IncidentAnalysisAgent,
    IncidentAnalysisRequest,
    IncidentAssessment,
)
from highway_agent.agents.plan_expert import (
    DeepSeekPlanExpertAgent,
    PlanExpertAgent,
    PlanQuery,
    PlanRecommendation,
)
from highway_agent.agents.resource_dispatch import (
    DispatchProposal,
    DispatchRequest,
    ResourceDispatchAgent,
)
from highway_agent.agents.safety_review import (
    SafetyReviewAgent,
    SafetyReviewRequest,
    SafetyReviewResult,
)

T = TypeVar("T")
```

### 第 2 步：定义请求

继续：

```python
class SupervisorRequest(BaseModel):
    """Supervisor 的统一输入；高风险动作默认未审批。"""

    incident_id: str
    raw_text: str = Field(
        min_length=2,
        max_length=2000,
    )
    road_code: str
    section_id: str
    camera_id: str | None = None
    required_resources: list[str] = Field(
        default_factory=list
    )
    human_approved: bool = False
```

审批默认 False，不能默认信任调用方。

### 第 3 步：定义 Trace

继续：

```python
class SupervisorTrace(BaseModel):
    """每次专业 Agent 尝试都留下可审计轨迹。"""

    agent_name: str
    attempt: int
    success: bool
    error: str | None = None
```

重试会产生两条同名 Agent Trace，attempt 分别为 1、2。

### 第 4 步：定义聚合结果

继续：

```python
class SupervisorResult(BaseModel):
    """Supervisor 只汇总结果，不把建议伪装成已执行动作。"""

    status: Literal[
        "ready",
        "needs_input",
        "needs_revision",
        "awaiting_approval",
        "blocked",
        "step_limit",
        "failed",
    ]
    incident: IncidentAssessment | None = None
    plan: PlanRecommendation | None = None
    dispatch: DispatchProposal | None = None
    safety: SafetyReviewResult | None = None
    route_trace: list[SupervisorTrace]
    awaiting_human_approval: bool = False
    executed_actions: list[str] = Field(
        default_factory=list
    )
```

### 第 5 步：创建内部控制异常

继续：

```python
class _StepLimitReached(RuntimeError):
    """内部控制信号：达到步数上限后立即停止后续调用。"""
```

这个异常只在 Supervisor 内部使用，对外转换为 `step_limit`。

### 第 6 步：创建构造函数

继续：

```python
class SupervisorAgent:
    """第五个 Agent：负责路由、一次重试和结果聚合。"""

    def __init__(
        self,
        incident_agent: IncidentAnalysisAgent,
        plan_agent: (
            PlanExpertAgent
            | DeepSeekPlanExpertAgent
        ),
        dispatch_agent: ResourceDispatchAgent,
        safety_agent: SafetyReviewAgent,
        *,
        max_steps: int = 8,
        max_retries: int = 1,
    ) -> None:
        self.incident_agent = incident_agent
        self.plan_agent = plan_agent
        self.dispatch_agent = dispatch_agent
        self.safety_agent = safety_agent
        self.max_steps = max_steps
        self.max_retries = max_retries
```

默认四个专业调用各一次，共 4 steps；有一次重试空间，但总数最多 8。

### 运行与预期输出

语法检查：

```bash
PYTHONPATH=backend/src .venv/bin/python -m py_compile backend/src/highway_agent/agents/supervisor.py
```

构造请求：

```bash
PYTHONPATH=backend/src .venv/bin/python -c "from highway_agent.agents.supervisor import SupervisorRequest; print(SupervisorRequest(incident_id='INC-SUP',raw_text='隧道追尾',road_code='G65',section_id='QINLING-01').model_dump())"
```

预期 human_approved=False、required_resources=[]。

### 对应测试

今天在测试中创建两个 helper：`build_supervisor` 和 `high_risk_request`。后续所有场景复用，减少重复装配。

### 常见错误

错误 1：SupervisorResult 只返回 summary

应保留结构化 incident/plan/dispatch/safety。

错误 2：human_approved 默认 True

高风险默认必须未批准。

错误 3：executed_actions 使用可变默认列表

使用 default_factory。

错误 4：Trace 不记录 attempt

无法分辨重试。

错误 5：把内部 StepLimit 直接抛给 API

应转换为结构化 status。

### 当天小练习

构造一个 SupervisorResult(status="needs_input", route_trace=[])，确认未传专业结果时都为 None、executed_actions 为空。

### 今日总结与明日预告

Supervisor 输入、轨迹和聚合输出已完成。

明天实现同步/异步通用调用、一次重试和步数上限。

## 5. Day 2：实现同步/异步通用调用、重试和步数上限

### 今天目标

1. 接收同步或异步 operation。
2. 用 isawaitable 判断。
3. 每次尝试前检查 max_steps。
4. 成功写 Trace。
5. 失败写 Trace 和 error。
6. 默认重试一次。
7. 重试耗费步骤。
8. 失败后重新抛给外层降级。

### 上一节衔接

Day 1 已有 Trace 和配置。

今天先实现调用基础设施，Day 3 再写业务顺序。

### 先说结论

为什么需要同时支持同步/异步？

| Agent | 方法 |
|---|---|
| IncidentAnalysisAgent | async ainvoke |
| Mock PlanExpertAgent | sync invoke |
| DeepSeekPlanExpertAgent | async ainvoke |
| ResourceDispatchAgent | async ainvoke |
| SafetyReviewAgent | sync invoke |

`_run_with_retry` 统一处理。

### 第 1 步：创建方法签名

在 SupervisorAgent 中添加：

```python
    async def _run_with_retry(
        self,
        name: str,
        operation: Callable[[], T],
        trace: list[SupervisorTrace],
    ) -> T:
        """只对异常重试一次；每次尝试都消耗一个步骤。"""

        last_error: Exception | None = None
```

operation 是零参数闭包，真实参数由 lambda 捕获。

### 第 2 步：实现尝试循环和步数检查

继续：

```python
        for attempt in range(
            1,
            self.max_retries + 2,
        ):
            if len(trace) >= self.max_steps:
                raise _StepLimitReached
```

`max_retries=1` 时 range 为 1、2，共最多两次尝试。

Trace 每条代表一个已发生尝试，因此 `len(trace)` 可作为总步数。

### 第 3 步：处理同步/异步成功

继续：

```python
            try:
                value: Any = operation()

                if isawaitable(value):
                    value = await value

                trace.append(
                    SupervisorTrace(
                        agent_name=name,
                        attempt=attempt,
                        success=True,
                    )
                )

                return value
```

### 第 4 步：记录失败

继续：

```python
            except Exception as exc:
                # Supervisor 是边界层，需要统一记录专业 Agent 异常。
                last_error = exc

                trace.append(
                    SupervisorTrace(
                        agent_name=name,
                        attempt=attempt,
                        success=False,
                        error=str(exc),
                    )
                )
```

课程正式代码带 noqa 注释，明确这是有意在边界统一捕获。

### 第 5 步：重试耗尽后抛出

循环后：

```python
        assert last_error is not None
        raise last_error
```

外层 `ainvoke` 会把异常转为 failed，同时保留 Trace 中的错误详情。

### 第 6 步：设计瞬时故障替身

测试中创建：

```python
class FlakyIncidentAgent:
    """第一次失败、第二次成功的可控替身。"""

    def __init__(self) -> None:
        self.calls = 0

    async def ainvoke(
        self,
        request,
    ):
        self.calls += 1

        if self.calls == 1:
            raise RuntimeError(
                "模拟瞬时故障"
            )

        return await real_agent.ainvoke(
            request
        )
```

### 第 7 步：设计步数限制测试

将 `max_steps=2`，完整请求理论上需要 4 个 Agent，因此应在第三个调用前停止。

### 运行与预期输出

Day 3 完成主方法后正式运行测试。今天先语法：

```bash
PYTHONPATH=backend/src .venv/bin/python -m py_compile backend/src/highway_agent/agents/supervisor.py
```

重试预期 Trace：

```json
[
  {
    "agent_name": "incident_analysis",
    "attempt": 1,
    "success": false,
    "error": "模拟瞬时故障"
  },
  {
    "agent_name": "incident_analysis",
    "attempt": 2,
    "success": true
  }
]
```

### 对应测试

后续断言：

```python
assert flaky.calls == 2
assert attempts == [1, 2]
```

步数限制：

```python
assert result.status == "step_limit"
assert len(result.route_trace) == 2
assert result.executed_actions == []
```

### 常见错误

错误 1：失败不计 step

每次尝试都必须 append Trace。

错误 2：无限重试

上限由 max_retries 明确控制，默认 1。

错误 3：同步返回被 await

先用 isawaitable 判断。

错误 4：step_limit 后继续调用

抛内部控制异常，外层立即返回。

错误 5：错误详情丢失

Trace 保存 str(exc)，对外 status 不必暴露堆栈。

### 当天小练习

分别计算：

- max_retries=0 最多尝试几次？
- max_retries=1 最多几次？
- max_steps=1 时第一次成功后还能调用第二个 Agent 吗？

答案分别是 1、2、不能。

### 今日总结与明日预告

有界调用基础设施完成。

明天实现固定四 Agent 顺序、缺字段提前停止和条件资源调度。

## 6. Day 3：按固定顺序编排四个专业 Agent

### 今天目标

1. 创建 ainvoke 状态变量。
2. 调用事件研判。
3. 缺字段立即 needs_input。
4. 构造更完整的 PlanQuery。
5. 兼容 Mock/Live Plan Agent。
6. 仅高风险且有需求时调度资源。
7. 不让 Supervisor 自由跳过安全复核。
8. 保留每一步结果。

### 上一节衔接

Day 2 已有有界调用方法。

今天编写业务主线，先到安全请求之前。

### 先说结论

资源 Agent 的调用条件：

```text
risk_level in {"high", "critical"}
AND required_resources 非空
```

中低风险或没有资源需求时不调用。

### 第 1 步：创建主方法和局部状态

在 SupervisorAgent 添加：

```python
    async def ainvoke(
        self,
        request: SupervisorRequest,
    ) -> SupervisorResult:
        """按研判、预案、调度、安全复核顺序执行有界编排。"""

        trace: list[SupervisorTrace] = []
        incident: IncidentAssessment | None = None
        plan: PlanRecommendation | None = None
        dispatch: DispatchProposal | None = None
        safety: SafetyReviewResult | None = None

        try:
```

try 内是正常编排，except 处理 step_limit/failed。

### 第 2 步：调用事件研判

继续：

```python
            incident_request = (
                IncidentAnalysisRequest(
                    raw_text=request.raw_text,
                    road_code=request.road_code,
                    section_id=request.section_id,
                    camera_id=request.camera_id,
                )
            )

            incident = await self._run_with_retry(
                "incident_analysis",
                lambda: self.incident_agent.ainvoke(
                    incident_request
                ),
                trace,
            )
```

### 第 3 步：缺字段立即停止

继续：

```python
            if incident.missing_fields:
                return SupervisorResult(
                    status="needs_input",
                    incident=incident,
                    route_trace=trace,
                    executed_actions=[],
                )
```

此分支 plan/dispatch/safety 全部保持 None。

### 第 4 步：构造 PlanQuery 并调用

继续：

```python
            plan_query = PlanQuery(
                event_summary=(
                    f"{incident.incident_type} "
                    f"{incident.risk_level} "
                    + " ".join(
                        incident.known_facts
                    )
                )
            )

            plan = await self._run_with_retry(
                "plan_expert",
                lambda: (
                    self.plan_agent.ainvoke(
                        plan_query
                    )
                    if isinstance(
                        self.plan_agent,
                        DeepSeekPlanExpertAgent,
                    )
                    else self.plan_agent.invoke(
                        plan_query
                    )
                ),
                trace,
            )
```

加入事件类型、风险和 known_facts，提高检索输入的完整性。

### 第 5 步：条件调用资源 Agent

继续：

```python
            should_dispatch = (
                incident.risk_level
                in {"high", "critical"}
                and bool(
                    request.required_resources
                )
            )

            if should_dispatch:
                dispatch_request = (
                    DispatchRequest(
                        incident_id=(
                            request.incident_id
                        ),
                        section_id=(
                            request.section_id
                        ),
                        required_types=(
                            request.required_resources
                        ),
                    )
                )

                dispatch = await (
                    self._run_with_retry(
                        "resource_dispatch",
                        lambda: (
                            self.dispatch_agent.ainvoke(
                                dispatch_request
                            )
                        ),
                        trace,
                    )
                )
```

### 第 6 步：准备 proposed_actions

资源有实际 assignments：

```python
            proposed_actions = (
                ["dispatch_resource"]
                if (
                    dispatch
                    and dispatch.assignments
                )
                else [
                    "prepare_warning_board"
                ]
            )
```

如果资源缺口导致无 assignment，就只建议低风险准备提示牌。

### 第 7 步：设计 needs_input 测试

测试输入：

```text
高速发生追尾
```

不传 camera，required_resources 空。

断言：

- status=needs_input。
- Trace 只有 incident_analysis。
- plan/dispatch/safety 为 None。
- executed_actions 空。

### 运行与预期输出

Day 4 补完安全调用后运行。

needs_input 预期：

```json
{
  "status": "needs_input",
  "plan": null,
  "dispatch": null,
  "safety": null,
  "route_trace": [
    {
      "agent_name": "incident_analysis",
      "success": true
    }
  ],
  "executed_actions": []
}
```

### 对应测试

核心测试名：

```text
test_supervisor_stops_when_required_incident_fields_are_missing
```

它证明 Supervisor 不带着猜测继续。

### 常见错误

错误 1：缺字段仍调用 Plan Agent

必须在 plan_query 前 return。

错误 2：所有事件都调度资源

检查风险和 required_resources 两个条件。

错误 3：resource partial 仍虚构 assignment

调度 Agent 已保证，Supervisor 不应修改结果。

错误 4：PlanQuery 只传 raw_text

使用研判后的结构化类型、风险和事实。

错误 5：Supervisor 重新实现专业规则

只做路由和聚合，不复制子 Agent 内部逻辑。

### 当天小练习

预测三种情况是否调用 ResourceDispatchAgent：

1. critical + 两种需求。
2. medium + 两种需求。
3. critical + 空需求。

只有第 1 种调用。

### 今日总结与明日预告

Supervisor 主路由已经到 proposed_actions。

明天从真实 ToolTrace 计算证据年龄，调用安全 Agent，并映射最终状态。

## 7. Day 4：计算真实证据年龄、调用安全复核并映射状态

### 今天目标

1. 只使用成功 ToolTrace。
2. 取最旧证据计算年龄。
3. 没有成功证据时默认 31 分钟。
4. 从真实 Plan Citation 构造引用。
5. 调用 SafetyReviewAgent。
6. 捕获 step_limit。
7. 捕获 failed。
8. 映射 PASS/REVISE/BLOCK。
9. 保证 executed_actions 为空。

### 上一节衔接

Day 3 已得到 incident、plan、可选 dispatch 和 proposed_actions。

今天完成安全闭环。

### 先说结论

证据年龄取最旧成功证据：

```text
now - min(successful observed_at)
```

如果路况 5 分钟、天气 120 分钟，整体年龄按 120 分钟，要求重新查询。

### 第 1 步：收集成功证据

在 proposed_actions 后添加：

```python
            successful_evidence = [
                item.observed_at
                for item in incident.tool_trace
                if item.success
            ]
```

失败的 Tool 不贡献可信 observed_at。

### 第 2 步：计算分钟年龄

继续：

```python
            evidence_age_minutes = (
                max(
                    0,
                    int(
                        (
                            datetime.now(UTC)
                            - min(
                                successful_evidence
                            )
                        ).total_seconds()
                        // 60
                    ),
                )
                if successful_evidence
                else 31
            )
```

系统时钟微小偏差用 max(0, ...) 防止负数。

没有成功证据时设 31，确保 safety 至少 REVISE。

### 第 3 步：构造安全请求

继续：

```python
            safety_request = (
                SafetyReviewRequest(
                    incident_id=(
                        request.incident_id
                    ),
                    recommendation=plan.summary,
                    citations=[
                        (
                            f"{citation.document_id}"
                            f"#{citation.section}"
                        )
                        for citation in plan.citations
                    ],
                    proposed_actions=(
                        proposed_actions
                    ),
                    evidence_age_minutes=(
                        evidence_age_minutes
                    ),
                    human_approved=(
                        request.human_approved
                    ),
                    user_input=request.raw_text,
                )
            )
```

引用来自 PlanRecommendation 的真实检索绑定结果。

### 第 4 步：调用安全 Agent

继续：

```python
            safety = await self._run_with_retry(
                "safety_review",
                lambda: self.safety_agent.invoke(
                    safety_request
                ),
                trace,
            )
```

### 第 5 步：处理步数和异常

try 后添加：

```python
        except _StepLimitReached:
            return SupervisorResult(
                status="step_limit",
                incident=incident,
                plan=plan,
                dispatch=dispatch,
                safety=safety,
                route_trace=trace,
                executed_actions=[],
            )

        except Exception:
            # 错误详情已在 Trace 中。
            return SupervisorResult(
                status="failed",
                incident=incident,
                plan=plan,
                dispatch=dispatch,
                safety=safety,
                route_trace=trace,
                executed_actions=[],
            )
```

### 第 6 步：映射安全结果

正常 try 结束后：

```python
        if safety.verdict == "BLOCK":
            approval_only = (
                set(safety.reason_codes)
                == {
                    "HUMAN_APPROVAL_REQUIRED"
                }
            )
            status = (
                "awaiting_approval"
                if approval_only
                else "blocked"
            )
        elif safety.verdict == "REVISE":
            status = "needs_revision"
        else:
            status = "ready"
```

只有唯一阻断原因是审批时才 awaiting_approval；同时有注入就必须 blocked。

### 第 7 步：返回聚合结果

完成方法：

```python
        return SupervisorResult(
            status=status,
            incident=incident,
            plan=plan,
            dispatch=dispatch,
            safety=safety,
            route_trace=trace,
            awaiting_human_approval=(
                status
                == "awaiting_approval"
            ),
            # 即使已审批，本周也只产出可执行建议。
            executed_actions=[],
        )
```

### 第 8 步：测试 stale 证据

测试替身返回一条 2 小时前 ToolTrace，一条当前 Trace。

最终：

```python
assert result.status == "needs_revision"
assert (
    "STALE_EVIDENCE"
    in result.safety.reason_codes
)
```

### 运行与预期输出

执行 Supervisor 测试：

```bash
.venv/bin/python -m pytest backend/tests/test_supervisor_agent.py -q
```

预期 7 条测试全部通过。

高风险未审批结果：

```json
{
  "status": "awaiting_approval",
  "awaiting_human_approval": true,
  "executed_actions": [],
  "safety": {
    "verdict": "BLOCK",
    "reason_codes": [
      "HUMAN_APPROVAL_REQUIRED"
    ]
  }
}
```

### 对应测试

本日覆盖：

- 固定四 Agent 顺序。
- 未审批等待。
- needs_input 提前停止。
- 瞬时故障重试。
- step_limit。
- stale -> needs_revision。
- executed_actions 始终为空。

### 常见错误

错误 1：取最新证据而非最旧

安全取 `min(observed_at)`，再用 now 减。

错误 2：没有证据当 0 分钟

应设 31，要求修订。

错误 3：任何 BLOCK 都 awaiting_approval

只有 reason_codes 精确等于审批一项。

错误 4：human_approved 后直接执行

Supervisor 仍只返回建议，executed_actions 为空。

错误 5：Trace 超过 max_steps

每次尝试前检查长度。

### 当天小练习

构造一个同时包含“绕过审批”输入和 dispatch_resource 的请求。预测 Supervisor 最终 status 应是 blocked，而不是 awaiting_approval。

### 今日总结与明日预告

Supervisor 业务编排和安全映射已完成。

明天接入 API，验证 Mock/Live 预案选择并完成第 9 周验收。

## 8. Day 5：接入 Supervisor API、验证 Live 模式并完成验收

### 今天目标

1. 在 API 导入 Supervisor。
2. 装配四专业 Agent。
3. 复用同一个 Tool Client。
4. 增加独立 Supervisor 路由。
5. 手动调用 awaiting_approval。
6. 测试 DeepSeek Live 预案节点。
7. 运行 Supervisor 评测。
8. 回归全部既有能力。

### 上一节衔接

Day 4 已通过 Python 入口完成多 Agent 编排。

今天增加最终后端聚合 API。

### 先说结论

新增：

```text
POST /api/agents/supervisor/invoke
```

它与旧 Agent、工作流和审批 API 同时保留。

### 第 1 步：导入 Supervisor

在 `api.py` 添加：

```python
from highway_agent.agents.supervisor import (
    SupervisorAgent,
    SupervisorRequest,
    SupervisorResult,
)
```

### 第 2 步：增加路由

在安全 Agent API 后添加：

```python
    @app.post(
        "/api/agents/supervisor/invoke",
        response_model=SupervisorResult,
    )
    async def invoke_supervisor(
        request: SupervisorRequest,
    ) -> SupervisorResult:
        """运行有步数上限的 Supervisor，且不执行任何真实高风险动作。"""

        tools = MockApiToolClient(
            transport=httpx.ASGITransport(
                app=app
            )
        )

        supervisor = SupervisorAgent(
            incident_agent=(
                IncidentAnalysisAgent(
                    tools
                )
            ),
            plan_agent=selected_plan_agent,
            dispatch_agent=(
                ResourceDispatchAgent(
                    tools
                )
            ),
            safety_agent=SafetyReviewAgent(),
        )

        return await supervisor.ainvoke(
            request
        )
```

事件和资源 Agent 复用同一个 Tool Client。

### 第 3 步：手动调用高风险请求

启动：

```bash
make run
```

调用：

```bash
curl -X POST http://127.0.0.1:8000/api/agents/supervisor/invoke -H "Content-Type: application/json" -d '{"incident_id":"INC-SUP-DEMO","raw_text":"秦岭隧道追尾出现烟雾，2人受伤，占用2车道","road_code":"G65","section_id":"QINLING-01","camera_id":"CAM-QINLING-01","required_resources":["ambulance","tow_truck"],"human_approved":false}'
```

### 第 4 步：检查路由顺序

响应 `route_trace` 依次：

```text
incident_analysis
plan_expert
resource_dispatch
safety_review
```

每条 attempt=1、success=true。

### 第 5 步：验证 Live 模式

测试通过：

```python
Settings(
    model_mode="live",
    deepseek_api_key="test-key",
)
```

和 `httpx.MockTransport` 注入 DeepSeek 响应。

断言：

- DeepSeek 调用 1 次。
- plan.summary 是模拟 DeepSeek 文本。
- 最终仍 awaiting_approval。
- executed_actions 为空。

### 第 6 步：运行统一验收

执行：

```bash
make test
make eval
make verify
```

本周 `make eval` 选择 supervisor 测试。

### 运行与预期输出

完整测试：

```text
.................................................................        [100%]
65 passed
```

高风险结果关键字段：

```json
{
  "status": "awaiting_approval",
  "awaiting_human_approval": true,
  "executed_actions": [],
  "incident": {
    "risk_level": "critical"
  },
  "dispatch": {
    "status": "ready"
  },
  "safety": {
    "verdict": "BLOCK",
    "reason_codes": [
      "HUMAN_APPROVAL_REQUIRED"
    ]
  }
}
```

### 对应测试

最终：

```bash
.venv/bin/python -m pytest backend/tests/test_supervisor_agent.py -q
make test
make eval
make verify
```

全部通过才通关。

### 常见错误

错误 1：Live 模式仍使用 Mock Plan Agent

路由传 `selected_plan_agent`。

错误 2：每个 Agent 新建不同 Tool Client

可以工作但难追踪，本周复用同一个实例。

错误 3：Supervisor API 执行动作

返回 executed_actions 必须为空。

错误 4：required_resources 空却出现 dispatch

检查条件路由。

错误 5：missing_fields 后还有 plan

必须提前 return。

### 当天小练习

分别调用：

1. 完整高风险未审批。
2. 同一请求 human_approved=true。
3. 缺少伤亡/车道信息。

比较 status 和 route_trace。第 2 条可以 ready，但 executed_actions 仍为空；第 3 条 Trace 只有 incident_analysis。

### 今日总结与明日预告

后端五 Agent 体系完成：

```text
预案专家
事件研判
资源调度
安全复核
Supervisor
```

第 10 周不再增加 Agent，开始创建 Vue 轻量指挥台展示 Supervisor、轨迹、审批和工具证据。

## 9. 本周唯一实战作业

任务：增加 Supervisor 三场景参数化 API 测试。

场景：

1. 完整 critical + 资源 + 未审批 -> awaiting_approval。
2. 完整 critical + 资源 + 已审批 -> ready，但 executed_actions 仍为空。
3. 缺字段 -> needs_input，Trace 只有 incident_analysis。

每个场景断言：

- HTTP 200。
- status。
- route_trace Agent 顺序。
- executed_actions=[]。
- plan/dispatch/safety 是否应存在。
- 未审批不绕过安全。
- 既有 4 个独立 Agent API仍通过。
- `make test`、`make eval`、`make verify` 全部通过。

## 10. 测试、常见错误与系统排查

诊断流程：

```text
Supervisor 状态错误
  -> 看 route_trace
  -> 找第一个 failed/缺失 Agent
  -> 看 incident.missing_fields
  -> 看 plan.citations
  -> 看 dispatch.assignments/unmet
  -> 看 safety.checks/reason_codes
  -> 看 max_steps
```

调试：

```bash
.venv/bin/python -m pytest backend/tests/test_supervisor_agent.py -vv
.venv/bin/python -m pytest backend/tests/test_incident_agent.py -q
.venv/bin/python -m pytest backend/tests/test_plan_agent.py -q
.venv/bin/python -m pytest backend/tests/test_resource_agent.py -q
.venv/bin/python -m pytest backend/tests/test_safety_agent.py -q
make test
```

症状表：

| 症状 | 可能原因 |
|---|---|
| Trace 顺序错 | 主路由顺序错误 |
| 重试超过一次 | max_retries 计算错误 |
| step_limit 仍继续 | 没抛控制异常 |
| 缺字段仍调 Plan | 提前 return 位置错误 |
| stale 没识别 | 取了最新而非最旧时间 |
| 所有 BLOCK 都等待审批 | 状态映射过宽 |
| ready 有 executed_actions | 越过执行边界 |
| Live 不调模型 | selected_plan_agent 错误 |

Supervisor 原则：

- 专业判断留给子 Agent。
- 路由规则显式。
- 循环有界。
- 异常有迹可查。
- 缺事实就停止。
- 安全复核必须最后经过。
- 不直接执行真实动作。

## 11. 通关清单与三道面试题

- [ ] 能说明为什么 Supervisor 最后开发。
- [ ] 能定义统一请求和聚合结果。
- [ ] 能记录每次 Agent 尝试。
- [ ] 能兼容同步/异步 Agent。
- [ ] 能实现一次重试。
- [ ] 能实现 max_steps。
- [ ] 能缺字段提前停止。
- [ ] 能条件调用资源 Agent。
- [ ] 能计算最旧证据年龄。
- [ ] 能映射安全三态。
- [ ] 能保证 executed_actions 始终为空。
- [ ] 能让 `make test`、`make eval`、`make verify` 通过。

### 面试题 1

为什么 Supervisor 不应该一开始就开发？

回答要点：

Supervisor 依赖专业 Agent 的输入输出和错误边界。如果子 Agent 尚不稳定，多 Agent 问题无法定位。先让每个 Agent 独立运行、测试和评测，再编排，能把复杂度分层并提高可维护性。

### 面试题 2

如何防止 Supervisor 陷入无限重试或无限调用？

回答要点：

每次专业 Agent 尝试记录 Trace 并消耗 step；max_retries 限制单操作重试，max_steps 限制全局尝试数。达到上限抛内部控制信号并返回 step_limit，且不执行任何动作。

### 面试题 3

为什么 Supervisor 即使 human_approved=true 也不直接执行动作？

回答要点：

审批只是执行前必要条件，不等于 Supervisor 应拥有执行权限。编排层只生成安全建议；真实副作用应在独立执行层完成权限、幂等、审计和回滚控制，降低越权风险。

## 12. 本周总结与下一周衔接

本周完成后端核心体系：

```text
四个专业 Agent
+ 一个受限 Supervisor
+ REST/MCP Tool
+ RAG/DeepSeek
+ LangGraph/HITL
+ 安全复核
+ 有界重试
+ 审计轨迹
```

进入第 10 周前执行：

```bash
make test
make eval
make verify
```

第 10 周开发 Vue 轻量指挥台：

- 事件输入表单。
- Supervisor 结果卡片。
- Agent route_trace 时间线。
- 资源 Proposal。
- 安全 reason_codes。
- 审批按钮。
- Mock 模式演示。
- Vitest 和构建。

不新增复杂后台、地图引擎或真实视频。
