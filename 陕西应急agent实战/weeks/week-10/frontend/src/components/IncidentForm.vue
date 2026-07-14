<script setup>
import { reactive } from "vue";

defineProps({
  loading: { type: Boolean, default: false },
});
const emit = defineEmits(["submit"]);

// 默认场景保证学习者第一次启动就能得到完整四 Agent 轨迹。
const form = reactive({
  incident_id: "INC-DEMO-010",
  raw_text: "秦岭隧道追尾出现烟雾，2人受伤，占用2车道",
  road_code: "G65",
  section_id: "QINLING-01",
  camera_id: "CAM-QINLING-01",
  required_resources: ["ambulance", "tow_truck"],
  human_approved: false,
});

function submit() {
  // 复制数组，避免请求过程中修改响应式表单对象。
  emit("submit", { ...form, required_resources: [...form.required_resources] });
}
</script>

<template>
  <form class="incident-form" @submit.prevent="submit">
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
      <small>请包含伤亡、车道占用和可见风险，便于结构化研判。</small>
    </label>

    <div class="field-grid">
      <label class="field">
        <span>事件编号</span>
        <input v-model="form.incident_id" required />
      </label>
      <label class="field">
        <span>高速编号</span>
        <input v-model="form.road_code" required />
      </label>
      <label class="field">
        <span>路段编号</span>
        <input v-model="form.section_id" required />
      </label>
      <label class="field">
        <span>摄像头编号</span>
        <input v-model="form.camera_id" />
      </label>
    </div>

    <fieldset>
      <legend>建议查询的应急资源</legend>
      <label class="check-option">
        <input v-model="form.required_resources" type="checkbox" value="ambulance" />
        <span>救护车</span>
      </label>
      <label class="check-option">
        <input v-model="form.required_resources" type="checkbox" value="tow_truck" />
        <span>清障车</span>
      </label>
    </fieldset>

    <button class="primary-button" type="submit" :disabled="loading">
      <span>{{ loading ? "Agent 协同处理中…" : "启动应急研判" }}</span>
      <span aria-hidden="true">→</span>
    </button>
    <p class="form-note">演示模式仅生成建议，任何高风险动作都不会自动执行。</p>
  </form>
</template>
