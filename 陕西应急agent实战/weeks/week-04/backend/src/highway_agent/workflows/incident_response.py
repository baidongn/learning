"""Week 4 的固定双 Agent 工作流。

图只负责编排和分支；专业判断仍由边界清晰的 Agent 完成。
"""

from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from highway_agent.agents.incident_analysis import IncidentAnalysisAgent, IncidentAnalysisRequest
from highway_agent.agents.plan_expert import (
    DeepSeekPlanExpertAgent,
    PlanExpertAgent,
    PlanQuery,
)
from highway_agent.tools import MockApiToolClient


class IncidentWorkflowState(TypedDict, total=False):
    """工作流跨节点传递的可序列化状态。"""

    request: dict[str, Any]
    assessment: dict[str, Any]
    plan: dict[str, Any] | None
    status: str
    events: list[str]


class EmergencyWorkflow:
    """串联事件研判和预案专家，不包含自主路由。"""

    def __init__(
        self,
        tools: MockApiToolClient,
        plan_agent: PlanExpertAgent | DeepSeekPlanExpertAgent,
    ) -> None:
        self.incident_agent = IncidentAnalysisAgent(tools)
        self.plan_agent = plan_agent
        builder = StateGraph(IncidentWorkflowState)
        builder.add_node("analyze_incident", self._analyze_incident)
        builder.add_node("needs_input", self._needs_input)
        builder.add_node("retrieve_plan", self._retrieve_plan)
        builder.add_edge(START, "analyze_incident")
        builder.add_conditional_edges(
            "analyze_incident",
            self._route_after_analysis,
            {"needs_input": "needs_input", "retrieve_plan": "retrieve_plan"},
        )
        builder.add_edge("needs_input", END)
        builder.add_edge("retrieve_plan", END)
        self.graph = builder.compile()

    async def _analyze_incident(self, state: IncidentWorkflowState) -> IncidentWorkflowState:
        """运行第二个 Agent，并把 Pydantic 结果转换为可持久化字典。"""

        request = IncidentAnalysisRequest.model_validate(state["request"])
        assessment = await self.incident_agent.ainvoke(request)
        return {
            "assessment": assessment.model_dump(mode="json"),
            "status": "analyzed",
            "events": ["incident_analyzed"],
        }

    @staticmethod
    def _route_after_analysis(state: IncidentWorkflowState) -> str:
        """信息不完整时强制停止，避免带着猜测继续生成方案。"""

        return "needs_input" if state["assessment"]["missing_fields"] else "retrieve_plan"

    @staticmethod
    def _needs_input(state: IncidentWorkflowState) -> IncidentWorkflowState:
        return {
            "status": "needs_input",
            "events": [*state.get("events", []), "needs_input"],
        }

    async def _retrieve_plan(self, state: IncidentWorkflowState) -> IncidentWorkflowState:
        """信息完整后才调用预案专家。"""

        request_text = str(state["request"]["raw_text"])
        query = PlanQuery(event_summary=request_text)
        if isinstance(self.plan_agent, DeepSeekPlanExpertAgent):
            plan = await self.plan_agent.ainvoke(query)
        else:
            plan = self.plan_agent.invoke(query)
        return {
            "plan": plan.model_dump(mode="json"),
            "status": "plan_ready" if plan.status == "ready" else plan.status,
            "events": [*state.get("events", []), "plan_retrieved"],
        }

    async def ainvoke(self, request: dict[str, Any]) -> IncidentWorkflowState:
        """以统一入口运行图，调用方不直接接触 LangGraph 配置。"""

        return await self.graph.ainvoke({"request": request, "events": []})
