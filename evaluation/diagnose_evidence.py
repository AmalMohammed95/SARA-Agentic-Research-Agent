import json
from collections import Counter

with open("evaluation/comparison_results.json", encoding="utf-8") as f:
    data = json.load(f)

fields = (
    "objective",
    "methodology",
    "dataset_sample",
    "findings",
    "limitations",
)

for result in data["results"]:
    if result["system"] != "SARA":
        continue

    records = result["raw_result"].get("evidence") or []

    empty = sum(
        all(
            not record.get(field)
            or str(record.get(field)).strip().upper() == "NOT_AVAILABLE"
            for field in fields
        )
        for record in records
    )

    partial = sum(
        any(
            record.get(field)
            and str(record.get(field)).strip().upper() != "NOT_AVAILABLE"
            for field in fields
        )
        and record.get("claim_support_status") != "supported"
        for record in records
    )

    supported = sum(
        record.get("claim_support_status") == "supported"
        for record in records
    )

    print(f"\n{result['case_id']}")
    print("Empty records:", empty)
    print("Partial unsupported records:", partial)
    print("Supported records:", supported)
    print("Total records:", len(records))
