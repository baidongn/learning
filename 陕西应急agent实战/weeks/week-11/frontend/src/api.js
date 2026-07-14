/**
 * 调用 Supervisor 的唯一前端网络边界。
 * 通过注入 fetchImpl，单元测试不需要真实启动后端。
 */
export async function runSupervisor(payload, fetchImpl = fetch) {
  const response = await fetchImpl("/api/agents/supervisor/invoke", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  if (!response.ok) {
    const detail =
      typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
    throw new Error(`请求失败（${response.status}）：${detail}`);
  }
  return data;
}
