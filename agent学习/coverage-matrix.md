# 知识覆盖矩阵

用途：证明压缩的是学习深度和重复实现，不是知识点。来源 `O` 为原 21 周 LLMOps 大纲，来源 `D` 为 DOCX《AI Agent / LangChain / LLMOps 实战学习路线》，`N` 为本课程补充。

深度：`实现`＝最终项目或练习亲手完成；`最小实验`＝可运行片段/操作；`理解选型`＝能说明用途、边界、取舍。一个来源行含多个原编号时，深度列按编号分配。

## A. 原 21 周 LLMOps 大纲

| 来源编号 | 原知识点（保留原编号） | 手册/周次章节 | 深度 | 最终代码位置或说明 | 验收方式 |
|---|---|---|---|---|---|
| O01.1–O01.6 | 1 LLM 与场景；2 软件构建/交互影响；3 LLM/Agent 交互与术语；4 LLMOps 架构；5 平台功能/业务拆分；6 ChatGPT 辅助学习开发 | 前置 1；README；W4-7 | 1–3 实现认知；4–6 理解选型 | README 架构与代码目录 | 能区分 ChatBot/RAG/Agent/Workflow/LLMOps，并画平台边界 |
| O02.1–O02.3 | 1 Python 环境；2 后端约定规范；3 统一 API | Python 1–9、14；前置 2；W4-1 | 实现 | `pyproject.toml`、`api.py` | uv 启动，API Schema/错误稳定 |
| O02.4–O02.7 | 4 PostgreSQL/ORM；5 数据库迁移；6 PyTest/版本控制；7 Postman 调试 | Python 12、15；W3-7；W4-1 | 4–5 最小实验；6 实现；7 理解选型 | pgvector 适配、tests、OpenAPI `/docs` | 解释事务/迁移，测试通过，用 `/docs` 调接口 |
| O02.8–O02.10 | 8 首个模型聊天；9 LangChain；10 Prompt/Model/Parser/LCEL/Callback/Runnable | 前置 2–4 | 实现 | `deepseek.py`；前置最小片段 | Fake/真实冒烟，能组合一条 LCEL |
| O03.1–O03.7 | 1 Node；2 前端规范；3 API/守卫/Pinia/页面；4 Tailwind；5 三种跨域；6 API 文档/公共服务；7 UI 聊天 | W4-5、W4-6 | 1–6 理解选型；7 实现 | `static/index.html`；CORS | 浏览器完成聊天；说清 Vue 迁移组件 |
| O04.1–O04.5 | 1 State/上下文窗口/限制；2 LCEL；3 LangChain Memory；4 缓冲/摘要/实体；5 历史摘要 Prompt | 前置 4、7；W1-2 | 1–2 实现；3–5 最小实验 | `context.py` | 消息裁剪、摘要与实体记忆边界可解释 |
| O04.6–O04.9 | 6 AutoGPT/MetaGPT 记忆；7 对话/状态数据库持久化；8 Runnable 高级/源码；9 记忆链机器人 | 前置 7；W3-6/7 | 6、8 理解选型；7、9 最小实验 | Context 接口；生产替换说明 | 用户隔离、过期/删除方案；能读 Runnable 轨迹 |
| O05.1–O05.4 | 1 幻觉与策略；2 Faiss/Pinecone/TCVectorDB/Weaviate；3 Embedding；4 Loader/Splitter/递归切分 | 前置 8；W2-1 | 1、3、4 实现；2 理解选型 | `retrieval.py`、`pgvector_store.py` | 建索引并解释五类向量库取舍 |
| O05.5–O05.7 | 5 Retriever；6 jieba/关键词；7 Rerank | 前置 8；W2-2 | 实现 | 内存 Retriever；混合/Rerank 练习 | Recall@K、排序可对比 |
| O05.8 | 多查询、问题分解、回答回退、doc-doc、混合、逻辑/语义路由、自查询、多向量、父文档、递归树、Rerank、CRAG、Self-RAG | W2-3/4 | 混合+Rerank+CRAG 实现；其余最小实验/理解选型 | W2 策略表与练习 | 能按失败类型选策略，不堆叠名词 |
| O06.1–O06.4 | 1 LLM 局限；2 GPT/New Bing 联网原理；3 Agent 概念/场景；4 函数回调/结构化输出 | 前置 1、3、5；W1-10 | 实现 | `deepseek.py`、安全搜索说明 | 能解释搜索 Tool 与模型的边界 |
| O06.5–O06.9 | 5 三种自定义 Tool；6 LangChain Agent 自主选工具；7 LCEL/LangGraph 流；8 LangGraph 可观测 Agent；9 实时联网 | 前置 5/6/9；W1 | 5–8 实现；9 最小实验 | `tools.py`、`agent.py` | 工具路由、图、搜索 Fake 跑通 |
| O07.1–O07.2 | 1 YAML+Python 动态插件；2 OpenAPI Schema 接任意 API | W2-6 | 最小实验 | 受控插件/OpenAPI 转换步骤 | Fake API Tool 被校验且 Host 受限 |
| O07.3、O07.6–O07.8 | 3 零/少样本 Prompt；6 用户 Prompt 编排；7 应用/Prompt 历史；8 AI 优化 Prompt | 前置 3；W3-1/2；W4-7 | 3 实现；6–8 最小实验 | 版本/评测说明 | Prompt 改动有版本和回归比较 |
| O07.4–O07.5 | 4 知识库分割/关键词/向量/CRUD；5 Celery 耗时任务 | W2-1/2；W4-3 | 实现 | `tasks.py`、Retriever | 文档任务幂等，知识写入可检索 |
| O08.1–O08.3 | 1 长短期记忆模块/Prompt；2 流式与非流式；3 Agent 流式响应 | 前置 7；W1-8；W4-2 | 实现 | `context.py`、SSE API | 区分两种响应并完成流式事件 |
| O08.4–O08.7 | 4 队列+协程突破图流限制；5 fetch 打字机；6 Token/中断；7 联调测试 | W1-8/9；W4-2/5 | 4 理解选型；5–7 实现 | `api.py`、前端、API 测试 | SSE token/done、取消、用量设计 |
| O09.1–O09.3 | 1 JWT；2 GitHub OAuth；3 Flask-Login | W4-4 | JWT/OAuth 最小实验；Flask-Login 理解选型 | 鉴权设计说明 | 校验签名/过期/权限，能比较 Session |
| O09.4–O09.6 | 4 fetch 携令牌；5 路由守卫；6 联调测试 | W4-4/6 | 最小实验 | Vue 迁移手册 | 401/403 行为与令牌存放正确 |
| O10.1、O10.3–O10.4 | 1 厂商内置审核；3 自定义关键词审核；4 流式审核 | W3-4/5 | 1 理解选型；3–4 实现/最小实验 | `safety.py`；流式审核说明 | Injection/关键词/PII 测试 |
| O10.5–O10.6 | 5 草稿配置输入输出审核/记忆/版本回退；6 联调 | W3-5/6；W4-7 | 最小实验 | 应用版本和 Workflow 说明 | 草稿/发布分离，可回滚后回归 |
| O11.1–O11.3 | 1 开放 API 架构；2 Key 生成/授权；3 频率限制 | W4-4 | 最小实验 | API Key 哈希/Scope/限流设计 | Key 撤销、Scope 与 429 策略可说明 |
| O11.4–O11.6 | 4 开放 API 集成；5 前后端联调；6 API/账号统一鉴权 | W4-1/4 | 最小实验 | FastAPI 接口与鉴权依赖说明 | 两类凭证映射同一 Runtime Context |
| O12.1–O12.2 | 1 多应用架构；2 应用/配置历史数据库 | W4-7 | 最小实验 | 管理域/版本 Schema | 草稿、发布版本、多租户可解释 |
| O12.3–O12.5 | 3 Agent→Workflow；4 YAML→LangGraph；5 八类节点/边 | W2-9；W4-7 | 最小实验 | Workflow 编译设计 | 一个三节点 YAML 被校验/解释 |
| O12.6–O12.8 | 6 dagre 排版；7 Workflow→Tool 并关联应用；8 Vue Flow/UI | W4-7 | 最小实验/理解选型 | 画布迁移说明 | 能说明后端校验为何不能省略 |
| O13.1–O13.4 | 1 LLM/ChatModel；2 YAML 动态多模型；3 OpenAI/月之暗面/文心/通义；4 应用/工作流多模型 | 前置 2；W3-9 | 1 实现认知；2–4 理解选型 | `ModelGateway`；业务只用 DeepSeek | 能按工具兼容/延迟/合规选型 |
| O13.5、O13.7–O13.8 | 5 Hugging Face；7 多模型联调；8 自动创建 Agent | W3-9；W5-7/8 | 理解选型 | 后续路线 | 用自有评测集比较，不实现多套业务 |
| O14上.1–O14上.4 | 1 流/工作流 Token 与费用；2 统计 API；3 ECharts；4 消息/Token/用户消费统计 | W1-9；W3-3；W4-7 | 1–2 实现；3–4 最小实验 | metrics、Usage 契约 | 指标含量/价/延迟/失败率 |
| O14上.6–O14上.8 | 6 统计联调；7 WebApp/发布 URL；8 markdown-it | W4-5/6/7 | 6–7 实现/最小实验；8 理解选型 | 浏览器 UI；Markdown 安全说明 | URL 可访问；富文本防 XSS |
| O14下.1–O14下.3 | 1 前端组件复用；2 403/404/hooks/ref；3 Tailwind 公共样式 | W4-6 | 理解选型 | Vue 迁移清单 | 能列迁移目录与错误页 |
| O14下.4–O14下.7 | 4 API 超时/重试/权限；5 骨架/加载；6 Vue 优化/部署；7 前端 Docker | W4-5/6/9 | 4 实现；5–7 理解选型/最小实验 | 原生前端、Compose | 取消/错误状态；能解释构建部署 |
| O15上.1–O15上.3 | 1 Weaviate 插件/内存；2 PostgreSQL 索引；3 环境/猴子补丁/并发 | W4-8/9 | 理解选型 | pgvector/并发说明 | 能用查询计划/负载指标判断优化 |
| O15上.4–O15上.6 | 4 pip-tools 复刻；5 小模型任务路由；6 复用/统一响应 | Python 9；W3-9；W4-8 | 4、6 实现（uv替代）；5 理解选型 | `uv.lock`、ModelGateway、响应模型 | lock 可同步；无重复业务代码 |
| O15下.1–O15下.3 | 1 本地向量库；2 OpenAI 额度/并发；3 Azure Key | W4-9 | 1 最小实验；2–3 理解选型 | pgvector Compose；云清单 | 能列数据/额度/合规检查项 |
| O15下.4–O15下.7 | 4 Gunicorn；5 Nginx 限流；6 Docker/Compose 七容器；7 阿里/腾讯部署 | W4-9 | 4–6 实现/最小实验；7 理解选型 | Dockerfile、Compose、Nginx | 配置解析、健康检查、云清单 |
| O16.1–O16.2 | 1 wechatpy/公众号长响应；2 开放 API 接现有应用 | W5-6 | 理解选型 | Channel Adapter 设计 | 验签、ACK、异步、幂等可说明 |
| O16.3–O16.7 | 3 文本 LLM 输出语音/图片架构；4 Whisper；5 TTS；6 DALL-E；7 多模态联调 | W5-2/6 | 最小实验/理解选型 | 多模态 Protocol/消息结构 | 能画 ASR→Agent→TTS 并标审核 |
| O16.8 | DeepSeek 两类模型接入测试 | 前置 2；W3-8 | 实现 | `deepseek.py` chat/reasoning | Chat 主循环、Reasoner 可替换 |
| O17上.1–O17上.4 | 1 客服知识/Prompt；2 审核；3 联调；4 物流 Workflow+CRAG | W5-1 | 实现 | Agent 主图、Retriever、Safety、API | 客服结课 30 条评测 |
| O17下.1–O17下.3 | 1 口语助手架构；2 知识/Prompt；3 多任务拆解 | W5-2 | 最小实验 | Speech Protocol/Workflow 说明 | 文本 Fake 跑一轮 |
| O17下.4–O17下.8 | 4 口语中间件；5 流→整响应；6 Gemini WebSocket；7 ElevenLabs；8 联调 | W5-2 | 4–5 最小实验；6–8 理解选型 | Adapter 与句子聚合设计 | 能解释实时/非实时两套方案 |
| O18上.1–O18上.5 | 1 GPT-4O/4V；2 图片转 HTML Prompt；3 开放 API；4 前端二开；5 联调 | W5-3 | 1 理解选型；2–5 最小实验 | 视觉网关/沙箱设计 | 结构 JSON、代码约束与安全预览 |
| O18下.1–O18下.4 | 1 数字人架构；2 Avatar/SadTalker/Echomimic；3 本地部署；4 应用/OpenAPI | W5-4 | 理解选型 | 异步任务状态机 | 能画脚本→TTS→渲染→存储 |
| O18下.5、O18下.7–O18下.9 | 5 Gradio+Echomimic；7 直播评论；8 OBS；9 联调 | W5-4 | 理解选型 | 重型模型不部署 | 标出授权、审核、队列、推流边界 |
| O19.1–O19.3 | 1 文本转 PPT 架构；2 任务拆解；3 python-pptx/Prompt | W5-5 | 最小实验 | 结构大纲与 Renderer 契约 | 生成三页结构 JSON |
| O19.4–O19.6 | 4 占位符/COS/DALL-E 插件；5 联调；6 Mistune 云 PPT | W5-5 | 最小实验/理解选型 | Adapter 与 Markdown AST 说明 | 素材来源/占位符/对象存储可追踪 |
| O20上.1–O20上.2 | 1 LangChain 问题/优缺点；2 社区/框架/发展 | W5-8 | 理解选型 | 后续路线 | 能说明何时不用 LangChain/LangGraph |
| O20上.3–O20上.5 | 3 模型平台/评测榜；4 Prompt 库；5 LangChain 源码/规划 | W3-2/3；W5-8 | 评测实现；其余理解选型 | Evaluator、官方资料路线 | 用自有评测，不盲从榜单/Prompt |
| O20上.6–O20上.7 | 6 职业/学习方向；7 课程总结 | W5-8；README | 理解选型 | 三个月路线 | 写个人后续项目计划 |
| O20下.1–O20下.5 | 1 预训练/微调/投喂；2 GPT 微调；3 开源本地预训练/部署；4 主流微调；5 企业阶段组合 | W5-7 | 理解选型 | RAG/微调/PEFT/本地模型决策 | 完成一页选型记录 |
| O21-LC.1–O21-LC.2 | 1 LangChain v1/v0.2、模型/Agent/多模态/Checkpoint/中间件/LCEL/上下文/子图/时间旅行；2 DeepAgents | 前置 4/9；W1；W2-9 | v1/LangGraph 实现；差异/DeepAgents 理解选型 | LangGraph 1.x 主图 | Interrupt/恢复/Fork 概念验收 |
| O21-PY.1 | Pydantic v1/v2、校验配置/Validator/ORM 替代 | Python 6 | 实现 | 全项目 Pydantic v2 | 无 v1 API，非法结构测试失败 |
| O21-UP.1–O21-UP.3 | 1 uv 替 pip；2 Pydantic v2；3 LangChain/LangGraph v1 升级 | Python 6/9；前置 4/9 | 实现 | `uv.lock`、Pydantic v2、LangGraph 1.x | uv sync、测试/Lint |
| O21-MCP.1–O21-MCP.2 | 1 MCP/模型上下文；2 LLMOps 配置接 MCP | W2-7 | 实现核心 Adapter | `mcp.py` | 白名单/命名空间/Schema 测试 |
| O21-SK.1–O21-SK.2 | 1 Skills 接 Agent 思路；2 AI 编程/编写与 Review | W2-8；Python 15 | 理解选型/实现流程 | Skill 安全说明、测试/Review 流程 | 能区分 Skill/Tool；变更经测试评审 |

## B. DOCX Agent / LangChain / LLMOps 路线

DOCX 中的重复基础知识由前置手册承接；下表覆盖其独有的阶段、训练营产物和平台路线。

| 来源编号 | 原知识点 | 手册/周次章节 | 深度 | 最终代码位置或说明 | 验收方式 |
|---|---|---|---|---|---|
| D01 | Agent 定义；目标理解、规划、工具、观察、继续决策；ChatBot vs Agent | 前置 1、6 | 实现认知 | `agent.py` | 能画 Agent Loop 和终止条件 |
| D02-LC | LangChain：模型、Prompt、结构化、Tool、RAG、简单 Agent | 前置 2–8 | 实现 | Model/Tool/Retriever | 完成聊天、工具、RAG |
| D02-LG | LangGraph：可控流程、持久化、中断恢复、人工、多 Agent | 前置 9；W1；W2-9 | 核心实现；Multi-Agent 理解选型 | `agent.py` | 图、Checkpoint、审批恢复 |
| D02-LS | LangSmith：调试、评估、上线观测 | W3-1/2/3 | 最小实验 | 本地 Evaluator + 接入说明 | 定位错误层，比较版本 |
| D03.1–D03.4 | 12 阶段 1 LLM/Agent；2 LangChain；3 简单 Agent；4 Memory | 前置 1–7 | 实现 | 最终代码相应模块 | 前置验收 1–3 |
| D03.5–D03.8 | 5 RAG；6 搜索；7 LangGraph；8 LangSmith | 前置 8/9；W1–3 | RAG/图实现；搜索/Smith 最小实验 | Retriever/Agent/Evaluator | RAG 引用、搜索路由、Trace |
| D03.9–D03.12 | 9 后端；10 前端；11 鉴权/限流/审核/部署；12 MCP/多模态/商业 | W3–5 | 后端/审核/部署实现；其余按标记 | API/UI/Deploy/MCP | 服务启动、案例选型 |
| D04-W1 | 7 天：概念、环境、ChatModel、Prompt、Parser/结构化、LCEL、聊天机器人 | 前置 1–4 | 实现 | `deepseek.py` | 普通聊天产物 |
| D04-W2 | 7 天：Tool、Python/HTTP、选择、参数、错误、订单 Agent | 前置 5/6 | 实现 | `tools.py`、订单 Tool | 订单查询轨迹 |
| D04-W3 | 7 天：窗口、短期/长期/摘要、DB、画像、记忆客服 | 前置 7；W3-6/7 | 内存实现；DB 最小实验 | `context.py` | 用户隔离/删除 |
| D04-W4 | 7 天：RAG、Loader、切分、Embedding、向量库、Retriever+Rerank、知识 Agent | 前置 8；W2-1/2 | 核心实现 | Retrieval/pgvector | 制度回答有引用 |
| D04-W5 | 7 天：联网原理、搜索 Tool、网页清洗、引用、路由、安全、实时搜索 | W1-3/10；W2-5 | 最小实验 | 受控 Fake Search/安全说明 | 实时信息不混入企业来源 |
| D04-W6 | 7 天：LangGraph、StateGraph、Node/Edge、分支、Checkpoint、Interrupt、报销 Agent | 前置 9；W1-2–6 | 实现 | `agent.py` | 审批 Agent 恢复 |
| D04-W7 | 7 天：Trace、Tool Debug、Dataset、自动评测、Prompt 版本、Token/费用、优化 | W3-1–3 | 评测实现；Smith 最小实验 | `evaluator.py` | 比较优化前后 |
| D04-W8 | 综合客服：聊天、订单、售后 RAG、搜索、记忆、审批、LangSmith、API | W5-1 | 实现/最小实验 | 最终项目 | 结课评测集 |
| D05-W9 | FastAPI：聊天、会话、应用管理 | W4-1/7 | 聊天/会话实现；应用最小实验 | `api.py` | API 测试 |
| D05-W10 | PostgreSQL、ORM、迁移、PyTest | W3-7；Python 12/15 | pgvector/测试实现；ORM/迁移最小实验 | pgvector、tests | 解释生产替换 |
| D05-W11 | Vue 聊天 UI、流式、应用列表 | W4-5/6 | 最小 UI 实现；Vue 理解选型 | `static/index.html` | 浏览器验收 |
| D05-W12 | 知识库、工具管理、上传/切分/向量/配置 | W2；W4-3/7 | 核心实现/管理最小实验 | Tool/Retrieval/Tasks | 新知识可搜索 |
| D05-W13 | Workflow 可视化：节点、边、条件、Vue Flow | W4-7 | 最小实验 | Workflow UI 说明 | 三节点配置可解释 |
| D05-W14 | JWT、API Key、审核、限流 | W3-4/5；W4-4 | 审核实现；鉴权限流最小实验 | Safety/设计说明 | 安全测试 |
| D05-W15 | 多模型配置、MCP | W2-7；W3-9 | MCP 实现；多模型接口/选型 | `mcp.py`、ModelGateway | 白名单测试 |
| D05-W16 | Docker、监控、费用统计、商业模板 | W3-3；W4-9；W5 | 实现/最小实验 | deployments、metrics | Compose/案例清单 |
| D06 | 每天固定格式：目标、类比、概念、代码、解释、练习、总结、下一步 | 所有手册/周次 | 实现课程结构 | 每周知识衔接/练习/验收 | 能按周独立学习 |
| D07 | 最终平台：多应用、Prompt、Tool、RAG、Memory、Graph、Smith、多模型、MCP、API Key、鉴权、Token、Docker、模板 | W1–5 | Agent 核心实现；平台按标记压缩 | 最终项目 | 覆盖矩阵无空项 |
| D08.1–D08.4 | 经验：最小聊天→Tool→Memory→RAG；Prompt 边界；Tool 设计；危险动作确认 | 前置 3–7；W1 | 实现 | Model/Tool/Approval | 执行轨迹与审批测试 |
| D08.5–D08.9 | 经验：RAG 不仅向量库；复杂图；上线评测；成本/延迟/失败；后端先于画布 | W2–4 | 实现/最小实验 | Retrieval/Eval/API | 诊断顺序、发布门禁 |
| D-App.1 | 智能客服：知识、订单、物流、售后、人工、审核 | W5-1 | 实现 | 最终客服 Agent | 30 条结课集 |
| D-App.2 | 数据分析：Excel、字段、SQL/Pandas、图表、结论 | W2 Tool 原则；W5 复用法 | 理解选型 | 新 Tool/Subgraph 案例 | 画状态/工具/审批边界 |
| D-App.3 | 知识问答：检索、引用、回退、RAG 优化 | W2 | 实现 | Retrieval/Evaluator | 错误引用/无结果测试 |
| D-App.4 | 报表 Agent：多源、指标、总结、报告 | W2-9；W5 复用法 | 理解选型 | Planner/Workflow 选型 | 能拆确定任务 |
| D-App.5 | PPT Agent：拆解、大纲、python-pptx、占位符 | W5-5 | 最小实验 | 结构化大纲骨架 | 三页结构 JSON |
| D-App.6 | 图片转 HTML：视觉、结构、代码 | W5-3 | 最小实验 | 视觉网关/沙箱设计 | 能力边界与安全验收 |

## C. 本课程补充的上线必需知识

| 来源编号 | 新增知识点 | 手册/周次章节 | 深度 | 最终代码位置或说明 | 验收方式 |
|---|---|---|---|---|---|
| N01 | Runtime/State/Store/模型/Tool 五层上下文 | W1-2 | 实现 | `context.py`、AgentState、ToolContext | 身份不由模型伪造 |
| N02 | 运行预算：循环、工具、Token、时间、费用、重复调用 | W1-9；W3-3 | 实现 | `ExecutionBudget` | 超限被阻止并可解释 |
| N03 | 副作用幂等与恢复语义 | W1-4/6；W2-5 | 实现 | ToolRegistry 幂等缓存/Key | 重放不重复写 |
| N04 | 取消、背压、SSE 终止事件 | W1-8；W4-2 | 实现/最小实验 | cancel/SSE API | 中断与 done/error |
| N05 | 记忆同意、来源、过期、删除、保留 | W3-6 | 最小实验 | Context 接口/生产 Schema | 两用户隔离、删除有效 |
| N06 | 知识/网页/Tool/MCP 内容不可信与污染 | W2-5/7；W3-4 | 实现安全边界 | Safety/MCP 白名单 | Injection 不触发工具 |
| N07 | 引用可信度：真实、支持、进入上下文、权限 | W1-1；W3-3 | 实现 | Retriever/Evaluator | 错误引用评测失败 |
| N08 | 轨迹评测：选择、参数、顺序、审批、终止 | W3-2/3 | 实现 | `evaluator.py` | 期望 Tool 序列通过 |
| N09 | Fake Client 与确定性回归 | W3-8 | 实现 | `FakeDeepSeekClient`、tests | 无 Key 全测试通过 |
| N10 | MCP 服务白名单、命名空间、授权、再校验 | W2-7 | 实现 | `mcp.py` | 未知 Server 被拒绝 |
| N11 | 模型能力边界：文本/Tool/推理/视觉/语音 | 前置 2；W5-2/3/6 | 实现接口/理解选型 | ModelGateway 与多模态 Adapter 说明 | 不把文本模型当视觉模型 |
| N12 | Workflow→单 Agent→Multi-Agent 的选择顺序 | 前置 1；W2-9 | 理解选型 | 编排决策表 | 能为案例说明理由 |

## 矩阵验收结论

- 原 21 周大纲的所有编号均有来源行；原大纲的跳号按原文保留。
- DOCX 的 12 阶段、8 周训练营、后续 8 周平台路线、经验和六类模板均已映射。
- Agent 核心达到实现级；前端/平台至少有最小实验或明确迁移手册；重型模型与云厂商达到理解选型。
- `N01–N12` 补上了原路线中影响生产可靠性的上下文、预算、幂等、恢复、记忆治理、轨迹评测和 MCP 安全。
