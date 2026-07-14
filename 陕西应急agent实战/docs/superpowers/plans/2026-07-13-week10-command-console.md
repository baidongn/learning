# 第 10 周轻量指挥台 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建可调用第 9 周 Supervisor API 的 Vue 3 求职演示指挥台。

**Architecture:** 前端保持单页和四个小模块，所有网络访问集中到 `src/api.js`。FastAPI 保留业务逻辑，Vite 只负责开发代理和生产构建。

**Tech Stack:** Vue 3.5.22、Vite 7.1.7、Vitest 3.2.4、FastAPI。

## Global Constraints

- 代码使用英文标识符和中文注释。
- 不增加认证、地图 SDK、真实视频或真实调度。
- Mock 模式无需模型 Key。
- Supervisor 的 `executed_actions` 必须保持为空。

---

### Task 1: 前端 API 边界

**Files:**
- Create: `weeks/week-10/frontend/src/api.js`
- Test: `weeks/week-10/frontend/src/api.test.js`

**Interfaces:**
- Consumes: `POST /api/agents/supervisor/invoke`
- Produces: `runSupervisor(payload, fetchImpl) -> Promise<object>`

- [ ] 先写测试：模拟 200 JSON 与 422 错误响应，断言成功返回对象、失败抛出含状态码的错误。
- [ ] 运行 `npm test -- --run src/api.test.js`，预期因 `runSupervisor` 尚不存在而失败。
- [ ] 实现唯一 `fetch` 封装：设置 JSON Header、序列化 payload、解析错误 detail。
- [ ] 再运行同一测试，预期通过。

### Task 2: 指挥台组件

**Files:**
- Create: `weeks/week-10/frontend/src/components/IncidentForm.vue`
- Create: `weeks/week-10/frontend/src/components/AgentTrace.vue`
- Create: `weeks/week-10/frontend/src/components/ResultPanel.vue`
- Create: `weeks/week-10/frontend/src/App.vue`
- Test: `weeks/week-10/frontend/src/App.test.js`

**Interfaces:**
- Consumes: `runSupervisor(payload)` 和 `SupervisorResult`
- Produces: `submit` 事件以及风险、引用、调度和审批状态视图

- [ ] 先写组件测试：默认表单存在、提交后显示“等待人工审批”、轨迹包含四个 Agent。
- [ ] 运行 `npm test -- --run src/App.test.js`，预期组件文件不存在而失败。
- [ ] 实现四个聚焦组件和加载/错误状态；默认数据使用课程演示场景。
- [ ] 再运行组件测试，预期通过。

### Task 3: 构建配置与联合验收

**Files:**
- Create: `weeks/week-10/frontend/package.json`
- Create: `weeks/week-10/frontend/vite.config.js`
- Create: `weeks/week-10/frontend/index.html`
- Create: `weeks/week-10/frontend/src/main.js`
- Create: `weeks/week-10/frontend/src/style.css`
- Modify: `weeks/week-10/Makefile`

**Interfaces:**
- Consumes: 本机 Node.js 20.19+ 与 FastAPI 8000 端口
- Produces: `npm run dev`、`npm test`、`npm run build`

- [ ] 固定 Vue、Vite、Vitest 和测试工具版本，配置 `/api` 代理到 `http://127.0.0.1:8000`。
- [ ] 运行 `npm test -- --run`，预期全部前端测试通过。
- [ ] 运行 `npm run build`，预期生成 `dist/index.html`。
- [ ] 运行后端 `pytest`，预期第 9 周累计功能继续通过。
