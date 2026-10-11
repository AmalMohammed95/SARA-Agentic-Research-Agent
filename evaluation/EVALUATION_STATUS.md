# Evaluation status (frozen E01–E05)

The offline summary is generated from `research_questions.csv` and `comparison_results_batch_v1.json` with:

```powershell
python evaluation/analyze_results.py
```

Only **E01** has recorded results for both systems (2 of 10 expected case-system pairs). The other eight pairs are **not evaluated** in this artifact; they must not be interpreted as failures. The E01 baseline has status `COMPLETED` and duration 1.328 seconds; SARA has `INSUFFICIENT_EVIDENCE` and duration 2695.436 seconds. No exception was recorded for either.

A workflow status does not measure scientific correctness. Paper retrieval/screening accuracy, extraction accuracy, and citation correctness require independently verified ground-truth annotations. No such gold labels are included here, so those metrics are **not available**. The recorded durations are single runs, not reliable latency distributions.

To expand the study, annotate gold-standard relevant paper IDs and claim/source correctness per case; run each system against the same fixed case set and report per-case results, failures, and repeated-run variability. The existing `run_comparison.py` can resume missing cases, but live SARA execution may take a long time and needs local Ollama and OpenAlex access. Do not run it as part of the offline summary.
