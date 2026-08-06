from datetime import datetime, timezone

import pandas as pd

from core.config import load_settings
from core.utils import read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    print("=== STARTING PHASE 2: CORRUPTION, REPAIR & COMPARISON FLOW ===")

    # 1. Load baseline settings & clean dataset
    settings = load_settings()
    paths = settings.paths
    run_date = datetime.now(timezone.utc)

    if not paths.baseline_metrics.exists():
        raise RuntimeError("Baseline metrics not found. Please run Phase 1 baseline pipeline first.")

    baseline_metrics = read_json(paths.baseline_metrics)
    if paths.clean_csv.exists():
        clean_df = pd.read_csv(paths.clean_csv)
    else:
        clean_df = pd.DataFrame(read_json(paths.clean_json))

    print(f"Loaded baseline clean dataset with {len(clean_df)} records.")

    # 2. Corrupt clean dataset
    print("Simulating data corruption scenario...")
    corrupted_df = corrupt_clean_dataframe(clean_df, paths.corruption_log)
    print(f"Corrupted dataset has {len(corrupted_df)} records.")

    # 3. Save corrupted clean artifacts
    write_csv(corrupted_df, paths.corrupted_clean_csv)
    write_json(paths.corrupted_clean_json, corrupted_df.to_dict(orient="records"))
    print(f"Saved corrupted dataset to {paths.corrupted_clean_csv}")

    # 4. Rebuild vector index for corrupted data
    print(f"Rebuilding vector index for corrupted data (Collection: '{settings.corrupted_collection_name}')...")
    corrupted_index = LocalEmbeddingIndex.build(corrupted_df, settings, paths.corrupted_embeddings_json)

    # 5. Evaluate corrupted pipeline on baseline test set
    print("Evaluating corrupted pipeline on existing baseline test set...")
    corrupted_eval = evaluate_pipeline(
        settings=settings,
        index=corrupted_index,
        test_set_path=paths.eval_testset,
        metrics_output_path=paths.corrupted_metrics,
        answers_output_path=paths.corrupted_answers,
    )
    print(f"Corrupted Metrics: {corrupted_eval.summary}")

    # 6. Run quality & freshness checks for corrupted data
    corrupted_quality = run_data_quality_checks(corrupted_df, settings, "corrupted")
    corrupted_freshness = build_freshness_report(
        corrupted_df, settings, settings.paths.quality_dir / "corrupted_freshness.json"
    )

    # 7. Repair data from raw records snapshot
    print("Repairing dataset by re-running ETL cleaning from raw Crossref snapshot...")
    raw_records = load_raw_records(paths.raw_records_json)
    repaired_df = build_clean_dataframe(raw_records, run_date)
    write_csv(repaired_df, paths.repaired_clean_csv)
    write_json(paths.repaired_clean_json, repaired_df.to_dict(orient="records"))
    print(f"Repaired dataset has {len(repaired_df)} records.")

    # 8. Rebuild vector index for repaired data
    print(f"Rebuilding vector index for repaired data (Collection: '{settings.repaired_collection_name}')...")
    repaired_index = LocalEmbeddingIndex.build(repaired_df, settings, paths.repaired_embeddings_json)

    # 9. Evaluate repaired pipeline
    print("Evaluating repaired pipeline on existing baseline test set...")
    repaired_eval = evaluate_pipeline(
        settings=settings,
        index=repaired_index,
        test_set_path=paths.eval_testset,
        metrics_output_path=paths.repaired_metrics,
        answers_output_path=paths.repaired_answers,
    )
    print(f"Repaired Metrics: {repaired_eval.summary}")

    # 10. Run quality & freshness checks for repaired data
    repaired_quality = run_data_quality_checks(repaired_df, settings, "repaired")
    repaired_freshness = build_freshness_report(
        repaired_df, settings, settings.paths.quality_dir / "repaired_freshness.json"
    )

    # 11. Generate comparison report
    print("Generating comprehensive comparison report...")
    generate_corruption_report(
        report_path=paths.comparison_report,
        baseline_metrics=baseline_metrics,
        corrupted_metrics=corrupted_eval.summary,
        repaired_metrics=repaired_eval.summary,
        corrupted_quality=corrupted_quality,
        repaired_quality=repaired_quality,
        corrupted_freshness=corrupted_freshness,
        repaired_freshness=repaired_freshness,
    )
    print(f"Comparison report generated at {paths.comparison_report}")

    print("=== PHASE 2 CORRUPTION & REPAIR FLOW COMPLETED SUCCESSFULLY ===")


if __name__ == "__main__":
    main()

