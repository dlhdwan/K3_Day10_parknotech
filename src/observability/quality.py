from __future__ import annotations

from typing import Any

import json
from unittest import result

import pandas as pd

from core.config import Settings

MIN_SUMMARY_LENGTH = 100

def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """TODO(student): tao bo data quality checks.

    Pseudo-code:
    1. Check row count.
    2. Check `paper_id` not null va unique.
    3. Check `title` not null.
    4. Check do dai `summary`.
    5. Check freshness bang `age_days`.
    6. Ghi ket qua vao `data/quality/`.
    """
    row_count = len(df)
    paper_id_missing = df["paper_id"].isna().sum()
    paper_id_unique = not df["paper_id"].duplicated().any()
    title_missing = (
        df["title"].isna()
        | (df["title"].str.strip() == "")
    ).sum()
    if "summary_chars" in df.columns:
        short_summary = (df["summary_chars"] < MIN_SUMMARY_LENGTH).sum()
    else:
        short_summary = (
            df["summary"]
            .fillna("")
            .str.len()
            .lt(MIN_SUMMARY_LENGTH)
            .sum()
        )
    stale_rows = (
        df["age_days"] > settings.freshness_threshold_days
    ).sum()
    passed = (
        paper_id_missing == 0
        and paper_id_unique
        and title_missing == 0
        and short_summary == 0
        and stale_rows == 0
    )
    result = {
        "row_count": row_count,
        "paper_id_missing": paper_id_missing,
        "paper_id_unique": paper_id_unique,
        "title_missing": title_missing,
        "short_summary": short_summary,
        "stale_rows": stale_rows,
        "passed": passed,
    }
    settings.paths.quality_dir.mkdir(parents=True, exist_ok=True)

    report_path = settings.paths.quality_dir / f"{report_name}.json"

    with report_path.open("w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    return result


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """TODO(student): tong hop freshness report.

    Pseudo-code:
    1. Tim latest va oldest published date.
    2. Dem so dong stale.
    3. Tao payload:
       - latest_published
       - oldest_published
       - stale_rows
       - total_rows
       - is_fresh
    4. Ghi JSON report.
    """
    latest_published = df["published"].max()
    oldest_published = df["published"].min()
    stale_rows = (
        df["age_days"] > settings.freshness_threshold_days
    ).sum()
    total_rows = len(df)
    is_fresh = stale_rows == 0
    latest_published = (
        latest_published.isoformat()
        if pd.notna(latest_published)
        else None
    )

    oldest_published = (
        oldest_published.isoformat()
        if pd.notna(oldest_published)
        else None
    )
    result = {
        "latest_published": latest_published,
        "oldest_published": oldest_published,
        "stale_rows": stale_rows,
        "total_rows": total_rows,
        "is_fresh": is_fresh,
    }
    with report_path.open("w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    return result
