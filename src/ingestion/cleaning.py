from datetime import datetime, timezone

import pandas as pd

from core.utils import compact_join, normalize_whitespace
from ingestion.crossref import PaperRecord


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    rows = []
    
    # Đảm bảo timezone-aware cho run_date
    if run_date.tzinfo is None:
        run_date_tz = run_date.replace(tzinfo=timezone.utc)
    else:
        run_date_tz = run_date

    for rec in records:
        title = normalize_whitespace(rec.title or "")
        summary = normalize_whitespace(rec.summary or "")
        
        # Bỏ qua các bản ghi không có title hoặc summary
        if not title or not summary:
            continue

        authors = [normalize_whitespace(a) for a in rec.authors if a and a.strip()]
        authors_joined = compact_join(authors, ", ") or "Unknown Author"

        categories = [normalize_whitespace(c) for c in rec.categories if c and c.strip()]
        categories_joined = compact_join(categories, ", ") or rec.primary_category or "General"

        # Tính published date & age_days
        published_str = rec.published or "2024-01-01"
        try:
            pub_dt = datetime.fromisoformat(published_str)
            if pub_dt.tzinfo is None:
                pub_dt = pub_dt.replace(tzinfo=timezone.utc)
        except Exception:
            pub_dt = run_date_tz

        age_days = max(0, (run_date_tz - pub_dt).days)

        # Cột text_for_embedding đặc biệt phục vụ cho Vector Store
        text_for_embedding = f"Title: {title}\nCategories: {categories_joined}\nSummary: {summary}"

        rows.append(
            {
                "paper_id": str(rec.paper_id).lower().strip(),
                "title": title,
                "summary": summary,
                "authors": authors,
                "authors_joined": authors_joined,
                "categories": categories,
                "categories_joined": categories_joined,
                "primary_category": rec.primary_category or "General",
                "published": published_str,
                "updated": rec.updated or published_str,
                "age_days": age_days,
                "summary_chars": len(summary),
                "text_for_embedding": text_for_embedding,
                "abs_url": rec.abs_url or "",
                "pdf_url": rec.pdf_url or "",
                "comment": rec.comment or "",
            }
        )

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    # Loại bỏ bản ghi trùng lặp paper_id
    df = df.drop_duplicates(subset=["paper_id"], keep="first")
    
    # Sắp xếp bài báo mới nhất lên đầu
    df = df.sort_values(by="published", ascending=False).reset_index(drop=True)
    return df

