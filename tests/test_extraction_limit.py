from sara.agent import MAX_EXTRACTIONS_PER_TURN


def test_extraction_limit_is_five():
    assert MAX_EXTRACTIONS_PER_TURN == 5