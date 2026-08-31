"""Pipeline integration test tier — re-runs Bronze, Silver, and Gold orchestrators."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from pyspark.sql.functions import col, sum as spark_sum

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BRONZE_SCRIPT = PROJECT_ROOT / "src" / "bronze" / "ingest_all.py"
SILVER_SCRIPT = PROJECT_ROOT / "src" / "silver" / "create_silver_tables.py"
GOLD_SCRIPT = PROJECT_ROOT / "src" / "gold" / "create_gold_tables.py"

BRONZE_EXPECTED_COUNTS = {
    "workspace.default.bronze_customers": 10_000,
    "workspace.default.bronze_orders": 100_000,
    "workspace.default.bronze_products": 500,
}

SILVER_EXPECTED_COUNTS = {
    "workspace.default.silver_customers": 10_000,
    "workspace.default.silver_orders": 100_000,
    "workspace.default.silver_products": 500,
}

GOLD_SALES_BY_PRODUCT = "workspace.default.gold_sales_by_product"
GOLD_REVENUE_BY_CUSTOMER = "workspace.default.gold_revenue_by_customer"
GOLD_DAILY_WEEKLY_TRENDS = "workspace.default.gold_daily_weekly_trends"
GOLD_CUSTOMER_SEGMENTATION = "workspace.default.gold_customer_segmentation"

GOLD_EXPECTED_COUNTS = {
    GOLD_SALES_BY_PRODUCT: 500,
    GOLD_REVENUE_BY_CUSTOMER: 9_940,
    GOLD_CUSTOMER_SEGMENTATION: 4,
}

# Informational only — depends on sample-data date range, not injected-issue spec.
GOLD_DAILY_WEEKLY_TRENDS_INFO_COUNT = 974


def _load_pipeline_module(script_path: Path, module_name: str):
    """
    Load a pipeline orchestrator script as a module by file path.

    Matches the importlib pattern used in create_silver_tables.py and
    create_gold_tables.py so numeric prefixes and repo-relative paths work.
    """
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _assert_stage_counts(stage_name: str, actual_by_table: dict[str, int], expected: dict[str, int]) -> None:
    """Assert per-table row counts for a pipeline stage and print PASS summaries."""
    for table_name, expected_count in expected.items():
        actual_count = actual_by_table[table_name]
        if actual_count != expected_count:
            raise AssertionError(
                f"{stage_name} {table_name}: expected {expected_count:,}, "
                f"got {actual_count:,}"
            )
        print(
            f"PASS {stage_name} | {table_name} | "
            f"row_count={actual_count:,} | expected={expected_count:,}"
        )


def test_pipeline_end_to_end(spark) -> None:
    """
    Run the full Bronze → Silver → Gold pipeline and assert ground-truth row counts.

    Re-executes all three orchestrators in sequence (overwriting live Delta tables),
    uses each stage's return values for efficient row-count checks, and validates
    Gold segmentation totals against Silver PASSED customer counts.
    """
    print(
        "\n*** WARNING: This test re-runs the full pipeline and will OVERWRITE "
        "workspace.default.bronze_*, silver_*, and gold_* tables (the same tables "
        "backing the published Dashboard). This is safe/idempotent given the fixed "
        "random seed in generate_sample_data.py, but it is a real side effect. ***\n"
    )

    bronze_mod = _load_pipeline_module(BRONZE_SCRIPT, "ingest_all_mod")
    silver_mod = _load_pipeline_module(SILVER_SCRIPT, "create_silver_tables_mod")
    gold_mod = _load_pipeline_module(GOLD_SCRIPT, "create_gold_tables_mod")

    bronze_results = bronze_mod.ingest_all(spark)
    bronze_counts = {result["table_name"]: result["row_count"] for result in bronze_results}
    _assert_stage_counts("Bronze", bronze_counts, BRONZE_EXPECTED_COUNTS)

    silver_tables = silver_mod.create_silver_tables(spark)
    silver_counts = {table_name: df.count() for table_name, df in silver_tables.items()}
    _assert_stage_counts("Silver", silver_counts, SILVER_EXPECTED_COUNTS)

    gold_tables = gold_mod.create_gold_tables(spark)
    gold_counts = {table_name: df.count() for table_name, df in gold_tables.items()}
    _assert_stage_counts("Gold", gold_counts, GOLD_EXPECTED_COUNTS)

    trends_count = gold_counts[GOLD_DAILY_WEEKLY_TRENDS]
    if trends_count <= 0:
        raise AssertionError(
            f"Gold {GOLD_DAILY_WEEKLY_TRENDS}: expected row count > 0, got {trends_count:,}"
        )
    print(
        f"PASS Gold | {GOLD_DAILY_WEEKLY_TRENDS} | "
        f"row_count={trends_count:,} | expected=>0 "
        f"(informational reference count={GOLD_DAILY_WEEKLY_TRENDS_INFO_COUNT:,})"
    )

    segmentation_total = (
        gold_tables[GOLD_CUSTOMER_SEGMENTATION]
        .agg(spark_sum("customer_count").alias("total_customers"))
        .collect()[0]["total_customers"]
    )
    silver_passed_customers = (
        silver_tables["workspace.default.silver_customers"]
        .filter(col("quality_check_result") == "PASSED")
        .count()
    )
    if segmentation_total != silver_passed_customers:
        raise AssertionError(
            "Gold segmentation SUM(customer_count) vs Silver PASSED customers: "
            f"expected {silver_passed_customers:,}, got {segmentation_total:,}"
        )
    print(
        "PASS Gold segmentation regression | SUM(customer_count)="
        f"{segmentation_total:,} | silver_customers PASSED="
        f"{silver_passed_customers:,}"
    )

    print("\nPIPELINE INTEGRATION TEST PASSED")


if __name__ == "__main__":
    test_pipeline_end_to_end(spark)
