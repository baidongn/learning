# Week 3：HTTP Tool 与事件研判 Agent

本周增加路况、气象、摄像头三个只读 Tool，以及第二个事件研判 Agent。Tool 调用经过真实 HTTP/ASGI 边界，失败统一转换为 `ToolResult`。

## 必做

- 阅读 `tools.py` 的统一成功/失败契约。
- 调用三个模拟 API Tool。
- 验证缺失信息不会被猜测。
- 完成 `make test && make eval && make verify`。

## 选做

- 增加 `timeout` 场景及重试实验。

```bash
make setup
make run
curl -X POST http://127.0.0.1:8000/api/agents/incident-analysis/invoke \
  -H 'Content-Type: application/json' \
  -d '{"raw_text":"秦岭隧道追尾，有烟，占用两条车道，无人伤亡","road_code":"G65","section_id":"QINLING-01","camera_id":"CAM-QINLING-01"}'
```

