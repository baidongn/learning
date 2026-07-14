# Week 9：Supervisor Agent

本周最后开发第五个 Agent——Supervisor。它按上限路由前四个专业 Agent、记录尝试、异常时最多重试一次，并把高风险建议停在人工审批前。

## 快速开始

```bash
cp .env.example .env
make setup
make run
make test
make eval
```

调用 `POST /api/agents/supervisor/invoke` 运行完整秦岭隧道案例。预期四个专业 Agent 依次完成，最终 `status=awaiting_approval` 且 `executed_actions=[]`。

代码入口：`agents/supervisor.py`。课程正文见 `WEEK-09-COURSE.md`。
