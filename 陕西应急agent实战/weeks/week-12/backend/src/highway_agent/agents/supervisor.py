"""受限 Supervisor Agent：按固定安全边界编排四个专业 Agent。"""

from collections.abc import Callable
from datetime import UTC, datetime
from inspect import isawaitable
from typing import Any, Literal, TypeVar

from pydantic import BaseModel, Field

from highway_agent.agents.incident_analysis import (
    IncidentAnalysisAgent,
    IncidentAnalysisRequest,
    IncidentAssessment,
)
from highway_agent.agents.plan_expert import (
    DeepSeekPlanExpertAgent,
    PlanExpertAgent,
    PlanQuery,
    PlanRecommendation,
)
from highway_agent.agents.resource_dispatch import (
    DispatchProposal,
    DispatchRequest,
    ResourceDispatchAgent,
)
from highway_agent.agents.safety_review import (
    SafetyReviewAgent,
    SafetyReviewRequest,
    SafetyReviewResult,
)

T = TypeVar("T")


class SupervisorRequest(BaseModel):
    """Supervisor 的统一输入；高风险动作默认未审批。"""

    incident_id: str
    raw_text: str = Field(min_length=2, max_length=2000)
    road_code: str
    section_id: str
    camera_id: str | None = None
    required_resources: list[str] = Field(default_factory=list)
    human_approved: bool = False


class SupervisorTrace(BaseModel):
    """每次专业 Agent 尝试都留下可审计轨迹。"""

    agent_name: str
    attempt: int
    success: bool
    error: str | None = None


class SupervisorResult(BaseModel):
    """Supervisor 只汇总结果，不把建议伪装成已执行动作。"""

    status: Literal[
        "ready",
        "needs_input",
        "needs_revision",
        "awaiting_approval",
        "blocked",
        "step_limit",
        "failed",
    ]
    incident: IncidentAssessment | None = None
    plan: PlanRecommendation | None = None
    dispatch: DispatchProposal | None = None
    safety: SafetyReviewResult | None = None
    route_trace: list[SupervisorTrace]
    awaiting_human_approval: bool = False
    executed_actions: list[str] = Field(default_factory=list)


class _StepLimitReached(RuntimeError):
    """内部控制信号：达到步数上限后立即停止后续调用。"""


class SupervisorAgent:
    """第五个 Agent：负责路由、一次重试和结果聚合。"""

    def __init__(
        self,
        incident_agent: IncidentAnalysisAgent,
        plan_agent: PlanExpertAgent | DeepSeekPlanExpertAgent,
        dispatch_agent: ResourceDispatchAgent,
        safety_agent: SafetyReviewAgent,
        *,
        max_steps: int = 8,
        max_retries: int = 1,
    ) -> None:
        self.incident_agent = incident_agent
        self.plan_agent = plan_agent
        self.dispatch_agent = dispatch_agent
        self.safety_agent = safety_agent
        self.max_steps = max_steps
        self.max_retries = max_retries

    async def _run_with_retry(
        self,
        name: str,
        operation: Callable[[], T],
        trace: list[SupervisorTrace],
    ) -> T:
        """只对异常重试一次；每次尝试都消耗一个步骤。"""

        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 2):
            if len(trace) >= self.max_steps:
                raise _StepLimitReached
            try:
                value: Any = operation()
                if isawaitable(value):
                    value = await value
                trace.append(
                    SupervisorTrace(
                        agent_name=name,
                        attempt=attempt,
                        success=True,
                    )
                )
                return value
            except Exception as exc:  # noqa: BLE001 - 边界层需要统一记录专业 Agent 异常
                last_error = exc
                trace.append(
                    SupervisorTrace(
                        agent_name=name,
                        attempt=attempt,
                        success=False,
                        error=str(exc),
                    )
                )
        assert last_error is not None
        raise last_error

    async def ainvoke(self, request: SupervisorRequest) -> SupervisorResult:
        """按研判、预案、调度、安全复核顺序执行有界编排。"""

        trace: list[SupervisorTrace] = []
        incident: IncidentAssessment | None = None
        plan: PlanRecommendation | None = None
        dispatch: DispatchProposal | None = None
        safety: SafetyReviewResult | None = None

        try:
            incident_request = IncidentAnalysisRequest(
                raw_text=request.raw_text,
                road_code=request.road_code,
                section_id=request.section_id,
                camera_id=request.camera_id,
            )
            incident = await self._run_with_retry(
                "incident_analysis",
                lambda: self.incident_agent.ainvoke(incident_request),
                trace,
            )

            # 关键事实不完整时立即交还人工补充，禁止带着猜测继续生成方案。
            if incident.missing_fields:
                return SupervisorResult(
                    status="needs_input",
                    incident=incident,
                    route_trace=trace,
                    executed_actions=[],
                )

            plan_query = PlanQuery(
                event_summary=(
                    f"{incident.incident_type} {incident.risk_level} "
                    + " ".join(incident.known_facts)
                )
            )
            plan = await self._run_with_retry(
                "plan_expert",
                lambda: (
                    self.plan_agent.ainvoke(plan_query)
                    if isinstance(self.plan_agent, DeepSeekPlanExpertAgent)
                    else self.plan_agent.invoke(plan_query)
                ),
                trace,
            )

            if incident.risk_level in {"high", "critical"} and request.required_resources:
                dispatch_request = DispatchRequest(
                    incident_id=request.incident_id,
                    section_id=request.section_id,
                    required_types=request.required_resources,
                )
                dispatch = await self._run_with_retry(
                    "resource_dispatch",
                    lambda: self.dispatch_agent.ainvoke(dispatch_request),
                    trace,
                )

            proposed_actions = (
                ["dispatch_resource"]
                if dispatch and dispatch.assignments
                else ["prepare_warning_board"]
            )
            successful_evidence = [
                item.observed_at for item in incident.tool_trace if item.success
            ]
            evidence_age_minutes = (
                max(
                    0,
                    int(
                        (datetime.now(UTC) - min(successful_evidence)).total_seconds()
                        // 60
                    ),
                )
                if successful_evidence
                else 31
            )
            safety_request = SafetyReviewRequest(
                incident_id=request.incident_id,
                recommendation=plan.summary,
                citations=[
                    f"{citation.document_id}#{citation.section}"
                    for citation in plan.citations
                ],
                proposed_actions=proposed_actions,
                evidence_age_minutes=evidence_age_minutes,
                human_approved=request.human_approved,
                user_input=request.raw_text,
            )
            safety = await self._run_with_retry(
                "safety_review",
                lambda: self.safety_agent.invoke(safety_request),
                trace,
            )
        except _StepLimitReached:
            return SupervisorResult(
                status="step_limit",
                incident=incident,
                plan=plan,
                dispatch=dispatch,
                safety=safety,
                route_trace=trace,
                executed_actions=[],
            )
        except Exception:  # noqa: BLE001 - 对外返回降级状态，错误详情已在轨迹中
            return SupervisorResult(
                status="failed",
                incident=incident,
                plan=plan,
                dispatch=dispatch,
                safety=safety,
                route_trace=trace,
                executed_actions=[],
            )

        if safety.verdict == "BLOCK":
            approval_only = set(safety.reason_codes) == {"HUMAN_APPROVAL_REQUIRED"}
            status = "awaiting_approval" if approval_only else "blocked"
        elif safety.verdict == "REVISE":
            status = "needs_revision"
        else:
            status = "ready"

        return SupervisorResult(
            status=status,
            incident=incident,
            plan=plan,
            dispatch=dispatch,
            safety=safety,
            route_trace=trace,
            awaiting_human_approval=status == "awaiting_approval",
            # 即使已审批，本周也只产出可执行建议；真正副作用仍由独立执行层负责。
            executed_actions=[],
        )
