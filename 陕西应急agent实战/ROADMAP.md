# 12 周渐进路线

| 周 | 只增加这一层 | Agent 数量 |
|---|---|---:|
| 1 | PostgreSQL、pgvector、领域模型、模拟 API | 0 |
| 2 | RAG、预案专家、DeepSeek Live 适配 | 1 |
| 3 | HTTP Tool、事件研判 Agent | 2 |
| 4 | 固定双 Agent LangGraph 工作流 | 2 |
| 5 | Checkpoint、工作记忆、人工审批 | 2 |
| 6 | 资源调度 Agent | 3 |
| 7 | MCP 协议适配，不新增 Agent | 3 |
| 8 | 安全复核 Agent | 4 |
| 9 | 有界 Supervisor Agent | 5 |
| 10 | Vue 轻量指挥台 | 5 |
| 11 | 20 场景评测、熔断、Prometheus | 5 |
| 12 | Docker、Kustomize、CI、求职包装 | 5 |

通关原则：每个专业 Agent 必须先独立运行、测试和评测，再被工作流或 Supervisor 调用；Supervisor 最后开发。
