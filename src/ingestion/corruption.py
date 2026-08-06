from pathlib import Path
import random
import pandas as pd

from core.utils import write_json


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path: Path) -> pd.DataFrame:
    corrupted_df = df.copy()
    original_count = len(corrupted_df)
    log_entries = []

    if original_count == 0:
        write_json(output_log_path, {"total_corruptions": 0, "logs": []})
        return corrupted_df

    random.seed(42)

    # 1. Drop latest records (xóa ~15% bài báo mới nhất)
    drop_count = max(1, int(original_count * 0.15))
    corrupted_df = corrupted_df.sort_values(by="published", ascending=False).iloc[drop_count:].reset_index(drop=True)
    log_entries.append(
        {
            "corruption_type": "drop_latest_records",
            "description": f"Dropped top {drop_count} newest records to simulate missing fresh articles.",
            "records_affected": drop_count,
        }
    )

    current_count = len(corrupted_df)
    indices = list(range(current_count))
    random.shuffle(indices)

    # Chia tập chỉ số cho các dạng biến đổi
    n = max(1, current_count // 5)
    blank_summary_idx = indices[:n]
    noise_idx = indices[n : 2 * n]
    truncate_title_idx = indices[2 * n : 3 * n]
    stale_date_idx = indices[3 * n : 4 * n]

    # 2. Blank summary (để trống summary)
    for idx in blank_summary_idx:
        corrupted_df.at[idx, "summary"] = ""
        corrupted_df.at[idx, "summary_chars"] = 0
    log_entries.append(
        {
            "corruption_type": "blank_summary",
            "description": f"Cleared summary text for {len(blank_summary_idx)} records.",
            "records_affected": len(blank_summary_idx),
        }
    )

    # 3. Inject noise (inject từ nhiễu/rác)
    noisy_words = ["CORRUPTED_NOISE_XXXX", "NULL_DATA_GARBAGE", "INVALID_TEXT_FOOBAR", "RANDOM_ERR_CHUNK"]
    for idx in noise_idx:
        orig = corrupted_df.at[idx, "summary"]
        noise_str = " " + " ".join(random.choices(noisy_words, k=6)) + " "
        corrupted_df.at[idx, "summary"] = str(orig) + noise_str
        corrupted_df.at[idx, "summary_chars"] = len(corrupted_df.at[idx, "summary"])
    log_entries.append(
        {
            "corruption_type": "inject_noise",
            "description": f"Injected random noise words into summary for {len(noise_idx)} records.",
            "records_affected": len(noise_idx),
        }
    )

    # 4. Truncate title (cắt ngắn tiêu đề)
    for idx in truncate_title_idx:
        orig_title = str(corrupted_df.at[idx, "title"])
        corrupted_df.at[idx, "title"] = orig_title[:8] + "..." if len(orig_title) > 8 else "Trunc..."
    log_entries.append(
        {
            "corruption_type": "truncate_title",
            "description": f"Truncated titles down to <10 characters for {len(truncate_title_idx)} records.",
            "records_affected": len(truncate_title_idx),
        }
    )

    # 5. Make published date old (thay đổi ngày xuất bản thành cũ > 180 ngày)
    for idx in stale_date_idx:
        corrupted_df.at[idx, "published"] = "2020-01-01"
        corrupted_df.at[idx, "age_days"] = 2000
    log_entries.append(
        {
            "corruption_type": "make_published_date_stale",
            "description": f"Set publication date to 2020-01-01 (stale > 180 days) for {len(stale_date_idx)} records.",
            "records_affected": len(stale_date_idx),
        }
    )

    # 6. Add duplicate rows (chèn thêm các dòng trùng lặp)
    dup_count = max(1, current_count // 6)
    dups = corrupted_df.iloc[:dup_count].copy()
    corrupted_df = pd.concat([corrupted_df, dups], ignore_index=True)
    log_entries.append(
        {
            "corruption_type": "add_duplicate_rows",
            "description": f"Duplicated {dup_count} records to create redundant vector entries.",
            "records_affected": dup_count,
        }
    )

    # 7. Rebuild text_for_embedding
    corrupted_df["text_for_embedding"] = (
        "Title: "
        + corrupted_df["title"].astype(str)
        + "\nCategories: "
        + corrupted_df["categories_joined"].astype(str)
        + "\nSummary: "
        + corrupted_df["summary"].astype(str)
    )

    audit_payload = {
        "original_record_count": original_count,
        "corrupted_record_count": len(corrupted_df),
        "total_corruptions": len(log_entries),
        "corruption_details": log_entries,
    }
    write_json(output_log_path, audit_payload)

    return corrupted_df

