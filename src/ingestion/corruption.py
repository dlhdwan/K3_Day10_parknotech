from __future__ import annotations

from pathlib import Path
import pandas as pd

from core.utils import write_json


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path: Path) -> pd.DataFrame:
    c_df = df.copy()
    total_original = len(c_df)
    if total_original < 6:
        raise ValueError("Dataframe too small to apply comprehensive corruptions.")

    corruption_log: dict[str, list[str]] = {
        "dropped_latest_paper_ids": [],
        "blank_summary_paper_ids": [],
        "noise_injected_paper_ids": [],
        "truncated_title_paper_ids": [],
        "stale_date_paper_ids": [],
        "duplicate_paper_ids": [],
    }

    dropped_ids = c_df.iloc[:2]["paper_id"].tolist()
    c_df = c_df.iloc[2:].reset_index(drop=True)
    corruption_log["dropped_latest_paper_ids"] = [str(i) for i in dropped_ids]

    blank_targets = c_df.index[:2]
    for idx in blank_targets:
        paper_id = c_df.at[idx, "paper_id"]
        c_df.at[idx, "summary"] = ""
        corruption_log["blank_summary_paper_ids"].append(str(paper_id))

    noise_targets = c_df.index[2:4]
    for idx in noise_targets:
        paper_id = c_df.at[idx, "paper_id"]
        c_df.at[idx, "summary"] = str(c_df.at[idx, "summary"]) + " [NOISE GARBAGE CORRUPTED_TEXT_12345]"
        corruption_log["noise_injected_paper_ids"].append(str(paper_id))

    if len(c_df) > 4:
        idx = c_df.index[4]
        paper_id = c_df.at[idx, "paper_id"]
        c_df.at[idx, "title"] = str(c_df.at[idx, "title"])[:10] + "..."
        corruption_log["truncated_title_paper_ids"].append(str(paper_id))

    if len(c_df) > 6:
        stale_targets = c_df.index[5:7]
        for idx in stale_targets:
            paper_id = c_df.at[idx, "paper_id"]
            c_df.at[idx, "published"] = "2019-01-01"
            c_df.at[idx, "age_days"] = 2500
            corruption_log["stale_date_paper_ids"].append(str(paper_id))

    dupes = c_df.head(2).copy()
    corruption_log["duplicate_paper_ids"] = [str(i) for i in dupes["paper_id"].tolist()]
    c_df = pd.concat([c_df, dupes], ignore_index=True)

    rebuilt_texts = []
    for _, row in c_df.iterrows():
        rebuilt_texts.append(
            f"Title: {row['title']}\n"
            f"Primary Category: {row['primary_category']}\n"
            f"Authors: {row['authors_joined']}\n"
            f"Published: {row['published']}\n"
            f"Summary: {row['summary']}"
        )
    c_df["text_for_embedding"] = rebuilt_texts
    c_df["summary_chars"] = c_df["summary"].astype(str).str.len()

    output_log_path = Path(output_log_path)
    output_log_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(output_log_path, corruption_log)
    return c_df

