from sara.batch_screening import screen_papers_in_batches


PAPERS = [
    {"id": "P1", "title": "Relevant Study", "abstract": "Relevant evidence."},
    {"id": "P2", "title": "Unrelated Study", "abstract": "Unrelated evidence."},
]


class MockModel:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = 0

    def generate(self, prompt):
        self.calls += 1
        return next(self.responses)


def test_batch_success():
    model = MockModel([
        '{"results": ['
        '{"paper_id": "P1", "decision": "INCLUDE", "reason": "Relevant evidence."},'
        '{"paper_id": "P2", "decision": "EXCLUDE", "reason": "Unrelated evidence."}'
        ']}'
    ])

    results = screen_papers_in_batches(
        PAPERS, "Research question", model
    )

    assert model.calls == 1
    assert len(results) == 2
    assert [r["decision"] for r in results] == ["INCLUDE", "EXCLUDE"]
    assert [r["status"] for r in results] == ["INCLUDE", "EXCLUDE"]


def test_batch_fallback():
    model = MockModel([
        "invalid json",
        "DECISION:\nINCLUDE\nREASON:\nRelevant evidence.",
        "DECISION:\nEXCLUDE\nREASON:\nUnrelated evidence.",
    ])

    results = screen_papers_in_batches(
        PAPERS, "Research question", model
    )

    assert model.calls == 3
    assert len(results) == 2
    assert [r["decision"] for r in results] == ["INCLUDE", "EXCLUDE"]


def test_batch_missing_paper_fallback():
    model = MockModel([
        '{"results": [{"paper_id": "P1", "decision": "INCLUDE", "reason": "Relevant."}]}',
        "DECISION:\nINCLUDE\nREASON:\nRelevant evidence.",
        "DECISION:\nEXCLUDE\nREASON:\nUnrelated evidence.",
    ])

    results = screen_papers_in_batches(
        PAPERS, "Research question", model
    )

    assert model.calls == 3
    assert len(results) == 2


def test_batch_individual_failure_is_safe():
    model = MockModel([
        "invalid json",
        "invalid individual response",
        "DECISION:\nEXCLUDE\nREASON:\nUnrelated evidence.",
    ])

    results = screen_papers_in_batches(
        PAPERS, "Research question", model
    )

    assert results[0]["decision"] == "EXCLUDE"
    assert results[0]["status"] == "INVALID"
    assert results[1]["decision"] == "EXCLUDE"
