
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS_FILE = HERE / "comparison_results_batch_v1.json"

EVIDENCE_FIELDS = (
    "objective",
    "methodology",
    "dataset_sample",
    "findings",
    "limitations",
)

MISSING_VALUES = {"", "NOT_AVAILABLE", "N/A", "NONE", "NULL", "UNKNOWN"}


def has_value(value):
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip().upper() not in MISSING_VALUES
    return bool(value)


def load_results():
    with RESULTS_FILE.open(encoding="utf-8") as file:
        data = json.load(file)

    if isinstance(data, list):
        return data

    if isinstance(data, dict) and isinstance(data.get("results"), list):
        return data["results"]

    raise ValueError("Unexpected evaluation results JSON structure.")


def classify_record(record):
    populated_fields = sum(
        has_value(record.get(field))
        for field in EVIDENCE_FIELDS
    )

    if populated_fields == 0:
        return "empty"

    if record.get("claim_support_status") == "supported":
        return "supported"

    return "partial_unsupported"


def main():
    results = load_results()

    for result in results:
        if result.get("system") != "SARA":
            continue

        raw_result = result.get("raw_result") or {}
        records = raw_result.get("evidence") or []

        counts = {
            "empty": 0,
            "partial_unsupported": 0,
            "supported": 0,
        }

        for record in records:
            category = classify_record(record)
            counts[category] += 1

        total = len(records)
        supported_rate = (
            counts["supported"] / total * 100
            if total else 0.0
        )

        print(f"\n{result.get('case_id', 'UNKNOWN')}")
        print("Empty records:", counts["empty"])
        print(
            "Partial unsupported records:",
            counts["partial_unsupported"],
        )
        print("Supported records:", counts["supported"])
        print("Total records:", total)
        print(f"Supported rate: {supported_rate:.1f}%")
        print("Execution status:", result.get("status", "UNKNOWN"))


if __name__ == "__main__":
    main()
