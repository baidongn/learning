"""带持久化中断和人工审批的 Week 5 工作流。"""

from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from highway_agent.agents.incident_analysis import IncidentAnalysisAgent
from highway_agent.agents.plan_expert import DeepSeekPlanExpertAgent, PlanExpertAgent
from highway_agent.tools import MockApiToolClient
from highway_agent.workflows.incident_response import EmergencyWorkflow, IncidentWorkflowState


class ApprovalEmergencyWorkflow(EmergencyWorkflow):
    """在方案生成后暂停，只有人工决定才能继续。"""

    def __init__(
        self,
        tools: MockApiToolClient,
        plan_agent: PlanExpertAgent | DeepSeekPlanExpertAgent,
        checkpointer: BaseCheckpointSaver,
    ) -> None:
        # 复用父类节点函数，但重新编译一张包含审批节点的图。
        self.incident_agent = IncidentAnalysisAgent(tools)
        self.plan_agent = plan_agent
        builder = StateGraph(IncidentWorkflowState)
        builder.add_node("analyze_incident", self._analyze_incident)
        builder.add_node("needs_input", self._needs_input)
        builder.add_node("retrieve_plan", self._retrieve_plan)
        builder.add_node("human_approval", self._human_approval)
        builder.add_edge(START, "analyze_incident")
        builder.add_conditional_edges(
            "analyze_incident",
            self._route_after_analysis,
            {"needs_input": "needs_input", "retrieve_plan": "retrieve_plan"},
        )
        builder.add_edge("needs_input", END)
        builder.add_edge("retrieve_plan", "human_approval")
        builder.add_edge("human_approval", END)
        self.graph = builder.compile(checkpointer=checkpointer)

    @staticmethod
    def _human_approval(state: IncidentWorkflowState) -> IncidentWorkflowState:
        """暂停图并等待 approve/edit/reject；暂停期间绝不记录执行动作。"""

        decision = interrupt(
            {
                "type": "approval_required",
                "allowed_decisions": ["approve", "edit", "reject"],
                "plan": state.get("plan"),
            }
        )
        action = str(decision.get("decision", "reject"))
        if action == "approve":
            return {
                "status": "approved",
                "approval": decision,
                # 这里只记录模拟动作，课程永远不会连接真实交通控制系统。
                "executed_actions": ["simulate_traffic_control"],
                "events": [*state.get("events", []), "human_approved"],
            }
        if action == "edit":
            return {
                "status": "needs_revision",
                "approval": decision,
                "executed_actions": [],
                "events": [*state.get("events", []), "human_edited"],
            }
        return {
            "status": "rejected",
            "approval": decision,
            "executed_actions": [],
            "events": [*state.get("events", []), "human_rejected"],
        }

    async def start(self, request: dict[str, Any], thread_id: str) -> dict[str, Any]:
        """启动新线程，并把 LangGraph Interrupt 转换为友好响应。"""

        config = {"configurable": {"thread_id": thread_id}}
        result = await self.graph.ainvoke(
            {"request": request, "events": [], "executed_actions": []}, config=config
        )
        if "__interrupt__" in result:
            value = result["__interrupt__"][0].value
            return {
                "thread_id": thread_id,
                "status": "awaiting_approval",
                "interrupt": value,
                "executed_actions": [],
            }
        return result

    async def resume(self, thread_id: str, decision: dict[str, Any]) -> dict[str, Any]:
        """从相同 Checkpoint 继续，不重新执行已经成功的前置节点。"""

        config = {"configurable": {"thread_id": thread_id}}
        return await self.graph.ainvoke(Command(resume=decision), config=config)
