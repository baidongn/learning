# Week 2：RAG 与预案专家 Agent

本周在 Week 1 完整代码上增加第一个单工具 Agent。它只能检索课程模拟预案，并且没有证据时必须拒答。

## 必做

- 理解中文确定性 Embedding 与检索阈值。
- 调用预案专家 Agent。
- 验证引用、拒答和 DeepSeek 请求格式。
- 保持 `MODEL_MODE=mock` 完成全部测试。

## 选做

- 增加一份新的模拟预案和五条评测样本。

```bash
cp .env.example .env
make setup
make run
curl -X POST http://127.0.0.1:8000/api/agents/plan-expert/invoke \
  -H 'Content-Type: application/json' \
  -d '{"event_summary":"秦岭隧道追尾并出现烟雾"}'
make verify
```

Live 模式使用 DeepSeek `deepseek-v4-flash`；Mock 是课程验收基线。

