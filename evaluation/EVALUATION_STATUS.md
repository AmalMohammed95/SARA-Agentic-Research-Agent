# Evaluation Status – Frozen E01–E05

## 1. Evaluation Coverage

The frozen evaluation dataset contains five research cases (E01–E05), evaluated using two systems:

- Baseline
- SARA – Smart Academic Research Agent

**Recorded results: 10/10 case-system pairs.**

No case-system pairs are missing.

## 2. Recorded Results

| Case | Baseline Status | SARA Status |
|---|---|---|
| E01 | COMPLETED | INSUFFICIENT_EVIDENCE |
| E02 | COMPLETED | INSUFFICIENT_EVIDENCE |
| E03 | COMPLETED | INSUFFICIENT_EVIDENCE |
| E04 | COMPLETED | INSUFFICIENT_EVIDENCE |
| E05 | COMPLETED | INSUFFICIENT_EVIDENCE |

The baseline completed all five workflows, while SARA stopped with `INSUFFICIENT_EVIDENCE` in all five cases.

These statuses describe workflow outcomes, not scientific correctness.

## 3. Evidence Sufficiency

Across the five SARA cases:

- Total evidence records: 69
- Supported records: 25
- Empty records: 22
- Partially populated or unsupported records: 22
- Supported record rate: approximately 36.2%

The evidence did not satisfy the system's sufficiency requirements in the recorded live evaluations.

## 4. Execution Time

The previously calculated mean execution times were:

- Baseline: approximately 1.50 seconds
- SARA: approximately 2002.48 seconds

These values describe the recorded runs only. They should not be interpreted as stable latency estimates because repeated-run distributions were not measured.

## 5. Functional Verification

The project previously passed 132 automated tests.

An additional controlled test of the original evidence-sufficiency function returned:

- `sufficient=True`
- Five unique studies
- Complete coverage of the test subquestion
- Zero missing evidence fields
- No reported sufficiency gaps

This controlled test used synthetic records and does not establish scientific validity.

## 6. Limitations

The evaluation does not establish scientific retrieval accuracy, extraction accuracy, or citation correctness against independently annotated ground truth.

The recorded baseline completion statuses do not demonstrate superior scientific correctness.

No repeated-run variability measurements are available.

The live SARA evaluations demonstrate conservative handling of insufficient evidence, but they do not demonstrate successful completion of a full research task with verified real-world evidence.

## 7. Reproducibility

The frozen results are stored in:

- `evaluation/research_questions.csv`
- `evaluation/comparison_results_batch_v1.json`

The offline summary can be regenerated with:

`python evaluation/analyze_results.py`

The summary is written to:

`evaluation/evaluation_summary.json`

Regenerating the offline summary does not require rerunning Ollama or external scholarly searches.