"""基于 LangGraph 的企业智能客服 Agent。"""

from __future__ import annotations

import re
import time
from typing import Any, Literal, TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt
from pydantic import BaseModel, Field

from agent_lab.context import ContextManager
from agent_lab.deepseek import ModelGateway, TokenUsage
from agent_lab.retrieval import Retriever
from agent_lab.safety import SafetyPolicy
from agent_lab.tools import ToolContext, ToolRegistry, ToolSpec


class OrderInput(BaseModel):
    order_id: str = Field(pattern=r"^\d{4,}$")


class RefundInput(BaseModel):
    order_id: str = Field(pattern=r"^\d{4,}$")


class RagInput(BaseModel):
    query: str = Field(min_length=2, max_length=500)
    top_k: int = Field(default=4, ge=1, le=10)


class SearchInput(BaseModel):
    query: str = Field(min_length=2, max_length=500)


class LogisticsInput(BaseModel):
    order_id: str = Field(pattern=r"^\d{4,}$")


class ToolTrace(BaseModel):
    name: str
    arguments: dict[str, Any]
    output: Any | None = None


class PendingAction(BaseModel):
    tool_name: str
    arguments: dict[str, Any]
    description: str


class AgentResult(BaseModel):
    answer: str = ""
    citations: list[str] = Field(default_factory=list)
    route: str = "direct"
    status: Literal["completed", "pending_approval", "blocked"] = "completed"
    pending_action: PendingAction | None = None
    tool_trace: list[ToolTrace] = Field(default_factory=list)
    usage: TokenUsage = Field(default_factory=TokenUsage)


class AgentState(TypedDict, total=False):
    messages: list[dict[str, Any]]
    query: str
    user_id: str
    thread_id: str
    runtime_context: dict[str, Any]
    memory: dict[str, Any]
    route: str
    answer: str
    citations: list[str]
    hits: list[dict[str, Any]]
    retrieval: dict[str, Any]
    status: str
    pending_action: dict[str, Any] | None
    tool_trace: list[dict[str, Any]]
    usage: dict[str, int]


class CustomerServiceAgent:
    """将安全、检索、工具和人工审批组装成一张状态图。"""

    def __init__(self, model: ModelGateway, retriever: Retriever) -> None:
        self.model = model
        self.retriever = retriever
        self.safety = SafetyPolicy()
        self.context = ContextManager()
        self.registry = ToolRegistry()
        self._pending_threads: set[str] = set()
        self._pending_owners: dict[str, str] = {}
        self._pending_deadlines: dict[str, float] = {}
        self._register_default_tools()
        self.graph = self._build_graph()

    @property
    def mode(self) -> str:
        return self.model.mode

    def _register_default_tools(self) -> None:
        orders = {"1001": "已付款，待发货", "1002": "已发货，运输中", "1003": "已签收"}

        async def query_order(order_id: str) -> str:
            return orders.get(order_id, "未找到订单")

        async def request_refund(order_id: str) -> str:
            return f"订单{order_id}退款申请已提交"

        async def query_logistics(order_id: str) -> str:
            routes = {
                "1002": "包裹已到达杭州配送中心",
                "1003": "包裹已由用户签收",
            }
            return routes.get(order_id, "未找到物流轨迹")

        async def rag_search(query: str, top_k: int = 4) -> list[dict[str, Any]]:
            return [hit.model_dump() for hit in self.retriever.retrieve(query, top_k=top_k)]

        async def web_search(query: str) -> dict[str, str]:
            # 课堂默认使用固定搜索结果；生产时替换为受域名和大小限制的搜索客户端。
            return {
                "title": "服务公告",
                "url": "https://example.com/service-notice",
                "snippet": f"与“{query}”相关的演示公告",
            }

        self.registry.register(
            ToolSpec(
                name="query_order",
                description="根据订单号查询订单状态",
                input_model=OrderInput,
                handler=query_order,
            )
        )
        self.registry.register(
            ToolSpec(
                name="query_logistics",
                description="根据订单号查询物流轨迹，只读",
                input_model=LogisticsInput,
                handler=query_logistics,
            )
        )
        self.registry.register(
            ToolSpec(
                name="rag_search",
                description="检索企业知识库并返回带来源和分数的资料",
                input_model=RagInput,
                handler=rag_search,
            )
        )
        self.registry.register(
            ToolSpec(
                name="web_search",
                description="查询需要最新公开信息的问题，不用于企业内部制度",
                input_model=SearchInput,
                handler=web_search,
            )
        )
        self.registry.register(
            ToolSpec(
                name="request_refund",
                description="为订单提交退款申请，需要人工确认",
                input_model=RefundInput,
                handler=request_refund,
                risky=True,
            )
        )

    def _build_graph(self):
        builder = StateGraph(AgentState)
        builder.add_node("guard", self._guard_node)
        builder.add_node("route", self._route_node)
        builder.add_node("rag", self._rag_node)
        builder.add_node("tool", self._tool_node)
        builder.add_node("logistics", self._logistics_node)
        builder.add_node("search", self._search_node)
        builder.add_node("memory", self._memory_node)
        builder.add_node("approval", self._approval_node)
        builder.add_node("direct", self._direct_node)
        builder.add_edge(START, "guard")
        builder.add_edge("guard", "route")
        builder.add_conditional_edges(
            "route",
            lambda state: state["route"],
            {
                "rag": "rag",
                "tool": "tool",
                "logistics": "logistics",
                "search": "search",
                "memory": "memory",
                "approval": "approval",
                "direct": "direct",
                "blocked": END,
            },
        )
        for node in ("rag", "tool", "logistics", "search", "memory", "approval", "direct"):
            builder.add_edge(node, END)
        return builder.compile(checkpointer=InMemorySaver())

    async def _guard_node(self, state: AgentState) -> dict[str, Any]:
        decision = self.safety.check_input(state["query"])
        if not decision.allowed:
            return {"route": "blocked", "status": "blocked", "answer": decision.reason}
        return {}

    async def _route_node(self, state: AgentState) -> dict[str, str]:
        if state.get("route") == "blocked":
            return {"route": "blocked"}
        query = state["query"]
        if "退款" in query:
            route = "approval"
        elif query.startswith("记住"):
            route = "memory"
        elif "物流" in query:
            route = "logistics"
        elif any(keyword in query for keyword in ("最新", "联网", "搜索")):
            route = "search"
        elif "订单" in query:
            route = "tool"
        elif self.retriever.retrieve(query, top_k=1):
            route = "rag"
        else:
            route = "direct"
        return {"route": route}

    async def _rag_node(self, state: AgentState) -> dict[str, Any]:
        hits = self.retriever.retrieve(state["query"])
        if not hits:
            return {"answer": "知识库中没有找到可靠依据。", "citations": []}
        material = "\n".join(hit.document.text for hit in hits)
        reply = await self.model.chat(
            [
                {"role": "system", "content": "只能根据检索资料回答，不要编造。"},
                {
                    "role": "user",
                    "content": f"问题：{state['query']}\n【检索资料】\n{material}",
                },
            ]
        )
        citations = list(dict.fromkeys(hit.citation for hit in hits))
        return {
            "answer": reply.content,
            "citations": citations,
            "hits": [hit.model_dump() for hit in hits],
            "usage": reply.usage.model_dump(),
        }

    async def _tool_node(self, state: AgentState) -> dict[str, Any]:
        order_id = self._extract_order_id(state["query"])
        if order_id is None:
            return {"answer": "请提供至少四位的订单号。"}
        arguments = {"order_id": order_id}
        result = await self.registry.invoke(
            "query_order", arguments, ToolContext(user_id=state["user_id"])
        )
        trace = ToolTrace(name="query_order", arguments=arguments, output=result.output)
        return {"answer": f"订单{order_id}：{result.output}", "tool_trace": [trace.model_dump()]}

    async def _logistics_node(self, state: AgentState) -> dict[str, Any]:
        order_id = self._extract_order_id(state["query"])
        if order_id is None:
            return {"answer": "请提供至少四位的订单号。"}
        arguments = {"order_id": order_id}
        result = await self.registry.invoke(
            "query_logistics", arguments, ToolContext(user_id=state["user_id"])
        )
        trace = ToolTrace(name="query_logistics", arguments=arguments, output=result.output)
        return {
            "answer": f"订单{order_id}物流：{result.output}",
            "tool_trace": [trace.model_dump()],
        }

    async def _search_node(self, state: AgentState) -> dict[str, Any]:
        arguments = {"query": state["query"]}
        result = await self.registry.invoke(
            "web_search", arguments, ToolContext(user_id=state["user_id"])
        )
        output = dict(result.output)
        trace = ToolTrace(name="web_search", arguments=arguments, output=output)
        return {
            "answer": f"{output['title']}：{output['snippet']}",
            "citations": [output["url"]],
            "tool_trace": [trace.model_dump()],
        }

    async def _memory_node(self, state: AgentState) -> dict[str, str]:
        match = re.search(r"记住我喜欢(.+)", state["query"])
        if not match:
            return {"answer": "请使用“记住我喜欢……”明确告诉我要保存的偏好。"}
        preference = match.group(1).strip()
        self.context.remember(state["user_id"], "preference", preference)
        return {"answer": f"已记住你的偏好：{preference}"}

    async def _approval_node(self, state: AgentState) -> dict[str, Any]:
        order_id = self._extract_order_id(state["query"])
        if order_id is None:
            return {"answer": "退款前请提供至少四位的订单号。", "status": "completed"}
        action = PendingAction(
            tool_name="request_refund",
            arguments={"order_id": order_id},
            description=f"为订单{order_id}提交退款申请",
        )
        decision = interrupt(action.model_dump())
        approved = bool(decision.get("approved")) if isinstance(decision, dict) else bool(decision)
        if not approved:
            return {"answer": "退款操作已取消。", "status": "completed", "pending_action": None}
        result = await self.registry.invoke(
            "request_refund",
            action.arguments,
            ToolContext(
                user_id=state["user_id"],
                idempotency_key=f"refund:{state['thread_id']}:{order_id}",
            ),
        )
        trace = ToolTrace(
            name="request_refund", arguments=action.arguments, output=result.output
        )
        return {
            "answer": str(result.output),
            "status": "completed",
            "pending_action": None,
            "tool_trace": [trace.model_dump()],
        }

    async def _direct_node(self, state: AgentState) -> dict[str, Any]:
        preference = self.context.recall(state["user_id"], "preference")
        messages: list[dict[str, str]] = []
        if preference:
            messages.append(
                {"role": "system", "content": f"用户明确保存的回答偏好：{preference}"}
            )
        messages.append({"role": "user", "content": state["query"]})
        reply = await self.model.chat(messages)
        return {"answer": reply.content, "usage": reply.usage.model_dump()}

    @staticmethod
    def _extract_order_id(text: str) -> str | None:
        match = re.search(r"\d{4,}", text)
        return match.group(0) if match else None

    @staticmethod
    def _to_result(state: dict[str, Any]) -> AgentResult:
        interrupts = state.get("__interrupt__", ())
        if interrupts:
            value = interrupts[0].value
            return AgentResult(
                route="approval",
                status="pending_approval",
                pending_action=PendingAction.model_validate(value),
            )
        return AgentResult(
            answer=state.get("answer", ""),
            citations=state.get("citations", []),
            route=state.get("route", "direct"),
            status=state.get("status", "completed"),
            pending_action=state.get("pending_action"),
            tool_trace=state.get("tool_trace", []),
            usage=TokenUsage.model_validate(state.get("usage", {})),
        )

    async def run(self, query: str, user_id: str, thread_id: str) -> AgentResult:
        config = {"configurable": {"thread_id": thread_id}}
        state = await self.graph.ainvoke(
            {
                "query": query,
                "user_id": user_id,
                "thread_id": thread_id,
                # 以下字段属于单轮临时状态，每次输入都必须重置。
                "route": "",
                "answer": "",
                "citations": [],
                "hits": [],
                "retrieval": {},
                "status": "completed",
                "pending_action": None,
                "tool_trace": [],
                "usage": {},
            },
            config=config,
        )
        result = self._to_result(state)
        if result.status == "pending_approval":
            self._pending_threads.add(thread_id)
            self._pending_owners[thread_id] = user_id
            self._pending_deadlines[thread_id] = time.monotonic() + 300
        return result

    async def resume(
        self, thread_id: str, approved: bool, user_id: str | None = None
    ) -> AgentResult:
        if thread_id not in self._pending_threads:
            raise ValueError("没有等待审批的会话")
        owner = self._pending_owners.get(thread_id)
        if user_id is not None and user_id != owner:
            raise PermissionError("当前用户无权审批该会话")
        if time.monotonic() > self._pending_deadlines.get(thread_id, 0):
            self._clear_pending(thread_id)
            raise ValueError("审批已过期，请重新发起")
        config = {"configurable": {"thread_id": thread_id}}
        state = await self.graph.ainvoke(Command(resume={"approved": approved}), config=config)
        self._clear_pending(thread_id)
        return self._to_result(state)

    def _clear_pending(self, thread_id: str) -> None:
        self._pending_threads.discard(thread_id)
        self._pending_owners.pop(thread_id, None)
        self._pending_deadlines.pop(thread_id, None)

    async def get_session(self, thread_id: str) -> dict[str, Any] | None:
        """读取 Checkpoint 中的最新会话状态。"""
        config = {"configurable": {"thread_id": thread_id}}
        snapshot = await self.graph.aget_state(config)
        if not snapshot.values:
            return None
        state = dict(snapshot.values)
        return {
            "thread_id": thread_id,
            "user_id": state.get("user_id", ""),
            "route": state.get("route", "direct"),
            "status": state.get("status", "completed"),
            "answer": state.get("answer", ""),
            "citations": state.get("citations", []),
        }
