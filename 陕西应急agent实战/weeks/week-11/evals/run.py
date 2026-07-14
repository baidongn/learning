"""执行 JSONL 场景并输出真实 Supervisor 验收摘要。"""

import asyncio
import json
import os
import sys
from pathlib import Path

import httpx

# api 模块会创建默认应用；导入前先固定 Mock，隔离调用者的 Live 环境变量。
os.environ["MODEL_MODE"] = "mock"
os.environ["CHECKPOINT_BACKEND"] = "memory"

from highway_agent.agents.incident_analysis import IncidentAnalysisAgent
from highway_agent.agents.plan_expert import PlanExpertAgent
from highway_agent.agents.resource_dispatch import ResourceDispatchAgent
from highway_agent.agents.safety_review import SafetyReviewAgent
from highway_agent.agents.supervisor import SupervisorAgent, SupervisorRequest, SupervisorResult
from highway_agent.api import create_app
from highway_agent.config import Settings
from highway_agent.evaluation import EvaluationRecord, evaluate_records
from highway_agent.rag import InMemoryPlanRetriever, load_demo_documents
from highway_agent.tools import MockApiToolClient


def build_supervisor() -> SupervisorAgent:
    """使用确定性 Mock Tool 组装最终五 Agent 流程。"""

    # 最终基线必须与调用者 Shell 环境隔离，始终使用无 Key 的确定性模式。
    app = create_app(Settings(model_mode="mock", checkpoint_backend="memory"))
    tools = MockApiToolClient(transport=httpx.ASGITransport(app=app))
    return SupervisorAgent(
        incident_agent=IncidentAnalysisAgent(tools),
        plan_agent=PlanExpertAgent(InMemoryPlanRetriever(load_demo_documents())),
        dispatch_agent=ResourceDispatchAgent(tools),
        safety_agent=SafetyReviewAgent(),
    )


async def run_case(supervisor: SupervisorAgent, case: dict[str, object]) -> EvaluationRecord:
    """调用真实 Supervisor，并从返回对象计算而不是手填实际值。"""

    result = await supervisor.ainvoke(SupervisorRequest.model_validate(case["input"]))
    # 再次通过 Pydantic 校验序列化结果，作为结构化输出合法性的判据。
    validated = SupervisorResult.model_validate(result.model_dump(mode="json"))
    actual_tools = (
        [item.tool_name for item in validated.incident.tool_trace]
        if validated.incident
        else []
    )
    request = SupervisorRequest.model_validate(case["input"])
    return EvaluationRecord(
        case_id=str(case["case_id"]),
        expected_tools=list(case["expected_tools"]),
        actual_tools=actual_tools,
        structured_output_valid=True,
        scenario_success=validated.status == case["expected_status"],
        human_approved=request.human_approved,
        executed_actions=validated.executed_actions,
    )


async def evaluate_file(path: Path):  # type: ignore[no-untyped-def]
    """顺序执行场景，保证演示结果确定且便于定位失败案例。"""

    cases = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    supervisor = build_supervisor()
    records = [await run_case(supervisor, case) for case in cases]
    return evaluate_records(records)


def main() -> int:
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "evals/week11_cases.jsonl")
    summary = asyncio.run(evaluate_file(path))
    print(json.dumps(summary.model_dump(), ensure_ascii=False, indent=2))
    return 0 if summary.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
