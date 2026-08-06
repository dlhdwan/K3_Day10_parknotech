from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import write_json


def build_test_set(df: pd.DataFrame, output_path: str | Path | None = None) -> list[dict[str, Any]]:
    """Generate evaluation test set from cleaned dataframe.

    1. Validate minimum document count.
    2. Select representative papers.
    3. Generate multiple question types:
       - summary (abstract / overview questions)
       - authors (author identification questions)
       - date (publication date questions)
       - categories (topic / category questions)
    4. Format each sample with:
       - id
       - question_type
       - question
       - ground_truth
       - ground_truth_doc_ids
    5. Save JSON file to output_path if provided.
    """
    if df.empty:
        raise ValueError("Cannot build test set from an empty DataFrame.")

    test_samples: list[dict[str, Any]] = []

    # Pick up to 10 representative papers
    sample_size = min(len(df), 10)
    sampled_df = df.head(sample_size)

    for idx, (_, row) in enumerate(sampled_df.iterrows(), start=1):
        paper_id = str(row["paper_id"])
        title = str(row["title"])
        summary = str(row["summary"])
        authors = str(row["authors_joined"])
        published = str(row["published"])
        categories = str(row["categories_joined"])
        primary_cat = str(row["primary_category"])

        # 1. Summary / Overview question
        test_samples.append(
            {
                "id": f"test-{len(test_samples) + 1:03d}",
                "question_type": "summary",
                "question": f"What is the main summary or research focus of the paper '{title}'?",
                "ground_truth": f"The paper '{title}' discusses: {summary}",
                "ground_truth_doc_ids": [paper_id],
            }
        )

        # 2. Authors question
        test_samples.append(
            {
                "id": f"test-{len(test_samples) + 1:03d}",
                "question_type": "authors",
                "question": f"Who are the authors of the paper titled '{title}'?",
                "ground_truth": f"The authors of '{title}' are {authors}.",
                "ground_truth_doc_ids": [paper_id],
            }
        )

        # 3. Date question
        test_samples.append(
            {
                "id": f"test-{len(test_samples) + 1:03d}",
                "question_type": "date",
                "question": f"When was the paper '{title}' published?",
                "ground_truth": f"The paper '{title}' was published on {published}.",
                "ground_truth_doc_ids": [paper_id],
            }
        )

        # 4. Categories question
        test_samples.append(
            {
                "id": f"test-{len(test_samples) + 1:03d}",
                "question_type": "categories",
                "question": f"What category or subject area does the paper '{title}' belong to?",
                "ground_truth": f"The paper '{title}' belongs to the {categories} categories (Primary: {primary_cat}).",
                "ground_truth_doc_ids": [paper_id],
            }
        )

    # Add a broad multi-document inquiry
    if len(df) >= 2:
        top_titles = [f"'{t}'" for t in df["title"].head(3)]
        top_ids = list(df["paper_id"].head(3))
        titles_str = ", ".join(top_titles)
        test_samples.append(
            {
                "id": f"test-{len(test_samples) + 1:03d}",
                "question_type": "summary",
                "question": "What are some recent papers discussing Large Language Models and Retrieval-Augmented Generation?",
                "ground_truth": f"Recent relevant papers include: {titles_str}.",
                "ground_truth_doc_ids": top_ids,
            }
        )

    if output_path is not None:
        write_json(Path(output_path), test_samples)

    return test_samples

