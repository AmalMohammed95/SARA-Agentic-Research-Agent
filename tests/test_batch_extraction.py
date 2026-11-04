import json
from sara.batch_extraction import extract_batch

ABSTRACT1 = "This study evaluates a CNN for leukemia detection. Accuracy was 96.5%."
ABSTRACT2 = "This study evaluates a transformer for leukemia detection. Accuracy was 92%."
QUESTIONS = ["What classification performance is reported?"]
PAPERS = [
    {"id": "a", "title": "CNN", "abstract": ABSTRACT1},
    {"id": "b", "title": "Transformer", "abstract": ABSTRACT2},
]

def record(abstract, result):
    return ("OBJECTIVE:\nTo evaluate leukemia detection.\nMETHODOLOGY:\n"
            "NOT_AVAILABLE\nDATASET_SAMPLE:\nNOT_AVAILABLE\nFINDINGS:\n"
            + result + "\nLIMITATIONS:\nNOT_AVAILABLE\n"
            "SUPPORTED_SUBQUESTIONS:\n- " + QUESTIONS[0] +
            "\nSUPPORTING_EVIDENCE:\n- " + abstract.split(". ")[1])

class Model:
    def __init__(self, response): self.response = response; self.calls = 0
    def generate(self, prompt): self.calls += 1; return self.response

def test_valid_independent_batch():
    m = Model(json.dumps({"P0": record(ABSTRACT1, "Accuracy was 96.5%."),
                          "P1": record(ABSTRACT2, "Accuracy was 92%.")}))
    result = extract_batch(m, PAPERS, QUESTIONS)
    assert set(result) == {"a", "b"}
    assert m.calls == 1

def test_cross_paper_quote_rejected():
    m = Model(json.dumps({"P0": record(ABSTRACT2, "Accuracy was 92%."),
                          "P1": record(ABSTRACT2, "Accuracy was 92%.")}))
    assert set(extract_batch(m, PAPERS, QUESTIONS)) == {"b"}

def test_malformed_response_falls_back():
    assert extract_batch(Model("not json"), PAPERS, QUESTIONS) == {}

def test_wrong_keys_fall_back():
    assert extract_batch(Model(json.dumps({"P0": "x"})), PAPERS, QUESTIONS) == {}

def test_one_paper_does_not_call_model():
    m = Model("x")
    assert extract_batch(m, PAPERS[:1], QUESTIONS) == {}
    assert m.calls == 0
