# Agent 前置完整手册

这部分保留已学内容，供复习和查漏。它不占新的五周时间。阅读目标不是背 API，而是形成一条稳定心智模型：**模型负责判断，代码负责约束，工具负责行动，状态负责连续性，评测负责证明效果。**

## 1. 基本认知 `[基础必会]`

### 心智模型

- **LLM**：根据上下文预测输出的模型，本身不会读取你的数据库或真正执行退款。
- **ChatBot**：输入消息、生成回复；流程通常只有一次模型调用。
- **RAG**：先检索外部资料，再让模型依据资料回答，解决知识缺失和引用问题。
- **Tool Calling**：模型生成“调用哪个工具及参数”的结构，应用代码校验并执行。
- **Agent**：围绕目标反复进行“判断 → 行动 → 观察 → 再判断”，直到结束或超限。
- **Workflow**：由代码预先规定步骤和分支，确定性更强。
- **Multi-Agent**：多个具有不同职责的 Agent 协作；不是单 Agent 的默认升级方向。
- **LLMOps**：围绕数据、Prompt、模型、评测、发布、监控、安全和成本的工程体系。

一个业务 Agent 至少有八部分：

```text
Model       负责理解、选择和生成
Prompt      定义角色、目标、边界和失败方式
Tool        读取数据或执行动作
Memory      保存跨轮次有价值的信息
State       保存本次图运行的事实与进度
Loop        决定何时继续、何时结束
Policy      权限、安全、审批和预算
Observability 记录轨迹、质量、延迟和费用
```

### Agent 还是 Workflow

先问三个问题：步骤是否固定、错误代价是否高、是否需要探索。

- 固定审批、转账、删数据：Workflow 主导，模型只做分类或抽取。
- 工具少、目标开放、允许尝试：单 Agent。
- 多领域、上下文相互独立、确有并行或专业分工：才考虑 Multi-Agent。

常见错误：把“调用一次工具”包装成多 Agent；把高风险业务交给模型自由循环；认为 RAG 就是 Agent。

自测：解释“订单查询 ChatBot”“售后 RAG”“退款审批 Workflow”“客服 Agent”的差别；若说不清边界，先不要继续。

最终代码：[agent.py](final-code/src/agent_lab/agent.py)、[safety.py](final-code/src/agent_lab/safety.py)。

## 2. Python、uv 与 DeepSeek 环境 `[基础必会]`

### 最小环境

```bash
uv init agent-lab
cd agent-lab
uv add openai pydantic langgraph fastapi uvicorn
uv add --dev pytest pytest-asyncio ruff
```

`.env`：

```dotenv
DEEPSEEK_API_KEY=不要写进代码或提交到 Git
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_CHAT_MODEL=deepseek-chat
DEEPSEEK_REASONING_MODEL=deepseek-reasoner
```

### DeepSeek OpenAI-compatible 最小调用

```python
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.environ["DEEPSEEK_API_KEY"],
    base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
)
response = client.chat.completions.create(
    model=os.getenv("DEEPSEEK_CHAT_MODEL", "deepseek-chat"),
    messages=[
        {"role": "system", "content": "你是企业客服，只回答职责范围内问题。"},
        {"role": "user", "content": "退货期限是多少？"},
    ],
    temperature=0,
)
print(response.choices[0].message.content)
```

消息角色：`system` 定规则，`user` 是输入，`assistant` 是模型回复，`tool` 把工具执行结果送回模型。Token 是计费和上下文预算单位，不等于汉字数。

### 模型职责

- `deepseek-chat`：主对话、JSON、Tool Calling。
- 推理模型：可选的复杂规划/反思；不要让主循环依赖其工具能力。
- `ModelGateway`：隔离厂商 SDK，但课程业务只实现 DeepSeek，避免多套重复代码。

错误按性质处理：认证错误停止并报警；429/网络错误指数退避重试；参数错误立即修代码；模型输出错误走校验/修复/回退；不可把所有异常无限重试。

常见错误：把 Key 写入示例；生产无超时；把 `reasoner` 当所有节点默认模型；忽略 Token 和速率限制。

自测：删除 Key 后程序是否明确进入 Fake 模式？修改 Base URL 是否不需要改业务代码？

最终代码：[config.py](final-code/src/agent_lab/config.py)、[deepseek.py](final-code/src/agent_lab/deepseek.py)。

## 3. Prompt 与结构化输出 `[基础必会]`

### Prompt 的五个部分

```text
角色：你是企业售后客服
目标：回答政策或调用工具完成查询
输入：用户问题、可信资料、已授权工具
边界：资料不足就说明；不得编造订单状态
输出：答案、引用、下一步；高风险操作必须申请审批
```

零样本用于规则清楚的任务；少样本用于分类边界、格式或语气难以描述的任务。示例要覆盖易错边界，不要只给最简单正例。

### Pydantic 校验

```python
from typing import Literal
from pydantic import BaseModel, Field

class RouteDecision(BaseModel):
    route: Literal["rag", "tool", "direct"]
    reason: str = Field(min_length=1, max_length=100)

# 模型返回 JSON 后仍由应用校验；失败时可以有限重试或回退。
decision = RouteDecision.model_validate_json(model_text)
```

JSON 只是文本格式；JSON Schema 描述字段与约束；Pydantic 把解析、类型转换和校验放到代码边界。OutputParser 方便串链，但不能替代业务校验。

Prompt 要版本化，并用固定测试集比较。至少记录：版本、模型、参数、输入、输出、校验结果、耗时和 Token。

常见失败：要求“严格 JSON”却混入解释；字段可选性不清；Prompt 同时承担检索、规划和文案；修改 Prompt 不跑回归。

自测：为“是否需要退款审批”写一个三字段 Schema，并列出非法输入的回退策略。

最终代码：[deepseek.py](final-code/src/agent_lab/deepseek.py)、[test_deepseek.py](final-code/tests/test_deepseek.py)。

## 4. LangChain 基础 `[基础必会]`

### 组件关系

- `ChatModel`：统一模型消息接口。
- `PromptTemplate` / `ChatPromptTemplate`：模板与变量。
- `OutputParser`：把模型文本转为业务结构。
- `Runnable`：具有 `invoke/ainvoke/stream/batch` 等统一能力的可组合单元。
- `LCEL`：用 `|` 组合 Runnable；适合短、确定、可复用的数据流。
- `Callback`：观察模型、工具、Token 和错误，不承载核心业务状态。

```python
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

prompt = ChatPromptTemplate.from_messages([
    ("system", "用一句话解释术语；不知道就说不知道。"),
    ("user", "{term}"),
])
chain = prompt | chat_model | StrOutputParser()
answer = await chain.ainvoke({"term": "Checkpoint"})
```

`RunnableSequence` 是顺序，`RunnableParallel` 是对同一输入并行产生多个结果。Streaming 只有上游组件支持流式且中间步骤不阻塞时才能平滑传递。

LangChain v1 的 `create_agent` 提供常用 Agent 循环；底层仍是“模型给 Tool Call → 应用执行 → ToolMessage 回传 → 模型继续”。学会手写循环后再用封装，遇错才知道看哪里。

常见错误：用 LCEL 隐藏复杂状态；把 Callback 当数据库；同步函数阻塞异步链；只会框架 API 不懂消息协议。

自测：什么时候用一条 LCEL，什么时候升级为 LangGraph？答案应包含“状态、分支、恢复和人工审批”。

最终代码以 LangGraph 为主；DeepSeek 网关在 [deepseek.py](final-code/src/agent_lab/deepseek.py)。

## 5. Tool Calling `[基础必会]`

### 工具契约

一个好工具应满足：单一动作、名称明确、描述说明何时用/何时不用、参数强类型、返回小而稳定、错误可分类、权限可判断。

```python
from pydantic import BaseModel, Field

class OrderQuery(BaseModel):
    order_id: str = Field(pattern=r"^\d{4,}$")

async def query_order(order_id: str) -> dict[str, str]:
    # 真实项目在此调用受权限保护的订单服务。
    return {"order_id": order_id, "status": "运输中"}
```

完整协议：

1. 把工具名称、描述、JSON Schema 发送给 `deepseek-chat`。
2. 模型返回 Tool Call；它只是建议，不是已执行。
3. 应用检查工具是否注册、用户是否有权、参数是否有效、是否需审批。
4. 应用设置超时并执行；对暂时性错误有限重试。
5. 以对应 `tool_call_id` 写入 ToolMessage。
6. 模型基于 Observation 继续，直到无 Tool Call 或达到预算。

DeepSeek 的 `strict` Function Calling 当前是可选 Beta 实验，需要 Beta Base URL，并只支持其文档规定的 JSON Schema 子集。即使启用 strict，应用仍要做 Pydantic、权限和业务校验。主线使用普通模式，避免核心流程依赖 Beta 能力。

HTTP Tool 要限制域名、方法、响应大小和重定向；数据库 Tool 优先暴露参数化的业务查询，不让模型自由生成并执行任意 SQL；写操作必须有幂等键和审计。

常见错误：工具描述含糊；模型参数不再校验；把异常栈直接发给模型；工具返回整页 HTML；允许模型拼 URL 或 SQL；危险动作无审批。

自测：订单查询与退款申请为什么必须是两个工具？列出退款工具在执行前需要的五项检查。

最终代码：[tools.py](final-code/src/agent_lab/tools.py)、[test_tools.py](final-code/tests/test_tools.py)。

## 6. Agent Loop 与 ReAct `[基础必会]`

ReAct 的工程含义是让“推理/决策”和“行动/观察”交替，不要求把模型私有思维完整输出。生产中记录简洁决策理由和工具轨迹即可。

```text
用户：查询订单 1002
模型：选择 query_order(order_id="1002")
代码：校验权限、参数与预算
工具：返回 {status: "运输中"}
模型：组织用户可读答案
结束：没有新 Tool Call
```

循环必须有：最大轮数、最大工具次数、总超时、Token/费用上限、重复调用检测、停止条件、取消信号和最终回退。工具失败要区分参数错误、权限错误、暂时性故障和永久故障。

最小伪代码：

```python
for step in range(max_steps):
    reply = await model.chat(messages, tools=schemas)
    if not reply.tool_calls:
        return reply.content
    for call in reply.tool_calls:
        result = await registry.invoke(call.name, call.arguments, context)
        messages.append(make_tool_message(call.id, result))
raise RuntimeError("Agent 超过最大循环次数")
```

常见错误：无上限 while；工具失败后原参数重复调用；把“模型回答完成”当唯一停止条件；记录完整敏感上下文。

自测：画出订单查询轨迹，标出模型边界、代码边界、外部系统边界。

最终代码：[agent.py](final-code/src/agent_lab/agent.py)、[safety.py](final-code/src/agent_lab/safety.py)。

## 7. Memory 与上下文 `[基础必会]`

### 五种容易混淆的东西

- 消息历史：本线程最近对话。
- 短期记忆：当前任务需要的事实和中间结果。
- 摘要记忆：把旧消息压缩，节省上下文。
- 实体/用户画像：跨会话稳定偏好，如语言、地区；必须有用户同意。
- Checkpoint：恢复图执行状态，不等于长期用户记忆。

上下文窗口有限。优先顺序通常是：系统约束 → 当前问题 → 必需状态 → 高相关资料 → 最近消息 → 摘要。不要把所有历史、所有检索结果和所有工具结果都塞给模型。

记忆写入应是独立决策：候选提取 → 类型/敏感性判断 → 用户同意 → 命名空间保存 → 设置来源和过期时间。提供查看、修改、删除和全部清除能力。

会话隔离至少包含 `tenant_id/user_id/thread_id`；工具 Runtime Context 由服务端注入，不能让模型填写 `user_id` 来越权。

常见错误：数据库聊天记录等于记忆；每句话都长期保存；跨用户共用 Thread；摘要丢失未完成事项；删除原消息却忘记删向量索引。

自测：把“我喜欢中文回复”“我的手机号是…”“订单 1002 正在退款”分别放入何种存储，保留多久，谁能读取？

最终代码：[context.py](final-code/src/agent_lab/context.py)、[test_context_safety.py](final-code/tests/test_context_safety.py)。

## 8. RAG 基础 `[基础必会]`

### 流程

```text
离线：加载 → 清洗 → 切分 → 元数据 → Embedding → 索引
在线：问题 → 检索 → 过滤/重排 → 上下文 → 受约束回答 → 引用
```

文档加载要保留标题、章节、页码、更新时间、权限和来源。递归切分优先保留段落/句子边界；Chunk 太小缺上下文，太大降低检索精度并浪费 Token。

Embedding 把文本映射为向量；向量数据库负责相似度检索与过滤。Retriever 是面向 Agent 的接口，不等于数据库本身。Top-K、最低分、权限过滤、去重、Rerank 和上下文预算共同决定最终材料。

引用必须来自实际进入回答上下文的文档；无结果或低置信度时明确回退，不让模型用常识伪装为企业政策。

向量库定位：

- Faiss：本地、简单、无完整服务治理。
- Pinecone：托管向量服务。
- TCVectorDB：腾讯云生态托管选择。
- Weaviate：独立向量数据库与混合检索能力。
- PostgreSQL/pgvector：已有 PostgreSQL 团队的低复杂度选择，事务和业务数据结合方便。

选择看数据规模、过滤需求、延迟、运维、合规、备份和团队经验，不按流行度选。

常见错误：只测“能搜到”；不保存元数据；向量相似就认为可信；引用未进入上下文的资料；知识更新不删除旧向量。

自测：为员工手册设计 Chunk 元数据；说明 RAG 无结果时 Agent 应如何路由。

最终代码：[retrieval.py](final-code/src/agent_lab/retrieval.py)、[pgvector_store.py](final-code/src/agent_lab/pgvector_store.py)。

## 9. LangGraph 入门 `[基础必会]`

LangGraph 适合有状态、分支、循环、暂停或恢复的流程。图不是为了画图，而是把隐式 Agent Loop 变成可检查的状态机。

- `StateGraph`：图定义。
- `State`：节点共享的业务数据契约。
- `Node`：读取 State，返回局部更新。
- `Edge`：固定流转。
- `Conditional Edge`：根据状态选择下一节点。
- `START/END`：入口和终点。
- `Reducer`：定义多个更新如何合并；消息常用追加而不是覆盖。
- `Command`：同时更新状态并控制跳转/恢复。
- `MessagesState`：官方提供的消息状态基础。
- `ToolNode`：执行已选择的工具；是否需要它取决于你的工具控制需求。

```python
from typing import Literal, TypedDict
from langgraph.graph import END, START, StateGraph

class State(TypedDict):
    query: str
    route: Literal["tool", "direct"]
    answer: str

def route(state: State) -> dict[str, str]:
    return {"route": "tool" if "订单" in state["query"] else "direct"}

builder = StateGraph(State)
builder.add_node("route", route)
builder.add_node("tool", query_order_node)
builder.add_node("direct", direct_answer_node)
builder.add_edge(START, "route")
builder.add_conditional_edges("route", lambda state: state["route"])
builder.add_edge("tool", END)
builder.add_edge("direct", END)
graph = builder.compile()
```

State 只放可序列化、恢复所需的信息；数据库连接、模型客户端和当前用户权限放 Runtime Context/依赖中。节点尽量小、幂等、输入输出清晰。

已经完成的普通 Tool 接入通常是：模型节点产生 Tool Call → 条件边判断是否有工具 → ToolNode 执行 → 回到模型节点。下一步不是再加一个普通工具，而是把 Retriever 做成具有引用和无结果语义的 RAG Tool。

常见错误：State 放 SDK 对象；节点内部偷偷修改全局变量；边与业务条件混在 Prompt；并发分支没有 Reducer；工具副作用在重放时重复执行。

自测：从最终图中找出每个 Node、Edge、Conditional Edge、State 字段和终止条件。

最终代码：[agent.py](final-code/src/agent_lab/agent.py)。继续阅读：[第 1 周](weeks/week-01-langgraph-rag-agent.md)。

官方校准资料：[DeepSeek Function Calling](https://api-docs.deepseek.com/guides/function_calling/)、[LangChain Agents](https://docs.langchain.com/oss/python/langchain/agents)、[LangGraph Persistence](https://docs.langchain.com/oss/python/langgraph/persistence)、[LangGraph Interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts)。

## 前置验收

不看答案，用 15 分钟完成：

1. 画出 Model → Tool → Observation → Model。
2. 写一个带 Pydantic 参数的只读 Tool。
3. 解释 Memory、State、Checkpoint 的差别。
4. 解释 Retriever、Vector Store、Rerank 的差别。
5. 说出危险工具必须由代码控制的五项条件。
6. 在 LangGraph 图中加入一个条件路由。

能完成 4 项即可开始第 1 周；不足部分按对应章节复习，不必从头重学。
