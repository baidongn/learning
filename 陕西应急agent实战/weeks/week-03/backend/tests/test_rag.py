from highway_agent.rag import InMemoryPlanRetriever, PlanDocument


DOCUMENTS = [
    PlanDocument(
        id="PLAN-TUNNEL",
        title="课程模拟隧道事件预案",
        section="烟雾与追尾",
        content="隧道发生追尾并出现烟雾时，应核实火情、伤亡和车道占用，准备交通管制。",
        source="synthetic://plans/tunnel",
    ),
    PlanDocument(
        id="PLAN-SNOW",
        title="课程模拟冰雪保畅预案",
        section="道路结冰",
        content="道路结冰时，应巡查路面、准备融雪物资并控制车辆速度。",
        source="synthetic://plans/snow",
    ),
]


def test_retriever_ranks_tunnel_plan_first() -> None:
    retriever = InMemoryPlanRetriever(DOCUMENTS)

    matches = retriever.search("秦岭隧道两车追尾并出现烟雾", limit=2)

    assert matches[0].document.id == "PLAN-TUNNEL"
    assert matches[0].score > 0.5


def test_retriever_returns_no_match_below_threshold() -> None:
    retriever = InMemoryPlanRetriever(DOCUMENTS)

    matches = retriever.search("服务区餐饮价格咨询", limit=2)

    assert matches == []


def test_deterministic_embedding_is_stable_and_has_16_dimensions() -> None:
    retriever = InMemoryPlanRetriever(DOCUMENTS)

    first = retriever.embed("隧道追尾")
    second = retriever.embed("隧道追尾")

    assert first == second
    assert len(first) == 16
