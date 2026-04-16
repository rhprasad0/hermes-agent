from codex_bridge.embeddings import embed_text, embed_texts


EMBED_DIMENSIONS = 1536


def test_embed_text_returns_expected_dimension() -> None:
    vector = embed_text("hello world")

    assert len(vector) == EMBED_DIMENSIONS
    assert any(value != 0.0 for value in vector)


def test_embed_texts_is_stable_for_same_input() -> None:
    first = embed_texts(["alpha beta", "gamma"])
    second = embed_texts(["alpha beta", "gamma"])

    assert first == second
