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
- Raw Records: {source_summary.get("raw_count")}
- Clean Records: {source_summary.get("clean_count")}

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
    report_path: Path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
) -> None:
    """Generate markdown comparison report for baseline/corrupted/repaired."""

    report = f"""# Corruption Comparison Report

## Evaluation Metrics

| Metric | Baseline | Corrupted | Repaired |
|--------|----------:|----------:|----------:|
| Retrieval Hit Rate | {baseline_metrics.get("retrieval_hit_rate")} | {corrupted_metrics.get("retrieval_hit_rate")} | {repaired_metrics.get("retrieval_hit_rate")} |
| Mean Token F1 | {baseline_metrics.get("mean_token_f1")} | {corrupted_metrics.get("mean_token_f1")} | {repaired_metrics.get("mean_token_f1")} |
| Judge Accuracy | {baseline_metrics.get("judge_accuracy")} | {corrupted_metrics.get("judge_accuracy")} | {repaired_metrics.get("judge_accuracy")} |
| Mean Judge Score | {baseline_metrics.get("mean_judge_score")} | {corrupted_metrics.get("mean_judge_score")} | {repaired_metrics.get("mean_judge_score")} |

## Data Quality

| Check | Corrupted | Repaired |
|-------|----------:|---------:|
| Row Count | {corrupted_quality.get("row_count")} | {repaired_quality.get("row_count")} |
| Missing Paper ID | {corrupted_quality.get("paper_id_missing")} | {repaired_quality.get("paper_id_missing")} |
| Paper ID Unique | {corrupted_quality.get("paper_id_unique")} | {repaired_quality.get("paper_id_unique")} |
| Missing Title | {corrupted_quality.get("title_missing")} | {repaired_quality.get("title_missing")} |
| Short Summary | {corrupted_quality.get("short_summary")} | {repaired_quality.get("short_summary")} |
| Stale Rows | {corrupted_quality.get("stale_rows")} | {repaired_quality.get("stale_rows")} |
| Passed | {corrupted_quality.get("passed")} | {repaired_quality.get("passed")} |

## Freshness

| Metric | Corrupted | Repaired |
|--------|----------:|---------:|
| Latest Published | {corrupted_freshness.get("latest_published")} | {repaired_freshness.get("latest_published")} |
| Oldest Published | {corrupted_freshness.get("oldest_published")} | {repaired_freshness.get("oldest_published")} |
| Stale Rows | {corrupted_freshness.get("stale_rows")} | {repaired_freshness.get("stale_rows")} |
| Total Rows | {corrupted_freshness.get("total_rows")} | {repaired_freshness.get("total_rows")} |
| Is Fresh | {corrupted_freshness.get("is_fresh")} | {repaired_freshness.get("is_fresh")} |
"""

    report_path.parent.mkdir(parents=True, exist_ok=True)

    with report_path.open("w", encoding="utf-8") as f:
        f.write(report)
