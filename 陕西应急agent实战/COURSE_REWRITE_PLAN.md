# 12 周手把手课程重构实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 12 份提纲式周课程重写为 60 个 Day 的手把手开发教程，使学习者能够基于上一周成果逐步完成当前周正式代码。

**Architecture:** 每周仍只有一个 `WEEK-XX-COURSE.md`，并保持 12 个二级数字章节；第 4～8 章分别承载 Day 1～Day 5。教程直接引用和编写当周真实源码，自动验证器负责检查章节、Day、篇幅、命令、代码围栏、练习和面试题数量，人工复审负责检查步骤是否真正可操作。

**Tech Stack:** Markdown、Bash、ripgrep、Python 3.11、现有 FastAPI/LangGraph/MCP/DeepSeek/Vue/Docker/Kustomize 项目。

## Global Constraints

- 每周 5 天，每天设计为 2～3 小时。
- 每周只保留一个主课程文件，不新增 60 个 Day 文件。
- Week 1 从项目初始化开始；Week 2～12 从上一周成果继续。
- 只写会进入最终项目的正式代码，不写完成后删除的玩具版。
- 每一步必须包含文件路径、代码或配置操作、运行命令、预期结果和测试入口。
- 只重点解释关键逻辑，但学习者必须填写的代码不得用 `...`、`TODO` 或“其余类似”省略。
- 每份课程恰好保留 12 个 `## N.` 数字章节，第 4～8 章对应 Day 1～Day 5。
- 每周只保留一个综合实战作业和三道面试题；每天允许一个小练习。
- 代码标识符使用英文，代码注释和教程说明使用中文。
- Mock 模式无需 DeepSeek Key；高风险动作必须保留人工审批和零越权执行边界。
- 不修改业务功能，除非教程核对发现可复现代码缺陷并单独报告。
- 当前目录没有可用 Git 工作树，因此计划中的版本检查使用文件备份、结构验证和测试，不执行 commit。

---

### Task 1: 建立课程质量自动验证器

**Files:**
- Create: `scripts/verify_course_quality.sh`
- Modify: `Makefile`
- Modify: `.github/workflows/ci.yml`

**Interfaces:**
- Consumes: `weeks/week-XX/WEEK-XX-COURSE.md`
- Produces: `make verify-course`，对 12 份课程执行结构和内容下限检查。

- [ ] **Step 1: 写验证脚本**

脚本逐周验证：恰好 12 个数字章节、Day 1～Day 5 各出现一次、每个 Day 至少 8 个三级标题、全文至少 700 行、代码围栏数量为偶数、存在 `make test/eval/verify`、存在“预期输出”“小练习”“常见错误”，面试题恰好 3 道。

`scripts/verify_course_quality.sh` 使用以下完整实现：

```bash
#!/usr/bin/env bash
set -euo pipefail

if test "$#" -eq 1; then
  numbers="$(printf '%02d' "$((10#$1))")"
else
  numbers="$(seq -w 1 12)"
fi

for number in ${numbers}; do
  course="weeks/week-${number}/WEEK-${number}-COURSE.md"
  test -f "${course}"

  section_count=$(rg -c '^## [0-9]+\.' "${course}")
  test "${section_count}" -eq 12

  line_count=$(wc -l <"${course}")
  test "${line_count}" -ge 700

  for day in 1 2 3 4 5; do
    day_heading_count=$(rg -c "^## [4-8]\\. Day ${day}：" "${course}")
    test "${day_heading_count}" -eq 1

    subsection_count=$(awk -v day="${day}" '
      $0 ~ "^## [4-8]\\. Day " day "：" { inside=1; next }
      inside && /^## / { inside=0 }
      inside && /^### / { count++ }
      END { print count + 0 }
    ' "${course}")
    test "${subsection_count}" -ge 8
  done

  fence_count=$(rg -c '^```' "${course}")
  test "$((fence_count % 2))" -eq 0
  test "${fence_count}" -gt 0

  test "$(rg -c '^### 今天目标' "${course}")" -eq 5
  test "$(rg -c '^### .*预期输出' "${course}")" -ge 5
  test "$(rg -c '^### 当天小练习' "${course}")" -eq 5
  test "$(rg -c '^### 面试题 [123]' "${course}")" -eq 3
  rg -q 'make test' "${course}"
  rg -q 'make eval' "${course}"
  rg -q 'make verify' "${course}"

  printf 'week-%s course quality: ok\n' "${number}"
done
```

- [ ] **Step 2: 让当前课程验证失败**

Run: `bash scripts/verify_course_quality.sh`

Expected: 在 Week 1 的篇幅或 Day 检查处失败，证明验证器能识别现有提纲式课程。

- [ ] **Step 3: 接入根 Makefile 和 CI**

新增 `verify-course` 目标，并让根级 CI 在结构检查之后执行课程质量验证。

Makefile 增加：

```make
.PHONY: verify-course

verify-course:
	bash scripts/verify_course_quality.sh
```

根级 CI 的课程检查步骤为：

```yaml
- name: 验证手把手课程质量
  run: bash scripts/verify_course_quality.sh
```

- [ ] **Step 4: 只运行 Shell 语法检查**

Run: `bash -n scripts/verify_course_quality.sh`

Expected: exit code 0。

---

### Task 2: 重写 Week 1 开发底座教程

**Files:**
- Modify: `weeks/week-01/WEEK-01-COURSE.md`

**Interfaces:**
- Consumes: `config.py`、`domain.py`、`database.py`、`api.py`、Alembic、Compose 和 Week 1 测试。
- Produces: 从目录初始化到 PostgreSQL/pgvector、模拟 API 和验收的五天教程。

- [ ] **Step 1: 写第 1～3 章**

明确本周成果、空项目起点、环境准备、架构图、最终目录和五天时间表。

- [ ] **Step 2: 写 Day 1～Day 2**

Day 1 手把手创建配置、包入口、Makefile 与 `.env`；Day 2 创建 Pydantic 领域枚举和模型，逐步运行 `test_config.py`、`test_domain.py`。

- [ ] **Step 3: 写 Day 3～Day 4**

Day 3 创建 SQLAlchemy 模型、Alembic 迁移和 Compose；Day 4 创建四类模拟 API，演示正常、404、stale、unavailable。

- [ ] **Step 4: 写 Day 5 和收尾章节**

带着运行测试、评测、验证，完成 G30/BAOJI-01 唯一作业，并提供排错树、通关清单和三道面试题回答要点。

- [ ] **Step 5: 验证 Week 1**

Run: `bash scripts/verify_course_quality.sh 01`

Expected: `week-01 course quality: ok`。

---

### Task 3: 重写 Week 2 RAG 与预案专家教程

**Files:**
- Modify: `weeks/week-02/WEEK-02-COURSE.md`

**Interfaces:**
- Consumes: `rag.py`、`agents/plan_expert.py`、`models.py`、相关 API 和测试。
- Produces: 从预案文档与确定性向量到 DeepSeek Live Agent 的五天教程。

- [ ] **Step 1: 写 Week 2 起点和架构**

说明从 Week 1 继承什么，列出 Retriever、Agent、DeepSeek Client 和 API 的调用链。

- [ ] **Step 2: 写 Day 1～Day 2**

手把手添加 `PlanDocument`、教学 Embedding、余弦相似度、阈值和 `InMemoryPlanRetriever`，运行排序与弱相关测试。

- [ ] **Step 3: 写 Day 3～Day 4**

创建 `PlanQuery/Citation/PlanRecommendation` 和 Mock Agent，再创建 DeepSeek HTTP Client 与 Live Agent；解释引用由检索代码绑定。

- [ ] **Step 4: 写 Day 5 和收尾章节**

调用预案 API，演示 ready/insufficient_evidence，完成危险品预案作业并分析 MockTransport 测试。

- [ ] **Step 5: 验证 Week 2**

Run: `bash scripts/verify_course_quality.sh 02`

Expected: `week-02 course quality: ok`。

---

### Task 4: 重写 Week 3 Tool 与事件研判教程

**Files:**
- Modify: `weeks/week-03/WEEK-03-COURSE.md`

**Interfaces:**
- Consumes: `tools.py`、`agents/incident_analysis.py`、模拟 API 和工具/Agent 测试。
- Produces: 与用户模板最接近的 Tool Schema、HTTP 调用、结构化轨迹和研判 Agent 教程。

- [ ] **Step 1: 写起点、Tool 边界和目录变化**

解释普通 HTTP 函数、Agent Tool、`ToolResult`、Schema 和 trace_id 的关系。

- [ ] **Step 2: 写 Day 1～Day 2**

创建正式 `ToolResult` 和 `MockApiToolClient`，实现路况、气象工具，手动调用并打印标准结果。

- [ ] **Step 3: 写 Day 3～Day 4**

实现摄像头 Tool 与 `IncidentAnalysisAgent`，再加入超时、断连、过期证据、缺失字段和工具轨迹。

- [ ] **Step 4: 写 Day 5 和收尾章节**

接入 API，逐项分析工具测试和 Agent 测试，完成新增路段故障场景作业。

- [ ] **Step 5: 验证 Week 3**

Run: `bash scripts/verify_course_quality.sh 03`

Expected: `week-03 course quality: ok`。

---

### Task 5: 重写 Week 4 固定 LangGraph 工作流教程

**Files:**
- Modify: `weeks/week-04/WEEK-04-COURSE.md`

**Interfaces:**
- Consumes: `workflows/incident_response.py`、两个专业 Agent 和工作流测试。
- Produces: State、Node、Edge、条件路由和 API 的五天教程。

- [ ] **Step 1: 写状态图架构和本周增量**

列出 `IncidentWorkflowState` 字段及 analyze/needs_input/retrieve_plan 三节点数据流。

- [ ] **Step 2: 写 Day 1～Day 3**

依次创建 StateGraph、事件研判节点、预案节点，并解释同步 Mock Agent 与异步 DeepSeek Agent 的兼容调用。

- [ ] **Step 3: 写 Day 4～Day 5**

实现 missing_fields 条件路由、API 和固定顺序测试，使用两类输入观察不同终态。

- [ ] **Step 4: 写作业、排错和面试**

作业只要求增加一种明确的缺失信息分支；排错覆盖 TypedDict、节点返回值和 thread state。

- [ ] **Step 5: 验证 Week 4**

Run: `bash scripts/verify_course_quality.sh 04`

Expected: `week-04 course quality: ok`。

---

### Task 6: 重写 Week 5 Checkpoint 与 HITL 教程

**Files:**
- Modify: `weeks/week-05/WEEK-05-COURSE.md`

**Interfaces:**
- Consumes: `checkpoints.py`、`workflows/approval_flow.py`、API lifespan 和审批测试。
- Produces: 可暂停、持久化和恢复的人工审批教程。

- [ ] **Step 1: 写记忆、Checkpoint、thread_id 的概念和调用链**

用一次事件从 start 到 interrupt 再到 resume 的时序图建立整体认识。

- [ ] **Step 2: 写 Day 1～Day 2**

创建 `to_psycopg_uri`、内存/PostgreSQL Saver 工厂，解释为什么测试默认内存、部署使用 PostgreSQL。

- [ ] **Step 3: 写 Day 3～Day 4**

实现审批图、`interrupt`、`Command(resume=...)`，分别完成 approve/edit/reject，明确 edit 不能等同 approve。

- [ ] **Step 4: 写 Day 5 和恢复测试**

接入 FastAPI lifespan 和审批端点，运行中断、恢复、无越权动作和 Saver 选择测试。

- [ ] **Step 5: 验证 Week 5**

Run: `bash scripts/verify_course_quality.sh 05`

Expected: `week-05 course quality: ok`。

---

### Task 7: 重写 Week 6 资源调度 Agent 教程

**Files:**
- Modify: `weeks/week-06/WEEK-06-COURSE.md`

**Interfaces:**
- Consumes: `agents/resource_dispatch.py`、资源/路线 Tool、API 和测试。
- Produces: 查询资源、估算 ETA、生成幂等调度建议的五天教程。

- [ ] **Step 1: 写建议/执行分离和调度数据模型**

说明 `DispatchRequest`、`ResourceAssignment`、`DispatchProposal` 的职责。

- [ ] **Step 2: 写 Day 1～Day 3**

实现附近资源查询、路线 POST、统一错误转换和 ETA 计算，运行正常、超时、资源不足测试。

- [ ] **Step 3: 写 Day 4～Day 5**

实现 `ResourceDispatchAgent`、稳定 proposal_id、API 和完整调度演示。

- [ ] **Step 4: 写作业、排错和面试**

作业增加一种资源类型和不可满足案例；排错覆盖空资源、路线失败和浮点 ETA。

- [ ] **Step 5: 验证 Week 6**

Run: `bash scripts/verify_course_quality.sh 06`

Expected: `week-06 course quality: ok`。

---

### Task 8: 重写 Week 7 MCP 工具服务教程

**Files:**
- Modify: `weeks/week-07/WEEK-07-COURSE.md`

**Interfaces:**
- Consumes: `mcp_servers/*.py`、根 `mcp-servers/*.py` 和 MCP 测试。
- Produces: 三个独立端口、五个工具、REST/MCP 契约一致性的五天教程。

- [ ] **Step 1: 写 REST 与 MCP 边界和进程图**

明确 MCP 不新增 Agent，只改变工具暴露协议。

- [ ] **Step 2: 写 Day 1～Day 3**

创建 common 序列化辅助、道路 Server、气象 Server 和资源 Server，打印工具名称和 Schema。

- [ ] **Step 3: 写 Day 4～Day 5**

配置 8101/8102/8103 端口，验证结构化结果、错误契约和工具发现。

- [ ] **Step 4: 写作业、排错和面试**

作业增加一个只读 MCP Tool；排错覆盖端口冲突、导入路径和 FastMCP 返回结构。

- [ ] **Step 5: 验证 Week 7**

Run: `bash scripts/verify_course_quality.sh 07`

Expected: `week-07 course quality: ok`。

---

### Task 9: 重写 Week 8 安全复核 Agent 教程

**Files:**
- Modify: `weeks/week-08/WEEK-08-COURSE.md`

**Interfaces:**
- Consumes: `agents/safety_review.py`、API 和安全测试。
- Produces: 动作、引用、证据时效、提示词注入和审批规则的五天教程。

- [ ] **Step 1: 写三态安全结果和检查顺序**

说明 BLOCK 优先于 REVISE，不能用低风险通过覆盖高风险阻断。

- [ ] **Step 2: 写 Day 1～Day 3**

创建请求/结果模型、动作白名单、审批检查、引用和 evidence_age 检查。

- [ ] **Step 3: 写 Day 4～Day 5**

加入提示词注入标记、sanitized_actions、API 和攻击回归测试。

- [ ] **Step 4: 写作业、排错和面试**

作业新增一条不破坏正常输入的安全规则；排错覆盖规则优先级和误报。

- [ ] **Step 5: 验证 Week 8**

Run: `bash scripts/verify_course_quality.sh 08`

Expected: `week-08 course quality: ok`。

---

### Task 10: 重写 Week 9 Supervisor Agent 教程

**Files:**
- Modify: `weeks/week-09/WEEK-09-COURSE.md`

**Interfaces:**
- Consumes: `agents/supervisor.py`、四个专业 Agent、API 和 Supervisor 测试。
- Produces: 五 Agent 有界编排、重试、步数、安全和审批的五天教程。

- [ ] **Step 1: 写 Supervisor 与固定图的取舍**

展示统一输入、四专业 Agent、route_trace 和终态的完整调用链。

- [ ] **Step 2: 写 Day 1～Day 3**

创建请求/结果/轨迹模型，实现 `_run_with_retry`、step limit 和四 Agent 顺序路由。

- [ ] **Step 3: 写 Day 4～Day 5**

加入 missing_fields 立即停止、最旧证据时效、安全复核、等待审批、API 和 live DeepSeek 测试。

- [ ] **Step 4: 写作业、排错和面试**

作业增加一个可恢复异常案例；排错覆盖无限循环、重复副作用和 Agent 异常丢失。

- [ ] **Step 5: 验证 Week 9**

Run: `bash scripts/verify_course_quality.sh 09`

Expected: `week-09 course quality: ok`。

---

### Task 11: 重写 Week 10 Vue 指挥台教程

**Files:**
- Modify: `weeks/week-10/WEEK-10-COURSE.md`

**Interfaces:**
- Consumes: `frontend/src/*.vue`、`api.js`、样式、Vite 配置和前端测试。
- Produces: 表单、API 调用、Agent 轨迹和结果展示的五天教程。

- [ ] **Step 1: 写前端数据流和组件树**

明确 IncidentForm → API → App state → AgentTrace/ResultPanel。

- [ ] **Step 2: 写 Day 1～Day 3**

创建 Vite/Vue 项目、表单组件、API Client 和加载/错误状态，给出 npm 命令和 Mock API 响应。

- [ ] **Step 3: 写 Day 4～Day 5**

创建轨迹和结果组件、样式、组件测试与前后端联调步骤。

- [ ] **Step 4: 写作业、排错和面试**

作业增加 needs_input 的明显提示；排错覆盖代理、CORS、响应字段和无 node_modules 环境。

- [ ] **Step 5: 验证 Week 10**

Run: `bash scripts/verify_course_quality.sh 10`

Expected: `week-10 course quality: ok`。

---

### Task 12: 重写 Week 11 评测与可靠性教程

**Files:**
- Modify: `weeks/week-11/WEEK-11-COURSE.md`

**Interfaces:**
- Consumes: `evaluation.py`、`evals/run.py`、`reliability.py`、`tools.py`、`observability.py` 和测试。
- Produces: 真实 Supervisor 场景评测、Tool 熔断和 Prometheus 的五天教程。

- [ ] **Step 1: 写指标和数据集边界**

明确 JSONL 只保存输入与期望，实际结果必须由 Supervisor 运行产生。

- [ ] **Step 2: 写 Day 1～Day 3**

创建评测模型、20 条场景和异步 Runner，逐项计算四项指标并验证安全红线。

- [ ] **Step 3: 写 Day 4～Day 5**

实现显式失败也计数的 CircuitBreaker、接入 GET/POST Tool、暴露 Prometheus 指标并运行回归。

- [ ] **Step 4: 写作业、排错和面试**

作业增加 5 条场景并故意填错 2 条期望；排错覆盖手填 actual、环境污染和熔断不恢复。

- [ ] **Step 5: 验证 Week 11**

Run: `bash scripts/verify_course_quality.sh 11`

Expected: `week-11 course quality: ok`。

---

### Task 13: 重写 Week 12 部署与求职教程

**Files:**
- Modify: `weeks/week-12/WEEK-12-COURSE.md`

**Interfaces:**
- Consumes: Dockerfile、Compose、Kustomize、Alembic、CI、根部署文档和求职材料。
- Produces: 从镜像到本地/生产部署、静态验证和项目演示的五天教程。

- [ ] **Step 1: 写部署架构和环境边界**

区分 demo 内置数据库、prod 外部数据库、Mock/Live 模型和静态/实际部署验证。

- [ ] **Step 2: 写 Day 1～Day 3**

创建前后端 Dockerfile、Nginx、Compose demo/prod、Kustomize base/dev/prod，逐条解释固定镜像和环境变量。

- [ ] **Step 3: 写 Day 4～Day 5**

创建唯一迁移 Job、根 CI、Compose/Kustomize/Alembic 验证命令，再编写 5 分钟演示和简历描述。

- [ ] **Step 4: 写作业、排错和面试**

作业在 kind 执行部署、滚动更新和回滚；排错覆盖镜像、命名空间、迁移、Secret 和探针。

- [ ] **Step 5: 验证 Week 12**

Run: `bash scripts/verify_course_quality.sh 12`

Expected: `week-12 course quality: ok`。

---

### Task 14: 全课程交叉核对、回归和交付

**Files:**
- Modify: `START_HERE.md`
- Modify: `ROADMAP.md`
- Modify: `CHANGELOG.md`
- Modify: `outputs/DELIVERY.md`
- Regenerate: `outputs/shaanxi-highway-agent-course.zip`

**Interfaces:**
- Consumes: 12 份重写课程、全部源码和测试。
- Produces: 可验证、可下载的新版完整课程包。

- [ ] **Step 1: 更新学习入口**

在 `START_HERE.md` 写明每周 5 天使用方式和“上一周成果 → 本周正式增量”的学习规则；ROADMAP 增加每周建议时长。

- [ ] **Step 2: 运行课程结构与质量验证**

Run: `bash scripts/verify_structure.sh`

Run: `bash scripts/verify_course_quality.sh`

Expected: 12 周全部输出 `ok`。

- [ ] **Step 3: 检查 Markdown 与路径**

检查所有代码围栏配对；检索 `TODO`、省略实现和旧测试数量；抽查教程中的源码路径、测试路径、API 路径和环境变量。

- [ ] **Step 4: 运行代码回归**

Run: `bash scripts/test_all_weeks.sh`

Expected: 12 周后端测试全部通过；无 npm 依赖时前端明确显示 skipped，不误报通过。

- [ ] **Step 5: 运行最终评测和部署静态验证**

Run: `make eval-final`

Run: `make verify-deploy`

Expected: 20 场景 `passed=true`；dev/prod Kustomize 均可渲染。

- [ ] **Step 6: 内容复审**

人工抽查 Week 1、3、5、9、12：确认每个 Day 都实际修改文件、运行命令、展示输出和验证测试；确认不是代码阅读提纲。

- [ ] **Step 7: 更新交付说明和压缩包**

记录教程重构、验证结果和仍受环境限制的 Docker/npm 实际运行项；重新生成排除 `.venv`、缓存、node_modules 和旧 outputs 的压缩包，并执行 `unzip -tq`。
