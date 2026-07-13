from agent_lab.pgvector_store import HashingEmbedder, PgVectorRetriever


def test_hashing_embedder_is_deterministic_and_normalized() -> None:
    embedder = HashingEmbedder(dimensions=16)

    first = embedder.embed("年假申请")
    second = embedder.embed("年假申请")

    assert first == second
    assert len(first) == 16
    assert round(sum(value * value for value in first), 6) == 1.0


def test_pgvector_literal_is_explicit_and_stable() -> None:
    assert PgVectorRetriever.vector_literal([0.25, -0.5]) == "[0.25,-0.5]"
