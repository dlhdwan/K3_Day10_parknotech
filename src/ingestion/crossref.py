import json
import re
import time
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path

from core.config import Settings
from core.utils import read_json, write_json


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


def _clean_html_tags(text: str) -> str:
    if not text:
        return ""
    cleaned = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", cleaned).strip()


def _parse_date(date_dict: dict | None) -> str:
    if not date_dict or not isinstance(date_dict, dict):
        return "2024-01-01"
    date_parts = date_dict.get("date-parts", [])
    if date_parts and isinstance(date_parts, list) and len(date_parts) > 0:
        parts = date_parts[0]
        if len(parts) >= 3:
            return f"{parts[0]:04d}-{parts[1]:02d}-{parts[2]:02d}"
        elif len(parts) == 2:
            return f"{parts[0]:04d}-{parts[1]:02d}-01"
        elif len(parts) == 1:
            return f"{parts[0]:04d}-01-01"
    return "2024-01-01"


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    items = payload.get("message", {}).get("items", [])
    records: list[PaperRecord] = []

    for item in items:
        doi = item.get("DOI", "").strip()
        if not doi:
            continue

        title_raw = item.get("title", [])
        title = ""
        if isinstance(title_raw, list) and title_raw:
            title = title_raw[0]
        elif isinstance(title_raw, str):
            title = title_raw
        title = _clean_html_tags(title)
        if not title:
            continue

        abstract_raw = item.get("abstract", "")
        summary = _clean_html_tags(abstract_raw)
        if not summary:
            summary = f"Academic paper titled '{title}' published in Crossref database."

        authors_raw = item.get("author", [])
        authors: list[str] = []
        if isinstance(authors_raw, list):
            for a in authors_raw:
                if isinstance(a, dict):
                    given = a.get("given", "").strip()
                    family = a.get("family", "").strip()
                    name = f"{given} {family}".strip() if (given or family) else a.get("name", "").strip()
                    if name:
                        authors.append(name)
        if not authors:
            authors = ["Unknown Author"]

        subjects = item.get("subject", [])
        categories = [str(s).strip() for s in subjects if str(s).strip()] if isinstance(subjects, list) else []
        if not categories:
            categories = ["Computer Science", "Artificial Intelligence"]
        primary_category = categories[0]

        published = _parse_date(
            item.get("published-online") or item.get("published-print") or item.get("issued") or item.get("created")
        )
        updated = _parse_date(item.get("deposited") or item.get("created"))

        abs_url = item.get("URL", f"https://doi.org/{doi}")
        pdf_url = abs_url
        links = item.get("link", [])
        if isinstance(links, list):
            for link in links:
                if isinstance(link, dict) and link.get("content-type") == "application/pdf":
                    pdf_url = link.get("URL", abs_url)
                    break

        publisher = str(item.get("publisher", "")).strip()
        comment = f"Publisher: {publisher}" if publisher else ""

        records.append(
            PaperRecord(
                paper_id=doi,
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
        )
    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    if not settings.refresh_source and settings.paths.raw_records_json.exists():
        return load_raw_records(settings.paths.raw_records_json)

    query_params = {
        "query": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
    }
    url = f"https://api.crossref.org/works?{urllib.parse.urlencode(query_params)}"
    headers = {"User-Agent": "K3-Day10-DataPipeline/1.0 (mailto:student@example.com)"}

    req = urllib.request.Request(url, headers=headers)
    payload = None

    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                if response.status == 200:
                    payload = json.loads(response.read().decode("utf-8"))
                    break
        except Exception as exc:
            if attempt == 2:
                if settings.paths.raw_api_response.exists():
                    payload = read_json(settings.paths.raw_api_response)
                else:
                    raise RuntimeError(f"Failed to fetch data from Crossref API: {exc}") from exc
            time.sleep(2**attempt)

    if payload is None:
        raise RuntimeError("No payload returned from Crossref API")

    settings.paths.raw_api_response.parent.mkdir(parents=True, exist_ok=True)
    write_json(settings.paths.raw_api_response, payload)

    records = parse_crossref_payload(payload)
    records_dict = [asdict(r) for r in records]
    settings.paths.raw_records_json.parent.mkdir(parents=True, exist_ok=True)
    write_json(settings.paths.raw_records_json, records_dict)

    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    items = read_json(path)
    records: list[PaperRecord] = []
    for item in items:
        records.append(PaperRecord(**item))
    return records

