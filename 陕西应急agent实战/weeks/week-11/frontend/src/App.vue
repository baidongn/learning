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
    result.value = await runSupervisor(payload);
  } catch (requestError) {
    error.value = requestError instanceof Error ? requestError.message : "未知请求错误";
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <div class="app-shell">
    <header class="topbar">
      <a class="brand" href="#" aria-label="陕西高速 AI 应急指挥台首页">
        <span class="brand-mark">S</span>
        <span>
          <strong>陕西高速</strong>
          <small>AI EMERGENCY COMMAND</small>
        </span>
      </a>
      <div class="system-state"><span></span> 教学演示系统在线</div>
    </header>

    <main>
      <section class="hero">
        <div>
          <p class="eyebrow">SHAANXI EXPRESSWAY NETWORK</p>
          <h1>路网应急指挥 <em>Agent</em></h1>
          <p class="hero-copy">从事件上报到安全复核，用可追溯的多 Agent 协同生成辅助决策。</p>
        </div>
        <dl class="hero-metrics">
          <div><dt>专业 Agent</dt><dd>4</dd></div>
          <div><dt>Supervisor</dt><dd>1</dd></div>
          <div><dt>自动执行</dt><dd>0</dd></div>
        </dl>
      </section>

      <div v-if="error" class="error-banner" role="alert">{{ error }}</div>

      <section class="workspace-grid">
        <aside class="input-panel">
          <IncidentForm :loading="loading" @submit="handleSubmit" />
        </aside>
        <div class="output-panel">
          <ResultPanel :result="result" />
          <AgentTrace :trace="result?.route_trace || []" />
        </div>
      </section>
    </main>

    <footer>
      <span>数据来源：课程合成数据</span>
      <span>MODEL_MODE=mock · 不连接真实高速系统</span>
    </footer>
  </div>
</template>
