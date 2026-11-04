"""Offline end-to-end lifecycle check; does not invoke Ollama or network."""
import sara.agent as agent


class PlanningOnlyModel:
    def generate(self, prompt, **kwargs):
        if 'SUBQUESTIONS' in prompt.upper() or 'OBJECTIVE' in prompt.upper():
            return (
                'OBJECTIVE:\nInvestigate evaluation of research LLM agents.\n'
                'SUBQUESTIONS:\n- What reliability benchmarks evaluate LLM agents?\n'
                'KEYWORDS:\n- LLM agents reliability evaluation benchmarks\n'
            )
        raise AssertionError('Unexpected model call: ' + prompt[:60])


def test_nine_selected_five_processed_four_pending(monkeypatch):
    monkeypatch.setattr(agent, 'OllamaModelClient', PlanningOnlyModel)
    monkeypatch.setenv('SARA_EXTRACTIVE_MODE', '1')
    monkeypatch.setenv('SARA_MAX_EXTRACTIONS', '5')
    monkeypatch.setenv('SARA_SEMANTIC_VERIFICATION', '0')
    monkeypatch.setenv('SARA_BATCH_EXTRACTION', '0')

    abstract = (
        'This study aims to evaluate agent reliability. '
        'We compare benchmark protocols using human judges. '
        'The dataset consists of 100 evaluation samples. '
        'Our results show that automated tests identify agent failures. '
        'Limitations include limited test environments.'
    )
    papers = [{'doi': f'10.1000/study{i}', 'title': 'LLM agent reliability evaluation',
               'abstract': abstract, 'year': 2026} for i in range(9)]
    monkeypatch.setattr(agent, 'execute_tool', lambda *_: {
        'status': 'COMPLETED', 'result': papers
    })
    monkeypatch.setattr(agent, 'screen_agent_papers', lambda retrieved, **kw: (retrieved, []))
    monkeypatch.setattr(agent, 'screen_papers_in_batches', lambda **kw: [
        {'paper': p, 'decision': 'INCLUDE', 'status': 'INCLUDE', 'reason': 'test'}
        for p in kw['papers']
    ])

    result = agent.run_agent(
        'What methods evaluate reliability of LLM agents?', max_turns=1
    )
    decisions = [event['details'] for event in result['trace']
                 if event['action'] == 'evaluate_evidence']
    assert len(decisions) == 1
    check = decisions[0]
    assert check['processed_studies_count'] == 5
    assert check['pending_studies_count'] == 4
    assert check['unsupported_claim_count'] == 0
    assert check['missing_field_rate'] < 1.0
    assert check['sufficient'] is False
    assert result['status'] != 'COMPLETED'
