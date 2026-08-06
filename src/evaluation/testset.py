from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import write_json


def build_test_set(df: pd.DataFrame, output_path: Path) -> list[dict[str, Any]]:
    if df.empty:
        raise ValueError("Cannot build test set from empty dataframe.")

    test_samples: list[dict[str, Any]] = []
    sample_df = df.head(6)

    q_index = 1
    for _, row in sample_df.iterrows():
        paper_id = str(row["paper_id"])
        title = str(row["title"])
        summary = str(row["summary"])
        authors = str(row["authors_joined"])
        published = str(row["published"])

        test_samples.append(
            {
                "id": f"q{q_index}",
                "question_type": "summary",
                "question": f"What is the main summary and contribution of paper DOI {paper_id} titled '{title}'?",
                "ground_truth": summary,
                "ground_truth_doc_ids": [paper_id],
            }
        )
        q_index += 1

        test_samples.append(
            {
                "id": f"q{q_index}",
                "question_type": "authors",
                "question": f"Who are the authors of the paper '{title}' (DOI: {paper_id})?",
                "ground_truth": f"The authors are {authors}.",
                "ground_truth_doc_ids": [paper_id],
            }
        )
        q_index += 1

        test_samples.append(
            {
                "id": f"q{q_index}",
                "question_type": "published_date",
                "question": f"When was the paper titled '{title}' (DOI: {paper_id}) published?",
                "ground_truth": f"The paper was published on {published}.",
                "ground_truth_doc_ids": [paper_id],
            }
        )
        q_index += 1

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(output_path, test_samples)
    return test_samples

