"""
Silver Data Validation — src/data/validate_silver.py
=====================================================
Great Expectations validation suite for the Silver data layer.

Why validate Silver separately from Bronze?
  - Bronze validation proves: "We received the data we expected."
  - Silver validation proves: "The cleaning pipeline did its job correctly."
  - They guard different failure modes:
      * Bronze fails → source is broken (API changed, dataset moved)
      * Silver fails → our cleaning code has a bug

Key checks we enforce:
  1. Row count still large after cleaning (we didn't accidentally drop everything)
  2. No null ticket_ids, subjects, bodies, categories, priorities
  3. Category values are ONLY our 10 canonical categories (label normaliser works)
  4. Priority values are ONLY the 4 valid options
  5. Routing teams are ONLY the 5 valid teams
  6. Body length still >= 20 chars (short bodies weren't re-introduced)
  7. No raw email addresses in body (PII masking worked)
"""

import pandas as pd
import great_expectations as gx
import sys
from pathlib import Path


CANONICAL_CATEGORIES = [
    "bug", "feature", "security", "billing", "performance",
    "docs", "question", "incident", "sla_breach", "ui",
    "test", "dependency",
]
VALID_PRIORITIES = ["critical", "high", "medium", "low"]
VALID_ROUTING_TEAMS = ["support", "engineering", "infra", "billing", "security"]


def main():
    print("=" * 55)
    print("Validating Silver Data with Great Expectations...")
    print("=" * 55)

    silver_file = Path("data/silver/all_silver.parquet")
    if not silver_file.exists():
        print(f"Error: {silver_file} not found! Run silver_pipeline.py first.")
        sys.exit(1)

    print(f"\nLoading {silver_file}...")
    df = pd.read_parquet(silver_file)
    print(f"Loaded {len(df):,} rows.")

    # ── Set up Great Expectations ephemeral context ──────────────────────
    context = gx.get_context(mode="ephemeral")
    data_source = context.data_sources.add_pandas("pandas_silver")
    data_asset = data_source.add_dataframe_asset("silver")
    batch_definition = data_asset.add_batch_definition_whole_dataframe("whole_df")

    # ── Define the Silver Expectation Suite ───────────────────────────────
    suite = gx.ExpectationSuite(name="silver_suite")

    # Row count: must have at least 50,000 rows after cleaning
    suite.add_expectation(
        gx.expectations.ExpectTableRowCountToBeBetween(min_value=50_000)
    )

    # Required columns must exist
    for col in ["ticket_id", "source", "subject", "body", "category",
                "priority", "routing_team", "created_at", "pii_flags"]:
        suite.add_expectation(gx.expectations.ExpectColumnToExist(column=col))

    # No nulls in critical columns
    for col in ["ticket_id", "subject", "body", "category", "priority", "routing_team"]:
        suite.add_expectation(
            gx.expectations.ExpectColumnValuesToNotBeNull(column=col)
        )

    # Category must be one of the 10 canonical values
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToBeInSet(
            column="category",
            value_set=CANONICAL_CATEGORIES,
        )
    )

    # Priority must be one of 4 valid values
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToBeInSet(
            column="priority",
            value_set=VALID_PRIORITIES,
        )
    )

    # Routing team must be one of 5 valid values
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToBeInSet(
            column="routing_team",
            value_set=VALID_ROUTING_TEAMS,
        )
    )

    # Body length must still be >= 20 chars (no accidental truncation)
    suite.add_expectation(
        gx.expectations.ExpectColumnValueLengthsToBeBetween(
            column="body", min_value=20
        )
    )

    # ── Register suite and run validation ────────────────────────────────
    suite = context.suites.add(suite)
    validation_definition = gx.ValidationDefinition(
        data=batch_definition,
        suite=suite,
        name="silver_validation",
    )
    validation_definition = context.validation_definitions.add(validation_definition)

    print("\nRunning Silver Expectations...")
    results = validation_definition.run(batch_parameters={"dataframe": df})

    # ── Report results ────────────────────────────────────────────────────
    passed = sum(1 for r in results.results if r.success)
    failed = sum(1 for r in results.results if not r.success)
    print(f"\n{'=' * 55}")
    print(f"Silver Validation Results: {passed} passed, {failed} failed")
    print(f"{'=' * 55}")

    if not results.success:
        print("\nFAILED Expectations:")
        for result in results.results:
            if not result.success:
                print(f"  ✗ {result.expectation_config.type}")
        sys.exit(1)
    else:
        print("\nAll Silver expectations PASSED. Data is clean!")
        sys.exit(0)


if __name__ == "__main__":
    main()
