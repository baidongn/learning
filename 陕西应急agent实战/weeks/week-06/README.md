# Week 6：资源调度 Agent

本周新增第三个专业 Agent。它查询模拟资源和路线 ETA，生成幂等调度建议，不调用真实调度接口，也不会编造不存在的资源。

## 快速开始

```bash
cp .env.example .env
make setup
make run
make test
make eval
```

完整演示：调用 `POST /api/agents/resource-dispatch/invoke`，事件路段使用 `QINLING-01`，资源类型使用 `ambulance` 和 `tow_truck`。重复请求的 `proposal_id` 应保持一致。

代码入口：`agents/resource_dispatch.py` 与 `tools.py`。课程正文见 `WEEK-06-COURSE.md`。
