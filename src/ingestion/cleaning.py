from __future__ import annotations

from datetime import datetime

import pandas as pd

from ingestion.crossref import PaperRecord


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    rows = []
    run_dt_date = run_date.date() if isinstance(run_date, datetime) else run_date

    for r in records:
        paper_id = (r.paper_id or "").strip()
        title = (r.title or "").strip()
        summary = (r.summary or "").strip()

        if not paper_id or not title or not summary:
            continue

        authors = r.authors if isinstance(r.authors, list) else []
        categories = r.categories if isinstance(r.categories, list) else []
        authors_joined = ", ".join(authors) if authors else "Unknown Author"
        categories_joined = ", ".join(categories) if categories else (r.primary_category or "General")
        primary_cat = r.primary_category or (categories[0] if categories else "General")

        published_str = r.published or "2024-01-01"
        try:
            pub_date = datetime.strptime(published_str[:10], "%Y-%m-%d").date()
        except ValueError:
            pub_date = run_dt_date

        age_days = max(0, (run_dt_date - pub_date).days)
        summary_chars = len(summary)

        text_for_embedding = (
            f"Title: {title}\n"
            f"Primary Category: {primary_cat}\n"
            f"Authors: {authors_joined}\n"
            f"Published: {published_str}\n"
            f"Summary: {summary}"
        )

        rows.append(
            {
                "paper_id": paper_id,
                "title": title,
                "summary": summary,
                "authors": authors,
                "categories": categories,
                "primary_category": primary_cat,
                "published": published_str,
                "updated": r.updated or published_str,
                "abs_url": r.abs_url or f"https://doi.org/{paper_id}",
                "pdf_url": r.pdf_url or f"https://doi.org/{paper_id}",
                "comment": r.comment or "",
                "authors_joined": authors_joined,
                "categories_joined": categories_joined,
                "summary_chars": summary_chars,
                "age_days": age_days,
                "text_for_embedding": text_for_embedding,
            }
        )

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    df = df.drop_duplicates(subset=["paper_id"], keep="first")
    df = df[df["summary_chars"] >= 15]
    df = df.sort_values(by="published", ascending=False).reset_index(drop=True)
    return df

