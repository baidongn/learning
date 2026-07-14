# 技术说明

## 技术栈

- Python 3.11、FastAPI、Pydantic v2。
- SQLAlchemy 2、asyncpg、Alembic。
- PostgreSQL 17、pgvector 0.8.1、Redis 7.4.2。
- LangGraph 1.x、MCP Python SDK 1.x。
- DeepSeek OpenAI-compatible Chat Completions；课程默认模型 `deepseek-v4-flash`。
- Vue 3、JavaScript、Vite、Vitest。
- Docker Compose、Kustomize、Kubernetes。

## 数据边界

PostgreSQL 是主数据库，Alembic 创建业务表、预案向量列和 pgvector 索引；部署模式使用 PostgreSQL Checkpointer 保存可恢复线程。Redis 仅用于缓存、幂等键和临时状态。为保证无 Key、无数据库也能完成每周测试，课程运行时的 Mock RAG 使用内存检索器和 16 维确定性教学向量；切换真实 Embedding/pgvector 查询属于明确的生产适配边界，不能把 Mock 基线误称为数据库向量检索实测。

## 模型边界

Mock 模式保证无 Key 可运行。Live 模式仅让 DeepSeek 基于已检索证据生成摘要和动作；检索来源、Tool 数据、权限和最终引用仍由代码控制。所有 Agent 输出都先通过 Pydantic 结构化契约。

## 工程边界

领域模型不依赖 FastAPI/LangGraph；Tool 统一返回 `ToolResult`；Agent 不直接执行真实业务动作；高风险建议必须经过安全复核和人工审批。
