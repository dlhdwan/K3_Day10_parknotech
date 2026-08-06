from __future__ import annotations

from datetime import UTC, datetime
import re

import pandas as pd

from core.utils import compact_join, normalize_whitespace
from ingestion.crossref import PaperRecord


def _parse_date_to_utc(date_str: str) -> datetime | None:
    if not date_str:
        return None
    try:
        dt = datetime.strptime(date_str.strip(), "%Y-%m-%d")
        return dt.replace(tzinfo=UTC)
    except ValueError:
        return None


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Clean raw records and construct a DataFrame ready for embedding.

    1. Normalize title, summary, authors, categories.
    2. Parse published/updated date.
    3. Compute age_days relative to run_date.
    4. Create helper columns:
       - authors_joined
       - categories_joined
       - summary_chars
       - text_for_embedding
    5. Drop duplicates and filter invalid rows.
    6. Sort dataframe by published date descending and return.
    """
    if not records:
        return pd.DataFrame(
            columns=[
                "paper_id",
                "title",
                "summary",
                "authors",
                "authors_joined",
                "categories",
                "categories_joined",
                "primary_category",
                "published",
                "updated",
                "age_days",
                "summary_chars",
                "text_for_embedding",
                "abs_url",
                "pdf_url",
                "comment",
            ]
        )

    run_date_utc = run_date.astimezone(UTC) if run_date.tzinfo else run_date.replace(tzinfo=UTC)

    cleaned_rows: list[dict] = []
    for rec in records:
        paper_id = rec.paper_id.strip() if rec.paper_id else ""
        title = normalize_whitespace(rec.title) if rec.title else ""
        summary = normalize_whitespace(rec.summary) if rec.summary else ""

        # Filter out invalid records (must have valid paper_id, title, and summary)
        if not paper_id or not title or len(summary) < 10:
            continue

        authors = [normalize_whitespace(a) for a in rec.authors if a and normalize_whitespace(a)]
        if not authors:
            authors = ["Unknown Author"]
        authors_joined = compact_join(authors, ", ")

        categories = [normalize_whitespace(c) for c in rec.categories if c and normalize_whitespace(c)]
        if not categories:
            categories = ["General"]
        categories_joined = compact_join(categories, ", ")
        primary_category = rec.primary_category.strip() if rec.primary_category else categories[0]

        published = rec.published.strip() if rec.published else ""
        updated = rec.updated.strip() if rec.updated else published

        pub_dt = _parse_date_to_utc(published)
        if pub_dt:
            age_days = max(0, (run_date_utc - pub_dt).days)
        else:
            age_days = 9999

        summary_chars = len(summary)

        # Build rich text for embedding
        text_for_embedding = (
            f"Title: {title}\n"
            f"Primary Category: {primary_category}\n"
            f"Authors: {authors_joined}\n"
            f"Published Date: {published}\n"
            f"Summary: {summary}"
        )

        cleaned_rows.append(
            {
                "paper_id": paper_id,
                "title": title,
                "summary": summary,
                "authors": authors,
                "authors_joined": authors_joined,
                "categories": categories,
                "categories_joined": categories_joined,
                "primary_category": primary_category,
                "published": published,
                "updated": updated,
                "age_days": age_days,
                "summary_chars": summary_chars,
                "text_for_embedding": text_for_embedding,
                "abs_url": rec.abs_url.strip() if rec.abs_url else "",
                "pdf_url": rec.pdf_url.strip() if rec.pdf_url else "",
                "comment": rec.comment.strip() if rec.comment else "",
            }
        )

    df = pd.DataFrame(cleaned_rows)

    if df.empty:
        return df

    # Drop duplicates by paper_id or title
    df = df.drop_duplicates(subset=["paper_id"], keep="first")
    df["title_lower"] = df["title"].str.lower()
    df = df.drop_duplicates(subset=["title_lower"], keep="first").drop(columns=["title_lower"])

    # Sort by published date descending (newest first)
    df = df.sort_values(by="published", ascending=False).reset_index(drop=True)

    return df

