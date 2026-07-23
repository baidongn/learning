# 开始学习

## 1. 先理解课程使用方式

这是 12 周累计式项目，不是 12 个互不相关的小 Demo。

- 每周学习 5 天。
- 每天建议 2～3 小时。
- 每周约 10～15 小时，全课程约 120～180 小时。
- 必须按 Week 1 → Week 12 顺序学习。
- 每周目录保存“截至本周的完整正式代码”，可以独立安装、运行和测试。
- 本周是在上一周正式成果上增加一层能力，不重新做一个最小项目。
- 先完成课程标注的“必做”，再考虑“选做”。

每周先读：

1. `weeks/week-XX/README.md`：了解成果、启动命令和验收方式。
2. `weeks/week-XX/WEEK-XX-COURSE.md`：从 Day 1 开始逐文件、逐命令动手完成。

不要只复制最终代码。每个 Day 都要运行当日测试、核对预期输出并完成唯一的小练习。

## 2. 本地环境

必需工具：

- Python 3.11+。
- Docker 24+ 与 Docker Compose。
- GNU Make。
- Week 10 起需要 Node.js 20.19+。
- Week 12 Kubernetes 练习需要 kubectl 与 kind。

检查：

```bash
python3 --version
docker --version
docker compose version
make --version
node --version
kubectl version --client
```

如果 Week 1～3 的依赖安装提示缺少 `uv`：

```bash
python3 -m pip install uv
```

## 3. 每周固定启动顺序

以第 1 周为例，后续只替换周编号：

```bash
cd weeks/week-01
cp .env.example .env
make setup
```

需要本地 PostgreSQL/Redis 的周，按课程执行：

```bash
make infra-up
make migrate
```

日常学习统一使用：

```bash
make run
make test
make eval
make verify
```

四条命令的含义：

| 命令 | 作用 |
|---|---|
| `make run` | 启动本周应用或最终演示栈 |
| `make test` | 运行截至本周的累计测试 |
| `make eval` | 运行本周 Agent 场景评测 |
| `make verify` | 运行构建、Compose 或部署静态验收 |

每天结束至少运行课程指定的单文件测试；Day 5 再完整运行 `make test`、`make eval`、`make verify`。

## 4. DeepSeek 的 Mock 与 Live 模式

默认 Mock 模式无需 Key、无费用、结果确定，适合学习、测试和 CI：

```dotenv
MODEL_MODE=mock
```

Live 模式调用 DeepSeek：

```dotenv
MODEL_MODE=live
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_API_KEY=your-key
DEEPSEEK_MODEL=deepseek-v4-flash
```

不要把真实 Key 提交到 Git。模型名称和接口可用性以 DeepSeek 官方文档为准。

自动验收始终使用 Mock 基线；Live 模式用于人工体验和对比，避免外部模型波动破坏课程可重复性。

## 5. 数据库和状态存储

- 主数据库：PostgreSQL。
- 向量检索：pgvector。
- LangGraph 部署状态：PostgreSQL Checkpointer。
- ORM：SQLAlchemy 2 + asyncpg。
- 迁移：Alembic。
- Redis：只用于缓存、幂等和临时状态。
- 单元测试：允许内存 Retriever 和 InMemorySaver，保持无外部依赖。

本地启动基础设施：

```bash
make infra-up
docker compose -f compose.dev.yaml ps
make migrate
```

生产部署不会把 PostgreSQL/Redis 放入应用 Pod，详见 `DEPLOY_DOCKER.md` 和 `DEPLOY_K8S.md`。

## 6. 学习中断后如何继续

1. 打开 `PROGRESS.md` 确认当前周。
2. 进入当前周课程，找到最后完成的 Day。
3. 先运行该 Day 的测试确认环境没有变化。
4. 从下一个未完成小节继续，不跳到 Supervisor 或部署周。

遇到问题按以下顺序：

```text
课程“常见错误”
  -> 本周 docs/troubleshooting.md
  -> 根目录 TROUBLESHOOTING.md
  -> 查看测试失败和 Tool Trace
```

准备好后，从 `weeks/week-01/README.md` 和 `weeks/week-01/WEEK-01-COURSE.md` 开始。
