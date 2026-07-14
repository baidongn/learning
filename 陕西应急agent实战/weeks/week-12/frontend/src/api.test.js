import { describe, expect, it, vi } from "vitest";

import { runSupervisor } from "./api";

describe("runSupervisor", () => {
  it("返回 Supervisor 的结构化结果", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ status: "awaiting_approval" }),
    });

    const result = await runSupervisor({ incident_id: "INC-010" }, fetchImpl);

    expect(result.status).toBe("awaiting_approval");
    expect(fetchImpl).toHaveBeenCalledWith(
      "/api/agents/supervisor/invoke",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("把后端校验错误转换成可展示异常", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: false,
      status: 422,
      json: async () => ({ detail: "字段校验失败" }),
    });

    await expect(runSupervisor({}, fetchImpl)).rejects.toThrow(
      "请求失败（422）：字段校验失败",
    );
  });
});
