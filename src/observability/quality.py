from __future__ import annotations

from typing import Any

import json
from unittest import result

import pandas as pd

from core.config import Settings

MIN_SUMMARY_LENGTH = 100

def run_data_quality_checks(
    df: pd.DataFrame,
    settings: Settings,
    report_name: str,
) -> dict[str, Any]:
    row_count = int(len(df))
    paper_id_missing = int(df["paper_id"].isna().sum())
    paper_id_unique = not df["paper_id"].duplicated().any()

    title_missing = int(
        (
            df["title"].isna()
            | (df["title"].str.strip() == "")
        ).sum()
    )

    if "summary_chars" in df.columns:
        short_summary = int(
            (df["summary_chars"] < MIN_SUMMARY_LENGTH).sum()
        )
    else:
        short_summary = int(
            df["summary"]
            .fillna("")
            .str.len()
            .lt(MIN_SUMMARY_LENGTH)
            .sum()
        )

    stale_rows = int(
        (df["age_days"] > settings.freshness_threshold_days).sum()
    )

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


def build_freshness_report(
    df: pd.DataFrame,
    settings: Settings,
    report_path,
) -> dict[str, Any]:
    """Generate freshness report."""

    latest_published = df["published"].max()
    oldest_published = df["published"].min()

    stale_rows = int(
        (df["age_days"] > settings.freshness_threshold_days).sum()
    )
    total_rows = int(len(df))
    is_fresh = bool(stale_rows == 0)

    latest_published = (
        latest_published.isoformat()
        if hasattr(latest_published, "isoformat")
        else latest_published
    )

    oldest_published = (
        oldest_published.isoformat()
        if hasattr(oldest_published, "isoformat")
        else oldest_published
    )

    result = {
        "latest_published": latest_published,
        "oldest_published": oldest_published,
        "stale_rows": stale_rows,
        "total_rows": total_rows,
        "is_fresh": is_fresh,
    }

    report_path.parent.mkdir(parents=True, exist_ok=True)

    with report_path.open("w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    return result