# 陕西高速路网应急指挥 Agent：课程交付说明

交付日期：2026-07-16

## 交付内容

- 12 个累计式周目录，每周保存截至当周的完整正式代码。
- 12 份手把手课程，共 21,865 行。
- 每周 5 天、每天建议 2～3 小时，总学习量约 120～180 小时。
- 每个 Day 包含目标、逐文件步骤、关键讲解、命令、预期输出、测试、一个练习和小结。
- 五个渐进 Agent：预案专家、事件研判、资源调度、安全复核、Supervisor。
- PostgreSQL、pgvector、Redis、RAG、REST/MCP Tool、LangGraph、Checkpoint、HITL。
- DeepSeek `MODEL_MODE=mock|live` 双模式，Mock 无 Key 可运行。
- Vue 轻量指挥台、20 场景评测、断路器、Prometheus 指标。
- Docker Compose、Kustomize `base + dev + prod`、CI 和求职文档。

## 已完成验证

- 12/12 周目录结构验证通过。
- 12/12 份课程质量门禁通过。
- 所有 Markdown 代码围栏配对。
- 课程未发现 TODO、伪省略实现或“请自行补全”。
- 12 周累计后端回归全部通过，共执行 597 条测试记录。
- 最终 20 条 Supervisor 场景通过：
  - 结构化输出合法率：1.0。
  - Tool 选择正确率：1.0。
  - 核心场景成功率：1.0。
  - 未审批动作率：0.0。
- Docker Compose demo 配置静态校验通过。
- Kustomize dev/prod 均可成功渲染。
- 最终压缩包执行 `unzip -tq` 完整性校验。

## 当前环境限制

- 当前工作区未安装 Week 10～12 的 `node_modules`，因此前端 Vitest 和 Vite build 在总回归中明确显示 `skipped`，未误报为通过。进入相应周执行 `make setup` 后可运行。
- 已完成 Docker Compose 静态配置验证；未在本次交付环境实际构建和启动四个 Docker 镜像服务。
- 已完成 dev/prod Kustomize 渲染；未在本次交付环境创建 kind 集群实际 apply。
- DeepSeek Live 需要学习者自行配置有效 API Key；自动测试和最终评测固定使用 Mock 模式。

## 使用顺序

1. 阅读根目录 `START_HERE.md`。
2. 按 Week 1 → Week 12 顺序学习。
3. 每周先读 README，再按 `WEEK-XX-COURSE.md` 的 Day 1～Day 5 动手。
4. 每周结束执行 `make test`、`make eval`、`make verify`。
5. 第 12 周按照 `DEPLOY_DOCKER.md` 和 `DEPLOY_K8S.md` 完成部署演练。

## 文件

- 完整课程压缩包：`shaanxi-highway-agent-course.zip`。
- 课程重构设计：`COURSE_REWRITE_DESIGN.md`。
- 课程重构执行计划：`COURSE_REWRITE_PLAN.md`。
