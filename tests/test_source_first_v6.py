from sara.source_first import source_candidates, build_source_first_mapping

def test_source_candidates_are_verbatim():
    abstract = ('We evaluate agent reliability using repeated trials and failure rates. '
                'The experiment uses three datasets and human raters.')
    quotes = source_candidates(abstract, 'How is reliability evaluated?')
    assert quotes and all(q in abstract for q in quotes)

def test_source_first_repairs_hallucinated_quote_without_accepting_it():
    abstract = 'We evaluate agent reliability using repeated trials and failure rates.'
    question = 'What reliability methods are used?'
    mapping, reasons = build_source_first_mapping(abstract, [question], {question: 'Made up quotation'})
    assert mapping[question] in abstract
    assert reasons[question] == 'source_sentence_candidate_unverified_semantics'

def test_no_abstract_no_evidence():
    mapping, reasons = build_source_first_mapping('', ['What methods?'], {})
    assert mapping == {}
    assert reasons['What methods?'] == 'no_source_candidate'
