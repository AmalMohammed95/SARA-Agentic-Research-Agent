def test_unattempted_papers_have_priority():
    papers = [
        {"id": "P1"},
        {"id": "P2"},
        {"id": "P3"},
    ]

    extraction_attempts = {
        "P1": 1,
        "P2": 0,
        "P3": 1,
    }

    papers.sort(
        key=lambda paper: extraction_attempts.get(
            paper.get("doi") or paper.get("id"), 0
        )
    )

    assert [paper["id"] for paper in papers] == [
        "P2", "P1", "P3"
    ]
