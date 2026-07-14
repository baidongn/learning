# 安全说明

- 所有数据均为课程合成数据，不代表陕西高速实时或官方信息。
- `.env`、DeepSeek Key、真实数据库密码、生产 Kubernetes Secret 不得提交。
- 路况、气象、摄像头、资源 Tool 都是只读/无副作用模拟接口。
- 封路、发布预警、真实调度、信号控制属于高风险动作，必须经过安全复核与人工审批。
- 安全复核使用动作白名单、证据引用、30 分钟时效、注入标志和审批状态；非 PASS 不透传动作。
- Supervisor 只生成建议，`executed_actions` 固定为空；HITL 示例只记录 `simulate_traffic_control`，不连接真实系统。
- MCP/REST 输入都按不可信数据处理，错误响应不泄露堆栈或 Secret。

生产上线前仍需另行补充身份认证、RBAC、审计日志保留、网络策略、Secret Manager、限流和真实组织审批制度；这些不属于本课程范围。
