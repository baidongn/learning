# REST API

最终 Week 12 实际实现如下。

## 基础与可观测性

- `GET /health`
- `GET /metrics`
- `GET /docs`
- `GET /openapi.json`

## 模拟外部系统

- `GET /mock/roads/{road_code}/sections/{section_id}/status`
- `GET /mock/weather/warnings?section_id=...`
- `GET /mock/cameras/{camera_id}/analysis`
- `GET /mock/resources/nearby?section_id=...&resource_type=...`
- `POST /mock/routes/estimate`

## 独立 Agent

- `POST /api/agents/plan-expert/invoke`
- `POST /api/agents/incident-analysis/invoke`
- `POST /api/agents/resource-dispatch/invoke`
- `POST /api/agents/safety-review/invoke`
- `POST /api/agents/supervisor/invoke`

## 工作流与审批

- `POST /api/workflows/incident-response/run`
- `POST /api/workflows/incident-response/{thread_id}/start`
- `POST /api/workflows/incident-response/{thread_id}/resume`

Tool 错误统一为 `success/data/error_code/message/source/observed_at/trace_id`。Agent 与工作流输出使用 Pydantic Schema；完整请求示例见各周 README 与 FastAPI `/docs`。
