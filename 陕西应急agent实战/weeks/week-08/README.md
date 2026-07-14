# Week 8：安全复核 Agent

本周新增第四个专业 Agent。它使用确定性白名单与安全规则输出 `PASS / REVISE / BLOCK`，阻断提示词注入、未知动作和未审批高风险操作。

## 快速开始

```bash
cp .env.example .env
make setup
make run
make test
make eval
```

调用 `POST /api/agents/safety-review/invoke`。合规只读建议返回 PASS；缺引用或证据过期返回 REVISE；注入或未审批调度返回 BLOCK。课程正文见 `WEEK-08-COURSE.md`。
