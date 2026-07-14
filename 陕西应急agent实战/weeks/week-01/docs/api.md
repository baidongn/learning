# Week 1 API

- `GET /health`
- `GET /mock/roads/{road_code}/sections/{section_id}/status`
- `GET /mock/weather/warnings?section_id=...`
- `GET /mock/resources/nearby?section_id=...&resource_type=...`

Header `X-Mock-Scenario` 支持 `stale` 与 `unavailable`。所有响应都标注 `synthetic-demo-data`。

