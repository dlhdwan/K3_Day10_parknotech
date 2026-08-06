from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd

from core.config import load_settings, require_llm_credentials
from core.utils import read_json, write_json
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    print("=== Phase 2: Corruption, Evaluation, Repair & Comparison Flow ===")
    settings = load_settings()
    require_llm_credentials(settings)

    if not settings.paths.clean_json.exists() or not settings.paths.baseline_metrics.exists():
        raise RuntimeError("Baseline artifacts not found. Please run script/run_phase1.py first.")

    baseline_metrics = read_json(settings.paths.baseline_metrics)

    print("1. Loading clean baseline dataset...")
    clean_df = pd.read_json(settings.paths.clean_json)

    print("2. Corrupting dataset...")
    corrupted_df = corrupt_clean_dataframe(clean_df, settings.paths.corruption_log)
    settings.paths.corrupted_clean_csv.parent.mkdir(parents=True, exist_ok=True)
    corrupted_df.to_csv(str(settings.paths.corrupted_clean_csv), index=False)
    write_json(settings.paths.corrupted_clean_json, corrupted_df.to_dict(orient="records"))
    print(f"   Corrupted dataset saved ({len(corrupted_df)} rows).")

    print("3. Building corrupted embedding index & evaluating...")
    corrupted_index = LocalEmbeddingIndex.build(corrupted_df, settings, settings.paths.corrupted_embeddings_json)
    corrupted_bundle = evaluate_pipeline(
        settings,
        corrupted_index,
        settings.paths.eval_testset,
        settings.paths.corrupted_metrics,
        settings.paths.corrupted_answers,
    )
    print(
        f"   Corrupted -> Hit Rate: {corrupted_bundle.summary.get('retrieval_hit_rate'):.4f} | "
        f"Token F1: {corrupted_bundle.summary.get('mean_token_f1'):.4f} | "
        f"Judge Score: {corrupted_bundle.summary.get('mean_judge_score'):.2f}"
    )

    corrupted_quality = run_data_quality_checks(corrupted_df, settings, "corrupted_quality")
    corrupted_freshness = build_freshness_report(
        corrupted_df, settings, settings.paths.quality_dir / "corrupted_freshness.json"
    )

    print("4. Repairing dataset from raw immutable records...")
    raw_records = load_raw_records(settings.paths.raw_records_json)
    repaired_df = build_clean_dataframe(raw_records, run_date=datetime.now(UTC))
    settings.paths.repaired_clean_csv.parent.mkdir(parents=True, exist_ok=True)
    repaired_df.to_csv(str(settings.paths.repaired_clean_csv), index=False)
    write_json(settings.paths.repaired_clean_json, repaired_df.to_dict(orient="records"))

    print("5. Building repaired embedding index & evaluating...")
    repaired_index = LocalEmbeddingIndex.build(repaired_df, settings, settings.paths.repaired_embeddings_json)
    repaired_bundle = evaluate_pipeline(
        settings,
        repaired_index,
        settings.paths.eval_testset,
        settings.paths.repaired_metrics,
        settings.paths.repaired_answers,
    )
    print(
        f"   Repaired -> Hit Rate: {repaired_bundle.summary.get('retrieval_hit_rate'):.4f} | "
        f"Token F1: {repaired_bundle.summary.get('mean_token_f1'):.4f} | "
        f"Judge Score: {repaired_bundle.summary.get('mean_judge_score'):.2f}"
    )

    repaired_quality = run_data_quality_checks(repaired_df, settings, "repaired_quality")
    repaired_freshness = build_freshness_report(
        repaired_df, settings, settings.paths.quality_dir / "repaired_freshness.json"
    )

    print("6. Generating comparison report...")
    generate_corruption_report(
        settings.paths.comparison_report,
        baseline_metrics,
        corrupted_bundle.summary,
        repaired_bundle.summary,
        corrupted_quality,
        repaired_quality,
        corrupted_freshness,
        repaired_freshness,
    )
    print(f"=== Phase 2 Corruption Flow Finished. Report: {settings.paths.comparison_report} ===")


if __name__ == "__main__":
    main()


