import pandas as pd
import great_expectations as gx
import sys
from pathlib import Path

def main():
    print("Validating Bronze Data with Great Expectations...")
    
    bronze_file = Path("data/bronze/all_bronze_combined.json")
    if not bronze_file.exists():
        print(f"Error: {bronze_file} not found!")
        sys.exit(1)
        
    print(f"Loading {bronze_file} into Pandas...")
    df = pd.read_json(bronze_file)
    print(f"Loaded {len(df)} rows.")

    context = gx.get_context(mode="ephemeral")
    
    try:
        data_source = context.data_sources.add_pandas("pandas")
        data_asset = data_source.add_dataframe_asset("bronze")
        batch_definition = data_asset.add_batch_definition_whole_dataframe("whole_df")
    except Exception as e:
        print(f"Failed to setup GE source: {e}")
        sys.exit(1)

    try:
        suite = gx.ExpectationSuite(name="bronze_suite")
        suite.add_expectation(gx.expectations.ExpectTableRowCountToBeBetween(min_value=50000))
        suite.add_expectation(gx.expectations.ExpectColumnToExist(column="ticket_id"))
        suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(column="ticket_id"))
        suite.add_expectation(gx.expectations.ExpectColumnToExist(column="source"))
        suite.add_expectation(gx.expectations.ExpectColumnValuesToBeInSet(column="source", value_set=["github", "zendesk", "synthetic", "hf_customer_support", "kaggle_github_issues"]))
        suite.add_expectation(gx.expectations.ExpectColumnToExist(column="body"))
        suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(column="body"))
        suite.add_expectation(gx.expectations.ExpectColumnValueLengthsToBeBetween(column="body", min_value=20))
        suite.add_expectation(gx.expectations.ExpectColumnToExist(column="subject"))
        suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(column="subject"))
        suite.add_expectation(gx.expectations.ExpectColumnToExist(column="created_at"))
        suite = context.suites.add(suite)
    except Exception as e:
        print(f"Failed to setup Expectations: {e}")
        sys.exit(1)

    try:
        validation_definition = gx.ValidationDefinition(
            data=batch_definition,
            suite=suite,
            name="bronze_validation"
        )
        validation_definition = context.validation_definitions.add(validation_definition)
    except Exception as e:
        print(f"Failed to setup Validation: {e}")
        sys.exit(1)

    print("Running Expectations...")
    results = validation_definition.run(batch_parameters={"dataframe": df})

    if not results.success:
        print("\nValidation FAILED.")
        for result in results.results:
            if not result.success:
                print(f"FAILED: {result.expectation_config.type}")
        sys.exit(1)
    else:
        print("\nAll expectations PASSED successfully!")
        sys.exit(0)

if __name__ == "__main__":
    main()
