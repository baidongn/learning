<script setup>
const props = defineProps({
  trace: { type: Array, default: () => [] },
});

const labels = {
  incident_analysis: "事件研判 Agent",
  plan_expert: "预案专家 Agent",
  resource_dispatch: "资源调度 Agent",
  safety_review: "安全复核 Agent",
};
</script>

<template>
  <section class="trace-section">
    <div class="section-heading compact">
      <span class="step-number">02</span>
      <div>
        <p class="eyebrow">AGENT TRACE</p>
        <h2>协同轨迹</h2>
      </div>
    </div>
    <ol v-if="props.trace.length" class="trace-list">
      <li v-for="(step, index) in props.trace" :key="`${step.agent_name}-${step.attempt}`">
        <span class="trace-index">{{ String(index + 1).padStart(2, "0") }}</span>
        <span class="trace-line" aria-hidden="true"></span>
        <div class="trace-content">
          <strong>{{ labels[step.agent_name] || step.agent_name }}</strong>
          <span>第 {{ step.attempt }} 次尝试</span>
        </div>
        <span :class="['status-dot', step.success ? 'success' : 'failed']">
          {{ step.success ? "完成" : "失败" }}
        </span>
      </li>
    </ol>
    <div v-else class="empty-state">提交事件后，这里会显示每个 Agent 的执行顺序。</div>
  </section>
</template>
