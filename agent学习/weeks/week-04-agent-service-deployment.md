# 第 4 周：Agent 服务、最小前端与部署

**本周 6–8 小时｜稳定内核 → API → 最小 UI → Docker**

前置：Agent 内核已有测试、评测、安全和失败策略。服务层只负责协议、身份、流式传输、任务调度和运维，不重写 Agent 逻辑。

## 学习结果

- 用 FastAPI 暴露聊天、SSE、取消、审批恢复、会话、知识库和指标。
- 用 Celery + Redis 处理文档上传后的耗时流程。
- 理解 JWT、OAuth、API Key、限流和统一鉴权。
- 用原生 HTML/JavaScript 完成聊天、来源、取消和审批。
- 用 Docker Compose 启动 API、pgvector、Redis、Celery 和 Nginx。
- 能读懂 Vue/Workflow UI 的迁移方案，但不投入主线开发时间。

## 时间安排

| 阶段 | 时间 | 产物 |
|---|---:|---|
| FastAPI 与 SSE | 2h | 可调用 API |
| 鉴权、限流、异步任务 | 1.5h | 安全接口设计 |
| 最小前端 | 1h | 浏览器演示 |
| Docker 与生产清单 | 1.5h | Compose |
| 平台/前端选型与验收 | 1–2h | 迁移手册 |

## 1. API 边界 `[项目实现]`

最小 API：

```text
POST /api/v1/chat                  普通聊天
POST /api/v1/chat/stream           SSE 流式
POST /api/v1/cancel                取消信号
POST /api/v1/approve               审批恢复
GET  /api/v1/sessions/{thread_id}  会话状态
POST /api/v1/knowledge             知识写入/触发任务
GET  /api/v1/health                健康检查
GET  /api/v1/metrics               教学指标
```

Pydantic v2 请求模型限制长度和类型；响应使用稳定业务 Schema，不泄漏框架内部 State。统一错误包含 `code/message/request_id`；日志保留内部原因，用户只收到可行动信息。

CORS 本地可为 `*`，生产只允许真实来源。上传限制大小、类型和解析时间，并做恶意文件检查。

## 2. SSE `[项目实现]`

事件类型建议：`metadata/node/token/source/approval/error/done`。每个 Run 最终必须有 `done` 或 `error`；断开后取消上游任务。Nginx 对 SSE 关闭响应缓冲、延长读取超时。

前端 `fetch` 读取 POST 流，使用 `AbortController` 取消。EventSource 原生只支持 GET，不能直接替代所有聊天 POST。

Token 统计以模型 Usage 为准；流中可显示估算，结束事件给最终值。流式审核可先缓存短片段，不能把已经输出的敏感内容“撤回”。

## 3. Celery + Redis `[项目实现]`

文档上传接口快速返回 `task_id`，后台执行：下载/读取 → 清洗 → 切分 → Embedding → Upsert → 更新状态。任务带 `tenant/document/version/idempotency_key`。

超时和重试按步骤区分；解析失败不重试无限次；Embedding 批次可重试。至少一次投递意味着任务可能重复，使用唯一约束和 Upsert。Redis 同时承担 Broker、缓存和取消时，应分 Key 命名空间并设置 TTL。

## 4. 鉴权与开放 API `[最小实验]`

- JWT：短期访问令牌，服务端校验签名、过期、issuer、audience 和权限。
- GitHub OAuth：第三方身份登录；回调后仍建立自己的用户/租户会话。
- Flask-Login：理解传统服务端 Session 对照，不在 FastAPI 主线实现。
- API Key：用于系统间调用；只展示一次，存哈希，支持作用域、过期、撤销和轮换。
- 限流：按 tenant/user/key/IP 与接口成本分层；429 返回重试提示。
- 统一鉴权依赖把可信 `user_id/tenant_id/scopes` 注入 Runtime Context。

危险操作不能因为“已登录”就跳过审批。开放 API 与账号接口可共享策略，但凭证和权限范围不同。

## 5. 最小前端 `[项目实现]`

只实现：聊天记录、发送、流式/普通响应、取消、引用、审批卡片和错误状态。使用原生 HTML/CSS/JavaScript，避免为学习 Agent 引入构建链。

防 XSS：普通文本使用 `textContent`；若用 Markdown，配置 HTML 白名单和链接策略。令牌不放 URL；401 清理会话，403 显示无权限，404 显示资源不存在。按钮有加载/禁用状态，网络请求有超时与重试边界。

## 6. Vue 迁移地图 `[理解选型]`

- Node.js：前端构建运行时。
- Vue 3：组件与组合式 API。
- Pinia：跨页面状态，如身份、应用和会话。
- Router：页面路由与守卫。
- Arco Design：管理后台组件。
- TailwindCSS：原子样式；与组件库建立明确边界。
- `fetch`：请求、SSE Reader、AbortController。
- `markdown-it`：富文本；必须做安全配置。

前端优化清单：API 公共服务、超时/重试/鉴权、403/404、统一 Hooks、组件复用、骨架屏、加载态、构建分包和环境配置。主线不实现完整 Vue 项目。

## 7. Workflow UI 与最小平台 `[最小实验]`

Vue Flow 负责画布，dagre 负责自动布局；画布只是配置编辑器，后端仍需校验并编译。八类最小节点可定义为：输入、Prompt、模型、条件、知识、工具、子工作流、输出。

节点/边保存版本，草稿与已发布配置分离。Workflow 转 Tool 时冻结版本与输入输出 Schema。Prompt 历史支持比较、回滚和发布，不覆盖旧版本。

平台管理接口只需理解六个域：应用、知识库、工具、Prompt、Workflow、模型配置。统计用 ECharts 展示消息、用户、Token、费用、延迟和失败率。多应用共享内核，不复制业务代码。

## 8. 性能 `[理解选型]`

- 缓存只读且可版本化的结果。
- PostgreSQL 为 tenant/thread/document/version 等查询建索引。
- 限制模型、检索和工具并发，避免下游雪崩。
- 小模型/不同任务路由必须通过评测，课程仍只用 DeepSeek。
- Weaviate 以插件适配避免业务依赖和资源泄漏；主项目用内存/pgvector。
- 提取模型网关、工具注册、错误和响应契约，减少重复。

## 9. Docker 与生产部署 `[项目实现]`

Compose 服务：API、PostgreSQL/pgvector、Redis、Celery、Nginx。Uvicorn 提供 ASGI；Gunicorn 可在非容器/特定部署中管理多 Worker。多个 Worker 的内存 State 不共享，因此 Checkpoint、取消和幂等缓存生产必须外置。

Nginx 负责 TLS 终止、请求大小、基础限流、SSE 缓冲和代理 Header。日志使用 stdout 结构化输出。健康检查分 liveness/readiness；部署前迁移，关闭时优雅完成在途任务。

云清单 `[理解选型]`：

- 阿里云/腾讯云：网络、容器/主机、托管数据库/Redis、负载均衡、域名证书、Secret、日志监控、备份和出网策略。
- Azure/OpenAI 企业配置：资源区域、额度/并发、网络、身份、内容策略、数据合规。课程不申请额度、不绑定云厂商。
- 本地向量库：持久卷、备份、版本升级、内存/磁盘监控和数据加密。

## 综合练习

1. 用 TestClient 测聊天、SSE、审批、取消和 404 会话。
2. 为文档任务加入 `document_id + version` 幂等键。
3. 用原生前端完成一次 RAG 问答和一次退款拒绝。
4. 重启单进程服务，观察内存 Checkpoint 丢失并解释生产替换方案。
5. 启动 Compose，检查 API/数据库/Redis/Worker 健康。

## 常见错误

- API 直接返回 LangGraph 内部对象。
- 多 Worker 仍用内存会话/取消状态。
- SSE 被代理缓冲，页面最后一次性显示。
- Celery 重试写入却无幂等。
- Markdown 直接开启原始 HTML。
- 先做复杂画布，再稳定后端 Schema。

## 本周验收

- [ ] Fake 模式可通过浏览器完成聊天、引用、取消和审批。
- [ ] API 错误结构稳定，SSE 有终止事件。
- [ ] 文档耗时任务不阻塞请求。
- [ ] 身份和权限由服务端注入。
- [ ] Docker Compose 服务关系和持久卷明确。
- [ ] 能说明 Vue/Workflow UI 如何迁移，但未偏离 Agent 主线。

代码索引：[api.py](../final-code/src/agent_lab/api.py)、[static/index.html](../final-code/src/agent_lab/static/index.html)、[tasks.py](../final-code/src/agent_lab/tasks.py)、[deployments](../final-code/deployments/)。

## 下一周为什么自然产生

平台已经可访问，但业务价值来自具体场景。第 5 周不再改 Agent 内核，只替换知识、工具、工作流和交互通道，验证复用能力。
