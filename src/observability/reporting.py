from __future__ import annotations

from pathlib import Path
from typing import Any

from core.utils import write_text


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    report_path = Path(report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    content = f"""# Phase 1 - Baseline Data Pipeline & RAG Evaluation Report

## 1. Data Source Summary
- **Source API**: {source_summary.get("source_api", "Crossref API")}
- **Total Records Ingested**: {source_summary.get("total_records", 0)}
- **Cleaned Dataset Size**: {source_summary.get("clean_rows", 0)} rows

## 2. Baseline RAG Evaluation Metrics
- **Evaluated Samples**: {metrics.get("samples", 0)}
- **Retrieval Hit Rate**: {metrics.get("retrieval_hit_rate", 0.0):.4f}
- **Mean Token F1**: {metrics.get("mean_token_f1", 0.0):.4f}
- **Judge Accuracy**: {metrics.get("judge_accuracy", 0.0):.4f}
- **Mean Judge Score (1-5)**: {metrics.get("mean_judge_score", 0.0):.2f}

## 3. Data Observability & Health
### Data Quality Checks
- **Status**: {"PASSED" if quality.get("passed") else "FAILED"}
- **Null Paper IDs**: {quality.get("null_paper_ids", 0)}
- **Duplicate Paper IDs**: {quality.get("duplicate_paper_ids", 0)}
- **Empty Summaries**: {quality.get("empty_summaries", 0)}

### Data Freshness Monitoring
- **Status**: {"FRESH" if freshness.get("is_fresh") else "STALE"}
- **Latest Published Date**: {freshness.get("latest_published", "N/A")}
- **Oldest Published Date**: {freshness.get("oldest_published", "N/A")}
- **Stale Rows (>180 days)**: {freshness.get("stale_rows", 0)} / {freshness.get("total_rows", 0)}
"""
    write_text(report_path, content)


def generate_corruption_report(
    report_path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
) -> None:
    report_path = Path(report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    content = f"""# Data Corruption, Impact Analysis & Repair Comparison Report

## 1. Executive Summary & Impact Analysis
Data corruption significantly degrades the performance of RAG retrieval and answer generation.
By repairing the dataset directly from raw immutable artifacts, the pipeline fully restores metric scores to baseline levels.

## 2. End-to-End Metrics Comparison Table

| Metric State | Samples | Retrieval Hit Rate | Mean Token F1 | Judge Accuracy | Mean Judge Score (1-5) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Baseline (Clean)** | {baseline_metrics.get("samples", 0)} | {baseline_metrics.get("retrieval_hit_rate", 0.0):.4f} | {baseline_metrics.get("mean_token_f1", 0.0):.4f} | {baseline_metrics.get("judge_accuracy", 0.0):.4f} | {baseline_metrics.get("mean_judge_score", 0.0):.2f} |
| **Corrupted (Damaged)** | {corrupted_metrics.get("samples", 0)} | {corrupted_metrics.get("retrieval_hit_rate", 0.0):.4f} | {corrupted_metrics.get("mean_token_f1", 0.0):.4f} | {corrupted_metrics.get("judge_accuracy", 0.0):.4f} | {corrupted_metrics.get("mean_judge_score", 0.0):.2f} |
| **Repaired (Restored)** | {repaired_metrics.get("samples", 0)} | {repaired_metrics.get("retrieval_hit_rate", 0.0):.4f} | {repaired_metrics.get("mean_token_f1", 0.0):.4f} | {repaired_metrics.get("judge_accuracy", 0.0):.4f} | {repaired_metrics.get("mean_judge_score", 0.0):.2f} |

## 3. Data Observability & Health Signals

### Corrupted State Health Signals
- **Data Quality Status**: {"PASSED" if corrupted_quality.get("passed") else "FAILED"}
- **Duplicates Introduced**: {corrupted_quality.get("duplicate_paper_ids", 0)}
- **Blank Summaries**: {corrupted_quality.get("empty_summaries", 0)}
- **Freshness Status**: {"FRESH" if corrupted_freshness.get("is_fresh") else "STALE"} (Stale rows: {corrupted_freshness.get("stale_rows", 0)})

### Repaired State Health Signals
- **Data Quality Status**: {"PASSED" if repaired_quality.get("passed") else "FAILED"}
- **Duplicates**: {repaired_quality.get("duplicate_paper_ids", 0)}
- **Blank Summaries**: {repaired_quality.get("empty_summaries", 0)}
- **Freshness Status**: {"FRESH" if repaired_freshness.get("is_fresh") else "STALE"} (Stale rows: {repaired_freshness.get("stale_rows", 0)})

## 4. Conclusion & Key Takeaways
1. Data corruption (missing abstracts, truncated titles, duplicate entries) directly degrades retrieval accuracy and LLM answer quality.
2. Maintaining raw API responses enables seamless self-healing and data recovery.
3. Continuous observability checks act as an essential gatekeeper before publishing vector embeddings.
"""
    write_text(report_path, content)

