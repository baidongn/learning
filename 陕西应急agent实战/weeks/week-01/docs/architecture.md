# Week 1 架构

本周只有同步边界：HTTP 请求进入 FastAPI，经 Pydantic 校验后读取内存中的确定性 Fixtures。数据库通过 Alembic 建表，为后续持久化和 RAG 做准备，但模拟 API 暂不依赖数据库，降低首次运行门槛。

