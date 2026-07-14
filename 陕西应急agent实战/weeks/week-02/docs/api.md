# Week 2 API

`POST /api/agents/plan-expert/invoke`

请求：`{"event_summary":"..."}`。响应包含 `status`、`summary`、`actions`、`citations`。`status` 为 `ready` 或 `insufficient_evidence`。

