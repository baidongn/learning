import { flushPromises, mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import App from "./App.vue";

vi.mock("./api", () => ({
  runSupervisor: vi.fn().mockResolvedValue({
    status: "awaiting_approval",
    awaiting_human_approval: true,
    executed_actions: [],
    incident: { risk_level: "critical", incident_type: "tunnel_smoke" },
    plan: { summary: "已生成建议", actions: [], citations: [] },
    dispatch: { assignments: [], unmet_requirements: [] },
    safety: { verdict: "BLOCK", reasons: ["高风险动作需要人工审批"] },
    route_trace: [
      { agent_name: "incident_analysis", attempt: 1, success: true },
      { agent_name: "plan_expert", attempt: 1, success: true },
      { agent_name: "resource_dispatch", attempt: 1, success: true },
      { agent_name: "safety_review", attempt: 1, success: true },
    ],
  }),
}));

describe("App", () => {
  it("展示课程默认事件表单", () => {
    const wrapper = mount(App);

    expect(wrapper.get("[data-test='incident-text']").element.value).toContain(
      "秦岭隧道",
    );
    expect(wrapper.text()).toContain("启动应急研判");
  });

  it("提交后显示人工审批状态与四个 Agent 轨迹", async () => {
    const wrapper = mount(App);

    await wrapper.get("form").trigger("submit");
    await flushPromises();

    expect(wrapper.text()).toContain("等待人工审批");
    expect(wrapper.text()).toContain("事件研判 Agent");
    expect(wrapper.text()).toContain("预案专家 Agent");
    expect(wrapper.text()).toContain("资源调度 Agent");
    expect(wrapper.text()).toContain("安全复核 Agent");
  });
});
