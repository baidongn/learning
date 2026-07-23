# 第 12 周：Docker、Kubernetes、CI 与求职项目包装

> 学习方式：5 天，每天 2～3 小时。继承第 11 周已通过测试、评测、可靠性和安全门禁的完整项目。
>
> 本周终点：制作锁定版本的后端和前端镜像；用 Docker Compose 一条命令启动完整演示环境；用 Kustomize 维护 base、dev、prod；在生产 overlay 中使用独立 Alembic Job；用 CI 验证测试、前端构建、Compose 和 Kubernetes 清单；完成可用于求职演示的交付包。

## 1. 本周学习地图与最终交付成果

前 11 周解决的是应用本身：

```text
领域模型
  -> RAG
  -> Tool
  -> 5 个 Agent
  -> LangGraph
  -> Checkpoint/HITL
  -> MCP
  -> Vue 指挥台
  -> 评测、断路器、指标
```

第 12 周解决的是如何交给别人运行：

```text
源代码
  -> Docker 镜像
  -> Compose 本地完整栈
  -> Kustomize 多环境清单
  -> CI 自动验证
  -> README / 部署文档 / 演示脚本
```

最终提供两套部署方式：

```text
Docker Compose
  - 面向学习、面试演示、单机部署
  - 一条命令启动 PostgreSQL、Redis、API、Web
  - 默认 Mock，无 DeepSeek Key 也能演示

Kubernetes + Kustomize
  - base：公共 API/Web 资源
  - overlays/dev：增加本地 PostgreSQL/Redis
  - overlays/prod：外部 PostgreSQL/Redis、Live DeepSeek、多副本、独立迁移 Job
```

五天安排：

| Day | 核心内容 | 当天成果 |
|---|---|---|
| Day 1 | 后端 Docker 镜像 | FastAPI/Alembic 进入固定版本镜像 |
| Day 2 | Vue 多阶段镜像与 Nginx | 静态站点和 API 反向代理可运行 |
| Day 3 | Compose 演示栈与生产差异 | 一条命令启动四服务完整环境 |
| Day 4 | Kustomize base/dev/prod | 两套环境可渲染，生产独立迁移 |
| Day 5 | CI、全量验收与求职包装 | 项目形成最终交付包 |

本周必做：

- 所有基础镜像锁定版本，不使用 `latest`。
- 后端镜像包含应用和 Alembic 迁移。
- 前端镜像使用 Node 构建阶段和 Nginx 运行阶段。
- Nginx 代理 `/api`、`/health`、`/metrics`、`/docs`。
- `compose.demo.yaml` 包含 PostgreSQL、Redis、API、Web。
- API 等待数据库和 Redis 健康。
- `compose.prod.yaml` 默认使用外部 PostgreSQL/Redis。
- Kustomize 采用 `base + overlays/dev + overlays/prod`。
- 生产 API 为 3 副本，Web 为 2 副本。
- 生产迁移使用独立 Job，不由多个 API Pod 并发执行。
- CI 验证后端、前端、Compose 和 Kustomize。
- `make test`、`make eval`、`make verify`。

本周选做：

- 把镜像推送到自己的 GHCR。
- 在 kind 上做完整本地部署。
- 为 Web 增加 Ingress 和 TLS。
- 给 Prometheus 添加 ServiceMonitor。

明确不做：

- 不搭建完整云厂商基础设施。
- 不在仓库中保存真实 DeepSeek Key。
- 不把生产数据库放进生产 K8s overlay。
- 不加入认证、计费、复杂运维平台。
- 不用 `latest` 作为镜像标签。

## 2. 前置知识、环境准备和安全边界

先验收第 11 周：

```bash
cd weeks/week-11
make test
make eval
make verify
```

进入第 12 周：

```bash
cd ../week-12
cp .env.example .env
make setup
```

检查本机工具：

```bash
python3 --version
node --version
npm --version
docker --version
docker compose version
kubectl version --client
```

课程锁定的主要版本：

```text
Python 基础镜像：python:3.11.11-slim-bookworm
Node 构建镜像：node:22.14.0-alpine3.21
Nginx：nginx:1.27.4-alpine
PostgreSQL/pgvector：pgvector/pgvector:0.8.1-pg17
Redis：redis:7.4.2-alpine
应用镜像版本：0.12.0
```

为什么不用 `latest`？

- 同一个 Dockerfile 在不同日期可能得到不同基础环境。
- 上游大版本变化可能破坏依赖。
- CI 成功的镜像无法被精确重现。
- 出现事故时无法判断运行的是哪个版本。

版本标签也不是绝对不可变。真正生产环境还可以锁定镜像 digest；课程先做到明确版本，保持学习复杂度可控。

本周安全边界：

```text
.env.example        -> 只放示例和空 Key，可以提交
.env                -> 本机真实配置，不提交
Kustomize literals  -> 课程演示占位符，上线前必须替换
CI                  -> 不需要 DeepSeek Key，使用 Mock 基线
prod                -> 明确要求外部 PostgreSQL、Redis 和 DeepSeek Key
```

## 3. 最终部署架构、目录与环境差异

完整 Compose 架构：

```text
Browser :8080
  -> Nginx web :80
       ├── /              -> Vue dist
       ├── /api/*         -> api:8000
       ├── /health        -> api:8000/health
       ├── /metrics       -> api:8000/metrics
       └── /docs          -> api:8000/docs

api:8000
  ├── postgres:5432
  ├── redis:6379
  └── DeepSeek API（仅 MODEL_MODE=live）
```

Kubernetes 架构：

```text
base
├── Namespace
├── ConfigMap / generated Secret
├── API Deployment + Service
└── Web Deployment + Service

overlays/dev
├── base
├── PostgreSQL Deployment + Service
└── Redis Deployment + Service

overlays/prod
├── base
├── API replicas=3
├── Web replicas=2
├── MODEL_MODE=live
├── 外部 PostgreSQL/Redis Secret
├── 镜像替换为 GHCR
├── 移除 API initContainer
└── 独立 Alembic migration Job
```

最终新增目录：

```text
weeks/week-12/
├── backend/Dockerfile
├── frontend/
│   ├── Dockerfile
│   └── nginx.conf
├── compose.demo.yaml
├── compose.dev.yaml
├── compose.prod.yaml
├── deploy/k8s/
│   ├── base/
│   └── overlays/
│       ├── dev/
│       └── prod/
├── .github/workflows/ci.yml
├── .dockerignore
├── docs/acceptance.md
└── Makefile
```

三种运行环境不要混淆：

| 环境 | 数据库/Redis | 模型 | 目标 |
|---|---|---|---|
| 本机源码 | Compose dev 可选 | mock/live | 开发调试 |
| Compose demo | 容器内置 | 默认 mock | 一键演示 |
| Kubernetes dev | overlay 内置 | mock | kind 学习 |
| Compose/K8s prod | 外部托管 | live | 生产结构示范 |

## 4. Day 1：制作后端 FastAPI 与 Alembic 镜像

### 今天目标

1. 理解 Docker build context 和 Dockerfile 路径。
2. 创建锁定 Python 版本的后端镜像。
3. 利用依赖层构建缓存。
4. 把 Alembic 配置和迁移脚本放入镜像。
5. 使用 exec 形式启动 Uvicorn。
6. 创建 `.dockerignore` 缩小构建上下文。
7. 构建并检查后端镜像。

今天只做后端镜像，不启动数据库和前端。

### 4.1 先理解构建上下文

最终 Compose 使用：

```yaml
build:
  context: .
  dockerfile: backend/Dockerfile
```

这表示：

```text
构建上下文 = weeks/week-12
Dockerfile  = weeks/week-12/backend/Dockerfile
```

因此 Dockerfile 中的 COPY 路径相对于上下文根目录：

```dockerfile
COPY backend/requirements.lock.txt ./
```

不是相对于 Dockerfile 所在目录。

如果你在 `backend` 目录运行 `docker build .`，当前 Dockerfile 的 COPY 路径会找不到。课程统一从 `weeks/week-12` 执行构建。

### 4.2 创建后端 Dockerfile 基础层

新建：

```text
backend/Dockerfile
```

写入：

```dockerfile
# 固定基础镜像版本，课程和 CI 都不使用 latest。
FROM python:3.11.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:${PATH}"

WORKDIR /app
```

环境变量作用：

- `PYTHONDONTWRITEBYTECODE=1`：容器中不生成 `.pyc`。
- `PYTHONUNBUFFERED=1`：日志立即输出到 stdout，便于 Docker/K8s 收集。
- `WORKDIR /app`：后续 COPY、RUN、CMD 都以 `/app` 为工作目录。

课程镜像直接把依赖安装到镜像 Python 环境中；`PATH` 保留未来切换镜像内虚拟环境的空间，不影响当前命令。

### 4.3 先复制依赖并安装

继续写：

```dockerfile
# 先复制固定版本依赖清单以复用 Docker 构建缓存。
COPY backend/requirements.lock.txt ./
RUN python -m pip install --no-cache-dir -r requirements.lock.txt
```

不要一开始就 `COPY backend/ ./backend/`。

Docker 按层缓存：

```text
requirements.lock.txt 不变
  -> 依赖安装层可以复用
只修改 src 代码
  -> 不需要重新下载全部 Python 包
```

`--no-cache-dir` 是不保留 pip 下载缓存，减少最终镜像冗余；它与 Docker layer cache 不是同一个缓存。

### 4.4 复制迁移和应用代码

继续写：

```dockerfile
COPY backend/alembic.ini ./alembic.ini
COPY backend/alembic ./alembic
COPY backend/src ./src
```

为什么必须复制 Alembic？

Compose 和 Kubernetes 的启动/迁移命令会执行：

```bash
alembic upgrade head
```

镜像里如果只有 API 源码，没有 `alembic.ini` 和迁移目录，容器无法初始化数据库。

最终镜像目录：

```text
/app/
├── requirements.lock.txt
├── alembic.ini
├── alembic/
└── src/highway_agent/
```

### 4.5 暴露端口并设置默认命令

完成 Dockerfile：

```dockerfile
EXPOSE 8000
CMD [
  "uvicorn",
  "highway_agent.main:app",
  "--app-dir",
  "src",
  "--host",
  "0.0.0.0",
  "--port",
  "8000"
]
```

仓库实际文件为了紧凑写成一行：

```dockerfile
CMD ["uvicorn", "highway_agent.main:app", "--app-dir", "src", "--host", "0.0.0.0", "--port", "8000"]
```

两者完全相同。

为什么监听 `0.0.0.0`？

容器内监听 `127.0.0.1` 只允许容器自身访问。监听 `0.0.0.0` 才能通过容器网络和 Service 访问。

为什么用 JSON exec 形式？

- 不经过额外 Shell。
- 信号直接发送给 Uvicorn。
- 容器停止和 Kubernetes 优雅终止更可靠。

### 4.6 创建 .dockerignore

在周目录根部新建：

```text
.dockerignore
```

写入：

```text
.git
.venv
**/__pycache__
**/.pytest_cache
**/node_modules
**/dist
work
```

这些内容不应该进入 build context：

- Git 历史。
- 本机虚拟环境。
- Python 缓存。
- 测试缓存。
- 本机 Node 依赖。
- 旧的前端构建产物。
- 临时工作目录。

不要忽略 `backend/alembic`、`frontend/src` 或 `data`，它们是有效源文件。

### 4.7 构建后端镜像

在 `weeks/week-12` 执行：

```bash
docker build \
  -f backend/Dockerfile \
  -t shaanxi-highway-agent-api:0.12.0 \
  .
```

检查镜像：

```bash
docker image inspect shaanxi-highway-agent-api:0.12.0 \
  --format '{{.Config.WorkingDir}} {{json .Config.Cmd}}'
```

预期工作目录为 `/app`，Cmd 中包含 `uvicorn` 和端口 `8000`。

### 4.8 在无数据库模式下检查镜像命令

API 默认配置可能需要 Checkpoint 初始化。为了快速验证镜像本身，运行：

```bash
docker run --rm \
  -e MODEL_MODE=mock \
  -e CHECKPOINT_BACKEND=memory \
  -p 8000:8000 \
  shaanxi-highway-agent-api:0.12.0
```

另开终端：

```bash
curl http://127.0.0.1:8000/health
```

### Day 1 预期输出

```json
{
  "status": "ok",
  "model_mode": "mock"
}
```

Docker 日志应包含类似：

```text
Uvicorn running on http://0.0.0.0:8000
GET /health 200 OK
```

停止前台容器使用 `Ctrl+C`。

### 当天小练习

只做一个练习：修改一行 Python 注释后再次执行 `docker build`。

观察：

- `COPY requirements.lock.txt` 和 pip 安装层是否显示缓存命中。
- `COPY backend/src` 之后的层是否重新执行。

用自己的话解释为什么“先复制依赖清单”能加速日常构建。

### 今日小结

今天完成了可独立运行的后端镜像：

- Python 版本固定。
- 依赖来自锁定清单。
- 源码和迁移均在镜像中。
- 日志无缓冲。
- Uvicorn 正确监听容器网络。
- build context 排除了本机垃圾文件。

## 5. Day 2：制作 Vue 多阶段镜像与 Nginx 反向代理

### 今天目标

1. 理解前端为什么使用多阶段构建。
2. 用固定 Node 版本构建 Vue。
3. 用固定 Nginx 版本运行静态资源。
4. 配置 `/api` 反向代理。
5. 代理 `/health`、`/metrics`、`/docs`。
6. 配置 Vue History fallback。
7. 构建并检查 Web 镜像。

最终浏览器只访问 Web 容器的 8080 端口，不直接暴露 API 端口。

### 5.1 为什么前端要两阶段

Vue 项目运行 `npm run build` 后，浏览器真正需要的是：

```text
dist/index.html
dist/assets/*.js
dist/assets/*.css
```

生产运行阶段不需要：

- Node.js。
- npm。
- Vite 开发服务器。
- 源码编译工具。
- 测试依赖。

因此：

```text
build stage：Node + npm + 源码 -> dist
runtime stage：Nginx + dist
```

最终镜像只保留运行所需内容。

### 5.2 创建 Node 构建阶段

新建：

```text
frontend/Dockerfile
```

写入：

```dockerfile
# 第一阶段使用固定 Node.js 版本构建 Vue 静态资源。
FROM node:22.14.0-alpine3.21 AS build

WORKDIR /web
COPY frontend/package.json ./

# package.json 已锁定直接依赖版本；联网安装后会生成 package-lock.json。
RUN npm install --ignore-scripts

COPY frontend/ ./
RUN npm run build
```

`--ignore-scripts` 禁止依赖安装阶段执行包的生命周期脚本，缩小供应链攻击面。Vite 构建仍在下一条明确命令中执行。

更严格的真实生产项目建议提交 `package-lock.json` 并使用 `npm ci`。当前课程用固定直接依赖版本和 `npm install` 保持快照结构简单；这是可以继续完善的工程点，不影响镜像版本锁定要求。

### 5.3 创建 Nginx 运行阶段

继续写：

```dockerfile
# 第二阶段只保留 Nginx 与构建产物。
FROM nginx:1.27.4-alpine

COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /web/dist /usr/share/nginx/html

EXPOSE 80
```

关键语句：

```dockerfile
COPY --from=build /web/dist /usr/share/nginx/html
```

它从名为 `build` 的前一阶段复制产物，Node 依赖不会进入最终 Nginx 镜像。

### 5.4 创建 Nginx Server 基础配置

新建：

```text
frontend/nginx.conf
```

写入：

```nginx
server {
    listen 80;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;
```

`server_name _` 是课程容器内的兜底主机名配置。真正生产域名和 TLS 通常由 Ingress、负载均衡器或外层网关处理。

### 5.5 代理 API

继续写：

```nginx
    location /api/ {
        proxy_pass http://api:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
```

`api` 不是公网域名，而是 Compose/Kubernetes Service 名称。

请求示例：

```text
浏览器请求 /api/agents/supervisor/invoke
  -> Nginx proxy_pass http://api:8000
  -> FastAPI 收到 /api/agents/supervisor/invoke
```

`proxy_pass` 这里没有尾部 `/`，因此保留完整 URI。

### 5.6 代理运维和文档端点

继续写：

```nginx
    location /metrics {
        proxy_pass http://api:8000/metrics;
    }

    location = /health {
        proxy_pass http://api:8000/health;
    }

    location /docs {
        proxy_pass http://api:8000/docs;
    }

    location = /openapi.json {
        proxy_pass http://api:8000/openapi.json;
    }
```

`/docs` 页面会继续请求 `/openapi.json`，所以两个路径都要代理。

生产环境是否允许公网访问 `/metrics` 和 `/docs` 要由网关权限策略决定。课程为本地演示保留，不能直接等同于生产安全策略。

### 5.7 配置 SPA fallback

完成配置：

```nginx
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

作用：

```text
请求真实文件 /assets/app.js -> 返回文件
请求前端路由 /incidents/123 -> 找不到静态文件 -> 返回 index.html
```

没有 fallback 时，刷新 Vue 前端路由可能得到 Nginx 404。

### 5.8 构建 Web 镜像

在周目录执行：

```bash
docker build \
  -f frontend/Dockerfile \
  -t shaanxi-highway-agent-web:0.12.0 \
  .
```

检查阶段和标签：

```bash
docker image inspect shaanxi-highway-agent-web:0.12.0 \
  --format '{{json .Config.ExposedPorts}}'
```

### 5.9 单独运行 Web 时理解依赖限制

可以检查静态页面：

```bash
docker run --rm -p 8080:80 shaanxi-highway-agent-web:0.12.0
```

打开：

```text
http://localhost:8080
```

页面静态资源能够加载，但提交事件会失败，因为当前容器网络中没有名为 `api` 的服务。这是预期现象，Day 3 用 Compose 解决服务发现。

### Day 2 预期输出

构建日志末尾应包含 Vite 成功信息，运行后：

```bash
curl -I http://127.0.0.1:8080/
```

预期：

```text
HTTP/1.1 200 OK
Server: nginx/1.27.4
Content-Type: text/html
```

### 当天小练习

只做一个练习：在浏览器直接访问一个不存在的前端路径，例如：

```text
http://localhost:8080/demo-route
```

使用 `curl -I` 确认仍返回 200 和 HTML。然后临时注释 `try_files` 重新构建，对比 404；练习结束后恢复正式配置。

### 今日小结

今天完成了前端生产镜像：

- Node 只负责构建。
- Nginx 只负责运行。
- 基础镜像均有固定版本。
- Vue 静态资源不依赖 Vite dev server。
- `/api` 与运维端点反向代理到 API。
- SPA 路由刷新有 fallback。

## 6. Day 3：用 Docker Compose 组装完整演示栈与生产结构

### 今天目标

1. 创建一条命令启动的四服务演示栈。
2. 配置 PostgreSQL/pgvector 持久化和健康检查。
3. 配置 Redis AOF 和健康检查。
4. 让 API 等待依赖健康并执行 Alembic。
5. 让 Web 等待 API 健康。
6. 理解 demo、dev、prod Compose 的职责差异。
7. 完成浏览器端到端演示。

今天开始把两个镜像和两个基础设施服务连接起来。

### 6.1 创建完整演示 Compose

新建：

```text
compose.demo.yaml
```

先写项目名和 PostgreSQL：

```yaml
name: shaanxi-highway-agent-demo

services:
  postgres:
    image: pgvector/pgvector:0.8.1-pg17
    environment:
      POSTGRES_DB: highway_agent
      POSTGRES_USER: highway
      POSTGRES_PASSWORD: highway
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U highway -d highway_agent"]
      interval: 5s
      timeout: 3s
      retries: 20
```

演示数据库使用明确的本地账号密码，只用于开发机器。生产环境绝不能复制这组凭据。

使用 pgvector 镜像，是因为第 1～2 周数据库迁移需要 `vector` 扩展。

### 6.2 加入 Redis

继续写：

```yaml
  redis:
    image: redis:7.4.2-alpine
    command: ["redis-server", "--appendonly", "yes"]
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 20
```

Redis 在本项目只用于缓存、幂等和临时状态，不替代 PostgreSQL 主数据和 LangGraph PostgreSQL Checkpointer。

AOF 让演示容器重启后保留 Redis 写入；`make reset` 会删除卷，彻底清空。

### 6.3 加入 API 服务

继续写：

```yaml
  api:
    image: shaanxi-highway-agent-api:0.12.0
    build:
      context: .
      dockerfile: backend/Dockerfile
    environment:
      MODEL_MODE: ${MODEL_MODE:-mock}
      CHECKPOINT_BACKEND: postgres
      DATABASE_URL: postgresql+asyncpg://highway:highway@postgres:5432/highway_agent
      REDIS_URL: redis://redis:6379/0
      DEEPSEEK_BASE_URL: https://api.deepseek.com
      DEEPSEEK_API_KEY: ${DEEPSEEK_API_KEY:-}
      DEEPSEEK_MODEL: ${DEEPSEEK_MODEL:-deepseek-v4-flash}
```

Compose 内部服务通过服务名访问：

```text
postgres -> PostgreSQL 容器 DNS
redis    -> Redis 容器 DNS
```

不能在 API 容器中使用 `localhost:5432`。容器内 `localhost` 指 API 容器自身。

### 6.4 启动前迁移并等待依赖

继续写 API：

```yaml
    command:
      - /bin/sh
      - -c
      - alembic upgrade head && exec uvicorn highway_agent.main:app --app-dir src --host 0.0.0.0 --port 8000
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"]
      interval: 10s
      timeout: 3s
      retries: 12
```

启动顺序：

```text
PostgreSQL/Redis 容器启动
  -> 两者 healthcheck 通过
  -> API 执行 alembic upgrade head
  -> 迁移成功后 exec Uvicorn
  -> API /health 通过
```

`exec uvicorn` 用 Uvicorn 替换 Shell 进程，使终止信号正确到达应用。

### 6.5 加入 Web 和数据卷

继续完成：

```yaml
  web:
    image: shaanxi-highway-agent-web:0.12.0
    build:
      context: .
      dockerfile: frontend/Dockerfile
    ports:
      - "8080:80"
    depends_on:
      api:
        condition: service_healthy

volumes:
  postgres_data:
  redis_data:
```

只把 Web 的 8080 暴露到宿主机：

```text
用户 -> localhost:8080 -> Web -> API
```

PostgreSQL、Redis、API 只在 Compose 内部网络可见，减少演示环境暴露面。

### 6.6 更新 Makefile 的一键命令

确认：

```make
infra-up:
	$(COMPOSE) -f compose.demo.yaml up -d --build

infra-down:
	$(COMPOSE) -f compose.demo.yaml down

run: infra-up

reset:
	$(COMPOSE) -f compose.demo.yaml down -v
```

区别：

```text
make infra-down -> 停止并删除容器/网络，保留数据卷
make reset      -> 连数据卷一起删除，数据库回到空状态
```

不要在还有学习数据时随意执行 `make reset`。

### 6.7 启动并观察服务状态

运行：

```bash
cp .env.example .env
make run
```

查看：

```bash
docker compose -f compose.demo.yaml ps
docker compose -f compose.demo.yaml logs api
```

打开：

```text
指挥台：http://localhost:8080
健康检查：http://localhost:8080/health
API 文档：http://localhost:8080/docs
指标：http://localhost:8080/metrics
```

使用页面默认案例提交，预期进入 `awaiting_approval`，页面显示各 Agent 轨迹且自动执行数为 0。

### 6.8 创建生产 Compose

新建：

```text
compose.prod.yaml
```

核心原则：生产 Compose 不启动数据库和 Redis。

写入：

```yaml
name: shaanxi-highway-agent-prod

# 生产 Compose 不启动数据库和 Redis，必须注入外部托管服务地址。
services:
  api:
    image: ${API_IMAGE:-shaanxi-highway-agent-api:0.12.0}
    build:
      context: .
      dockerfile: backend/Dockerfile
    restart: unless-stopped
    environment:
      MODEL_MODE: ${MODEL_MODE:-live}
      CHECKPOINT_BACKEND: postgres
      DATABASE_URL: ${DATABASE_URL:?请设置外部 PostgreSQL 地址}
      REDIS_URL: ${REDIS_URL:?请设置外部 Redis 地址}
      DEEPSEEK_BASE_URL: ${DEEPSEEK_BASE_URL:-https://api.deepseek.com}
      DEEPSEEK_API_KEY: ${DEEPSEEK_API_KEY:?请设置 DeepSeek API Key}
      DEEPSEEK_MODEL: ${DEEPSEEK_MODEL:-deepseek-v4-flash}
    command:
      - /bin/sh
      - -c
      - alembic upgrade head && exec uvicorn highway_agent.main:app --app-dir src --host 0.0.0.0 --port 8000

  web:
    image: ${WEB_IMAGE:-shaanxi-highway-agent-web:0.12.0}
    build:
      context: .
      dockerfile: frontend/Dockerfile
    restart: unless-stopped
    ports:
      - "8080:80"
    depends_on:
      - api
```

`${VARIABLE:?提示}` 表示变量缺失时 Compose 立即失败，避免误连本地默认地址。

单机生产 Compose 仍由一个 API 实例执行迁移；Kubernetes 多副本场景将在 Day 4 改用独立 Job。

### 6.9 理解 compose.dev.yaml 的用途

仓库还保留：

```text
compose.dev.yaml
```

它只启动 PostgreSQL 和 Redis，并把端口暴露给宿主机：

```text
源码 Uvicorn/Vite 在宿主机运行
数据库/Redis 在 Docker 运行
```

使用场景：

```bash
docker compose -f compose.dev.yaml up -d
make run-backend
make run-frontend
```

不要把 `compose.dev.yaml` 当最终一键演示文件；最终演示使用 `compose.demo.yaml`。

### Day 3 预期输出

`docker compose ps` 预期四个服务：

```text
postgres   running (healthy)
redis      running (healthy)
api        running (healthy)
web        running
```

健康检查：

```bash
curl http://localhost:8080/health
```

预期：

```json
{"status":"ok","model_mode":"mock"}
```

### 当天小练习

只做一个练习：执行 `make infra-down` 后重新 `make run`，观察 PostgreSQL 数据卷仍存在；再明确确认不需要数据后执行 `make reset`，观察卷被删除。

写下 `infra-down` 和 `reset` 的使用边界，避免以后误删本地数据。

### 今日小结

今天完成了三种 Compose 用途：

- demo：四服务完整一键演示。
- dev：仅基础设施，配合宿主机源码热更新。
- prod：API/Web，依赖外部 PostgreSQL/Redis 和真实 Key。

同时掌握了服务 DNS、健康依赖、迁移顺序、持久卷和环境变量必填校验。

## 7. Day 4：用 Kustomize 构建 base、dev、prod 和独立迁移 Job

### 今天目标

1. 理解 Kustomize base 与 overlay。
2. 创建公共 Namespace、ConfigMap、Secret 生成器。
3. 创建 API/Web Deployment 与 Service。
4. 在 dev overlay 增加 PostgreSQL 和 Redis。
5. 在 prod overlay 修改副本、镜像和 Live 配置。
6. 移除生产 API initContainer。
7. 用独立 Job 串行执行生产迁移。

今天先静态渲染清单，不要求已经有云集群。

### 7.1 为什么使用 Kustomize

如果复制两套完整 YAML：

```text
dev/api-deployment.yaml
prod/api-deployment.yaml
```

以后修改探针、端口、资源名时容易漏掉某一套。

Kustomize 结构：

```text
base = 公共资源
overlay = 环境差异
```

当前差异：

| 内容 | dev | prod |
|---|---|---|
| PostgreSQL/Redis | 集群内教学实例 | 外部服务 |
| MODEL_MODE | mock | live |
| API 副本 | 1 | 3 |
| Web 副本 | 1 | 2 |
| 镜像 | 本地 0.12.0 | GHCR 0.12.0 |
| 迁移 | API initContainer | 独立 Job |

### 7.2 创建 Namespace 和公共配置

创建：

```text
deploy/k8s/base/namespace.yaml
```

写入：

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: highway-agent
```

创建：

```text
deploy/k8s/base/app-config.yaml
```

写入：

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: highway-agent-config
data:
  MODEL_MODE: mock
  CHECKPOINT_BACKEND: postgres
  DEEPSEEK_BASE_URL: https://api.deepseek.com
  DEEPSEEK_MODEL: deepseek-v4-flash
```

ConfigMap 只保存非敏感配置。数据库地址、Redis 地址和 Key 放 Secret 生成器。

### 7.3 创建 API Deployment

创建：

```text
deploy/k8s/base/api-deployment.yaml
```

先写元数据和 selector：

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: highway-agent-api
spec:
  replicas: 1
  selector:
    matchLabels:
      app: highway-agent-api
  template:
    metadata:
      labels:
        app: highway-agent-api
```

`selector.matchLabels` 必须与 Pod template label 对应，否则 Deployment 无法管理自己的 Pod。

### 7.4 加入开发迁移 initContainer

继续写：

```yaml
    spec:
      # 课程使用 Alembic 的幂等 upgrade；生产可替换为独立发布 Job。
      initContainers:
        - name: migrate
          image: shaanxi-highway-agent-api:0.12.0
          command: ["alembic", "upgrade", "head"]
          envFrom:
            - configMapRef:
                name: highway-agent-config
            - secretRef:
                name: highway-agent-secrets
```

initContainer 成功退出后，主 API 容器才启动。

Base 只有 1 个 API 副本，所以教学 dev 环境不会出现多个 Pod 同时迁移的问题；prod 会明确移除它。

### 7.5 加入 API 容器、探针和资源

继续完成 Pod spec：

```yaml
      containers:
        - name: api
          image: shaanxi-highway-agent-api:0.12.0
          imagePullPolicy: IfNotPresent
          ports:
            - name: http
              containerPort: 8000
          envFrom:
            - configMapRef:
                name: highway-agent-config
            - secretRef:
                name: highway-agent-secrets
          readinessProbe:
            httpGet:
              path: /health
              port: http
            initialDelaySeconds: 5
            periodSeconds: 5
          livenessProbe:
            httpGet:
              path: /health
              port: http
            initialDelaySeconds: 15
            periodSeconds: 10
          resources:
            requests:
              cpu: 100m
              memory: 192Mi
            limits:
              cpu: 500m
              memory: 512Mi
```

探针区别：

```text
readiness 失败 -> 不接收 Service 流量
liveness 失败  -> kubelet 重启容器
```

资源 requests 用于调度，limits 限制最大资源使用。

### 7.6 创建 API Service

创建：

```text
deploy/k8s/base/api-service.yaml
```

写入：

```yaml
apiVersion: v1
kind: Service
metadata:
  name: api
spec:
  selector:
    app: highway-agent-api
  ports:
    - name: http
      port: 8000
      targetPort: http
```

Service 名称必须为 `api`，因为 Nginx 配置使用：

```nginx
proxy_pass http://api:8000;
```

命名空间内 DNS 会把 `api` 解析到 Service ClusterIP。

### 7.7 创建 Web Deployment 和 Service

创建：

```text
deploy/k8s/base/web-deployment.yaml
```

写入：

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: highway-agent-web
spec:
  replicas: 1
  selector:
    matchLabels:
      app: highway-agent-web
  template:
    metadata:
      labels:
        app: highway-agent-web
    spec:
      containers:
        - name: web
          image: shaanxi-highway-agent-web:0.12.0
          imagePullPolicy: IfNotPresent
          ports:
            - name: http
              containerPort: 80
          readinessProbe:
            httpGet:
              path: /
              port: http
            initialDelaySeconds: 3
            periodSeconds: 5
          resources:
            requests:
              cpu: 50m
              memory: 64Mi
            limits:
              cpu: 200m
              memory: 128Mi
```

创建：

```text
deploy/k8s/base/web-service.yaml
```

写入：

```yaml
apiVersion: v1
kind: Service
metadata:
  name: web
spec:
  selector:
    app: highway-agent-web
  ports:
    - name: http
      port: 80
      targetPort: http
```

课程不加入 Ingress。kind 演示时使用 `kubectl port-forward service/web 8080:80`。

### 7.8 创建 base kustomization

创建：

```text
deploy/k8s/base/kustomization.yaml
```

写入：

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
namespace: highway-agent
resources:
  - namespace.yaml
  - app-config.yaml
  - api-deployment.yaml
  - api-service.yaml
  - web-deployment.yaml
  - web-service.yaml
secretGenerator:
  - name: highway-agent-secrets
    literals:
      - DATABASE_URL=postgresql+asyncpg://highway:highway@postgres:5432/highway_agent
      - REDIS_URL=redis://redis:6379/0
      - DEEPSEEK_API_KEY=
generatorOptions:
  disableNameSuffixHash: true
```

这些 Secret literals 是教学默认值，不是安全的生产 Secret 管理方式。生产可使用 External Secrets、Sealed Secrets 或云厂商 Secret 管理器。

### 7.9 创建 dev overlay 的 PostgreSQL

创建：

```text
deploy/k8s/overlays/dev/postgres.yaml
```

写入：

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: postgres
spec:
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
        - name: postgres
          image: pgvector/pgvector:0.8.1-pg17
          env:
            - name: POSTGRES_DB
              value: highway_agent
            - name: POSTGRES_USER
              value: highway
            - name: POSTGRES_PASSWORD
              value: highway
          ports:
            - name: postgres
              containerPort: 5432
          readinessProbe:
            exec:
              command: ["pg_isready", "-U", "highway", "-d", "highway_agent"]
            initialDelaySeconds: 5
            periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: postgres
spec:
  selector:
    app: postgres
  ports:
    - name: postgres
      port: 5432
      targetPort: postgres
```

课程 dev 为轻量学习，没有增加 PVC。Pod 重建可能丢失数据；这正是它不适合生产的原因之一。

### 7.10 创建 dev overlay 的 Redis 和入口

创建：

```text
deploy/k8s/overlays/dev/redis.yaml
```

写入：

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis
spec:
  replicas: 1
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
        - name: redis
          image: redis:7.4.2-alpine
          args: ["redis-server", "--appendonly", "yes"]
          ports:
            - name: redis
              containerPort: 6379
          readinessProbe:
            exec:
              command: ["redis-cli", "ping"]
            initialDelaySeconds: 3
            periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: redis
spec:
  selector:
    app: redis
  ports:
    - name: redis
      port: 6379
      targetPort: redis
```

创建 `deploy/k8s/overlays/dev/kustomization.yaml`：

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
namespace: highway-agent
resources:
  - ../../base
  - postgres.yaml
  - redis.yaml
```

### 7.11 创建生产副本和配置 Patch

创建 `deploy/k8s/overlays/prod/prod-patch.yaml`：

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: highway-agent-api
spec:
  replicas: 3
  template:
    spec:
      containers:
        - name: api
          resources:
            requests:
              cpu: 250m
              memory: 384Mi
            limits:
              cpu: "1"
              memory: 1Gi
```

创建 `web-patch.yaml`：

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: highway-agent-web
spec:
  replicas: 2
```

创建 `config-patch.yaml`：

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: highway-agent-config
data:
  MODEL_MODE: live
```

### 7.12 创建独立迁移 Job

创建：

```text
deploy/k8s/overlays/prod/migration-job.yaml
```

写入：

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: highway-agent-migrate
spec:
  backoffLimit: 3
  template:
    metadata:
      labels:
        app: highway-agent-migrate
    spec:
      restartPolicy: Never
      containers:
        - name: migrate
          image: shaanxi-highway-agent-api:0.12.0
          command: ["alembic", "upgrade", "head"]
          envFrom:
            - configMapRef:
                name: highway-agent-config
            - secretRef:
                name: highway-agent-secrets
```

为什么不能让三个 API Pod 各自运行 initContainer migration？

```text
Pod A -> ALTER TABLE
Pod B -> 同时 ALTER TABLE
Pod C -> 同时读取/写入 alembic_version
```

即使迁移通常是幂等的，并发 DDL 仍可能锁冲突或失败。生产发布应先运行一次迁移 Job，成功后再滚动应用。

### 7.13 创建生产 kustomization

创建：

```text
deploy/k8s/overlays/prod/kustomization.yaml
```

写入：

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
namespace: highway-agent
resources:
  - ../../base
  - migration-job.yaml
patches:
  - path: prod-patch.yaml
  - path: web-patch.yaml
  - path: config-patch.yaml
  # 生产只允许独立 Job 执行一次迁移，禁止三个 API Pod 并发执行 DDL。
  - target:
      group: apps
      version: v1
      kind: Deployment
      name: highway-agent-api
    patch: |-
      - op: remove
        path: /spec/template/spec/initContainers
images:
  - name: shaanxi-highway-agent-api
    newName: ghcr.io/your-name/shaanxi-highway-agent-api
    newTag: 0.12.0
  - name: shaanxi-highway-agent-web
    newName: ghcr.io/your-name/shaanxi-highway-agent-web
    newTag: 0.12.0
secretGenerator:
  - name: highway-agent-secrets
    behavior: replace
    literals:
      - DATABASE_URL=postgresql+asyncpg://app:change-me@external-postgres.example:5432/highway_agent
      - REDIS_URL=redis://external-redis.example:6379/0
      - DEEPSEEK_API_KEY=replace-before-deploy
generatorOptions:
  disableNameSuffixHash: true
```

部署生产前必须替换：

```text
your-name
external-postgres.example
external-redis.example
change-me
replace-before-deploy
```

这些是明确占位符，不能当真实配置上线。

### 7.14 静态渲染两套清单

运行：

```bash
kubectl kustomize deploy/k8s/overlays/dev >/tmp/highway-dev.yaml
kubectl kustomize deploy/k8s/overlays/prod >/tmp/highway-prod.yaml
```

检查：

```bash
rg 'kind: Deployment|kind: Job|name: postgres|name: redis|replicas:' \
  /tmp/highway-dev.yaml /tmp/highway-prod.yaml
```

### Day 4 预期输出

dev 应包含：

```text
PostgreSQL Deployment/Service
Redis Deployment/Service
API Deployment replicas=1
Web Deployment replicas=1
```

prod 应包含：

```text
不包含 PostgreSQL/Redis Deployment
API Deployment replicas=3
Web Deployment replicas=2
Migration Job
MODEL_MODE=live
ghcr.io/...:0.12.0
API Deployment 不包含 initContainers
```

### 当天小练习

只做一个练习：渲染 prod 到临时文件，使用 `rg -n 'initContainers|kind: Job|replicas:'` 检查：

- API Deployment 没有 initContainers。
- Migration Job 存在。
- API/Web 副本数正确。

不要直接部署仍含示例 Secret 和 `your-name` 镜像路径的生产清单。

### 今日小结

今天完成了可维护的多环境 Kubernetes 结构：

- 公共资源只写一份。
- dev 自带教学数据库和 Redis。
- prod 使用外部依赖、Live 模型和多副本。
- 镜像通过 Kustomize 替换。
- 生产迁移只有一个独立 Job。
- 两套清单无需集群即可静态渲染验证。

## 8. Day 5：CI、全量验收、kind 演示与求职包装

### 今天目标

1. 创建 GitHub Actions 验证流程。
2. 增加部署文件静态测试。
3. 统一执行测试、评测和部署清单验证。
4. 在 kind 中部署 dev overlay。
5. 验证浏览器完整演示。
6. 整理求职 README 和技术材料。
7. 完成 12 周最终通关清单。

今天不新增业务功能，重点是可交付证据和项目表达。

### 8.1 创建 CI 工作流

新建：

```text
.github/workflows/ci.yml
```

写入：

```yaml
name: course-ci

on:
  push:
  pull_request:

jobs:
  verify:
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11.11"
      - name: 安装并测试后端
        run: |
          python -m pip install -r backend/requirements.lock.txt
          python -m pytest backend/tests -q
      - uses: actions/setup-node@v4
        with:
          node-version: "22.14.0"
      - name: 安装、测试并构建前端
        run: |
          cd frontend
          npm install
          npm run test:run
          npm run build
      - name: 验证 Docker Compose
        run: docker compose -f compose.demo.yaml config --quiet
      - name: 验证 Kustomize 输出
        run: |
          kubectl kustomize deploy/k8s/overlays/dev >/dev/null
          kubectl kustomize deploy/k8s/overlays/prod >/dev/null
```

这个 CI 不启动容器和集群，重点做快速静态回归。

在成熟项目中还应增加：

- `make eval`。
- Docker build。
- 镜像漏洞扫描。
- 推送带 commit SHA 的镜像。
- 在临时 kind 集群做 smoke test。

课程根目录的最终验收会补做真实评测；本周 CI 保持简洁便于学习。

### 8.2 创建部署文件静态测试

新建：

```text
backend/tests/test_deployment_files.py
```

先写公共路径：

```python
"""部署清单的静态验收测试，不要求本机已经运行 Kubernetes。"""

from pathlib import Path

import yaml


WEEK_ROOT = Path(__file__).resolve().parents[2]
```

检查镜像不使用 latest：

```python
def test_docker_images_never_use_latest_tag() -> None:
    deployment_files = [
        WEEK_ROOT / "backend" / "Dockerfile",
        WEEK_ROOT / "frontend" / "Dockerfile",
        *sorted((WEEK_ROOT / "deploy" / "k8s").rglob("*.yaml")),
    ]

    assert all(path.exists() for path in deployment_files)
    for path in deployment_files:
        assert ":latest" not in path.read_text(encoding="utf-8")
```

### 8.3 检查 Compose 服务边界

继续写：

```python
def test_demo_compose_contains_complete_local_environment() -> None:
    compose = yaml.safe_load(
        (WEEK_ROOT / "compose.demo.yaml").read_text(encoding="utf-8")
    )

    assert set(compose["services"]) == {
        "postgres",
        "redis",
        "api",
        "web",
    }
    assert (
        compose["services"]["api"]["depends_on"]["postgres"]["condition"]
        == "service_healthy"
    )
    assert compose["services"]["web"]["ports"] == ["8080:80"]


def test_production_compose_requires_external_database_and_redis() -> None:
    compose = yaml.safe_load(
        (WEEK_ROOT / "compose.prod.yaml").read_text(encoding="utf-8")
    )

    assert set(compose["services"]) == {"api", "web"}
    api_environment = compose["services"]["api"]["environment"]
    assert "DATABASE_URL" in api_environment
    assert "REDIS_URL" in api_environment
    assert "alembic upgrade head" in " ".join(
        compose["services"]["api"]["command"]
    )
```

这两个测试把“demo 完整、prod 外部依赖”的架构决策固化下来。

### 8.4 检查 Kustomize 环境边界

继续写：

```python
def test_kustomize_has_base_dev_and_prod_without_prod_databases() -> None:
    base = yaml.safe_load(
        (WEEK_ROOT / "deploy/k8s/base/kustomization.yaml").read_text(
            encoding="utf-8"
        )
    )
    dev = yaml.safe_load(
        (WEEK_ROOT / "deploy/k8s/overlays/dev/kustomization.yaml").read_text(
            encoding="utf-8"
        )
    )
    prod = yaml.safe_load(
        (WEEK_ROOT / "deploy/k8s/overlays/prod/kustomization.yaml").read_text(
            encoding="utf-8"
        )
    )

    assert "api-deployment.yaml" in base["resources"]
    assert "postgres.yaml" in dev["resources"]
    assert "redis.yaml" in dev["resources"]
    assert dev["namespace"] == "highway-agent"
    assert prod["namespace"] == "highway-agent"
    assert all(
        "postgres" not in item and "redis" not in item
        for item in prod["resources"]
    )
```

### 8.5 检查 Live 配置和单一迁移 Job

继续写：

```python
def test_production_kustomize_enables_live_model_mode() -> None:
    config_patch = yaml.safe_load(
        (WEEK_ROOT / "deploy/k8s/overlays/prod/config-patch.yaml").read_text(
            encoding="utf-8"
        )
    )

    assert config_patch["kind"] == "ConfigMap"
    assert config_patch["data"]["MODEL_MODE"] == "live"


def test_production_uses_single_migration_job_instead_of_pod_init() -> None:
    prod_source = (
        WEEK_ROOT / "deploy/k8s/overlays/prod/kustomization.yaml"
    ).read_text(encoding="utf-8")
    job = yaml.safe_load(
        (WEEK_ROOT / "deploy/k8s/overlays/prod/migration-job.yaml").read_text(
            encoding="utf-8"
        )
    )

    assert job["kind"] == "Job"
    assert "migration-job.yaml" in prod_source
    assert "/spec/template/spec/initContainers" in prod_source
    assert job["spec"]["template"]["spec"]["restartPolicy"] == "Never"
```

再检查 Alembic 运行时数据库地址：

```python
def test_alembic_uses_runtime_database_url() -> None:
    env_source = (WEEK_ROOT / "backend/alembic/env.py").read_text(
        encoding="utf-8"
    )

    assert "Settings().database_url" in env_source
    assert "config.set_main_option(" in env_source
    assert '"sqlalchemy.url"' in env_source
```

这保证迁移不会偷偷使用 `alembic.ini` 中固定的本机地址，而是读取容器环境变量。

### 8.6 运行最终三层验证

首先运行测试：

```bash
make test
```

然后真实评测：

```bash
make eval
```

最后部署静态验证和构建：

```bash
make verify
```

第 12 周 Makefile：

```make
PYTHON ?= python3
VENV ?= .venv
COMPOSE ?= docker compose
KUBECTL ?= kubectl

.PHONY: setup infra-up infra-down migrate run run-backend run-frontend test eval verify k8s-render reset

setup:
	$(PYTHON) -m venv $(VENV)
	$(VENV)/bin/python -m pip install -r backend/requirements.lock.txt
	cd frontend && npm install

infra-up:
	$(COMPOSE) -f compose.demo.yaml up -d --build

infra-down:
	$(COMPOSE) -f compose.demo.yaml down

run: infra-up

run-backend:
	$(VENV)/bin/uvicorn highway_agent.main:app --app-dir backend/src --reload

run-frontend:
	cd frontend && npm run dev

migrate:
	cd backend && ../$(VENV)/bin/alembic upgrade head

test:
	$(VENV)/bin/python -m pytest backend/tests -q
	cd frontend && npm run test:run

eval:
	PYTHONPATH=backend/src $(VENV)/bin/python evals/run.py evals/week12_cases.jsonl

k8s-render:
	$(KUBECTL) kustomize deploy/k8s/overlays/dev >/dev/null
	$(KUBECTL) kustomize deploy/k8s/overlays/prod >/dev/null

verify: test k8s-render
	$(COMPOSE) -f compose.demo.yaml config --quiet
	cd frontend && npm run build

reset:
	$(COMPOSE) -f compose.demo.yaml down -v
```

### 8.7 在 kind 中部署 dev overlay

先构建镜像：

```bash
docker build -f backend/Dockerfile \
  -t shaanxi-highway-agent-api:0.12.0 .
docker build -f frontend/Dockerfile \
  -t shaanxi-highway-agent-web:0.12.0 .
```

创建集群：

```bash
kind create cluster --name highway-agent
```

把本地镜像加载进 kind：

```bash
kind load docker-image shaanxi-highway-agent-api:0.12.0 \
  --name highway-agent
kind load docker-image shaanxi-highway-agent-web:0.12.0 \
  --name highway-agent
```

部署：

```bash
kubectl apply -k deploy/k8s/overlays/dev
kubectl -n highway-agent get pods -w
```

等待 API/Web/PostgreSQL/Redis Pod Ready。

端口转发：

```bash
kubectl -n highway-agent port-forward service/web 8080:80
```

打开：

```text
http://localhost:8080
```

演示结束：

```bash
kind delete cluster --name highway-agent
```

### 8.8 完整求职演示顺序

建议控制在 8～10 分钟：

1. 30 秒说明业务问题：陕西高速突发事件信息分散、研判与资源建议需要多系统证据。
2. 1 分钟展示架构图和五 Agent 职责。
3. 2 分钟在 Vue 指挥台提交秦岭隧道场景。
4. 1 分钟展示 Tool Trace、预案引用、调度建议和 Safety verdict。
5. 30 秒强调未审批动作数组为空。
6. 1 分钟运行 20 条 `make eval`，解释四项指标。
7. 1 分钟展示断路器测试和 `/metrics`。
8. 1 分钟展示 Compose/Kustomize 的 dev/prod 差异。
9. 30 秒说明 DeepSeek `mock|live` 双模式。

不要把全部代码从头翻一遍。面试演示要围绕：

```text
业务价值 -> 架构决策 -> 安全边界 -> 可验证证据 -> 部署能力
```

### 8.9 最终执行顺序与预期输出

源码验收：

```bash
make test
make eval
make verify
```

Compose 验收：

```bash
make run
curl http://localhost:8080/health
curl http://localhost:8080/metrics
make infra-down
```

Kustomize 验收：

```bash
make k8s-render
```

### Day 5 预期输出

最终核心结果：

```text
后端全量 pytest：通过
前端 Vitest：通过
前端 Vite build：通过
20 条场景评测：passed=true
结构化输出合法率：1.0
Tool 选择正确率：1.0
场景成功率：1.0
未审批动作率：0.0
Compose config：通过
Kustomize dev：可渲染
Kustomize prod：可渲染
Docker demo：4 个服务正常运行
kind dev overlay：Pod Ready，页面可访问
```

### 当天小练习

只做一个练习：录制或完整走一遍 8 分钟面试演示，并用下面五项自评：

- 是否在 1 分钟内说清业务问题？
- 是否说明五 Agent 不是同时随意聊天，而是受 Supervisor 编排？
- 是否展示量化评测而非口头说“效果不错”？
- 是否明确未审批不执行？
- 是否能说清 demo 与 prod 的数据库差异？

把超时或讲不清的部分记录到自己的面试笔记中，不再增加新功能。

### 今日小结

今天完成了工程交付最后一环：

- CI 能验证代码和清单。
- 部署决策有静态测试保护。
- kind 能运行 dev overlay。
- Compose 能一条命令演示。
- 评测提供量化证据。
- 项目可以按业务价值、安全与工程能力表达。

## 9. 部署常见错误与逐层排查

### 错误 1：Docker COPY 找不到文件

现象：

```text
failed to calculate checksum: /backend/requirements.lock.txt not found
```

原因：在 `backend` 目录把构建上下文设成了 `.`。

修复：回到周目录：

```bash
docker build -f backend/Dockerfile .
```

### 错误 2：API 容器连接 localhost 数据库

容器内 `localhost` 指自己。

Compose 使用：

```text
postgresql+asyncpg://...@postgres:5432/...
```

Kubernetes 使用同命名空间 Service 名 `postgres`，生产使用外部 DNS。

### 错误 3：Web 页面能打开但 API 502

排查顺序：

```bash
docker compose -f compose.demo.yaml ps
docker compose -f compose.demo.yaml logs api
docker compose -f compose.demo.yaml exec web \
  wget -qO- http://api:8000/health
```

检查 API 是否健康、服务名是否为 `api`、Nginx proxy_pass 是否正确。

### 错误 4：数据库未准备好就迁移

不要只写普通 `depends_on`。演示 Compose 使用：

```yaml
condition: service_healthy
```

并为 PostgreSQL 配置 `pg_isready`。

### 错误 5：Vite 开发代理在 Nginx 中不起作用

`vite.config.js` 只对 `npm run dev` 有效。生产 dist 由 Nginx 提供，必须在 `nginx.conf` 单独配置 `/api` 代理。

### 错误 6：刷新前端路由得到 404

检查：

```nginx
try_files $uri $uri/ /index.html;
```

### 错误 7：kind 拉不到本地镜像

kind 节点有独立容器运行时。构建后执行：

```bash
kind load docker-image IMAGE:0.12.0 --name highway-agent
```

同时 base 使用 `imagePullPolicy: IfNotPresent`。

### 错误 8：dev API initContainer 一直等待或失败

查看：

```bash
kubectl -n highway-agent describe pod POD_NAME
kubectl -n highway-agent logs POD_NAME -c migrate
kubectl -n highway-agent get pods
```

确认 PostgreSQL Ready、Secret 数据库地址正确、Alembic 能读取 `Settings().database_url`。

### 错误 9：prod 三个 Pod 同时迁移

检查 prod 渲染结果是否仍含 API `initContainers`。

正式设计必须：

- JSON Patch 移除 API initContainers。
- 只保留 `highway-agent-migrate` Job。

### 错误 10：生产仍使用示例 Secret

`replace-before-deploy` 和 `change-me` 是阻止误解的占位符，不是默认可用配置。

上线前必须接入真实 Secret 管理并轮换凭据。

### 错误 11：使用 latest 导致版本漂移

运行：

```bash
rg ':latest' backend/Dockerfile frontend/Dockerfile deploy/k8s
```

预期无输出。

### 错误 12：make verify 因本机工具缺失失败

`make verify` 需要：

- Python 依赖。
- 前端 `node_modules`。
- Docker Compose CLI。
- kubectl 的内置 Kustomize。

缺少某个工具时应明确记录环境限制，完成其他独立验证后安装缺失工具再补跑；不能把“没有运行”说成“已经通过”。

## 10. 最终完整代码、文档和部署清单

最终周目录：

```text
weeks/week-12/
├── README.md
├── WEEK-12-COURSE.md
├── CHANGELOG.md
├── backend/
│   ├── Dockerfile
│   ├── alembic.ini
│   ├── alembic/
│   ├── requirements.lock.txt
│   ├── src/highway_agent/
│   └── tests/
├── frontend/
│   ├── Dockerfile
│   ├── nginx.conf
│   ├── package.json
│   └── src/
├── mcp-servers/
├── data/
├── evals/
│   ├── run.py
│   └── week12_cases.jsonl
├── deploy/k8s/
│   ├── base/
│   │   ├── namespace.yaml
│   │   ├── app-config.yaml
│   │   ├── api-deployment.yaml
│   │   ├── api-service.yaml
│   │   ├── web-deployment.yaml
│   │   ├── web-service.yaml
│   │   └── kustomization.yaml
│   └── overlays/
│       ├── dev/
│       │   ├── postgres.yaml
│       │   ├── redis.yaml
│       │   └── kustomization.yaml
│       └── prod/
│           ├── config-patch.yaml
│           ├── migration-job.yaml
│           ├── prod-patch.yaml
│           ├── web-patch.yaml
│           └── kustomization.yaml
├── .github/workflows/ci.yml
├── .dockerignore
├── .env.example
├── compose.demo.yaml
├── compose.dev.yaml
├── compose.prod.yaml
└── Makefile
```

根目录最终技术资料应包括：

```text
README.md
START_HERE.md
ROADMAP.md
TECHNICAL_OVERVIEW.md
GLOSSARY.md
PROGRESS.md
ARCHITECTURE.md
API.md
MCP.md
EVALUATION.md
SECURITY.md
TROUBLESHOOTING.md
DEPLOY_DOCKER.md
DEPLOY_K8S.md
INTERVIEW.md
CHANGELOG.md
```

最终验收证据：

- 12 个周目录都能独立安装、启动和测试。
- 每周都有 README、课程、代码、测试、评测和变更记录。
- Mock 无 Key 可运行。
- DeepSeek Live 通过环境变量启用。
- 5 个 Agent 先独立测试再进入 Supervisor。
- 未审批高风险动作执行率为 0。
- 20 条最终场景评测通过。
- Compose 一条命令启动。
- dev/prod Kustomize 可渲染。
- 生产使用外部 PostgreSQL/Redis。
- 所有镜像都有明确版本。

## 11. 最终通关清单与面试题

课程通关前逐项确认：

- [ ] 我能从第 1 周解释数据库、pgvector 和领域模型。
- [ ] 我能解释 RAG 引用如何绑定检索证据。
- [ ] 我能解释 Tool Schema、HTTP Adapter 和 MCP 的差异。
- [ ] 我能独立运行 5 个 Agent。
- [ ] 我能说明为什么 Supervisor 最后开发。
- [ ] 我能画出 LangGraph、Checkpoint 和 HITL 流程。
- [ ] 我能解释 PASS/REVISE/BLOCK。
- [ ] 我能展示 Vue 指挥台和 Agent Trace。
- [ ] 我能解释四项评测指标。
- [ ] 我能说明断路器三状态。
- [ ] 我能读取 `/metrics`。
- [ ] 我能构建 API 和 Web 镜像。
- [ ] 我能解释 Compose 服务发现和健康依赖。
- [ ] 我能渲染 dev/prod Kustomize。
- [ ] 我能解释生产为什么使用外部 PostgreSQL/Redis。
- [ ] 我能解释多副本为什么使用独立迁移 Job。
- [ ] 我没有在仓库保存真实 DeepSeek Key。
- [ ] 所有镜像不使用 latest。
- [ ] `make test` 通过。
- [ ] `make eval` 通过。
- [ ] `make verify` 通过。
- [ ] 我能在 8～10 分钟完成项目演示。

### 面试题 1

问：你的 Docker Compose 本地演示和生产部署有什么区别？

参考回答：

本地 `compose.demo.yaml` 追求一键可运行，包含 pgvector PostgreSQL、Redis、FastAPI 和 Nginx/Vue 四个服务，默认 Mock 模式，无 DeepSeek Key 也能演示；API 等待依赖健康后先执行 Alembic，再启动 Uvicorn。生产 `compose.prod.yaml` 只保留 API 和 Web，强制从环境变量注入外部 PostgreSQL、Redis 和 DeepSeek Key，默认 Live 模式。数据库与 Redis 不和应用生命周期绑定，便于备份、高可用和独立扩容。

### 面试题 2

问：为什么 Kubernetes 生产环境不用每个 API Pod 的 initContainer 执行数据库迁移？

参考回答：

生产 API 有三个副本，如果每个 Pod 都通过 initContainer 执行 Alembic，会出现多个迁移进程并发执行 DDL、竞争锁和修改 `alembic_version` 的风险。我的 base 为单副本 dev 保留 initContainer，prod overlay 用 JSON Patch 移除它，并增加一个 `restartPolicy: Never` 的独立 migration Job。发布流程先等待 Job 成功，再滚动 API Deployment，保证迁移只有一个执行者。

### 面试题 3

问：你如何证明这个项目不是只能在你电脑上运行的 Demo？

参考回答：

项目每周保存可独立运行的累计快照，统一提供 setup、run、test、eval 和 verify。最终后端与前端都有锁定基础版本的镜像；Compose 可一条命令启动完整栈；Kustomize 有公共 base、带本地依赖的 dev 和外部依赖、多副本、独立迁移 Job 的 prod。CI 验证后端测试、前端测试与构建、Compose 配置以及 dev/prod 清单渲染。功能侧还有 20 条真实 Supervisor 场景，结构化输出、Tool 选择、场景成功和未审批动作四项指标形成发布门禁。

## 12. 12 周总结、项目表达与后续学习方向

你已经完成一条平滑递进的工程路线：

```text
Week 1  PostgreSQL、pgvector、领域模型、模拟 API
Week 2  RAG 与预案专家 Agent
Week 3  HTTP Tool 与事件研判 Agent
Week 4  双 Agent LangGraph 工作流
Week 5  Checkpoint、记忆与人工审批
Week 6  资源调度 Agent
Week 7  MCP 工具服务
Week 8  安全复核 Agent
Week 9  Supervisor Agent
Week 10 Vue 轻量指挥台
Week 11 评测、可靠性、安全与可观察性
Week 12 Docker、Kubernetes、CI 与项目包装
```

五个 Agent 的最终职责：

```text
PlanExpertAgent       -> 检索预案并给出带引用建议
IncidentAnalysisAgent -> 调用路况/天气/摄像头 Tool 完成事件研判
ResourceDispatchAgent -> 查询资源、估算路线、输出调度建议与缺口
SafetyReviewAgent     -> 检查证据、安全规则和高风险动作
SupervisorAgent       -> 有限步骤编排、聚合状态、停止或等待审批
```

最终求职项目一句话：

```text
我用 FastAPI、PostgreSQL/pgvector、LangGraph、MCP、DeepSeek 和 Vue 实现了陕西高速路网应急指挥多 Agent 系统，并通过 HITL、安全复核、量化评测、断路器、Prometheus、Docker Compose 和 Kustomize，把它从聊天 Demo 做成了可验证、可部署的工程项目。
```

后续学习只建议沿三条线选择一条，不要同时扩张：

```text
工程线：OpenTelemetry、集中日志、真实 Prometheus/Grafana、发布回滚
Agent 线：Live DeepSeek 评测、Prompt 版本管理、更丰富 Tool 错误策略
业务线：接入授权后的真实路况/气象接口、完善陕西高速预案数据
```

不要继续加入登录、计费、视频识别和复杂后台来堆功能。先把当前项目做到：

- 能从空环境按文档启动。
- 能稳定通过测试和评测。
- 能解释每个架构决策。
- 能在 10 分钟内清楚演示。
- 能回答安全、可靠性和部署追问。

最终执行：

```bash
make test
make eval
make verify
```

再分别按照根目录 `DEPLOY_DOCKER.md` 和 `DEPLOY_K8S.md` 完成部署演练。到这里，12 周主体课程结束。
