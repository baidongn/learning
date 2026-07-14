<script setup>
import { computed } from "vue";

const props = defineProps({
  result: { type: Object, default: null },
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
  return labels[props.result?.status] || "尚未运行";
});
</script>

<template>
  <section class="result-section">
    <div class="result-header">
      <div>
        <p class="eyebrow">DECISION SUPPORT</p>
        <h2>辅助决策结果</h2>
      </div>
      <span :class="['decision-status', result?.status || 'idle']">{{ statusLabel }}</span>
    </div>

    <div v-if="result" class="result-grid">
      <article class="result-card risk-card">
        <span class="card-label">风险等级</span>
        <strong>{{ result.incident?.risk_level || "未知" }}</strong>
        <p>{{ result.incident?.incident_type || "尚未识别事件类型" }}</p>
      </article>
      <article class="result-card">
        <span class="card-label">预案依据</span>
        <strong>{{ result.plan?.citations?.length || 0 }} 条引用</strong>
        <p>{{ result.plan?.summary || "未生成预案建议" }}</p>
      </article>
      <article class="result-card">
        <span class="card-label">资源建议</span>
        <strong>{{ result.dispatch?.assignments?.length || 0 }} 项资源</strong>
        <p>
          {{ result.dispatch?.unmet_requirements?.length ? "存在资源缺口" : "当前需求可满足" }}
        </p>
      </article>
      <article class="result-card safety-card">
        <span class="card-label">安全复核</span>
        <strong>{{ result.safety?.verdict || "未复核" }}</strong>
        <p>{{ result.safety?.reasons?.[0] || "全部规则检查通过" }}</p>
      </article>
    </div>

    <div v-if="result?.awaiting_human_approval" class="approval-banner">
      <span class="approval-icon" aria-hidden="true">!</span>
      <div>
        <strong>高风险动作已暂停，等待人工审批</strong>
        <p>系统已生成调度建议，但已执行动作仍为 {{ result.executed_actions.length }} 项。</p>
      </div>
    </div>

    <div v-if="!result" class="empty-state result-empty">
      <span aria-hidden="true">⌁</span>
      <p>运行 Supervisor 后展示研判、预案、资源和安全复核结果。</p>
    </div>
  </section>
</template>
