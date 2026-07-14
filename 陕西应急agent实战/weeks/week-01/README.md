# Week 1：领域模型、PostgreSQL/pgvector 与模拟 API

本周不使用 LLM，先建立后续 Agent 共同依赖的稳定业务底座。

## 必做

- 定义事件、风险等级、状态、路况、气象和资源模型。
- 启动 PostgreSQL/pgvector 与 Redis。
- 执行 Alembic 初始迁移。
- 调用三个确定性模拟 API。
- 运行领域、API、数据库和环境契约测试。

## 选做

- 为模拟 API 增加一个新的路段。
- 增加一种确定性故障场景。

## 快速开始

```bash
cp .env.example .env
make setup
make infra-up
make migrate
make run
```

打开 <http://127.0.0.1:8000/docs>，测试：

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/mock/roads/G65/sections/QINLING-01/status
```

测试与验收：

```bash
make test
make eval
make verify
```

预期健康检查：

```json
{"status":"ok","model_mode":"mock"}
```

模拟数据仅用于课程，不代表陕西高速实时官方数据。

