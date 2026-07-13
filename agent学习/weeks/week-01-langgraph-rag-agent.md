# 第 1 周：LangGraph RAG Agent

**本周 6–8 小时｜普通 Tool → RAG Tool → 可恢复 Agent**

你已经会在 LangGraph 接入普通 Tool。本周不重学 ToolNode，而是解决三个自然出现的问题：知识工具怎样返回可信依据？危险动作怎样暂停？进程中断后怎样继续？

## 学习结果

完成后你能：

- 把 Retriever 封装为有明确输入/输出的 RAG Tool。
- 区分 Runtime Context、State、Store、模型上下文和工具上下文。
- 用条件边在直接回答、RAG、搜索、业务工具之间路由。
- 用 Checkpoint + Thread 保存进度，用 Interrupt + Resume 做人工审批。
- 解释 Replay/Fork 为什么可能重复副作用，并用幂等避免。
- 输出引用、流式事件和用量，支持取消和运行预算。

## 时间安排

| 阶段 | 时间 | 动手结果 |
|---|---:|---|
| 1. RAG Tool 契约 | 1.5h | 查询、命中、来源、分数、无结果 |
| 2. State 与路由 | 1.5h | 四路条件分支 |
| 3. 持久化与审批 | 2h | Interrupt、批准、拒绝、恢复 |
| 4. Streaming 与预算 | 1h | 事件、取消、Token/工具上限 |
| 5. 综合练习与验收 | 1–2h | 客服 RAG Agent |

## 1. Retriever 变成 RAG Tool `[当前起点]` `[项目实现]`

普通业务 Tool 的返回常是一个事实；RAG Tool 的返回必须表达“找到了什么、可信度如何、如何引用、没找到怎么办”。

```python
from pydantic import BaseModel, Field

class RagQuery(BaseModel):
    query: str = Field(min_length=2, max_length=500)
    top_k: int = Field(default=4, ge=1, le=10)

class RagHit(BaseModel):
    text: str
    source: str
    score: float = Field(ge=0, le=1)

class RagResult(BaseModel):
    hits: list[RagHit]
    no_result: bool
```

关键规则：

1. Tool 返回资料，不替模型写最终答案。
2. `source` 来自索引元数据，不能由模型生成。
3. 低于阈值视为无结果；不要为了凑 Top-K 返回弱相关材料。
4. 先做权限过滤，再做检索与 Rerank。
5. 最终引用只允许来自实际放入上下文的命中。

RAG Tool 与“图内 RAG 节点”都可用。需要让 Agent 自主决定查询次数或把 RAG 复用给其他 Workflow 时用 Tool；流程固定、需要更强控制时用独立节点。最终项目用独立 RAG 节点表达路由，Retriever 契约可直接包装成 Tool。

无结果策略：改写查询一次 → 可选搜索 → 明确说明无可靠依据 → 请求补充信息/人工转接。禁止直接让模型凭常识补企业规则。

## 2. 五层上下文 `[基础必会]`

| 层 | 放什么 | 不放什么 |
|---|---|---|
| 模型上下文 | 本次模型真正需要看的消息、资料、工具结果 | 全量历史和连接对象 |
| Graph State | 当前执行可恢复的事实、路由、审批、引用、用量 | API Key、数据库连接 |
| Runtime Context | 由服务端注入的 user/tenant、权限、客户端 | 模型可修改的业务内容 |
| Store | 跨会话用户记忆、应用配置、长期资料 | 当前节点的临时变量 |
| Tool Context | 当前用户、允许工具、幂等键、Trace ID | 由模型填写的权限字段 |

State 设计遵循“恢复所需的最小事实”。工具客户端用依赖注入，不进入 State。用户身份必须来自认证层，不能信任模型输出。

```python
class AgentState(TypedDict, total=False):
    query: str
    route: str
    citations: list[str]
    pending_action: dict[str, object] | None
    tool_trace: list[dict[str, object]]
    token_count: int
```

消息过长时按顺序处理：删除无关工具原文 → 只保留高相关 RAG Chunk → 摘要旧对话 → 保留最近消息。摘要也是模型生成数据，重要事实应结构化保存并可追溯来源。

## 3. 路由 `[项目实现]`

路由可以是代码规则、结构化模型判断或二者结合：

```text
危险写操作 → approval
明确订单/物流 → business_tool
企业制度/售后知识 → rag
需要最新公开信息 → search
闲聊或无需外部事实 → direct
```

高风险和权限规则必须代码优先；语义模糊部分再让模型输出结构化 `route + reason`。所有路由都要有默认回退，禁止返回不存在的节点。

逻辑路由是显式业务规则；语义路由基于意图或向量相似。路由失败应纳入评测：是否选对工具、是否不必要调用、是否正确结束。

## 4. Checkpoint、Thread 与 Store `[基础必会]`

- **Checkpoint**：某个 Thread 在图运行中的 State 快照。
- **Thread ID**：同一执行历史的标识；不同用户不能复用。
- **Store**：跨 Thread 的长期数据。

内存 Checkpointer 只供本地测试。生产应使用持久化 Checkpointer，并让 `tenant_id + user_id + thread_id` 建立隔离关系。服务重启后能否恢复，是“持久化”的最低验收。

Checkpoint 保存状态，不会撤销外部副作用。若节点先提交退款、再在保存 Checkpoint 前崩溃，恢复可能再次提交。因此写工具需使用稳定幂等键：

```text
idempotency_key = tenant + thread + action_type + business_object
```

数据库用唯一约束兜底；第三方 API 若支持幂等 Header，必须传递。

## 5. Interrupt、Resume 与人工审批 `[项目实现]`

危险节点不要“询问模型是否同意”，而应产生一个待审批结构并 `interrupt`：

```python
from langgraph.types import interrupt

decision = interrupt({
    "tool_name": "request_refund",
    "arguments": {"order_id": "1002"},
    "description": "为订单1002提交退款",
})
if not decision["approved"]:
    return {"answer": "操作已取消"}
```

审批界面显示动作、参数、影响和发起者；审批接口只提交 `approved` 或允许修改后的受控字段。恢复前重新检查权限、数据是否过期、预算和幂等状态。

三条路径都要测：批准、拒绝、修改。超时未审批要过期，不能永久挂起。

## 6. Time Travel、Replay 与 Fork `[最小实验]`

- Replay：从历史 Checkpoint 重跑，用于调试。
- Fork：修改历史 State 后从分支继续，用于比较 Prompt/路由。
- Time Travel 是调试能力，不是数据库回滚。

实验：选一次错误路由的 State，把 `route` 从 `direct` 攺为 `rag` 后 Fork；观察新分支结果。只使用只读工具，或给写工具传同一幂等键。

## 7. Subgraph `[最小实验]`

当一段流程有独立输入输出、可单测、可复用时提取 Subgraph。例如“检索 → Rerank → 置信度判断 → 回退”是知识子图；“判断风险 → 审批 → 执行 → 审计”是动作子图。

不要按文件数量拆 Subgraph。父图与子图之间只传契约字段，避免共享巨大 State。

## 8. Streaming、取消与背压 `[项目实现]`

区分三类事件：

- Token 事件：用户看到的文本增量。
- Update 事件：节点开始/结束、工具状态、审批请求。
- Custom 事件：检索进度、引用、用量等业务事件。

SSE 适合浏览器单向输出。客户端断开时取消模型/工具任务；代理关闭缓冲；长任务发送心跳。生产者比网络快时不能无限排队，这就是背压问题：使用有界队列、合并小 Token 或降低事件频率。

取消是协作式的：服务保存取消信号，节点边界主动检查，外部 HTTP 调用也设置超时。已经完成的副作用不能靠取消撤销，应设计补偿动作。

## 9. 预算与停止 `[项目实现]`

每次运行至少限制：

```text
max_iterations / max_tool_calls / max_tokens
max_seconds / max_cost / max_repeated_call
```

达到预算时返回可解释状态，保存轨迹，不把内部异常直接展示给用户。Reasoner 的规划也计入预算。

## 10. 搜索与不可信内容 `[最小实验]`

搜索 Tool 只返回标题、URL、摘要/清洗文本和时间；限制域名、结果数、正文长度、超时与重定向。网页中的“忽略系统指令”“调用某工具”只是数据，不能改变 Agent Policy。

搜索适合实时公开信息；RAG 适合企业受控知识；直接回答适合无需外部事实的交流。回答中分别标注来源，过期内容需显示日期。

## 综合练习

在最终项目基础上完成：

1. 给 RAG 结果增加 `score` 阈值并测试无结果。
2. 新增 `search` 路由，但先使用固定 Fake Search，不接真实网络。
3. 为退款加入审批过期字段。
4. 记录一次批准、一次拒绝的工具轨迹。
5. 将循环上限改为 2，构造重复工具调用并验证停止。

## 常见错误

- RAG Tool 返回一大段字符串，丢失来源和分数。
- 把身份/权限放进模型可修改的 State。
- Checkpoint 后就认为写操作自动“仅执行一次”。
- 审批恢复时不重新校验权限。
- 只流 Token，不流错误、完成和审批事件。
- 取消 HTTP 响应，却没有取消后台任务。

## 本周验收

- [ ] RAG 命中返回答案和真实引用。
- [ ] 无结果不会编造。
- [ ] RAG/搜索/工具/直接回答可解释路由。
- [ ] 危险工具暂停，批准和拒绝均可恢复。
- [ ] Replay 不会造成重复副作用。
- [ ] 不同 Thread 的 State 隔离。
- [ ] 循环、工具、Token 和时间有上限。
- [ ] SSE 有 token/done/error 或等价事件，客户端可取消。

代码索引：[agent.py](../final-code/src/agent_lab/agent.py)、[retrieval.py](../final-code/src/agent_lab/retrieval.py)、[tools.py](../final-code/src/agent_lab/tools.py)、[api.py](../final-code/src/agent_lab/api.py)。

## 下一周为什么自然产生

现在 Agent 能检索和执行，但“能找到”不等于“找得准”，“能接工具”不等于“工具可靠”。第 2 周专门提高知识质量、工具工程和扩展协议，然后才讨论复杂编排。
