# DeepSeek 企业智能客服 Agent：最终代码

这是五周课程唯一的一套最终代码。它不是完整商业平台，而是一个结构清楚、可测试、可继续扩展的生产型骨架。

## 已实现

- DeepSeek OpenAI-compatible 客户端：对话、结构化输出、流式输出、Tool Calling 结果转换、推理节点。
- Fake DeepSeek：无 Key 可运行、无费用、结果确定。
- LangGraph：RAG、工具、直接回答、安全阻断、人工审批、中断恢复和 Checkpoint。
- Tool Registry：Pydantic 参数校验、权限、超时、重试、幂等和统一结果。
- RAG：内存检索器、引用、无结果回退，以及 pgvector 生产适配示例。
- 上下文与安全：用户记忆隔离、消息裁剪、Injection 检测、PII 脱敏、执行预算。
- MCP：服务白名单、工具命名空间和 Schema 转换。
- 评测：答案关键词、引用来源和工具轨迹的确定性回归评测。
- FastAPI：聊天、SSE、当前任务取消、带发起人校验的审批恢复、知识写入、会话、健康检查和指标。
- Celery + Redis 文档处理任务、极简原生前端、Docker Compose 和 Nginx。

## 目录

```text
src/agent_lab/
├── agent.py            # LangGraph 主图与人工审批
├── api.py              # FastAPI 与 SSE
├── config.py           # 环境变量
├── context.py          # 上下文与长期记忆接口
├── deepseek.py         # 真实/Fake 模型网关
├── evaluator.py        # 答案、引用、轨迹评测
├── mcp.py              # 受控 MCP 适配
├── pgvector_store.py   # pgvector 生产检索适配
├── retrieval.py        # 内存检索与引用
├── safety.py           # 审核、PII 与预算
├── tasks.py            # Celery 文档任务
├── tools.py            # 工具注册与执行控制
└── static/index.html   # 最小聊天/来源/审批 UI
```

## 本地启动

要求 Python 3.11+ 和 uv。

```bash
cp .env.example .env
uv sync --dev
uv run pytest
uv run ruff check .
uv run uvicorn agent_lab.api:app --reload
```

打开 `http://127.0.0.1:8000`。`.env` 中不填 `DEEPSEEK_API_KEY` 即为 Fake 模式。

真实 DeepSeek：

```dotenv
DEEPSEEK_API_KEY=你的密钥
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_CHAT_MODEL=deepseek-chat
DEEPSEEK_REASONING_MODEL=deepseek-reasoner
```

`deepseek-reasoner` 仅供规划/反思实验；Agent 的 Tool Calling 主循环使用 `deepseek-chat`。

## API 快速试用

```bash
curl -s http://127.0.0.1:8000/api/v1/health

curl -s http://127.0.0.1:8000/api/v1/chat \
  -H 'Content-Type: application/json' \
  -d '{"message":"年假怎么申请","user_id":"u1","thread_id":"t1"}'

curl -s http://127.0.0.1:8000/api/v1/chat \
  -H 'Content-Type: application/json' \
  -d '{"message":"为订单1002申请退款","user_id":"u1","thread_id":"approval-1"}'

curl -s http://127.0.0.1:8000/api/v1/approve \
  -H 'Content-Type: application/json' \
  -d '{"thread_id":"approval-1","user_id":"u1","approved":true}'
```

交互式文档：`http://127.0.0.1:8000/docs`。

## Docker 启动

```bash
cp .env.example .env
docker compose --env-file .env -f deployments/docker-compose.yml up --build
```

访问 `http://127.0.0.1:8080`。Compose 包含 API、PostgreSQL/pgvector、Redis、Celery 和 Nginx。教学默认仍使用内存检索；把 `build_default_agent()` 的 Retriever 换成 `PgVectorRetriever` 即可连接数据库。

教学 Compose 固定单个 API Worker，因为 Checkpoint、审批和记忆仍是内存实现。不要直接改成多 Worker；先替换为共享 PostgreSQL/Redis 存储。

## 测试覆盖

测试覆盖结构化输出失败、未知工具、参数错误、同步/异步超时重试、幂等、RAG 无结果、错误引用、记忆隔离、单轮状态重置、循环超限、Prompt Injection、人工批准/拒绝/所有者校验、中断恢复、SSE、活动任务取消、会话与管理接口。

## 生产化前仍要做什么

- 把 `InMemorySaver`、长期记忆和取消信号换成 PostgreSQL/Redis 持久化实现。
- 用真实 Embedding 模型替换 `HashingEmbedder`；它只为离线测试提供确定性向量。
- 接入企业身份源、租户隔离、API Key 哈希存储和网关限流。
- 使用 Alembic 管理业务表，增加备份、数据保留和删除流程。
- 接入 LangSmith/OpenTelemetry、集中日志和告警。
- 对搜索、订单、物流和 MCP 使用真实服务，并为危险操作建立审批与审计。
