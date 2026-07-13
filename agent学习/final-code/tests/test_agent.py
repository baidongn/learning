from agent_lab.agent import CustomerServiceAgent
from agent_lab.deepseek import FakeDeepSeekClient, ModelReply, TokenUsage
from agent_lab.retrieval import Document, InMemoryRetriever


def build_agent() -> CustomerServiceAgent:
    return CustomerServiceAgent(
        model=FakeDeepSeekClient(),
        retriever=InMemoryRetriever(
            [Document(id="leave", text="年假需要提前三天申请。", source="员工手册/休假制度")]
        ),
    )


def test_agent_is_built_as_a_langgraph_workflow() -> None:
    agent = build_agent()

    nodes = set(agent.graph.get_graph().nodes)

    assert {"guard", "route", "rag", "tool", "approval", "direct"} <= nodes


async def test_rag_question_returns_grounded_answer_with_citation() -> None:
    agent = build_agent()

    result = await agent.run("年假怎么申请？", user_id="u1", thread_id="t1")

    assert "提前三天" in result.answer
    assert result.citations == ["员工手册/休假制度"]
    assert result.route == "rag"


async def test_order_question_calls_order_tool() -> None:
    agent = build_agent()

    result = await agent.run("查询订单1002", user_id="u1", thread_id="t2")

    assert "运输中" in result.answer
    assert result.route == "tool"
    assert result.tool_trace[0].name == "query_order"


async def test_risky_refund_pauses_and_can_resume_after_approval() -> None:
    agent = build_agent()

    pending = await agent.run("为订单1002申请退款", user_id="u1", thread_id="approval-thread")

    assert pending.status == "pending_approval"
    assert pending.pending_action is not None

    completed = await agent.resume("approval-thread", approved=True)

    assert completed.status == "completed"
    assert "退款申请已提交" in completed.answer


async def test_risky_refund_can_be_rejected() -> None:
    agent = build_agent()
    await agent.run("为订单1002申请退款", user_id="u1", thread_id="reject-thread")

    completed = await agent.resume("reject-thread", approved=False)

    assert completed.status == "completed"
    assert "已取消" in completed.answer


async def test_search_and_logistics_are_independent_tools() -> None:
    agent = build_agent()
    names = {schema["function"]["name"] for schema in agent.registry.schemas()}

    assert {"rag_search", "web_search", "query_order", "query_logistics"} <= names

    search = await agent.run("联网查询最新服务公告", user_id="u1", thread_id="search-thread")
    logistics = await agent.run("查询订单1002物流", user_id="u1", thread_id="logistics-thread")

    assert search.route == "search"
    assert search.citations == ["https://example.com/service-notice"]
    assert logistics.route == "logistics"
    assert "配送中心" in logistics.answer


async def test_new_turn_clears_ephemeral_state_in_same_thread() -> None:
    agent = build_agent()
    first = await agent.run("年假怎么申请？", user_id="u1", thread_id="same-thread")
    second = await agent.run("你好", user_id="u1", thread_id="same-thread")

    assert first.citations
    assert second.route == "direct"
    assert second.citations == []


async def test_agent_returns_model_usage() -> None:
    agent = CustomerServiceAgent(
        FakeDeepSeekClient(
            replies=[
                ModelReply(
                    content="你好",
                    usage=TokenUsage(prompt_tokens=3, completion_tokens=2),
                )
            ]
        ),
        InMemoryRetriever(),
    )

    result = await agent.run("你好", user_id="u1", thread_id="usage-thread")

    assert result.usage.total_tokens == 5


async def test_agent_can_remember_explicit_preference() -> None:
    agent = build_agent()

    saved = await agent.run("记住我喜欢简洁回答", user_id="u1", thread_id="memory-1")

    assert saved.route == "memory"
    assert agent.context.recall("u1", "preference") == "简洁回答"
    assert agent.context.recall("u2", "preference") is None


async def test_refund_without_order_id_does_not_interrupt() -> None:
    result = await build_agent().run("我想退款", user_id="u1", thread_id="missing-order")

    assert result.status == "completed"
    assert "订单号" in result.answer


async def test_only_pending_owner_can_resume_approval() -> None:
    import pytest

    agent = build_agent()
    await agent.run("为订单1002申请退款", user_id="owner", thread_id="owned-approval")

    with pytest.raises(PermissionError, match="无权"):
        await agent.resume("owned-approval", approved=True, user_id="another-user")
