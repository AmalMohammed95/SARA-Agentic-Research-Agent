from sara.topic_guard import repair_reliability_plan


def test_repairs_peer_review_drift_without_changing_original_question():
    question = 'What methods are used to evaluate the reliability of LLM agents in academic research?'
    sub = [
        'What are common methods used to evaluate LLM agents?',
        'How do peer reviews and literature reviews differ in evaluating LLM agent reliability?',
        'What are the limitations of LLM agent reliability evaluation?',
    ]
    repaired, warnings = repair_reliability_plan(sub, question)
    assert repaired[0] == sub[0]
    assert repaired[2] == sub[2]
    assert 'human judgments' in repaired[1]
    assert warnings == [sub[1]]


def test_unrelated_plans_are_not_rewritten():
    sub = ['How do peer reviews work?']
    assert repair_reliability_plan(sub, 'What is peer review?') == (sub, [])

class NoCallModel:
    def generate(self, prompt):
        raise AssertionError('Clearly relevant titles should not require an LLM screening call')


def test_obvious_agent_evaluation_skips_expensive_screening():
    from sara.batch_screening import screen_papers_in_batches
    paper = {'doi': 'doi:test', 'title': 'Evaluation and Benchmarking of LLM Agents: A Survey',
             'abstract': 'A review of agent evaluation methods, benchmark design, reliability, and performance across real-world scenarios. ' * 2}
    result = screen_papers_in_batches([paper], 'reliability of LLM agents', NoCallModel())
    assert result[0]['decision'] == 'INCLUDE'
