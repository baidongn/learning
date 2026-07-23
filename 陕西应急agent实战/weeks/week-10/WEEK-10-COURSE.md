# 第 10 周：Vue 轻量应急指挥台

> 学习方式：5 天，每天 2～3 小时。继承第 9 周完整后端，不新增 Agent。
>
> 本周终点：创建一个可本地运行、测试和构建的 Vue 3 指挥台。用户提交事件后调用 Supervisor API，展示风险、预案引用、资源建议、安全结论、人工审批提示和四 Agent 轨迹。

## 1. 本周学习地图与最终成果

本周把后端结构化结果变成可观察界面：

```text
IncidentForm
  -> runSupervisor
  -> POST /api/agents/supervisor/invoke
  -> SupervisorResult
       -> ResultPanel
       -> AgentTrace
       -> approval banner
```

界面不是复杂后台，只做求职演示最重要的内容：

- 事件录入。
- 默认完整演示场景。
- 提交/加载状态。
- API 错误提示。
- 风险与事件类型。
- 预案引用数量。
- 资源建议与缺口。
- 安全 verdict/reason。
- 等待人工审批。
- Agent 调用顺序。
- 明确“自动执行 0”。

五天安排：

| Day | 核心内容 | 当天成果 |
|---|---|---|
| Day 1 | Vite/Vue 工程与代理 | 前端能启动并访问后端 |
| Day 2 | API 边界与事件表单 | 能发送 SupervisorRequest |
| Day 3 | ResultPanel 与 AgentTrace | 能展示结构化结果 |
| Day 4 | App 状态管理与响应式样式 | 完成桌面/移动端轻量指挥台 |
| Day 5 | Vitest、构建和验收 | 前后端测试与生产构建通过 |

本周必做：

- Vue 3.5.22。
- Vite 7.1.7。
- API 函数可注入 fetch。
- 事件表单。
- 结果卡片。
- Agent Trace。
- loading/error。
- Vitest。
- `npm run build`。
- `make test`、`make eval`、`make verify`。

本周选做：

- 增加审批 start/resume 按钮。
- 加入 JSON 折叠详情。
- 加入深色/浅色切换。

明确不做：

- 登录/权限后台。
- 地图引擎。
- 视频播放器。
- WebSocket 实时推送。
- 复杂状态管理库。
- 真实高速数据。

## 2. 前置知识、环境准备和本周起点

验收第 9 周：

```bash
cd weeks/week-09
make test
make eval
make verify
```

检查 Node：

```bash
node --version
npm --version
```

本周要求：

```text
Node.js >= 20.19
```

进入第 10 周：

```bash
cd ../week-10
cp .env.example .env
make setup
```

`make setup` 同时安装后端和前端依赖：

```make
setup:
	$(PYTHON) -m venv $(VENV)
	$(VENV)/bin/python -m pip install -r backend/requirements.lock.txt
	cd frontend && npm install
```

新增目录：

```text
frontend/
├── index.html
├── package.json
├── vite.config.js
└── src/
    ├── App.vue
    ├── App.test.js
    ├── api.js
    ├── api.test.js
    ├── main.js
    ├── style.css
    └── components/
        ├── IncidentForm.vue
        ├── AgentTrace.vue
        └── ResultPanel.vue
```

后端代码与第 9 周保持一致。前端开发服务器 5173，通过 Vite proxy 把 `/api` 转到后端 8000，因此开发时不需要额外配置 CORS。

## 3. 本周架构、目录变化与完整调用链

浏览器调用：

```text
http://127.0.0.1:5173
  -> fetch("/api/agents/supervisor/invoke")
  -> Vite dev proxy
  -> http://127.0.0.1:8000/api/agents/supervisor/invoke
```

组件关系：

```text
App.vue
├── IncidentForm
│   └── emit("submit", payload)
├── ResultPanel
│   └── result prop
└── AgentTrace
    └── result.route_trace prop
```

App 只管理三项页面状态：

```text
loading
result
error
```

为什么不引入 Pinia？

当前只有一个页面和一个请求，`ref` 足够。过早引入全局状态会增加学习负担。

前端安全边界：

- 页面只展示建议。
- 不自动调用审批 resume。
- 不显示“已执行”假状态。
- 读取 `executed_actions.length`。
- 页脚明确合成数据和 mock 模式。
- 错误返回对用户可见。

## 4. Day 1：创建 Vite/Vue 工程、入口与开发代理

### 今天目标

1. 创建 package.json。
2. 锁定 Vue/Vite/Vitest 版本。
3. 配置 Vite Vue 插件。
4. 配置 5173 开发端口。
5. 配置 /api 代理。
6. 配置 jsdom 测试环境。
7. 创建 HTML/JS 入口。
8. 启动前端空壳。

### 上一节衔接

第 9 周已有完整 Supervisor API。

今天只搭前端工程，不改后端。

### 先说结论

开发时需要两个进程：

```text
后端 8000
前端 5173
```

前端请求始终写相对路径 `/api/...`，不要把 8000 硬编码进组件。

### 第 1 步：创建 package.json

新建 `frontend/package.json`：

```json
{
  "name": "shaanxi-highway-command-console",
  "private": true,
  "version": "0.10.0",
  "type": "module",
  "scripts": {
    "dev": "vite --host 0.0.0.0",
    "build": "vite build",
    "test": "vitest",
    "test:run": "vitest run"
  },
  "engines": {
    "node": ">=20.19"
  },
  "dependencies": {
    "vue": "3.5.22"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "6.0.1",
    "@vue/test-utils": "2.4.6",
    "jsdom": "26.1.0",
    "vite": "7.1.7",
    "vitest": "3.2.4"
  }
}
```

所有版本固定，不使用 `latest`。

### 第 2 步：创建 Vite 配置

新建 `frontend/vite.config.js`：

```javascript
import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      "/api": "http://127.0.0.1:8000",
    },
  },
  test: {
    environment: "jsdom",
  },
});
```

proxy 只在开发服务器生效。第 12 周生产部署由 Nginx/服务路由处理。

### 第 3 步：创建 HTML 入口

新建 `frontend/index.html`：

```html
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta
      name="description"
      content="陕西高速路网应急指挥 Agent 教学演示台"
    />
    <title>陕西高速 AI 应急指挥台</title>
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="/src/main.js"></script>
  </body>
</html>
```

如果课程成品中的 meta 文案略有不同，不影响运行；核心是 `#app` 和 module 入口。

### 第 4 步：创建 main.js

新建 `frontend/src/main.js`：

```javascript
import { createApp } from "vue";

import App from "./App.vue";
import "./style.css";

createApp(App).mount("#app");
```

### 第 5 步：创建临时 App 骨架

正式 App 在 Day 4 完成。先创建合法组件：

```vue
<template>
  <main>
    <h1>陕西高速路网应急指挥 Agent</h1>
  </main>
</template>
```

Day 4 会替换为最终正式内容，这不是单独的玩具项目，而是同一个文件的增量开发。

### 第 6 步：安装并启动

```bash
cd frontend
npm install
npm run dev
```

浏览器打开：

```text
http://127.0.0.1:5173
```

### 运行与预期输出

终端应包含类似：

```text
VITE ready
Local: http://localhost:5173/
```

页面显示：

```text
陕西高速路网应急指挥 Agent
```

### 对应测试

今天还没有组件行为测试。先验证生产构建骨架：

```bash
npm run build
```

预期生成 `frontend/dist`。

### 常见错误

错误 1：Node 版本不足

Vite 7 要求较新 Node，升级到 20.19 或更高。

错误 2：5173 被占用

停止旧 Vite 进程，不要随意改端口后忘记课程命令。

错误 3：无法导入 .vue

确认安装 `@vitejs/plugin-vue` 并配置 plugins。

错误 4：页面空白

检查 index.html 的 `#app` 和 main.js mount 选择器一致。

错误 5：网络环境无法 npm install

这是依赖下载问题，不是代码问题；可更换可用 npm registry 后重试。不要提交 node_modules。

### 当天小练习

把浏览器宽度缩小到 375px，确认基础页面仍能显示；Day 4 再实现正式响应式布局。

### 今日总结与明日预告

Vue/Vite 工程和代理已建立。

明天创建唯一网络边界 api.js 和完整事件表单。

## 5. Day 2：实现 Supervisor API 客户端与事件录入表单

### 今天目标

1. 创建唯一前端网络函数。
2. POST JSON 到 Supervisor。
3. 处理非 2xx。
4. 注入 fetch 方便测试。
5. 创建响应式默认表单。
6. 复制 required_resources。
7. 发出 submit 事件。
8. 展示 loading 状态。

### 上一节衔接

Day 1 已能启动 Vue。

今天完成用户输入到 SupervisorRequest 的映射。

### 先说结论

组件不直接调用 fetch。

```text
IncidentForm -> emit payload
App -> runSupervisor(payload)
api.js -> fetch
```

这样网络错误和测试集中在一个文件。

### 第 1 步：创建 api.js

新建 `frontend/src/api.js`：

```javascript
/**
 * 调用 Supervisor 的唯一前端网络边界。
 * 通过注入 fetchImpl，单元测试不需要真实启动后端。
 */
export async function runSupervisor(
  payload,
  fetchImpl = fetch,
) {
  const response = await fetchImpl(
    "/api/agents/supervisor/invoke",
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    },
  );

  const data = await response.json();

  if (!response.ok) {
    const detail =
      typeof data.detail === "string"
        ? data.detail
        : JSON.stringify(data.detail);

    throw new Error(
      `请求失败（${response.status}）：${detail}`
    );
  }

  return data;
}
```

### 第 2 步：创建 IncidentForm 脚本

新建 `frontend/src/components/IncidentForm.vue`：

```vue
<script setup>
import { reactive } from "vue";

defineProps({
  loading: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits(["submit"]);

// 默认场景保证学习者第一次启动就能得到完整四 Agent 轨迹。
const form = reactive({
  incident_id: "INC-DEMO-010",
  raw_text: "秦岭隧道追尾出现烟雾，2人受伤，占用2车道",
  road_code: "G65",
  section_id: "QINLING-01",
  camera_id: "CAM-QINLING-01",
  required_resources: [
    "ambulance",
    "tow_truck",
  ],
  human_approved: false,
});

function submit() {
  // 复制数组，避免请求过程中修改响应式表单对象。
  emit("submit", {
    ...form,
    required_resources: [
      ...form.required_resources,
    ],
  });
}
</script>
```

### 第 3 步：创建表单结构

继续在同一文件添加：

```vue
<template>
  <form
    class="incident-form"
    @submit.prevent="submit"
  >
    <div class="section-heading">
      <span class="step-number">01</span>
      <div>
        <p class="eyebrow">INCIDENT INPUT</p>
        <h2>事件录入</h2>
      </div>
    </div>

    <label class="field field-wide">
      <span>现场描述</span>
      <textarea
        v-model="form.raw_text"
        data-test="incident-text"
        rows="5"
        required
      />
      <small>
        请包含伤亡、车道占用和可见风险，便于结构化研判。
      </small>
    </label>
```

### 第 4 步：增加定位字段

继续：

```vue
    <div class="field-grid">
      <label class="field">
        <span>事件编号</span>
        <input
          v-model="form.incident_id"
          required
        />
      </label>

      <label class="field">
        <span>高速编号</span>
        <input
          v-model="form.road_code"
          required
        />
      </label>

      <label class="field">
        <span>路段编号</span>
        <input
          v-model="form.section_id"
          required
        />
      </label>

      <label class="field">
        <span>摄像头编号</span>
        <input v-model="form.camera_id" />
      </label>
    </div>
```

### 第 5 步：增加资源多选

继续：

```vue
    <fieldset>
      <legend>建议查询的应急资源</legend>

      <label class="check-option">
        <input
          v-model="form.required_resources"
          type="checkbox"
          value="ambulance"
        />
        <span>救护车</span>
      </label>

      <label class="check-option">
        <input
          v-model="form.required_resources"
          type="checkbox"
          value="tow_truck"
        />
        <span>清障车</span>
      </label>
    </fieldset>
```

### 第 6 步：增加提交按钮和安全说明

完成 template：

```vue
    <button
      class="primary-button"
      type="submit"
      :disabled="loading"
    >
      <span>
        {{
          loading
            ? "Agent 协同处理中…"
            : "启动应急研判"
        }}
      </span>
      <span aria-hidden="true">→</span>
    </button>

    <p class="form-note">
      演示模式仅生成建议，任何高风险动作都不会自动执行。
    </p>
  </form>
</template>
```

### 第 7 步：测试 API 成功与错误

新建 `frontend/src/api.test.js`：

```javascript
import {
  describe,
  expect,
  it,
  vi,
} from "vitest";

import { runSupervisor } from "./api";

describe("runSupervisor", () => {
  it("返回 Supervisor 的结构化结果", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        status: "awaiting_approval",
      }),
    });

    const result = await runSupervisor(
      { incident_id: "INC-010" },
      fetchImpl,
    );

    expect(result.status).toBe(
      "awaiting_approval"
    );
    expect(fetchImpl).toHaveBeenCalledWith(
      "/api/agents/supervisor/invoke",
      expect.objectContaining({
        method: "POST",
      }),
    );
  });

  it("把后端校验错误转换成可展示异常", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: false,
      status: 422,
      json: async () => ({
        detail: "字段校验失败",
      }),
    });

    await expect(
      runSupervisor({}, fetchImpl)
    ).rejects.toThrow(
      "请求失败（422）：字段校验失败"
    );
  });
});
```

### 运行与预期输出

执行：

```bash
cd frontend
npm run test:run -- src/api.test.js
```

预期：

```text
2 tests passed
```

### 对应测试

API 测试不启动后端，使用注入的 `fetchImpl`。

重点验证 URL、POST 和错误文案。

### 常见错误

错误 1：组件直接 fetch

网络逻辑统一在 api.js。

错误 2：response.ok 为 false 仍返回 data

必须 throw，让 App 展示 error。

错误 3：required_resources 与响应式对象共享

提交时复制数组。

错误 4：默认文本缺伤亡/车道

会导致 needs_input，无法展示完整 Trace；默认场景要完整。

错误 5：把 human_approved 默认 true

界面默认必须等待审批。

### 当天小练习

在 API 测试中断言 fetch body 解析后 `incident_id=INC-010`，确认 payload 被 JSON.stringify。

### 今日总结与明日预告

表单和 API 网络边界完成。

明天创建结果面板和 Agent Trace 组件。

## 6. Day 3：创建结果卡片与 Agent 执行轨迹

### 今天目标

1. 创建 AgentTrace。
2. 映射内部 Agent 名称。
3. 展示 attempt/success。
4. 创建 ResultPanel。
5. 映射 Supervisor 状态。
6. 展示四类结果卡片。
7. 展示审批 Banner。
8. 处理空状态。

### 上一节衔接

Day 2 能提交事件，但还没有展示响应。

今天把结构化 SupervisorResult 映射到两个组件。

### 先说结论

不要把整个 JSON 原样丢给用户。

面试演示最重要的结构：

```text
状态
风险
预案
资源
安全
轨迹
审批
```

### 第 1 步：创建 AgentTrace 脚本

新建 `frontend/src/components/AgentTrace.vue`：

```vue
<script setup>
const props = defineProps({
  trace: {
    type: Array,
    default: () => [],
  },
});

const labels = {
  incident_analysis: "事件研判 Agent",
  plan_expert: "预案专家 Agent",
  resource_dispatch: "资源调度 Agent",
  safety_review: "安全复核 Agent",
};
</script>
```

### 第 2 步：创建 Trace 模板

```vue
<template>
  <section class="trace-section">
    <div class="section-heading compact">
      <span class="step-number">02</span>
      <div>
        <p class="eyebrow">AGENT TRACE</p>
        <h2>协同轨迹</h2>
      </div>
    </div>

    <ol
      v-if="props.trace.length"
      class="trace-list"
    >
      <li
        v-for="(step, index) in props.trace"
        :key="`${step.agent_name}-${step.attempt}`"
      >
        <span class="trace-index">
          {{
            String(index + 1).padStart(
              2,
              "0",
            )
          }}
        </span>
        <span
          class="trace-line"
          aria-hidden="true"
        ></span>

        <div class="trace-content">
          <strong>
            {{
              labels[step.agent_name]
                || step.agent_name
            }}
          </strong>
          <span>
            第 {{ step.attempt }} 次尝试
          </span>
        </div>

        <span
          :class="[
            'status-dot',
            step.success
              ? 'success'
              : 'failed',
          ]"
        >
          {{
            step.success
              ? "完成"
              : "失败"
          }}
        </span>
      </li>
    </ol>

    <div v-else class="empty-state">
      提交事件后，这里会显示每个 Agent 的执行顺序。
    </div>
  </section>
</template>
```

key 同时包含 agent_name 和 attempt，重试时不会冲突。

### 第 3 步：创建 ResultPanel 状态映射

新建 `frontend/src/components/ResultPanel.vue`：

```vue
<script setup>
import { computed } from "vue";

const props = defineProps({
  result: {
    type: Object,
    default: null,
  },
});

const statusLabel = computed(() => {
  const labels = {
    awaiting_approval: "等待人工审批",
    ready: "建议已就绪",
    needs_revision: "需要补充证据",
    blocked: "安全复核阻断",
    step_limit: "达到步数上限",
    failed: "协同流程失败",
  };

  return (
    labels[props.result?.status]
    || "尚未运行"
  );
});
</script>
```

### 第 4 步：创建结果 Header

```vue
<template>
  <section class="result-section">
    <div class="result-header">
      <div>
        <p class="eyebrow">
          DECISION SUPPORT
        </p>
        <h2>辅助决策结果</h2>
      </div>

      <span
        :class="[
          'decision-status',
          result?.status || 'idle',
        ]"
      >
        {{ statusLabel }}
      </span>
    </div>
```

### 第 5 步：创建四张结果卡片

继续：

```vue
    <div
      v-if="result"
      class="result-grid"
    >
      <article class="result-card risk-card">
        <span class="card-label">风险等级</span>
        <strong>
          {{ result.incident?.risk_level || "未知" }}
        </strong>
        <p>
          {{
            result.incident?.incident_type
            || "尚未识别事件类型"
          }}
        </p>
      </article>

      <article class="result-card">
        <span class="card-label">预案依据</span>
        <strong>
          {{
            result.plan?.citations?.length
            || 0
          }} 条引用
        </strong>
        <p>
          {{
            result.plan?.summary
            || "未生成预案建议"
          }}
        </p>
      </article>

      <article class="result-card">
        <span class="card-label">资源建议</span>
        <strong>
          {{
            result.dispatch?.assignments?.length
            || 0
          }} 项资源
        </strong>
        <p>
          {{
            result.dispatch?.unmet_requirements?.length
              ? "存在资源缺口"
              : "当前需求可满足"
          }}
        </p>
      </article>

      <article class="result-card safety-card">
        <span class="card-label">安全复核</span>
        <strong>
          {{
            result.safety?.verdict
            || "未复核"
          }}
        </strong>
        <p>
          {{
            result.safety?.reasons?.[0]
            || "全部规则检查通过"
          }}
        </p>
      </article>
    </div>
```

可选链防止 needs_input 等部分结果导致前端异常。

### 第 6 步：创建审批 Banner 和空状态

完成：

```vue
    <div
      v-if="result?.awaiting_human_approval"
      class="approval-banner"
    >
      <span
        class="approval-icon"
        aria-hidden="true"
      >!</span>
      <div>
        <strong>
          高风险动作已暂停，等待人工审批
        </strong>
        <p>
          系统已生成调度建议，但已执行动作仍为
          {{ result.executed_actions.length }} 项。
        </p>
      </div>
    </div>

    <div
      v-if="!result"
      class="empty-state result-empty"
    >
      <span aria-hidden="true">⌁</span>
      <p>
        运行 Supervisor 后展示研判、预案、资源和安全复核结果。
      </p>
    </div>
  </section>
</template>
```

### 运行与预期输出

组件还未装入 App，先运行 Vue 编译：

```bash
cd frontend
npm run build
```

预期成功生成 dist，无 template 语法错误。

### 对应测试

Day 5 的 App.test 会通过完整 App 验证两个组件文本。

今天可选单独 mount 组件，不作为必做。

### 常见错误

错误 1：result 为 null 时访问属性

使用可选链和 v-if。

错误 2：Trace key 只用 agent_name

重试会重复，加入 attempt。

错误 3：显示 proposed actions 为已执行

Banner 只读取 executed_actions 数量，并明确暂停。

错误 4：资源 dispatch 为 null 报错

使用 `result.dispatch?.assignments?.length || 0`。

错误 5：失败 Trace 仍显示完成

根据 step.success 切换 class 和文字。

### 当天小练习

构造一个含 incident_analysis 两次尝试的静态 trace，确认页面显示“第 1 次失败、第 2 次完成”。

### 今日总结与明日预告

结果和轨迹组件完成。

明天在 App 中管理 loading/result/error，并添加最终响应式样式。

## 7. Day 4：组装 App 状态并完成响应式指挥台样式

### 今天目标

1. 在 App 导入三个组件。
2. 管理 loading/result/error。
3. 用 try/catch/finally 调用 API。
4. 创建顶部、Hero、工作区和页脚。
5. 展示错误 Banner。
6. 加入深色应急指挥视觉。
7. 支持 980/620 断点。
8. 明确 mock 与零自动执行。

### 上一节衔接

Day 2/3 已有表单、网络、结果和轨迹组件。

今天组装最终页面。

### 先说结论

请求状态：

```text
submit
  -> loading=true
  -> error=""
  -> await runSupervisor
       -> result
       -> 或 error
  -> finally loading=false
```

finally 保证成功/失败都恢复按钮。

### 第 1 步：创建 App 脚本

将 `frontend/src/App.vue` 替换为：

```vue
<script setup>
import { ref } from "vue";

import { runSupervisor } from "./api";
import AgentTrace from "./components/AgentTrace.vue";
import IncidentForm from "./components/IncidentForm.vue";
import ResultPanel from "./components/ResultPanel.vue";

const loading = ref(false);
const result = ref(null);
const error = ref("");

async function handleSubmit(payload) {
  loading.value = true;
  error.value = "";

  try {
    result.value = await runSupervisor(
      payload
    );
  } catch (requestError) {
    error.value =
      requestError instanceof Error
        ? requestError.message
        : "未知请求错误";
  } finally {
    loading.value = false;
  }
}
</script>
```

### 第 2 步：创建顶部与 Hero

继续：

```vue
<template>
  <div class="app-shell">
    <header class="topbar">
      <a
        class="brand"
        href="#"
        aria-label="陕西高速 AI 应急指挥台首页"
      >
        <span class="brand-mark">S</span>
        <span>
          <strong>陕西高速</strong>
          <small>
            AI EMERGENCY COMMAND
          </small>
        </span>
      </a>

      <div class="system-state">
        <span></span>
        教学演示系统在线
      </div>
    </header>

    <main>
      <section class="hero">
        <div>
          <p class="eyebrow">
            SHAANXI EXPRESSWAY NETWORK
          </p>
          <h1>
            路网应急指挥 <em>Agent</em>
          </h1>
          <p class="hero-copy">
            从事件上报到安全复核，用可追溯的多 Agent 协同生成辅助决策。
          </p>
        </div>

        <dl class="hero-metrics">
          <div>
            <dt>专业 Agent</dt>
            <dd>4</dd>
          </div>
          <div>
            <dt>Supervisor</dt>
            <dd>1</dd>
          </div>
          <div>
            <dt>自动执行</dt>
            <dd>0</dd>
          </div>
        </dl>
      </section>
```

### 第 3 步：组装工作区和错误

继续：

```vue
      <div
        v-if="error"
        class="error-banner"
        role="alert"
      >
        {{ error }}
      </div>

      <section class="workspace-grid">
        <aside class="input-panel">
          <IncidentForm
            :loading="loading"
            @submit="handleSubmit"
          />
        </aside>

        <div class="output-panel">
          <ResultPanel
            :result="result"
          />
          <AgentTrace
            :trace="result?.route_trace || []"
          />
        </div>
      </section>
    </main>
```

### 第 4 步：创建页脚

完成 App：

```vue
    <footer>
      <span>
        数据来源：课程合成数据
      </span>
      <span>
        MODEL_MODE=mock · 不连接真实高速系统
      </span>
    </footer>
  </div>
</template>
```

### 第 5 步：创建 CSS 基础变量和布局

新建 `frontend/src/style.css`，先写：

```css
@import url("https://fonts.googleapis.com/css2?family=Manrope:wght@500;600;700&family=Noto+Sans+SC:wght@400;500;600;700&display=swap");

:root {
  font-family: "Manrope", "Noto Sans SC", sans-serif;
  color: #eaf0f6;
  background: #07121d;
  font-synthesis: none;
  --navy: #07121d;
  --panel: #0c1b29;
  --panel-light: #112536;
  --line: rgba(151, 177, 198, 0.17);
  --muted: #8fa5b8;
  --cyan: #37d3cb;
  --amber: #f3b34c;
  --red: #ff6d67;
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  min-width: 320px;
  min-height: 100vh;
}

button,
input,
textarea {
  font: inherit;
}

button {
  cursor: pointer;
}

.app-shell {
  min-height: 100vh;
  background:
    radial-gradient(
      circle at 78% 8%,
      rgba(55, 211, 203, 0.09),
      transparent 28rem
    ),
    linear-gradient(
      rgba(255, 255, 255, 0.018) 1px,
      transparent 1px
    ),
    linear-gradient(
      90deg,
      rgba(255, 255, 255, 0.018) 1px,
      transparent 1px
    ),
    var(--navy);
  background-size:
    auto,
    48px 48px,
    48px 48px,
    auto;
}
```

### 第 6 步：增加核心网格和状态样式

继续添加与成品一致的关键布局：

```css
.topbar,
main,
footer {
  max-width: 1440px;
  margin: 0 auto;
}

.topbar {
  height: 74px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 42px;
  border-bottom: 1px solid var(--line);
}

main {
  padding: 58px 42px 48px;
}

.hero {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-bottom: 42px;
}

.workspace-grid {
  display: grid;
  grid-template-columns:
    minmax(320px, 0.78fr)
    minmax(480px, 1.42fr);
  gap: 18px;
}

.input-panel,
.result-section,
.trace-section {
  background: rgba(12, 27, 41, 0.94);
  border: 1px solid var(--line);
}

.input-panel,
.result-section,
.trace-section {
  padding: 28px;
}

.output-panel {
  display: grid;
  gap: 18px;
}

.result-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 9px;
}

.decision-status.awaiting_approval {
  color: var(--amber);
  border-color: rgba(243, 179, 76, 0.38);
  background: rgba(243, 179, 76, 0.07);
}

.decision-status.ready {
  color: var(--cyan);
}

.decision-status.blocked,
.decision-status.failed {
  color: var(--red);
}

.error-banner {
  color: #ffaaa6;
  background: rgba(255, 109, 103, 0.08);
  border: 1px solid rgba(255, 109, 103, 0.3);
  padding: 12px 15px;
  margin-bottom: 15px;
  font-size: 12px;
}
```

继续在同一文件补齐品牌、表单、卡片和轨迹样式：

```css
.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  color: inherit;
  text-decoration: none;
}

.brand-mark {
  width: 37px;
  height: 37px;
  display: grid;
  place-items: center;
  color: #06201f;
  background: var(--cyan);
  font-weight: 800;
  border-radius: 3px 12px 3px 3px;
}

.brand strong,
.brand small {
  display: block;
}

.brand strong {
  font-size: 16px;
  letter-spacing: 0.08em;
}

.brand small {
  color: var(--muted);
  font-size: 8px;
  letter-spacing: 0.16em;
  margin-top: 2px;
}

.system-state {
  color: #a9bbc9;
  font-size: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.system-state span {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--cyan);
  box-shadow: 0 0 12px var(--cyan);
}

.eyebrow {
  color: var(--cyan);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.2em;
  margin: 0 0 9px;
}

h1 {
  font-size: clamp(34px, 5vw, 62px);
  letter-spacing: -0.045em;
  line-height: 1.05;
  margin: 0;
}

h1 em {
  color: var(--cyan);
  font-style: normal;
  font-weight: 500;
}

.hero-copy {
  color: var(--muted);
  max-width: 610px;
  margin: 17px 0 0;
  line-height: 1.8;
}

.hero-metrics {
  display: flex;
  gap: 8px;
  margin: 0;
}

.hero-metrics div {
  min-width: 105px;
  padding: 15px 18px;
  border: 1px solid var(--line);
  background: rgba(10, 28, 42, 0.65);
}

.hero-metrics dt {
  color: var(--muted);
  font-size: 10px;
}

.hero-metrics dd {
  font-size: 24px;
  font-weight: 700;
  margin: 5px 0 0;
}

.section-heading {
  display: flex;
  align-items: center;
  gap: 13px;
  margin-bottom: 27px;
}

.section-heading.compact {
  margin-bottom: 20px;
}

.section-heading h2,
.result-header h2 {
  font-size: 20px;
  margin: 0;
}

.section-heading .eyebrow {
  margin-bottom: 3px;
}

.step-number {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  color: var(--cyan);
  border: 1px solid rgba(55, 211, 203, 0.5);
  font-size: 11px;
}

.field-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 15px;
}

.field {
  display: grid;
  gap: 7px;
  margin-bottom: 15px;
}

.field > span,
fieldset legend {
  color: #b9c8d4;
  font-size: 12px;
}

.field small {
  color: #667f93;
  font-size: 10px;
  line-height: 1.5;
}

.field input,
.field textarea {
  width: 100%;
  color: #eef6fa;
  background: #091723;
  border: 1px solid #1e3548;
  border-radius: 2px;
  padding: 11px 12px;
  outline: none;
  resize: vertical;
}

.field input:focus,
.field textarea:focus {
  border-color: var(--cyan);
  box-shadow: 0 0 0 2px rgba(55, 211, 203, 0.08);
}

fieldset {
  display: flex;
  gap: 18px;
  border: 0;
  border-top: 1px solid var(--line);
  margin: 10px 0 22px;
  padding: 18px 0 0;
}

fieldset legend {
  padding: 0 8px 0 0;
}

.check-option {
  display: flex;
  align-items: center;
  gap: 7px;
  color: #d4e0e7;
  font-size: 12px;
}

.check-option input {
  accent-color: var(--cyan);
}

.primary-button {
  width: 100%;
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: #032120;
  background: var(--cyan);
  border: 0;
  padding: 14px 16px;
  font-weight: 700;
  transition: transform 0.15s, filter 0.15s;
}

.primary-button:hover {
  filter: brightness(1.08);
  transform: translateY(-1px);
}

.primary-button:disabled {
  opacity: 0.55;
  cursor: wait;
  transform: none;
}

.form-note {
  color: #667f93;
  font-size: 10px;
  text-align: center;
  margin: 12px 0 0;
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 22px;
}

.decision-status {
  color: var(--muted);
  background: #0a1824;
  border: 1px solid var(--line);
  padding: 7px 10px;
  font-size: 11px;
}

.result-card {
  min-height: 132px;
  background: var(--panel-light);
  border-top: 2px solid #46637a;
  padding: 16px;
}

.result-card.risk-card {
  border-color: var(--red);
}

.result-card.safety-card {
  border-color: var(--amber);
}

.card-label {
  color: var(--muted);
  font-size: 10px;
}

.result-card strong {
  display: block;
  font-size: 18px;
  margin: 14px 0 6px;
  text-transform: uppercase;
}

.result-card p {
  color: #8fa5b8;
  font-size: 10px;
  line-height: 1.55;
  margin: 0;
}

.approval-banner {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-top: 15px;
  padding: 13px 15px;
  border: 1px solid rgba(243, 179, 76, 0.25);
  background: rgba(243, 179, 76, 0.07);
}

.approval-icon {
  display: grid;
  place-items: center;
  flex: 0 0 27px;
  height: 27px;
  color: #17200c;
  background: var(--amber);
  font-weight: 800;
  border-radius: 50%;
}

.approval-banner strong {
  color: #f7c873;
  font-size: 12px;
}

.approval-banner p {
  color: #9e9278;
  font-size: 10px;
  margin: 3px 0 0;
}

.trace-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  grid-template-columns: repeat(4, 1fr);
}

.trace-list li {
  position: relative;
  display: grid;
  grid-template-columns: 30px 1fr;
  grid-template-rows: auto auto;
  gap: 9px;
}

.trace-index {
  z-index: 1;
  display: grid;
  place-items: center;
  width: 27px;
  height: 27px;
  border: 1px solid var(--cyan);
  color: var(--cyan);
  background: var(--panel);
  font-size: 9px;
}

.trace-line {
  position: absolute;
  height: 1px;
  left: 27px;
  right: 0;
  top: 13px;
  background: rgba(55, 211, 203, 0.35);
}

.trace-content {
  grid-column: 1 / -1;
}

.trace-content strong,
.trace-content span {
  display: block;
}

.trace-content strong {
  font-size: 11px;
}

.trace-content span {
  color: var(--muted);
  font-size: 9px;
  margin-top: 4px;
}

.status-dot {
  grid-column: 1 / -1;
  width: max-content;
  padding: 3px 7px;
  font-size: 8px;
  border-radius: 8px;
}

.status-dot.success {
  color: var(--cyan);
  background: rgba(55, 211, 203, 0.09);
}

.status-dot.failed {
  color: var(--red);
  background: rgba(255, 109, 103, 0.1);
}

.empty-state {
  color: #657f92;
  border: 1px dashed #243d50;
  padding: 28px;
  text-align: center;
  font-size: 11px;
}

.result-empty {
  min-height: 174px;
  display: grid;
  place-content: center;
}

.result-empty span {
  color: var(--cyan);
  font-size: 34px;
}

.result-empty p {
  margin: 8px 0 0;
}

footer {
  display: flex;
  justify-content: space-between;
  color: #5f778a;
  border-top: 1px solid var(--line);
  padding: 22px 42px 32px;
  font-size: 9px;
  letter-spacing: 0.08em;
}
```

### 第 7 步：添加响应式断点

文件末尾：

```css
@media (max-width: 980px) {
  .hero {
    align-items: flex-start;
    gap: 30px;
  }

  .hero-metrics {
    display: none;
  }

  .workspace-grid {
    grid-template-columns: 1fr;
  }

  .result-grid {
    grid-template-columns: 1fr 1fr;
  }
}

@media (max-width: 620px) {
  .topbar {
    padding: 0 20px;
  }

  .system-state {
    display: none;
  }

  main {
    padding: 38px 20px;
  }

  .field-grid,
  .result-grid {
    grid-template-columns: 1fr;
  }

  .trace-list {
    grid-template-columns: 1fr;
    gap: 15px;
  }

  .trace-line {
    display: none;
  }

  footer {
    padding: 20px;
    flex-direction: column;
    gap: 8px;
  }
}
```

### 运行与预期输出

终端 A：

```bash
make run-backend
```

终端 B：

```bash
make run-frontend
```

打开 5173，提交默认事件。

预期显示：

- 等待人工审批。
- critical/tunnel_smoke。
- 预案引用。
- 两项资源。
- 安全 BLOCK。
- 四个 Agent 轨迹。
- 已执行动作 0。

### 对应测试

今天先手动检查桌面和移动宽度，Day 5 用 App.test 自动验证关键文本。

### 常见错误

错误 1：提交后 loading 不恢复

必须使用 finally。

错误 2：新错误前保留旧 error

请求开始时清空。

错误 3：result 未传到两个组件

ResultPanel 用 result；AgentTrace 用 route_trace。

错误 4：CSS 移动端仍两列

检查 980/620 media query。

错误 5：外部字体离线失败

浏览器会回退到 sans-serif，不影响功能测试。

### 当天小练习

让后端暂时停止，再提交表单。确认页面显示 error-banner，按钮从 loading 恢复可点击。然后重启后端。

### 今日总结与明日预告

轻量指挥台已经完整可用。

明天写组件测试、运行前后端测试和生产构建。

## 8. Day 5：编写 Vitest、构建前端并完成验收

### 今天目标

1. Mock api 模块。
2. mount App。
3. 验证默认表单。
4. 触发表单 submit。
5. 等待 Promise。
6. 验证审批状态。
7. 验证四 Agent 轨迹。
8. 运行前后端测试和 build。

### 上一节衔接

Day 4 已手动运行完整页面。

今天把关键演示路径固化为自动测试。

### 先说结论

前端测试不启动真实后端。

```text
vi.mock("./api")
  -> 固定 SupervisorResult
  -> mount App
  -> submit
  -> 验证 UI
```

API 序列化已由 api.test 单独验证。

### 第 1 步：创建 App 测试导入和 Mock

新建 `frontend/src/App.test.js`：

```javascript
import {
  flushPromises,
  mount,
} from "@vue/test-utils";
import {
  describe,
  expect,
  it,
  vi,
} from "vitest";

import App from "./App.vue";

vi.mock("./api", () => ({
  runSupervisor: vi.fn().mockResolvedValue({
    status: "awaiting_approval",
    awaiting_human_approval: true,
    executed_actions: [],
    incident: {
      risk_level: "critical",
      incident_type: "tunnel_smoke",
    },
    plan: {
      summary: "已生成建议",
      actions: [],
      citations: [],
    },
    dispatch: {
      assignments: [],
      unmet_requirements: [],
    },
    safety: {
      verdict: "BLOCK",
      reasons: [
        "高风险动作需要人工审批"
      ],
    },
    route_trace: [
      {
        agent_name: "incident_analysis",
        attempt: 1,
        success: true,
      },
      {
        agent_name: "plan_expert",
        attempt: 1,
        success: true,
      },
      {
        agent_name: "resource_dispatch",
        attempt: 1,
        success: true,
      },
      {
        agent_name: "safety_review",
        attempt: 1,
        success: true,
      },
    ],
  }),
}));
```

### 第 2 步：测试默认表单

继续：

```javascript
describe("App", () => {
  it("展示课程默认事件表单", () => {
    const wrapper = mount(App);

    expect(
      wrapper.get(
        "[data-test='incident-text']"
      ).element.value
    ).toContain("秦岭隧道");

    expect(wrapper.text()).toContain(
      "启动应急研判"
    );
  });
```

data-test 选择器比依赖 CSS 类更稳定。

### 第 3 步：测试提交结果

继续完成：

```javascript
  it("提交后显示人工审批状态与四个 Agent 轨迹", async () => {
    const wrapper = mount(App);

    await wrapper.get("form").trigger(
      "submit"
    );
    await flushPromises();

    expect(wrapper.text()).toContain(
      "等待人工审批"
    );
    expect(wrapper.text()).toContain(
      "事件研判 Agent"
    );
    expect(wrapper.text()).toContain(
      "预案专家 Agent"
    );
    expect(wrapper.text()).toContain(
      "资源调度 Agent"
    );
    expect(wrapper.text()).toContain(
      "安全复核 Agent"
    );
  });
});
```

`flushPromises()` 等待 Mock API Promise 和 Vue 更新。

### 第 4 步：运行前端测试

```bash
cd frontend
npm run test:run
```

预期 api 2 条、App 2 条，共 4 条通过。

### 第 5 步：运行构建

```bash
npm run build
```

预期生成：

```text
frontend/dist/index.html
frontend/dist/assets/*
```

### 第 6 步：运行后端评测

回到 Week 根：

```bash
cd ..
make eval
```

本周评测继续聚焦 Supervisor 和 Safety，保证前端依赖的状态稳定。

### 第 7 步：统一验收

```bash
make test
make eval
make verify
```

`make test` 同时跑后端 pytest 和前端 Vitest；`make verify` 还执行 Compose 静态校验和前端 build。

### 运行与预期输出

后端：

```text
65 passed
```

前端：

```text
Test Files  2 passed
Tests       4 passed
```

构建：

```text
vite build
built in ...
```

### 对应测试

最终检查：

```bash
.venv/bin/python -m pytest backend/tests -q
cd frontend
npm run test:run
npm run build
```

### 常见错误

错误 1：提交测试找不到 form

确认 IncidentForm 已在 App 渲染。

错误 2：文本断言太早

调用 `await flushPromises()`。

错误 3：测试访问真实 fetch

在 import App 后是否正确 vi.mock；当前 Vitest 会提升 mock。

错误 4：jsdom 未配置

vite.config test.environment 必须是 jsdom。

错误 5：构建成功但 API 不通

开发代理需要前后端同时运行；构建只验证静态资源。

### 当天小练习

增加 API 失败的 App 测试：

- Mock runSupervisor reject Error。
- 提交。
- 断言 role=alert。
- 断言错误文案。
- 断言按钮恢复“启动应急研判”。

### 今日总结与明日预告

第 10 周完成可测试、可构建的求职演示界面。

第 11 周将建立正式评测集、可靠性组件和可观察性，不再主要新增 UI。

## 9. 本周唯一实战作业

任务：在 ResultPanel 增加“资源到达时间列表”。

要求：

1. 有 assignments 时逐条显示 name、resource_type、eta_minutes。
2. 无 dispatch 时不报错。
3. partial 时同时显示 unmet_requirements。
4. 使用语义化列表。
5. 增加 App 测试 fixture 两条资源。
6. 断言显示 6 分钟、9 分钟。
7. 不显示为“已派出”。
8. 移动端单列。
9. `make test`、`make eval`、`make verify` 通过。

## 10. 测试、常见错误与系统排查

前后端诊断：

```text
页面请求失败
  -> 浏览器 Network
  -> Vite 5173 是否运行
  -> proxy 是否 /api -> 8000
  -> FastAPI 8000 health
  -> 请求 JSON 是否符合 SupervisorRequest
  -> 后端 response body
```

命令：

```bash
curl http://127.0.0.1:8000/health
cd frontend
npm run test:run
npm run build
cd ..
make test
```

症状表：

| 症状 | 原因 |
|---|---|
| npm install 失败 | Node/网络/registry |
| 页面空白 | main mount 或 Vue 编译错误 |
| 404 /api | Vite proxy 或后端路由 |
| 422 | 表单字段不符合后端 |
| CORS | 没通过 Vite proxy |
| 测试 window 未定义 | 未配置 jsdom |
| 结果组件报 null | 缺可选链/v-if |
| 移动端溢出 | grid 断点错误 |

学习范围控制：

- 一个页面。
- 三个子组件。
- 一个 API 函数。
- 两个测试文件。
- 不引入全局状态库。
- 不引入 UI 大型框架。
- 不引入地图和图表库。

## 11. 通关清单与三道面试题

- [ ] 能创建 Vite/Vue 工程。
- [ ] 能配置 /api proxy。
- [ ] 能编写可注入 fetch 的 API 函数。
- [ ] 能创建响应式表单。
- [ ] 能 emit 提交事件。
- [ ] 能处理 loading/error/result。
- [ ] 能展示 Supervisor 结构化结果。
- [ ] 能展示重试 Trace。
- [ ] 能明确审批和零执行。
- [ ] 能写 Vitest/jsdom 测试。
- [ ] 能生产构建。
- [ ] 能让 `make test`、`make eval`、`make verify` 通过。

### 面试题 1

为什么前端网络请求封装在 api.js，而不是写进每个组件？

回答要点：

统一 URL、JSON 序列化和错误处理；组件只负责交互与展示。fetch 可注入，使单元测试不依赖真实后端；未来切换认证、超时或 API base 也只改一处。

### 面试题 2

为什么界面要展示 route_trace 和 executed_actions？

回答要点：

多 Agent 系统需要可解释性。route_trace 显示实际调用顺序、尝试次数和失败；executed_actions 证明建议与执行分离，未审批状态为 0，增强演示可信度。

### 面试题 3

Vite 开发代理和生产部署代理有什么区别？

回答要点：

开发时 Vite 5173 将 /api 转发到本地 8000，避免 CORS；生产 build 是静态文件，需由 Nginx/Ingress 或同域后端路由 /api，Vite dev proxy 不会进入生产包。

## 12. 本周总结与下一周衔接

本周把后端能力变成可演示产品：

```text
事件表单
+ Supervisor API
+ 决策卡片
+ Agent Trace
+ 审批提示
+ 错误处理
+ 响应式页面
+ 前端测试与构建
```

进入第 11 周前执行：

```bash
make test
make eval
make verify
```

第 11 周新增工程质量能力：

- JSONL 评测数据。
- 结构化输出率。
- Tool 选择正确率。
- 场景成功率。
- 未授权动作率。
- 重试与断路器。
- 审计事件与指标。
- 安全回归集。
- 最终验收阈值。

UI 保持轻量，不扩展新功能。
