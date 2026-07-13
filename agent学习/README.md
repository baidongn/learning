# 5 周 DeepSeek Agent 快速上手手册

这套材料把原 21 周 LLMOps 大纲和 8 周 Agent 路线压缩为一条 **Agent 优先、每周 6–8 小时** 的主线。知识点没有删除，只改变学习深度：核心能力亲手实现，平台能力做最小实验，重型模型和厂商产品学会选型。

## 两条阅读路径

### 当前学习路径

你已经完成“LangGraph 接入普通 Tool”，直接从 [第 1 周：LangGraph RAG Agent](weeks/week-01-langgraph-rag-agent.md) 开始。

### 完整手册路径

第一次系统学习或需要复习时，先读 [Agent 前置基础手册](00-agent-foundations.md)，再按五周顺序学习。

## 课程地图

| 材料 | 解决的问题 | 时间 | 产物 |
|---|---|---:|---|
| [前置手册](00-agent-foundations.md) | 补齐 LLM、Prompt、Tool、ReAct、Memory、RAG、LangGraph 基础 | 不计入五周 | 能读懂主线代码 |
| [第 1 周](weeks/week-01-langgraph-rag-agent.md) | Agent 如何检索、路由、暂停和恢复 | 6–8h | 可恢复 RAG Agent |
| [第 2 周](weeks/week-02-advanced-rag-tools-mcp.md) | 如何提高知识质量并安全扩展工具 | 6–8h | 知识型可扩展 Agent |
| [第 3 周](weeks/week-03-reliable-secure-agent.md) | 如何证明 Agent 可靠、安全、可回归 | 6–8h | 评测与安全基线 |
| [第 4 周](weeks/week-04-agent-service-deployment.md) | 如何把 Agent 变成可访问服务 | 6–8h | API、最小 UI、Docker |
| [第 5 周](weeks/week-05-agent-cases-roadmap.md) | 如何复用内核构建商业案例 | 6–8h | 企业智能客服与进阶路线 |

配套资料：

- [Python 关键知识点](python-key-points.md)：按 Agent 开发需要组织的 Python 知识地图。
- [知识覆盖矩阵](coverage-matrix.md)：逐项映射两份原始路线和新增必需能力。
- [最终代码](final-code/README.md)：只维护一套持续演进后的最终项目，不重复生成每周代码。

## 统一标记

- `[基础必会]`：不理解会阻塞后续。
- `[当前起点]`：你现在从这里继续。
- `[项目实现]`：最终代码中有可运行实现。
- `[最小实验]`：动手完成一个小实验，不扩建平台。
- `[理解选型]`：理解用途、边界和选择标准即可。

## 每周固定节奏

每周 6–8 小时：概念约 1.5 小时，编码/阅读最终项目约 3.5 小时，练习与集成 1.5–2.5 小时。

1. 先看“知识衔接”，知道为什么现在学它。
2. 只读核心概念，再运行最小实验。
3. 完成练习，不抄完整平台。
4. 按验收清单自测。
5. 看“下一周衔接”，形成问题驱动的学习链。

## 模型与工程约定

- 主循环统一使用 DeepSeek OpenAI-compatible API。
- `deepseek-chat` 承担对话、结构化输出与 Tool Calling。
- `deepseek-reasoner` 只作为可替换的规划/反思节点，不让核心流程依赖其工具兼容性。
- API Key、Base URL 和模型名全部使用环境变量。
- Tool Calling 的参数必须再经 Pydantic 校验；模型输出不能直接执行。
- 默认 Fake 模式，不需要 API Key；真实 DeepSeek 只做可选冒烟测试。

## 对原路线的完善

原路线覆盖面很广，但若要真正上线 Agent，还缺少几条连接主线。本手册已补齐：

- **上下文工程**：分清模型上下文、图 State、Runtime Context、Store 与 Tool Context。
- **可恢复执行**：Checkpoint 只能恢复状态，副作用还必须配合幂等键。
- **工具工程**：超时、重试、权限、错误分类、缓存、结果压缩和审计同等重要。
- **记忆治理**：记住什么、何时过期、用户是否同意、如何删除，比“有记忆”更重要。
- **RAG 信任边界**：网页和知识库内容都是不可信数据，不能把其中指令当系统指令执行。
- **轨迹评测**：不只评最终答案，还评工具选择、参数、顺序、引用和终止行为。
- **运行预算**：限制循环、工具次数、Token、时间和费用，并支持取消与降级。
- **MCP 安全**：服务白名单、工具命名空间、授权和 Schema 再校验。
- **选型边界**：先选确定性 Workflow，再选单 Agent，最后才是 Multi-Agent。

## 最终验收

进入 `final-code` 后运行：

```bash
uv sync --dev
uv run pytest
uv run ruff check .
uv run uvicorn agent_lab.api:app --reload
```

浏览器打开 `http://127.0.0.1:8000`。无 Key 时页面显示 Fake 结果；配置 `DEEPSEEK_API_KEY` 后使用真实 DeepSeek。Docker 部署见最终代码说明。

## 官方资料

- [DeepSeek Function Calling](https://api-docs.deepseek.com/guides/function_calling/)
- [LangChain Agents](https://docs.langchain.com/oss/python/langchain/agents)
- [LangGraph Persistence](https://docs.langchain.com/oss/python/langgraph/persistence)
- [LangGraph Interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts)
- [LangGraph Time Travel](https://docs.langchain.com/oss/python/langgraph/use-time-travel)
- [Model Context Protocol](https://modelcontextprotocol.io/docs/learn/architecture)
