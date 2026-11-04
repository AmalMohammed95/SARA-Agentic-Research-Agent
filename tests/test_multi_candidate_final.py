import json
from sara.source_first import build_multi_source_mapping
from sara.semantic_verification import verify_semantic_candidates

ABSTRACT = ('We evaluate LLM agents using repeated trials and failure rates. '
            'We also analyze benchmark limitations and distribution shifts.')
Q = 'What methods evaluate agent reliability?'

class Fake:
    def __init__(self): self.calls = 0
    def generate(self, prompt):
        self.calls += 1
        assert 'Pairs:' in prompt
        pairs = json.loads(prompt.split('Pairs: ', 1)[1])
        return json.dumps({'results': [
            {'id': p['id'], 'verdict': 'SUPPORTED' if 'repeated trials' in p['quote'] else 'UNSUPPORTED'}
            for p in pairs]})

def test_multi_candidate_uses_only_source_spans():
    mapping, _ = build_multi_source_mapping(ABSTRACT, [Q], {})
    assert len(mapping[Q]) == 2
    assert all(quote in ABSTRACT for quote in mapping[Q])
    client = Fake()
    result = verify_semantic_candidates(client, ABSTRACT, mapping)
    assert result['verdicts'][Q] == 'SUPPORTED'
    assert client.calls == 1

def test_unverifiable_quotes_fail_closed():
    result = verify_semantic_candidates(Fake(), ABSTRACT, {Q: ['fabricated quotation']})
    assert result['verdicts'][Q] == 'UNCERTAIN'
    assert result['model_calls'] == 0
