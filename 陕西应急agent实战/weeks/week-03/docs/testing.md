# Week 3 测试

单元测试使用 `httpx.ASGITransport` 穿过真实 FastAPI 路由，不启动网络端口；故障由 `X-Mock-Scenario` 精确触发。

