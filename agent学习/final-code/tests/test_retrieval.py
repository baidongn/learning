from agent_lab.retrieval import Document, InMemoryRetriever


def test_retriever_returns_relevant_document_and_citation() -> None:
    retriever = InMemoryRetriever(
        [
            Document(id="leave", text="年假需要提前三天申请", source="员工手册/休假制度"),
            Document(id="expense", text="报销需要上传发票", source="财务制度/报销"),
        ]
    )

    hits = retriever.retrieve("年假怎么申请", top_k=2)

    assert hits[0].document.id == "leave"
    assert hits[0].citation == "员工手册/休假制度"
    assert hits[0].score > 0


def test_retriever_can_return_no_result() -> None:
    retriever = InMemoryRetriever(
        [Document(id="leave", text="年假需要提前三天申请", source="员工手册")],
        min_score=0.2,
    )

    assert retriever.retrieve("火星天气") == []

