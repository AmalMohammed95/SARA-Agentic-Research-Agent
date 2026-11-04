import json
from sara.semantic_verification import verify_semantic_batch

ABSTRACT = 'The CNN achieved test accuracy of 95%. The SVM achieved 88% accuracy.'
Q1 = 'What test accuracy did the CNN achieve?'
Q2 = 'What accuracy did the SVM achieve?'


class FakeModel:
    def __init__(self, response=None, error=None):
        self.response, self.error, self.calls = response, error, 0

    def generate(self, prompt):
        self.calls += 1
        assert 'Pairs (JSON):' in prompt
        if self.error:
            raise self.error
        return self.response


def test_batch_two_questions_one_call():
    response = json.dumps({'results': [
        {'question': Q1, 'verdict': 'SUPPORTED'},
        {'question': Q2, 'verdict': 'UNSUPPORTED'},
    ]})
    model = FakeModel(response)
    result = verify_semantic_batch(model, ABSTRACT, {
        Q1: 'The CNN achieved test accuracy of 95%.',
        Q2: 'The SVM achieved 88% accuracy.',
    })
    assert result['verdicts'] == {Q1: 'SUPPORTED', Q2: 'UNSUPPORTED'}
    assert model.calls == 1


def test_hallucinated_quote_not_submitted():
    model = FakeModel()
    result = verify_semantic_batch(model, ABSTRACT, {Q1: 'CNN achieved 99%.'})
    assert result['verdicts'][Q1] == 'UNCERTAIN'
    assert model.calls == 0


def test_malformed_or_partial_response_fails_closed():
    for response in ('not json', json.dumps({'results': []}),
                     json.dumps({'results': [{'question': Q1, 'verdict': 'YES'}]})):
        model = FakeModel(response)
        result = verify_semantic_batch(model, ABSTRACT, {Q1: 'The CNN achieved test accuracy of 95%.'})
        assert result['verdicts'][Q1] == 'UNCERTAIN'
        assert result['error']


def test_model_error_fails_closed():
    model = FakeModel(error=RuntimeError('offline'))
    result = verify_semantic_batch(model, ABSTRACT, {Q1: 'The CNN achieved test accuracy of 95%.'})
    assert result['verdicts'][Q1] == 'UNCERTAIN'
    assert result['error'] == 'offline'


def test_fenced_json_verdict_response():
    model = FakeModel('```json\n' + json.dumps({'results': [
        {'question': Q1, 'verdict': 'SUPPORTED'}
    ]}) + '\n```')
    result = verify_semantic_batch(model, ABSTRACT, {
        Q1: 'The CNN achieved test accuracy of 95%.'
    })
    assert result['verdicts'][Q1] == 'SUPPORTED'
    assert result['error'] is None


def test_constrained_json_for_real_ollama_interface(monkeypatch):
    from sara.model import OllamaModelClient
    client = OllamaModelClient()
    seen = {}
    def fake_generate(prompt, *, format=None):
        seen['schema'] = format
        return json.dumps({'results': [{'question': Q1, 'verdict': 'SUPPORTED'}]})
    monkeypatch.setattr(client, 'generate', fake_generate)
    result = verify_semantic_batch(client, ABSTRACT, {
        Q1: 'The CNN achieved test accuracy of 95%.'
    })
    assert result['verdicts'][Q1] == 'SUPPORTED'
    assert seen['schema']['properties']['results']['type'] == 'array'
