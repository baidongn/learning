# Week 4：双 Agent LangGraph 工作流

本周把已经独立通过测试的“事件研判 Agent”和“预案专家 Agent”接入固定工作流。图只负责编排，不允许模型临时改变顺序，也不包含 Supervisor。

## 快速开始

```bash
cp .env.example .env
make setup
make run
```

另开终端执行：

```bash
make test
make eval
make verify
```

完整演示：向 `POST /api/workflows/incident-response/run` 提交秦岭隧道事件。信息完整时返回 `plan_ready`；缺少伤亡或车道信息时返回 `needs_input`。

本周代码入口：`backend/src/highway_agent/workflows/incident_response.py`。课程正文见 `WEEK-04-COURSE.md`。
