# Week 2 架构

预案专家是单一职责组件，只能调用一个 Retriever。Mock 检索器与未来 pgvector Repository 将共享 `search(query, limit)` 语义，Agent 不关心存储实现。

