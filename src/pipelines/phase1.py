from __future__ import annotations

from datetime import UTC, datetime

from core.config import load_settings, require_llm_credentials
from core.utils import write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    print("=== Phase 1: Baseline Pipeline Execution ===")
    settings = load_settings()
    require_llm_credentials(settings)

    print(f"1. Fetching raw records from {settings.source_api}...")
    records = fetch_source_records(settings)
    print(f"   Fetched {len(records)} raw paper records.")

    print("2. Building clean dataframe...")
    clean_df = build_clean_dataframe(records, run_date=datetime.now(UTC))
    settings.paths.clean_csv.parent.mkdir(parents=True, exist_ok=True)
    clean_df.to_csv(str(settings.paths.clean_csv), index=False)
    write_json(settings.paths.clean_json, clean_df.to_dict(orient="records"))
    print(f"   Saved {len(clean_df)} clean rows to {settings.paths.clean_json}.")

    print("3. Building Chroma embedding index...")
    index = LocalEmbeddingIndex.build(clean_df, settings, settings.paths.embeddings_json)
    print("   ChromaDB baseline index created.")

    print("4. Preparing evaluation test set...")
    if settings.refresh_test_set or not settings.paths.eval_testset.exists():
        build_test_set(clean_df, settings.paths.eval_testset)
        print(f"   Created test set at {settings.paths.eval_testset}.")

    print("5. Evaluating baseline RAG pipeline...")
    bundle = evaluate_pipeline(
        settings,
        index,
        settings.paths.eval_testset,
        settings.paths.baseline_metrics,
        settings.paths.baseline_answers,
    )
    print("   Baseline evaluation completed.")
    print(
        f"   Hit Rate: {bundle.summary.get('retrieval_hit_rate'):.4f} | "
        f"Token F1: {bundle.summary.get('mean_token_f1'):.4f} | "
        f"Judge Score: {bundle.summary.get('mean_judge_score'):.2f}"
    )

    print("6. Running data observability checks...")
    quality = run_data_quality_checks(clean_df, settings, "baseline_quality")
    freshness = build_freshness_report(clean_df, settings, settings.paths.freshness_report)

    print("7. Generating Phase 1 report...")
    source_summary = {
        "source_api": settings.source_api,
        "total_records": len(records),
        "clean_rows": len(clean_df),
    }
    generate_phase1_report(settings.paths.baseline_report, source_summary, bundle.summary, quality, freshness)
    print(f"=== Phase 1 Baseline Execution Finished. Report: {settings.paths.baseline_report} ===")


if __name__ == "__main__":
    main()


