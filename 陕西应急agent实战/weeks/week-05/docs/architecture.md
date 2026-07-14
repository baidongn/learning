# Week 5 架构：Checkpoint 与人工审批

双 Agent 图在预案节点后进入 `interrupt`；开发使用 InMemorySaver，生产使用 PostgreSQL Checkpointer。
