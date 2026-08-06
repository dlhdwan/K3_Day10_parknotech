# Data Corruption & Recovery Comparison Report

## Performance Metrics Comparison Across 3 States

| Metric | Baseline | Corrupted | Repaired | Impact / Recovery Delta |
|---|---|---|---|---|
| **Retrieval Hit Rate** | 0.9756 | 0.6829 | 0.9756 | Corrupted Delta: -0.2927 |
| **Mean Token F1** | 0.1982 | 0.0981 | 0.1982 | Corrupted Delta: -0.1001 |
| **Judge Accuracy** | 0.3171 | 0.1707 | 0.3171 | Corrupted Delta: -0.1463 |
| **Mean Judge Score** | 2.2927 | 1.6585 | 2.3415 | Corrupted Delta: -0.6341 |

## Data Quality & Observability Comparison
- **Corrupted Quality Passed:** `False`
- **Repaired Quality Passed:** `True`
- **Corrupted Stale Rows:** 6
- **Repaired Stale Rows:** 0

## Conclusion & Findings
- **Data Corruption Impact:** Data defects (missing summaries, truncated titles, noisy text, stale dates, duplicates) significantly degrade retrieval accuracy and agent response quality.
- **Recovery Verification:** Re-running the ETL pipeline from reliable raw Crossref snapshots successfully restores evaluation scores and quality status back to baseline levels.
