from datetime import datetime, timezone

from core.config import load_settings
from core.utils import write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.index import LocalEmbeddingIndex
from retrieval.qa import answer_question


def main() -> None:
    print("=== STARTING PHASE 1: BASELINE DATA PIPELINE ===")

    # 1. Load settings
    settings = load_settings()
    paths = settings.paths
    run_date = datetime.now(timezone.utc)

    # 2. Fetch/load raw records
    print(f"Fetching raw records from source ({settings.source_api})...")
    raw_records = fetch_source_records(settings)
    print(f"Loaded {len(raw_records)} raw records.")

    # 3. Clean data
    print("Cleaning raw records...")
    clean_df = build_clean_dataframe(raw_records, run_date)
    print(f"Cleaned dataset has {len(clean_df)} records.")

    # 4. Save clean CSV & JSON
    write_csv(clean_df, paths.clean_csv)
    write_json(paths.clean_json, clean_df.to_dict(orient="records"))
    print(f"Saved clean dataset to {paths.clean_csv}")

    # 5. Build Chroma embedding index
    print(f"Building vector index using embedding model '{settings.embedding_model}'...")
    index = LocalEmbeddingIndex.build(clean_df, settings, paths.embeddings_json)
    print(f"Index created in collection '{index.collection_name}' with {len(index.documents)} documents.")

    # 6. Build or load test set
    print("Building evaluation test set...")
    test_set = build_test_set(clean_df, paths.eval_testset)
    print(f"Test set ready with {len(test_set)} question samples.")

    # 7. Evaluate pipeline
    print("Evaluating baseline pipeline performance...")
    eval_bundle = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=paths.eval_testset,
        metrics_output_path=paths.baseline_metrics,
        answers_output_path=paths.baseline_answers,
    )
    print(f"Baseline Metrics: {eval_bundle.summary}")

    # 8. Run quality checks & freshness monitoring
    print("Running observability & data quality checks...")
    quality_results = run_data_quality_checks(clean_df, settings, "baseline")
    freshness_report = build_freshness_report(clean_df, settings, paths.freshness_report)

    # 9. Generate phase 1 markdown report
    source_summary = {
        "source": settings.source_api,
        "raw_count": len(raw_records),
        "clean_count": len(clean_df),
    }
    generate_phase1_report(
        report_path=paths.baseline_report,
        source_summary=source_summary,
        metrics=eval_bundle.summary,
        quality=quality_results,
        freshness=freshness_report,
    )
    print(f"Phase 1 report written to {paths.baseline_report}")

    # 10. Agent demo sample
    if not clean_df.empty:
        sample_title = clean_df.iloc[0]["title"]
        sample_q = f"Who authored the paper titled '{sample_title}'?"
        ans_res = answer_question(sample_q, settings=settings, index=index)
        demo_payload = [
            {
                "question": sample_q,
                "answer": ans_res.answer,
                "retrieved_doc_ids": ans_res.retrieved_doc_ids,
            }
        ]
        write_json(paths.demo_answers, demo_payload)
        print(f"Agent Demo Answer: '{ans_res.answer}'")

    print("=== PHASE 1 BASELINE COMPLETED SUCCESSFULLY ===")


if __name__ == "__main__":
    main()

