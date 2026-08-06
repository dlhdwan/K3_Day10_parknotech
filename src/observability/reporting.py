from __future__ import annotations

from typing import Any
from pathlib import Path


def generate_phase1_report(
    report_path: Path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Generate markdown report for Phase 1 baseline."""

    report = f"""# Phase 1 Report

## Source Summary

- Source: {source_summary.get("source")}
- Query: {source_summary.get("query")}
- Total Records: {source_summary.get("total_records")}

## Evaluation Metrics

- Retrieval Hit Rate: {metrics.get("retrieval_hit_rate")}
- Mean Token F1: {metrics.get("mean_token_f1")}
- Judge Accuracy: {metrics.get("judge_accuracy")}
- Mean Judge Score: {metrics.get("mean_judge_score")}
- RAGAS: {metrics.get("ragas")}

## Data Quality

- Row Count: {quality.get("row_count")}
- Missing Paper ID: {quality.get("paper_id_missing")}
- Paper ID Unique: {quality.get("paper_id_unique")}
- Missing Title: {quality.get("title_missing")}
- Short Summary: {quality.get("short_summary")}
- Stale Rows: {quality.get("stale_rows")}
- Passed: {quality.get("passed")}

## Freshness

- Latest Published: {freshness.get("latest_published")}
- Oldest Published: {freshness.get("oldest_published")}
- Stale Rows: {freshness.get("stale_rows")}
- Total Rows: {freshness.get("total_rows")}
- Is Fresh: {freshness.get("is_fresh")}
"""

    report_path.parent.mkdir(parents=True, exist_ok=True)

    with report_path.open("w", encoding="utf-8") as f:
        f.write(report)


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
    """TODO(student): viet markdown report so sanh baseline/corrupted/repaired."""
    raise NotImplementedError("Student task: implement corruption comparison report.")
