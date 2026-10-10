import csv
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sara.agent import run_agent
from sara.baseline import run_baseline

EVALUATION_DIR = ROOT / "evaluation"
QUESTIONS_FILE = EVALUATION_DIR / "research_questions.csv"
RESULTS_FILE = EVALUATION_DIR / "comparison_results_batch_v1.json"


def evaluate(system_name, function, question):
    start = time.perf_counter()

    try:
        result = function(question)
        elapsed = time.perf_counter() - start

        return {
            "system": system_name,
            "status": result.get("status", "UNKNOWN"),
            "duration_seconds": round(elapsed, 3),
            "error": None,
            "raw_result": result,
        }

    except Exception as exc:
        elapsed = time.perf_counter() - start

        return {
            "system": system_name,
            "status": "EXCEPTION",
            "duration_seconds": round(elapsed, 3),
            "error": str(exc),
            "raw_result": None,
        }
def load_existing_results():
    """Load previous evaluation results for safe resumption."""
    if not RESULTS_FILE.exists():
        return []

    data = json.loads(RESULTS_FILE.read_text(encoding="utf-8"))
    results = data.get("results")

    if not isinstance(results, list):
        raise ValueError("Invalid evaluation results file.")

    return results
def save_results(results):
    """Atomically save evaluation results."""
    payload = {
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "results": results,
    }

    temporary_file = RESULTS_FILE.with_suffix(".json.tmp")

    temporary_file.write_text(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
            default=str,
        ),
        encoding="utf-8",
    )

    temporary_file.replace(RESULTS_FILE)

def main():
    with QUESTIONS_FILE.open(
        "r", encoding="utf-8-sig", newline=""
    ) as file:
        questions = list(csv.DictReader(file))
    if len(sys.argv) > 1:
        selected_case = sys.argv[1]
        questions = [
            case for case in questions
            if case["case_id"] == selected_case
        ]

        if not questions:
            raise ValueError(
                f"Unknown evaluation case: {selected_case}"
            )

    results = load_existing_results()

    completed = {
        (item["case_id"], item["system"])
        for item in results
        if item.get("status") != "EXCEPTION"
    }

    for case in questions:
        case_id = case["case_id"]
        question = case["research_question"]

        print(f"\nEvaluating {case_id}: {question}", flush=True)

        for system_name, function in [
            ("Baseline", run_baseline),
            ("SARA", run_agent),
        ]:
            key = (case_id, system_name)

            if key in completed:
                print(
                    f"Skipping {system_name} for {case_id}: "
                    "already evaluated.",
                    flush=True,
                )
                continue
            print(f"Running {system_name}...", flush=True)

            outcome = evaluate(system_name, function, question)

            # Replace any previous attempt for this case and system.
            results = [
                item for item in results
                if (
                    item.get("case_id"),
                    item.get("system"),
                ) != key
            ]

            results.append({
                "case_id": case_id,
                "category": case["category"],
                "research_question": question,
                **outcome,
            })

            if outcome["status"] != "EXCEPTION":
                completed.add(key)
            
            save_results(results)

    print(f"\nResults saved to: {RESULTS_FILE}")


if __name__ == "__main__":
    main()
