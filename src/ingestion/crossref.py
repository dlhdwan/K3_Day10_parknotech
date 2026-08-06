from __future__ import annotations

import dataclasses
from dataclasses import dataclass
import json
import logging
from pathlib import Path
import re
import time
from typing import Any

import requests

from core.config import Settings
from core.utils import normalize_whitespace, read_json, write_json

logger = logging.getLogger(__name__)

CROSSREF_API_URL = "https://api.crossref.org/works"


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


def _parse_crossref_date(date_obj: dict | None) -> str:
    if not isinstance(date_obj, dict):
        return ""
    date_parts = date_obj.get("date-parts", [])
    if not date_parts or not isinstance(date_parts, list) or not date_parts[0]:
        return ""
    parts = date_parts[0]
    if not isinstance(parts, list):
        return ""
    year = int(parts[0]) if len(parts) > 0 and str(parts[0]).isdigit() else 1970
    month = int(parts[1]) if len(parts) > 1 and str(parts[1]).isdigit() else 1
    day = int(parts[2]) if len(parts) > 2 and str(parts[2]).isdigit() else 1
    return f"{year:04d}-{month:02d}-{day:02d}"


def _clean_html_tags(text: str) -> str:
    if not text:
        return ""
    cleaned = re.sub(r"<[^>]+>", " ", text)
    return normalize_whitespace(cleaned)


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse Crossref payload JSON into list of PaperRecord.

    1. Duyet `payload["message"]["items"]`.
    2. Lay DOI, title, abstract, authors, subject, dates, URLs.
    3. Chuan hoa text va bo record khong hop le.
    4. Tra ve list `PaperRecord`.
    """
    if not isinstance(payload, dict):
        return []

    message = payload.get("message", {})
    if not isinstance(message, dict):
        return []

    items = message.get("items", [])
    if not isinstance(items, list):
        return []

    records: list[PaperRecord] = []
    for item in items:
        if not isinstance(item, dict):
            continue

        doi = str(item.get("DOI", "")).strip()

        # Title
        title_raw = item.get("title", [])
        if isinstance(title_raw, list) and title_raw:
            title_text = str(title_raw[0])
        elif isinstance(title_raw, str):
            title_text = title_raw
        else:
            title_text = ""
        title = _clean_html_tags(title_text)

        # Skip record if title is missing
        if not title:
            continue

        paper_id = f"crossref:{doi}" if doi else f"crossref:{hash(title)}"

        # Abstract / Summary
        abstract_raw = item.get("abstract", "")
        summary = _clean_html_tags(str(abstract_raw))

        # Authors
        authors_raw = item.get("author", [])
        authors: list[str] = []
        if isinstance(authors_raw, list):
            for a in authors_raw:
                if isinstance(a, dict):
                    given = str(a.get("given", "")).strip()
                    family = str(a.get("family", "")).strip()
                    full_name = f"{given} {family}".strip()
                    name = full_name or str(a.get("name", "")).strip()
                    if name:
                        authors.append(name)
        if not authors:
            authors = ["Unknown Author"]

        # Categories
        subjects = item.get("subject", [])
        categories: list[str] = []
        if isinstance(subjects, list):
            categories = [str(s).strip() for s in subjects if str(s).strip()]
        if not categories:
            categories = ["General"]
        primary_category = categories[0]

        # Dates
        published = ""
        for date_key in ["published-online", "published-print", "issued", "posted", "created"]:
            published = _parse_crossref_date(item.get(date_key))
            if published:
                break

        updated = ""
        for date_key in ["indexed", "deposited", "updated"]:
            updated = _parse_crossref_date(item.get(date_key))
            if updated:
                break
        if not updated:
            updated = published

        # URLs
        abs_url = str(item.get("URL", f"https://doi.org/{doi}" if doi else "")).strip()

        pdf_url = ""
        links = item.get("link", [])
        if isinstance(links, list):
            for link in links:
                if isinstance(link, dict) and link.get("content-type") == "application/pdf":
                    pdf_url = str(link.get("URL", "")).strip()
                    break
        if not pdf_url:
            pdf_url = abs_url

        # Comment / Publisher / Container title
        container_title = item.get("container-title", [])
        if isinstance(container_title, list) and container_title:
            comment = str(container_title[0]).strip()
        else:
            comment = str(item.get("publisher", "")).strip()

        record = PaperRecord(
            paper_id=paper_id,
            title=title,
            summary=summary,
            authors=authors,
            categories=categories,
            primary_category=primary_category,
            published=published,
            updated=updated,
            abs_url=abs_url,
            pdf_url=pdf_url,
            comment=comment,
        )
        records.append(record)

    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Goi source API, luu raw response, parse thanh records.

    1. Tao params tu `settings.source_query`, `settings.source_filter`, `settings.max_results`.
    2. Goi API voi retry cho cac status code nhu 429/503.
    3. Luu raw response vao `settings.paths.raw_api_response`.
    4. Parse payload bang `parse_crossref_payload`.
    5. Luu records vao `settings.paths.raw_records_json`.
    """
    raw_api_path = settings.paths.raw_api_response
    raw_records_path = settings.paths.raw_records_json

    if raw_api_path.exists() and not settings.refresh_source:
        logger.info(f"Loading raw API response from cache: {raw_api_path}")
        payload = read_json(raw_api_path)
    else:
        params = {
            "query": settings.source_query,
            "filter": settings.source_filter,
            "rows": settings.max_results,
        }
        headers = {
            "User-Agent": "DataObservabilityLab/1.0 (mailto:student@example.com)",
        }
        logger.info(f"Fetching source records from {CROSSREF_API_URL} with params: {params}")

        max_retries = 3
        response = None
        for attempt in range(1, max_retries + 1):
            try:
                res = requests.get(CROSSREF_API_URL, params=params, headers=headers, timeout=30)
                if res.status_code in (429, 503, 504):
                    logger.warning(f"Attempt {attempt}: Received status {res.status_code}. Retrying...")
                    time.sleep(2 * attempt)
                    continue
                res.raise_for_status()
                response = res
                break
            except requests.RequestException as e:
                logger.warning(f"Attempt {attempt}: Request error: {e}")
                if attempt == max_retries:
                    raise
                time.sleep(2 * attempt)

        if response is None:
            raise RuntimeError("Failed to fetch data from Crossref API after retries.")

        payload = response.json()
        write_json(raw_api_path, payload)

    records = parse_crossref_payload(payload)

    # Save raw records snapshot
    records_dict = [dataclasses.asdict(r) for r in records]
    write_json(raw_records_path, records_dict)

    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Doc JSON snapshot va map thanh `PaperRecord`."""
    data = read_json(path)
    if not isinstance(data, list):
        return []

    records: list[PaperRecord] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        record = PaperRecord(
            paper_id=item.get("paper_id", ""),
            title=item.get("title", ""),
            summary=item.get("summary", ""),
            authors=item.get("authors", []),
            categories=item.get("categories", []),
            primary_category=item.get("primary_category", "General"),
            published=item.get("published", ""),
            updated=item.get("updated", ""),
            abs_url=item.get("abs_url", ""),
            pdf_url=item.get("pdf_url", ""),
            comment=item.get("comment", ""),
        )
        records.append(record)

    return records

