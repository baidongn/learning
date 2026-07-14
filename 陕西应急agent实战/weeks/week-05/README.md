# Week 5：Checkpoint、工作记忆与人工审批

本周让 LangGraph 工作流可以按 `thread_id` 暂停、保存和恢复。开发测试使用 `InMemorySaver`，生产工厂使用 PostgreSQL Checkpointer；未审批时执行动作列表必须为空。

## 快速开始

```bash
cp .env.example .env
make setup
make infra-up
make run
```

先调用 `POST /api/workflows/incident-response/{thread_id}/start`，再向同一 `thread_id` 的 `/resume` 提交 `approve/edit/reject`。运行 `make test`、`make eval`、`make verify` 完成验收。

代码入口：`workflows/approval_flow.py`、`checkpoints.py`。课程正文见 `WEEK-05-COURSE.md`。
