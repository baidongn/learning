"""安全复核 Agent：在建议进入人工审批前执行确定性守门。"""

from typing import Literal

from pydantic import BaseModel, Field


class SafetyReviewRequest(BaseModel):
    """需要复核的建议、证据和拟执行动作。"""

    incident_id: str
    recommendation: str = Field(min_length=2, max_length=4000)
    citations: list[str] = Field(default_factory=list)
    proposed_actions: list[str] = Field(default_factory=list)
    evidence_age_minutes: int = Field(ge=0)
    human_approved: bool = False
    user_input: str = Field(default="", max_length=4000)


class SafetyReviewResult(BaseModel):
    """稳定的三态输出，便于工作流路由和评测。"""

    verdict: Literal["PASS", "REVISE", "BLOCK"]
    reason_codes: list[str]
    reasons: list[str]
    sanitized_actions: list[str]
    checks: dict[str, bool]


class SafetyReviewAgent:
    """第四个专业 Agent；使用白名单和规则完成最终安全复核。"""

    high_risk_actions = {
        "close_road",
        "dispatch_resource",
        "publish_warning",
        "control_signal",
    }
    allowed_actions = high_risk_actions | {
        "prepare_warning_board",
        "request_more_information",
        "simulate_traffic_control",
    }
    injection_markers = (
        "忽略之前",
        "忽略以上",
        "绕过审批",
        "直接执行",
        "system prompt",
        "developer message",
    )

    def invoke(self, request: SafetyReviewRequest) -> SafetyReviewResult:
        """按 BLOCK 优先于 REVISE 的顺序检查，避免低风险结果覆盖阻断项。"""

        reason_codes: list[str] = []
        reasons: list[str] = []
        combined_text = f"{request.user_input}\n{request.recommendation}".lower()
        injection_safe = not any(
            marker.lower() in combined_text for marker in self.injection_markers
        )
        actions_known = all(
            action in self.allowed_actions for action in request.proposed_actions
        )
        approval_valid = request.human_approved or not any(
            action in self.high_risk_actions for action in request.proposed_actions
        )
        citation_present = bool(request.citations)
        evidence_fresh = request.evidence_age_minutes <= 30

        if not injection_safe:
            reason_codes.append("PROMPT_INJECTION")
            reasons.append("输入包含疑似提示词注入或绕过审批指令")
        if not actions_known:
            reason_codes.append("UNKNOWN_ACTION")
            reasons.append("拟执行动作不在课程白名单中")
        if not approval_valid:
            reason_codes.append("HUMAN_APPROVAL_REQUIRED")
            reasons.append("高风险动作尚未获得人工审批")
        if not citation_present:
            reason_codes.append("MISSING_CITATION")
            reasons.append("处置建议缺少可追溯预案引用")
        if not evidence_fresh:
            reason_codes.append("STALE_EVIDENCE")
            reasons.append("工具证据超过 30 分钟，需要重新查询")

        blocking_codes = {
            "PROMPT_INJECTION",
            "UNKNOWN_ACTION",
            "HUMAN_APPROVAL_REQUIRED",
        }
        if blocking_codes.intersection(reason_codes):
            verdict: Literal["PASS", "REVISE", "BLOCK"] = "BLOCK"
            sanitized_actions: list[str] = []
        elif reason_codes:
            verdict = "REVISE"
            sanitized_actions = []
        else:
            verdict = "PASS"
            sanitized_actions = list(request.proposed_actions)

        return SafetyReviewResult(
            verdict=verdict,
            reason_codes=reason_codes,
            reasons=reasons,
            sanitized_actions=sanitized_actions,
            checks={
                "injection_safe": injection_safe,
                "actions_known": actions_known,
                "approval_valid": approval_valid,
                "citation_present": citation_present,
                "evidence_fresh": evidence_fresh,
            },
        )
