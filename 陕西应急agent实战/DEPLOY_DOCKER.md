# Docker 部署

所有命令在 `weeks/week-12` 执行。

## 本地完整演示

```bash
cd weeks/week-12
cp .env.example .env
docker compose -f compose.demo.yaml up -d --build
docker compose -f compose.demo.yaml ps
```

浏览器访问 `http://localhost:8080`。健康检查、指标和 Swagger 分别位于：

```bash
curl http://localhost:8080/health
curl http://localhost:8080/metrics
open http://localhost:8080/docs
```

Demo 包含以下固定版本镜像：

- `pgvector/pgvector:0.8.1-pg17`
- `redis:7.4.2-alpine`
- `python:3.11.11-slim-bookworm`
- `node:22.14.0-alpine3.21`
- `nginx:1.27.4-alpine`

停止但保留数据：

```bash
docker compose -f compose.demo.yaml down
```

删除本地课程数据卷：

```bash
docker compose -f compose.demo.yaml down -v
```

## Live 模式

在 `.env` 填入 DeepSeek Key，再设置 `MODEL_MODE=live`。Compose 不把 Key 写进镜像，运行时才注入。

## 生产 Compose

`compose.prod.yaml` 只启动 API 和 Web，PostgreSQL/Redis 必须使用外部服务：

```dotenv
MODEL_MODE=live
DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@DB_HOST:5432/highway_agent
REDIS_URL=redis://REDIS_HOST:6379/0
DEEPSEEK_API_KEY=replace-me
API_IMAGE=registry.example/highway-agent-api:0.12.0
WEB_IMAGE=registry.example/highway-agent-web:0.12.0
```

```bash
docker compose --env-file .env -f compose.prod.yaml up -d
```

上线前先备份 PostgreSQL；升级时先构建新版本标签、运行测试和迁移，再替换镜像。回滚时恢复上一个明确标签，禁止使用 `latest`。
