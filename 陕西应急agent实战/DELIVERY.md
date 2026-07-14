# 陕西高速路网应急指挥 Agent：交付说明

## 交付内容

- 12 个可独立学习、安装、启动和测试的累计周快照。
- 4 个专业 Agent（预案专家、事件研判、资源调度、安全复核）与 1 个受限 Supervisor。
- 模拟 REST Tool、3 个 MCP 服务、LangGraph 工作流、Checkpoint/HITL。
- PostgreSQL/pgvector 数据结构、Alembic 迁移、Redis 配置边界。
- `MODEL_MODE=mock|live`，Live 模式使用 DeepSeek，Mock 模式无需 API Key。
- Vue 3 轻量指挥台、Prometheus 指标、Tool 熔断和安全回归。
- Docker Compose demo/prod 与 Kustomize base/dev/prod。
- 根级技术文档、课程路线、部署手册和求职面试材料。
- Python 代码注释和 docstring 以中文为主，标识符保持英文。

## 推荐入口

1. 阅读根目录 `START_HERE.md`。
2. 从 `weeks/week-01/README.md` 开始，按周完成课程正文。
3. 直接查看最终成果时进入 `weeks/week-12`。
4. 无 DeepSeek Key 时保留 `MODEL_MODE=mock`。

## 已执行验证

- 12 周目录结构和每周课程 12 节结构通过。
- 12 周累计后端测试全部通过。
- 20 条场景真实执行 Supervisor：结构化输出 100%、Tool 选择 100%、场景成功 100%、未审批动作 0%。
- Compose demo/prod 静态配置通过。
- Kustomize dev/prod 成功渲染，所有资源位于 `highway-agent` 命名空间；prod 使用唯一迁移 Job，避免多副本并发 DDL。
- Alembic 使用运行时 `DATABASE_URL` 成功生成 PostgreSQL/pgvector 离线迁移 SQL。
- 所有预期输出 SVG 通过 XML 校验；前端 JavaScript 通过 Node 语法检查。

## 当前环境未完成的运行验证

- 当前沙箱不能连接 Docker daemon，因此没有实际构建/启动镜像或创建 kind 集群。
- 当前沙箱不能下载 npm 依赖，因此没有执行 Vitest 和 Vite build；根级 CI 已配置在正常联网环境执行这些步骤。

这些限制不影响源码、课程和静态部署清单交付，但首次本地运行时仍应按 `DEPLOY_DOCKER.md` 和 `DEPLOY_K8S.md` 完成环境冒烟测试。
