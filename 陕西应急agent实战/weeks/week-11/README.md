# Week 11：评测、可靠性与安全

本周不增加业务功能，把课程验收标准变成代码：结构化输出、Tool 选择、场景成功率、未审批执行率；同时加入 Tool 熔断和 Prometheus 指标。

## 快速开始

```bash
cp .env.example .env
make setup
make test
make eval
make verify
```

启动 API 后访问 `/metrics` 查看 Supervisor 状态计数。真实场景 runner：`evals/run.py`；指标入口：`backend/src/highway_agent/evaluation.py`；可靠性入口：`backend/src/highway_agent/reliability.py`。课程正文见 `WEEK-11-COURSE.md`。
