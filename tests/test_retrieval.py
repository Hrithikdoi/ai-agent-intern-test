from app.retrieval import Retriever, load_knowledge_base


def test_knowledge_base_loads():
    chunks = load_knowledge_base()

    assert len(chunks) > 0


def test_chunks_have_source_metadata():
    chunks = load_knowledge_base()

    chunk = chunks[0]

    assert chunk.filename
    assert chunk.heading
    assert chunk.content


def test_returns_policy_for_return_query():
    retriever = Retriever()

    results = retriever.search(
        "How long do I have to return an item?",
        top_k=3,
    )

    assert len(results) > 0

    filenames = [chunk.filename for chunk, _ in results]

    assert any("returns-policy" in filename for filename in filenames)


def test_returns_shipping_information():
    retriever = Retriever()

    results = retriever.search(
        "Do you ship internationally?",
        top_k=3,
    )

    assert len(results) > 0

    filenames = [chunk.filename for chunk, _ in results]

    assert any("shipping" in filename for filename in filenames)


def test_current_policy_is_preferred_over_legacy():
    retriever = Retriever()

    results = retriever.search(
        "What is the return policy?",
        top_k=5,
    )

    assert len(results) > 0

    first_chunk = results[0][0]

    assert first_chunk.status == "active"