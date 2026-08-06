from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from core.config import Settings
from core.utils import write_json


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    total_rows = len(df)
    null_paper_ids = int(df["paper_id"].isnull().sum()) if "paper_id" in df.columns else total_rows
    unique_paper_ids = int(df["paper_id"].nunique()) if "paper_id" in df.columns else 0
    duplicate_paper_ids = total_rows - unique_paper_ids

    null_titles = int(df["title"].isnull().sum()) if "title" in df.columns else total_rows
    empty_summaries = int((df["summary"].str.strip() == "").sum()) if "summary" in df.columns else total_rows
    short_summaries = int((df["summary"].str.len() < 30).sum()) if "summary" in df.columns else total_rows

    stale_rows = int((df["age_days"] > settings.freshness_threshold_days).sum()) if "age_days" in df.columns else 0

    passed = (
        null_paper_ids == 0
        and duplicate_paper_ids == 0
        and null_titles == 0
        and empty_summaries == 0
        and total_rows > 0
    )

    result = {
        "report_name": report_name,
        "total_rows": total_rows,
        "null_paper_ids": null_paper_ids,
        "unique_paper_ids": unique_paper_ids,
        "duplicate_paper_ids": duplicate_paper_ids,
        "null_titles": null_titles,
        "empty_summaries": empty_summaries,
        "short_summaries": short_summaries,
        "stale_rows": stale_rows,
        "passed": passed,
    }

    out_dir = settings.paths.quality_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{report_name}.json"
    write_json(out_path, result)
    return result


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path: Path) -> dict[str, Any]:
    total_rows = len(df)
    if total_rows == 0:
        report = {
            "latest_published": "N/A",
            "oldest_published": "N/A",
            "stale_rows": 0,
            "total_rows": 0,
            "stale_ratio": 0.0,
            "is_fresh": False,
        }
    else:
        latest = str(df["published"].max())
        oldest = str(df["published"].min())
        stale_rows = int((df["age_days"] > settings.freshness_threshold_days).sum()) if "age_days" in df.columns else 0
        stale_ratio = round(stale_rows / total_rows, 4)
        is_fresh = stale_rows == 0 or stale_ratio < 0.25

        report = {
            "latest_published": latest,
            "oldest_published": oldest,
            "stale_rows": stale_rows,
            "total_rows": total_rows,
            "stale_ratio": stale_ratio,
            "is_fresh": is_fresh,
        }

    report_path = Path(report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(report_path, report)
    return report

