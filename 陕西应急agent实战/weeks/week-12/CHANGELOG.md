# Week 12 更新

- 新增后端/前端多阶段 Dockerfile 和完整本地 Compose。
- 新增 Kustomize base、dev 本地依赖和 prod 外部依赖 overlay。
- 新增 CI、部署静态测试和最终项目包装。
- 部署启用 PostgreSQL Checkpointer 与启动前迁移，dev overlay 统一使用 `highway-agent` 命名空间。
- 最终评测真实执行 Supervisor，Mock 基线四项指标为 100% / 100% / 100% / 0%。
- 最终累计后端测试全量通过，具体数量以 `make test` 输出为准。
