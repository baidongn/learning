# 术语表

- **Agent**：基于模型、工具和状态完成目标的可执行组件。
- **Tool**：带输入输出 Schema 的外部能力。
- **RAG**：先检索证据，再让模型基于证据回答。
- **Embedding**：把文本映射为可做相似度检索的向量。
- **pgvector**：PostgreSQL 的向量类型与索引扩展。
- **LangGraph**：用于构建长运行、有状态 Agent 工作流的框架。
- **Checkpoint**：工作流每一步的持久化状态快照。
- **HITL**：Human-in-the-loop，关键动作由人批准、修改或拒绝。
- **MCP**：模型上下文协议，标准化 Tools、Resources 和 Prompts。
- **Supervisor**：选择和协调专业 Agent 的编排 Agent。
- **Trajectory**：Agent 的完整决策与工具调用轨迹。
- **Idempotency**：重复请求不会产生重复副作用。

