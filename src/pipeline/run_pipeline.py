"""SupportPulse Data Pipeline — src/pipeline/run_pipeline.py"""

import sys
import subprocess
import argparse
import time
from pathlib import Path

from prefect import flow, task, get_run_logger
from prefect.task_runners import ThreadPoolTaskRunner

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.data.silver_pipeline import load_bronze, load_label_map, clean_to_silver, write_silver
from src.features.gold_pipeline import build_gold


# ── Stage 1: Data Ingestion ────────────────────────────────────────────────

@task(name="ingest-github", retries=2, retry_delay_seconds=30)
def task_ingest_github():
    """Collect GitHub issues from the 20 curated repositories."""
    logger = get_run_logger()
    logger.info("Stage 1a: Ingesting GitHub issues...")
    from src.data.github_collector import main as github_main
    github_main()
    logger.info("GitHub ingestion complete.")


@task(name="ingest-huggingface", retries=1, retry_delay_seconds=10)
def task_ingest_hf():
    """Download support ticket datasets from Hugging Face Hub."""
    logger = get_run_logger()
    logger.info("Stage 1b: Ingesting Hugging Face datasets...")
    from src.data.hf_collector import main as hf_main
    hf_main()
    logger.info("HuggingFace ingestion complete.")


@task(name="generate-synthetic")
def task_generate_synthetic():
    """Generate 7,000 synthetic edge-case tickets for rare categories."""
    logger = get_run_logger()
    logger.info("Stage 1c: Generating synthetic tickets...")
    from src.data.synthetic_generator import main as synth_main
    synth_main()
    logger.info("Synthetic generation complete.")


# ── Stage 2: Bronze Combine + Validate ────────────────────────────────────

@task(name="combine-bronze")
def task_combine_bronze():
    """Merge all Bronze sources into a single combined JSON file."""
    logger = get_run_logger()
    logger.info("Stage 2a: Combining Bronze sources...")
    from src.data.bronze_combiner import main as combiner_main
    combiner_main()
    logger.info("Bronze combine complete.")


@task(name="validate-bronze")
def task_validate_bronze():
    """Run Great Expectations validation on the Bronze combined file."""
    logger = get_run_logger()
    logger.info("Stage 2b: Validating Bronze data with Great Expectations...")

    bronze_file = Path("data/bronze/all_bronze_combined.json")
    if not bronze_file.exists():
        raise FileNotFoundError(f"Bronze file not found: {bronze_file}")

    import pandas as pd
    import great_expectations as gx

    df = pd.read_json(bronze_file)
    logger.info(f"Bronze rows loaded: {len(df):,}")

    context = gx.get_context(mode="ephemeral")
    data_source = context.data_sources.add_pandas("pandas_bronze_pipeline")
    data_asset = data_source.add_dataframe_asset("bronze_pipeline")
    batch_definition = data_asset.add_batch_definition_whole_dataframe("whole_df")

    suite = gx.ExpectationSuite(name="bronze_suite_pipeline")
    suite.add_expectation(gx.expectations.ExpectTableRowCountToBeBetween(min_value=50_000))
    suite.add_expectation(gx.expectations.ExpectColumnToExist(column="ticket_id"))
    suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(column="ticket_id"))
    suite.add_expectation(gx.expectations.ExpectColumnToExist(column="body"))
    suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(column="body"))
    suite.add_expectation(gx.expectations.ExpectColumnValueLengthsToBeBetween(column="body", min_value=20))
    suite = context.suites.add(suite)

    vd = gx.ValidationDefinition(data=batch_definition, suite=suite, name="bronze_vd_pipeline")
    vd = context.validation_definitions.add(vd)
    results = vd.run(batch_parameters={"dataframe": df})

    if not results.success:
        failed = [r.expectation_config.type for r in results.results if not r.success]
        raise RuntimeError(f"Bronze validation FAILED: {failed}")

    logger.info("Bronze validation PASSED — all expectations met.")


# ── Stage 3: Silver Cleaning ───────────────────────────────────────────────

@task(name="run-silver-pipeline")
def task_silver_pipeline():
    """Apply PII masking, label normalisation, deduplication → Silver Parquet."""
    logger = get_run_logger()
    logger.info("Stage 3: Running Silver cleaning pipeline...")

    bronze_path = Path("data/bronze/all_bronze_combined.json")
    label_map = load_label_map()
    raw_df = load_bronze(bronze_path)
    silver_df = clean_to_silver(raw_df, label_map)
    output_path = write_silver(silver_df)

    logger.info(f"Silver pipeline complete: {len(silver_df):,} rows → {output_path}")
    return len(silver_df)


# ── Stage 4: Silver Validation ─────────────────────────────────────────────

@task(name="validate-silver")
def task_validate_silver():
    """Run Great Expectations validation on the Silver Parquet."""
    logger = get_run_logger()
    logger.info("Stage 4: Validating Silver data...")

    silver_file = Path("data/silver/all_silver.parquet")
    if not silver_file.exists():
        raise FileNotFoundError(f"Silver file not found: {silver_file}")

    import pandas as pd
    import great_expectations as gx

    CANONICAL_CATEGORIES = [
        "bug", "feature", "security", "billing", "performance",
        "docs", "question", "incident", "sla_breach", "ui",
        "test", "dependency",
    ]

    df = pd.read_parquet(silver_file)
    logger.info(f"Silver rows loaded: {len(df):,}")

    context = gx.get_context(mode="ephemeral")
    data_source = context.data_sources.add_pandas("pandas_silver_pipeline")
    data_asset = data_source.add_dataframe_asset("silver_pipeline")
    batch_definition = data_asset.add_batch_definition_whole_dataframe("whole_df")

    suite = gx.ExpectationSuite(name="silver_suite_pipeline")
    suite.add_expectation(gx.expectations.ExpectTableRowCountToBeBetween(min_value=50_000))
    suite.add_expectation(gx.expectations.ExpectColumnValuesToBeInSet(
        column="category", value_set=CANONICAL_CATEGORIES
    ))
    suite.add_expectation(gx.expectations.ExpectColumnValuesToBeInSet(
        column="priority", value_set=["critical", "high", "medium", "low"]
    ))
    suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(column="ticket_id"))
    suite = context.suites.add(suite)

    vd = gx.ValidationDefinition(data=batch_definition, suite=suite, name="silver_vd_pipeline")
    vd = context.validation_definitions.add(vd)
    results = vd.run(batch_parameters={"dataframe": df})

    if not results.success:
        failed = [r.expectation_config.type for r in results.results if not r.success]
        raise RuntimeError(f"Silver validation FAILED: {failed}")

    logger.info("Silver validation PASSED.")


# ── Stage 5: Gold Feature Engineering ─────────────────────────────────────

@task(name="build-gold-features")
def task_gold_pipeline():
    """Compute train/val/test splits, structured features, and BGE-M3 embeddings."""
    logger = get_run_logger()
    logger.info("Stage 5: Building Gold feature layer...")
    build_gold()
    logger.info("Gold pipeline complete.")


# ── Stage 6: Feast Apply + Materialise ────────────────────────────────────

@task(name="feast-apply-and-materialise")
def task_feast():
    """Apply Feast feature definitions and materialise online store."""
    logger = get_run_logger()
    logger.info("Stage 6: Applying Feast feature store definitions...")

    feast_dir = Path("feature_store")
    if not feast_dir.exists():
        raise FileNotFoundError("feature_store/ directory not found.")

    gold_features = Path("data/gold/train_features.parquet")
    if not gold_features.exists():
        logger.warning("Gold features not yet generated — skipping Feast materialise.")
        logger.warning("Run the Gold pipeline first, then re-run this stage.")
        return

    # feast apply registers entity + feature view definitions
    result = subprocess.run(
        ["python", "-m", "feast", "apply"],
        cwd=str(feast_dir),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        logger.warning(f"feast apply output: {result.stdout}\n{result.stderr}")
    else:
        logger.info("feast apply complete.")

    # materialize-incremental pushes features into the online store
    from datetime import datetime
    now_str = datetime.now().isoformat()
    logger.info(f"Materializing features up to {now_str}...")
    result_mat = subprocess.run(
        ["python", "-m", "feast", "materialize-incremental", now_str],
        cwd=str(feast_dir),
        capture_output=True,
        text=True,
    )
    if result_mat.returncode == 0:
        logger.info("Feast materialization successful.")
    else:
        logger.warning(f"Feast materialization failed: {result_mat.stderr}")

    logger.info("Feast stage complete.")


# ── Main Flow ──────────────────────────────────────────────────────────────

@flow(
    name="SupportPulse Data Pipeline",
    description=(
        "End-to-end data pipeline: ingest → validate Bronze → clean Silver "
        "→ validate Silver → build Gold → materialise Feast."
    ),
    task_runner=ThreadPoolTaskRunner(max_workers=1),
)
def data_pipeline(skip_ingest: bool = False):
    """The main Prefect flow for the SupportPulse data pipeline."""
    logger = get_run_logger()
    start = time.time()

    logger.info("=" * 60)
    logger.info("SupportPulse Data Pipeline — Starting")
    logger.info("=" * 60)

    bronze_exists = Path("data/bronze/all_bronze_combined.json").exists()

    if skip_ingest or bronze_exists:
        if bronze_exists:
            logger.info("Bronze data found — skipping ingestion stage.")
        else:
            logger.info("--skip-ingest flag set — skipping ingestion stage.")
    else:
        logger.info("Stage 1: Running ingestion...")
        task_ingest_github()
        task_ingest_hf()
        task_generate_synthetic()
        task_combine_bronze()

    # Always validate Bronze (even if we skipped ingestion)
    task_validate_bronze()

    # Silver
    task_silver_pipeline()
    task_validate_silver()

    # Gold
    task_gold_pipeline()

    # Feast
    task_feast()

    elapsed = (time.time() - start) / 60
    logger.info("=" * 60)
    logger.info(f"Pipeline COMPLETE in {elapsed:.1f} minutes")
    logger.info("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SupportPulse Data Pipeline")
    parser.add_argument(
        "--skip-ingest",
        action="store_true",
        help="Skip data ingestion (use existing Bronze data)",
    )
    args = parser.parse_args()
    data_pipeline(skip_ingest=args.skip_ingest)
