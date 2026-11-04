from sara.agent import filter_unseen_papers


def test_does_not_screen_papers_seen_in_previous_turn():
    old = [{"id": "W1", "title": "Already seen"}]
    current = [
        {"id": "W1", "title": "Already seen"},
        {"id": "W2", "title": "New paper"},
    ]
    assert filter_unseen_papers(current, old) == [current[1]]


def test_does_not_remove_new_papers():
    papers = [{"id": "W2", "title": "New paper"}]
    assert filter_unseen_papers(papers, []) == papers
