"""Offline, evidence-limited summary of frozen baseline-vs-SARA runs.

Does not contact OpenAlex or Ollama and does not infer research accuracy.
"""
import argparse
import csv
import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
SYSTEMS = ("Baseline", "SARA")


def summarize(questions_file, results_file):
    with Path(questions_file).open(encoding="utf-8-sig", newline="") as stream:
        cases = list(csv.DictReader(stream))
    ids = [case["case_id"] for case in cases]
    if not ids or len(ids) != len(set(ids)):
        raise ValueError("Frozen evaluation cases must have unique, nonempty IDs")
    payload = json.loads(Path(results_file).read_text(encoding="utf-8"))
    records = payload.get("results")
    if not isinstance(records, list):
        raise ValueError("Results must contain a list")
    by_key = {}
    for record in records:
        key = (record.get("case_id"), record.get("system"))
        if key[0] not in ids or key[1] not in SYSTEMS:
            raise ValueError(f"Unknown evaluation pair: {key}")
        if key in by_key:
            raise ValueError(f"Duplicate evaluation pair: {key}")
        if record.get("status") is None:
            raise ValueError(f"Missing status: {key}")
        by_key[key] = record
    rows = []
    for case in cases:
        for system in SYSTEMS:
            record = by_key.get((case["case_id"], system))
            rows.append({
                "case_id": case["case_id"],
                "category": case["category"],
                "system": system,
                "recorded": record is not None,
                "status": record.get("status") if record else None,
                "duration_seconds": record.get("duration_seconds") if record else None,
                "exception": record.get("error") if record else None,
            })
    counts = {system: dict(Counter(row["status"] for row in rows if row["system"] == system and row["recorded"])) for system in SYSTEMS}
    return {
        "total_cases": len(cases),
        "expected_pairs": len(cases) * len(SYSTEMS),
        "recorded_pairs": len(by_key),
        "missing_pairs": len(cases) * len(SYSTEMS) - len(by_key),
        "status_counts": counts,
        "rows": rows,
        "limitations": [
            "Missing runs are not failures or successes; they were not recorded.",
            "COMPLETED is a workflow status, not a verified scientific correctness score.",
            "No gold-standard paper relevance labels or claim-level annotations are supplied; retrieval, screening, extraction, and citation accuracy cannot be computed.",
            "Elapsed times are single-run observations, not repeated-run latency estimates.",
        ],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--questions", type=Path, default=HERE / "research_questions.csv")
    parser.add_argument("--results", type=Path, default=HERE / "comparison_results_batch_v1.json")
    parser.add_argument("--output", type=Path, default=HERE / "evaluation_summary.json")
    args = parser.parse_args()
    summary = summarize(args.questions, args.results)
    args.output.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Recorded {summary['recorded_pairs']}/{summary['expected_pairs']} case-system pairs; missing {summary['missing_pairs']}.")
    print(f"Summary saved: {args.output}")


if __name__ == "__main__":
    main()
