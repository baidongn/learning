"""每个 FastAPI 实例独立的 Prometheus 指标注册表。"""

from prometheus_client import CollectorRegistry, Counter, generate_latest


class AppMetrics:
    """避免测试创建多个应用时发生全局指标重名。"""

    def __init__(self) -> None:
        self.registry = CollectorRegistry()
        self.supervisor_invocations = Counter(
            "highway_supervisor_invocations_total",
            "Supervisor 按最终状态统计的调用次数",
            labelnames=("status",),
            registry=self.registry,
        )

    def render(self) -> bytes:
        """返回 Prometheus 文本 exposition 格式。"""

        return generate_latest(self.registry)
