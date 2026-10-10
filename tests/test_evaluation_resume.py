import importlib.util
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "evaluation"
    / "run_comparison.py"
)

spec = importlib.util.spec_from_file_location(
    "run_comparison", SCRIPT
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_resume_and_atomic_save(tmp_path, monkeypatch):
    results_file = tmp_path / "results.json"

    monkeypatch.setattr(
        module, "RESULTS_FILE", results_file
    )

    previous_results = [
        {
            "case_id": "E01",
            "system": "Baseline",
            "status": "COMPLETED",
        },
        {
            "case_id": "E01",
            "system": "SARA",
            "status": "EXCEPTION",
        },
    ]

    module.save_results(previous_results)

    loaded = module.load_existing_results()

    assert loaded == previous_results
    assert results_file.exists()

    completed = {
        (item["case_id"], item["system"])
        for item in loaded
        if item["status"] != "EXCEPTION"
    }

    assert ("E01", "Baseline") in completed
    assert ("E01", "SARA") not in completed

    assert not results_file.with_suffix(
        ".json.tmp"
    ).exists()

def test_main_resumes_without_duplicate_results(tmp_path, monkeypatch):
    import csv
    import json

    questions_file = tmp_path / "questions.csv"
    results_file = tmp_path / "results.json"

    with questions_file.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=["case_id", "research_question", "category"],
        )
        writer.writeheader()
        writer.writerow({
            "case_id": "E01",
            "research_question": "Test research question",
            "category": "specific",
        })

    monkeypatch.setattr(module, "QUESTIONS_FILE", questions_file)
    monkeypatch.setattr(module, "RESULTS_FILE", results_file)

    module.save_results([
        {
            "case_id": "E01",
            "system": "Baseline",
            "status": "COMPLETED",
        },
        {
            "case_id": "E01",
            "system": "SARA",
            "status": "EXCEPTION",
        },
    ])

    calls = []

    def fake_baseline(question):
        calls.append("Baseline")
        return {"status": "COMPLETED"}

    def fake_agent(question):
        calls.append("SARA")
        return {"status": "INSUFFICIENT_EVIDENCE"}

    monkeypatch.setattr(module, "run_baseline", fake_baseline)
    monkeypatch.setattr(module, "run_agent", fake_agent)

    module.main()

    assert calls == ["SARA"]

    saved = json.loads(results_file.read_text(encoding="utf-8"))
    results = saved["results"]

    assert len(results) == 2
    assert len({
        (item["case_id"], item["system"])
        for item in results
    }) == 2

    sara_result = next(
        item for item in results if item["system"] == "SARA"
    )
    assert sara_result["status"] == "INSUFFICIENT_EVIDENCE"

    module.main()

    assert calls == ["SARA"]
    assert len(module.load_existing_results()) == 2