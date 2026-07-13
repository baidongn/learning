# 第 2 周：高级 RAG、Tool、MCP 与复杂编排

**本周 6–8 小时｜先提高信息和动作质量，再增加 Agent 数量**

前置：第 1 周 Agent 已有明确 State、RAG 路由、审批和恢复。本周的核心不是收集“几十种 RAG 名词”，而是建立诊断顺序：先看数据，再看召回，再看排序，再看回答。

## 学习结果

- 建立可更新、可评估、带权限元数据的知识索引。
- 实现关键词 + 向量混合检索、Rerank 和 CRAG 回退。
- 把 Tool 做到有权限、超时、重试、幂等、缓存和错误恢复。
- 安全接入 OpenAPI、MCP，并理解 Skills。
- 根据确定性选择 Workflow、单 Agent、Planner-Executor、Supervisor 或 Multi-Agent。

## 时间安排

| 阶段 | 时间 | 深度 |
|---|---:|---|
| 数据、切分与基础检索 | 1.5h | 实现 |
| 混合检索、Rerank、CRAG | 2h | 实现 |
| 其他 RAG 策略 | 1h | 理解/最小实验 |
| Tool、OpenAPI、MCP | 2h | 实现/最小实验 |
| 编排选型与验收 | 1–1.5h | 理解选型 |

## 1. 数据进入索引前 `[基础必会]`

流水线：加载 → 去页眉页脚/重复 → 统一编码 → 保留结构 → 切分 → 元数据 → Embedding → Upsert → 删除旧版本。

元数据至少含：`document_id/chunk_id/source/title/section/version/updated_at/tenant_id/acl`。检索权限应在数据库过滤，不是在回答后隐藏。

切分评估不要只看字符数。抽取 20 个真实问题，检查答案所需事实是否位于完整 Chunk，标题和列表是否被切断，Chunk 是否包含太多不同主题。递归字符切分是默认起点；代码、Markdown、表格、问答对要用结构感知策略。

索引更新使用内容哈希识别变化；同一文档新版本写入后删除旧 Chunk。Embedding 模型或维度变化需要新索引版本，不能混放。

## 2. 检索组合 `[最小实验]`

- **关键词/BM25/jieba**：专有名词、订单号、精确短语强。
- **向量检索**：同义表达和语义问题强。
- **混合检索**：分别召回，使用 RRF 或归一分数融合。
- **Rerank**：对少量候选做更精细的 query-doc 相关性排序。
- **上下文压缩**：从命中文档提取与问题有关片段，降低噪声和 Token。

RRF 示例：`score(d) = Σ 1 / (k + rank_i(d))`。它不要求不同检索器分数同尺度，适合作为稳健起点。

诊断指标分开看：Recall@K 测召回，MRR/NDCG 测排序，Groundedness/引用准确率测回答。最终答案错时，先确认正确 Chunk 是否召回，再看 Rerank 和 Prompt。

## 3. CRAG 主线 `[最小实验]`

```text
检索 → 评估相关性
  高：直接 Rerank 后回答
  中：改写查询/补检索
  低：搜索或明确无结果
```

相关性评估可用规则、Reranker 或结构化 LLM。设置最多一次改写，防止循环。回答必须只用最终选中的上下文。

Self-RAG 更强调模型决定是否检索并自我批评，灵活但延迟和评测复杂；先把 CRAG 做稳，再尝试 Self-RAG。

## 4. RAG 策略地图 `[理解选型]`

| 策略 | 解决问题 | 何时用 |
|---|---|---|
| 多查询融合 | 一个问法召回不全 | 同义表达多 |
| 问题分解 | 问题包含多个子问题 | 比较、汇总、多跳 |
| 回答回退 | 资料不足 | 所有生产 RAG |
| doc-doc | 已知一段，找相似段 | 推荐/去重/扩展 |
| 逻辑路由 | 业务规则明确 | 部门、知识库选择 |
| 语义路由 | 意图边界难写规则 | 多知识域 |
| 自查询 | 问题含时间/作者等过滤 | 元数据完整 |
| 多向量 | 同一文档有摘要/标题向量 | 长文档多视角 |
| 父文档 | 小块好召回、大块好阅读 | 上下文被切碎 |
| 递归文档树 | 不同粒度逐层定位 | 超长层级文档 |
| 上下文压缩 | 命中块仍太长 | Token 紧张 |
| CRAG | 召回质量不稳定 | 有回退渠道 |
| Self-RAG | 动态检索与反思 | 有充分评测预算 |

每次只引入一个策略，并用同一测试集对比；不要一次堆叠导致无法归因。

## 5. Tool 工程 `[项目实现]`

Tool 是受控业务 API，不是“给模型一个 Python 函数”。标准执行顺序：

```text
注册检查 → 权限 → Schema 校验 → 风险判断/审批 → 幂等缓存
→ 超时执行 → 可重试错误分类 → 结果裁剪/脱敏 → 审计
```

- 重试只用于超时、429、短暂 5xx；参数/权限/业务拒绝不重试。
- 写工具使用幂等键；缓存不能替代业务幂等。
- 缓存 Key 包含租户、权限、参数和数据版本，敏感结果慎存。
- 返回结构包含 `status/data/error_code/retryable`，不要把异常栈交给模型。
- 超长结果存对象存储或数据库，给模型摘要与引用 ID。
- 工具描述写“何时用、何时不用”，减少错误选择。

HTTP Tool 防 SSRF；数据库 Tool 使用参数化白名单查询；写操作最小权限并审计。

## 6. YAML 插件与 OpenAPI `[最小实验]`

YAML 只描述配置，不允许任意 Python 表达式。动态导入使用固定插件目录和允许类名单，校验版本与签名。

OpenAPI 转 Tool 时不要直接暴露整个企业 API：选择 Operation、重写面向模型的描述、限制 Host/Method/Body、注入服务端认证、收紧 Schema、裁剪响应。模型永远看不到真实密钥。

实验：选一个只读天气接口的 OpenAPI Operation，转换为 Tool Schema；用 Fake Handler 测参数，不必联网。

## 7. MCP `[项目实现]`

MCP 把外部能力标准化为：

- **Tools**：模型可请求的动作。
- **Resources**：应用可读取的上下文资源。
- **Prompts**：服务端提供的可复用提示模板。
- **Transport**：本地常见 STDIO，远端标准传输为 Streamable HTTP。

安全接入顺序：配置允许的 Server → 完成认证 → 列举能力 → 用户/管理员选择允许项 → 为工具加 `mcp_{server}_` 命名空间 → JSON Schema 再转 Pydantic → 调用仍经过内部 Tool Registry。

不要把“能发现工具”理解为“自动信任工具”。远端描述、Resource 内容和返回都不可信；限制响应大小、超时、域名、文件路径和环境变量。远端 Server 权限变化需重新授权。

Streamable HTTP 服务要验证 Origin、使用认证并在生产强制 HTTPS；本地服务优先绑定回环地址或使用 STDIO。详见 [MCP 架构](https://modelcontextprotocol.io/docs/learn/architecture)、[Transport 规范](https://modelcontextprotocol.io/specification/latest/basic/transports) 和 [安全最佳实践](https://modelcontextprotocol.io/docs/tutorials/security/security_best_practices)。

最终项目只实现受控 Adapter，不绑定具体 MCP SDK，便于课堂理解边界。

## 8. Skills `[理解选型]`

Skill 是可复用的说明、流程、脚本和资源包，告诉 Agent 在某类任务中如何工作。它与 Tool 不同：Tool 提供动作，Skill 提供操作方法和上下文组织。Skill 也要版本化、限制依赖、审查脚本权限和外部写入。

## 9. 复杂编排 `[理解选型]`

按以下顺序选择：

1. 固定 Workflow：步骤/合规要求明确。
2. 单 Agent + Tools：目标开放但领域集中。
3. Planner-Executor：计划可检查，执行步骤相对独立。
4. Supervisor：需要动态分派给多个专业 Worker。
5. Multi-Agent：上下文、权限或专业性确实需要隔离。

Subgraph 是代码/状态组织；Workflow 转 Tool 是让上层 Agent 调用一段确定流程；Multi-Agent 是多个独立决策者，成本和错误面最大。DeepAgents 是快速搭建复杂 Agent 的框架选择，先理解其规划、文件/上下文和子 Agent 抽象，再决定采用。

## 综合练习

1. 用 20 个问题建立 RAG 小测试集，标注期望来源。
2. 实现关键词 + 向量结果的 RRF 融合。
3. 加一个 Rerank 接口 Fake，并验证排序改变。
4. 实现 CRAG 的高/中/低三路。
5. 给一个 Tool 添加超时、两次重试和幂等测试。
6. 注册一个白名单 MCP Fake Tool，验证未知 Server 被拒绝。

## 常见错误

- RAG 错误先改 Prompt，却不检查召回。
- Rerank 全库，成本和延迟失控。
- OpenAPI/MCP 自动暴露全部能力。
- Tool 重试所有异常，导致重复写。
- 为展示架构而上 Multi-Agent。

## 本周验收

- [ ] 正确 Chunk 的 Recall@K 可测。
- [ ] 混合检索 + Rerank 比单路基线可比较。
- [ ] CRAG 低置信度不编造。
- [ ] Tool 参数、权限、超时、重试、幂等和结果大小受控。
- [ ] MCP 只暴露白名单且带命名空间。
- [ ] 能用一句话解释单 Agent/Workflow/Multi-Agent 选型。

代码索引：[retrieval.py](../final-code/src/agent_lab/retrieval.py)、[pgvector_store.py](../final-code/src/agent_lab/pgvector_store.py)、[tools.py](../final-code/src/agent_lab/tools.py)、[mcp.py](../final-code/src/agent_lab/mcp.py)。

## 下一周为什么自然产生

检索和工具更强后，错误也更隐蔽、风险也更大。第 3 周先建立评测、Trace、安全和数据治理，证明 Agent 可靠后再包装平台。
