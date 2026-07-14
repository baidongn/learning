# 秦路智调：陕西高速路网应急指挥 Agent

一个面向 AI 应用 / Agent 工程师求职的 12 周实战课程。项目只使用明确标注的课程合成数据，循序实现预案专家、事件研判、资源调度、安全复核和 Supervisor 五个 Agent。

## 从这里开始

- [环境与学习方法](START_HERE.md)
- [12 周路线](ROADMAP.md)
- [总体架构](ARCHITECTURE.md)
- [技术说明](TECHNICAL_OVERVIEW.md)
- [进度勾选表](PROGRESS.md)
- [术语表](GLOSSARY.md)

## 每周课程

| 周 | 主题 | 课程入口 |
|---|---|---|
| 1 | PostgreSQL、pgvector、领域模型、模拟 API | [Week 1](weeks/week-01/README.md) |
| 2 | RAG、预案专家、DeepSeek Live 适配 | [Week 2](weeks/week-02/README.md) |
| 3 | HTTP Tool、事件研判 Agent | [Week 3](weeks/week-03/README.md) |
| 4 | 双 Agent LangGraph | [Week 4](weeks/week-04/README.md) |
| 5 | Checkpoint、记忆、HITL | [Week 5](weeks/week-05/README.md) |
| 6 | 资源调度 Agent | [Week 6](weeks/week-06/README.md) |
| 7 | MCP 工具服务 | [Week 7](weeks/week-07/README.md) |
| 8 | 安全复核 Agent | [Week 8](weeks/week-08/README.md) |
| 9 | Supervisor Agent | [Week 9](weeks/week-09/README.md) |
| 10 | Vue 轻量指挥台 | [Week 10](weeks/week-10/README.md) |
| 11 | 评测、可靠性、安全 | [Week 11](weeks/week-11/README.md) |
| 12 | Docker、Kubernetes、求职交付 | [Week 12](weeks/week-12/README.md) |

## 核心保证

- 每周目录保存截至当周的完整代码，可单独学习。
- 默认 `MODEL_MODE=mock`，无需模型 Key；`live` 的预案专家使用 DeepSeek。
- PostgreSQL + pgvector 提供业务/向量数据结构，部署模式使用 PostgreSQL Checkpointer；Mock 测试使用内存 Retriever/Saver，避免依赖外部服务。
- Redis 只作为缓存、幂等和临时状态基础设施，不充当主数据库。
- 未审批高风险动作执行率为 0；项目不连接真实高速控制系统。

进入任意周目录后统一使用 `make run`、`make test`、`make eval`、`make verify`。完整容器交付位于 Week 12。
