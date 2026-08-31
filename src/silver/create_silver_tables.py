"""Orchestrate Silver-layer quality checks and materialize validated Delta tables."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from pyspark.sql import DataFrame
from pyspark.sql.functions import col, concat_ws, lit, trim, when

SILVER_DIR = Path(__file__).resolve().parent

CUSTOMER_FLAG_COLUMNS = [
    "_flag_null_email",
    "_flag_duplicate_customer_id",
    "_flag_invalid_email_format",
    "_flag_invalid_signup_date",
]

ORDER_FLAG_COLUMNS = [
    "_flag_null_customer_id",
    "_flag_null_product_id",
    "_flag_duplicate_order_id",
    "_flag_invalid_order_date",
    "_flag_orphan_customer_id",
    "_flag_orphan_product_id",
    "_flag_calculation_mismatch",
    "_flag_invalid_quantity",
]

PRODUCT_FLAG_COLUMNS = [
    "_flag_duplicate_product_id",
    "_flag_price_below_cost",
]

# Expected injected issue counts from the sample-data generation spec.
EXPECTED_ISSUE_COUNTS = {
    "workspace.default.silver_customers": {
        "FAIL_NULL_EMAIL": 50,
        "FAIL_DUPLICATE_CUSTOMER_ID": 10,
    },
    "workspace.default.silver_orders": {
        "FAIL_NULL_CUSTOMER_ID": 100,
        "FAIL_NULL_PRODUCT_ID": 200,
        "FAIL_ORPHAN_CUSTOMER_ID": 50,
        "FAIL_ORPHAN_PRODUCT_ID": 30,
        "FAIL_DUPLICATE_ORDER_ID": 20,
    },
    "workspace.default.silver_products": {},
}


def _load_quality_module(filename: str, module_name: str):
    """
    Load a numbered Silver quality script as a module.

    Numeric filename prefixes (01_, 02_, etc.) are not valid Python import names,
    so importlib is used to load them by file path instead.
    """
    path = SILVER_DIR / filename
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def consolidate_quality_flags(
    df: DataFrame,
    flag_columns: list[str],
    original_columns: list[str],
) -> DataFrame:
    """
    Merge temporary per-check flag columns into a single quality_check_result value.

    Failed checks are pipe-delimited. Rows with no failures explicitly become PASSED,
    including when the concatenated flag string is empty, whitespace, or NULL.
    """
    flag_exprs = [
        when(col(flag_name).isNotNull(), col(flag_name)) for flag_name in flag_columns
    ]
    combined_flags = concat_ws("|", *flag_exprs)
    quality_check_result = when(
        combined_flags.isNull() | (trim(combined_flags) == ""),
        lit("PASSED"),
    ).otherwise(combined_flags)

    return df.select(
        *[col(column_name) for column_name in original_columns],
        quality_check_result.alias("quality_check_result"),
    )


def build_silver_customers(
    bronze_customers: DataFrame,
    completeness_mod,
    uniqueness_mod,
    type_validation_mod,
) -> DataFrame:
    """
    Run modules 01-03 for customers and append quality_check_result.

    Referential and business-logic modules do not apply to the customers entity.
    """
    original_columns = bronze_customers.columns
    flagged_df = completeness_mod.apply_customer_completeness_checks(bronze_customers)
    flagged_df = uniqueness_mod.apply_customer_uniqueness_checks(flagged_df)
    flagged_df = type_validation_mod.apply_customer_type_checks(flagged_df)
    return consolidate_quality_flags(flagged_df, CUSTOMER_FLAG_COLUMNS, original_columns)


def build_silver_orders(
    bronze_orders: DataFrame,
    bronze_customers: DataFrame,
    bronze_products: DataFrame,
    completeness_mod,
    uniqueness_mod,
    type_validation_mod,
    referential_mod,
    business_logic_mod,
) -> DataFrame:
    """Run modules 01-05 for orders and append quality_check_result."""
    original_columns = bronze_orders.columns
    flagged_df = completeness_mod.apply_order_completeness_checks(bronze_orders)
    flagged_df = uniqueness_mod.apply_order_uniqueness_checks(flagged_df)
    flagged_df = type_validation_mod.apply_order_type_checks(flagged_df)
    flagged_df = referential_mod.apply_order_referential_checks(
        flagged_df,
        bronze_customers,
        bronze_products,
    )
    flagged_df = business_logic_mod.apply_order_business_checks(flagged_df)
    return consolidate_quality_flags(flagged_df, ORDER_FLAG_COLUMNS, original_columns)


def build_silver_products(
    bronze_products: DataFrame,
    uniqueness_mod,
    business_logic_mod,
) -> DataFrame:
    """
    Run applicable modules for products and append quality_check_result.

    Completeness, type, and referential checks are not defined for products in the
    current spec; uniqueness and price-versus-cost business rules are applied.
    """
    original_columns = bronze_products.columns
    flagged_df = uniqueness_mod.apply_product_uniqueness_checks(bronze_products)
    flagged_df = business_logic_mod.apply_product_business_checks(flagged_df)
    return consolidate_quality_flags(flagged_df, PRODUCT_FLAG_COLUMNS, original_columns)


def _count_rows_for_code(df: DataFrame, failure_code: str) -> int:
    """Count rows whose quality_check_result contains a specific failure code."""
    return df.filter(col("quality_check_result").contains(failure_code)).count()


def _build_check_breakdown(df: DataFrame, failure_codes: list[str]) -> dict[str, int]:
    """Return per-check-code row counts for the supplied failure codes."""
    return {code: _count_rows_for_code(df, code) for code in failure_codes}


def _format_breakdown(breakdown: dict[str, int]) -> str:
    """Format a per-check breakdown for the metrics report."""
    parts = [f"{code}={count}" for code, count in sorted(breakdown.items()) if count > 0]
    return "; ".join(parts) if parts else "none"


def print_quality_metrics_report(silver_tables: dict[str, DataFrame]) -> None:
    """
    Print a text-table summary of row counts, pass rates, and per-check failures.

    Compares caught counts against the intentionally injected issue targets for
    customers and orders.
    """
    code_labels = {
        "_flag_null_email": "FAIL_NULL_EMAIL",
        "_flag_duplicate_customer_id": "FAIL_DUPLICATE_CUSTOMER_ID",
        "_flag_invalid_email_format": "FAIL_INVALID_EMAIL_FORMAT",
        "_flag_invalid_signup_date": "FAIL_INVALID_DATE",
        "_flag_null_customer_id": "FAIL_NULL_CUSTOMER_ID",
        "_flag_null_product_id": "FAIL_NULL_PRODUCT_ID",
        "_flag_duplicate_order_id": "FAIL_DUPLICATE_ORDER_ID",
        "_flag_invalid_order_date": "FAIL_INVALID_DATE",
        "_flag_orphan_customer_id": "FAIL_ORPHAN_CUSTOMER_ID",
        "_flag_orphan_product_id": "FAIL_ORPHAN_PRODUCT_ID",
        "_flag_calculation_mismatch": "FAIL_CALCULATION_MISMATCH",
        "_flag_invalid_quantity": "FAIL_INVALID_QUANTITY",
        "_flag_duplicate_product_id": "FAIL_DUPLICATE_PRODUCT_ID",
        "_flag_price_below_cost": "FAIL_PRICE_BELOW_COST",
    }
    report_codes = sorted(set(code_labels.values()))

    print("\n=== Data Quality Metrics Report ===")
    header = (
        f"{'Table Name':<36} | {'Total Rows':>10} | {'Rows Passed':>11} | "
        f"{'% Passed':>8} | {'Issues Caught':>13} | Breakdown per Check Code"
    )
    print(header)
    print("-" * len(header))

    for table_name, silver_df in silver_tables.items():
        total_rows = silver_df.count()
        rows_passed = silver_df.filter(col("quality_check_result") == "PASSED").count()
        pct_passed = (rows_passed / total_rows * 100) if total_rows else 0.0
        breakdown = _build_check_breakdown(silver_df, report_codes)
        issues_caught = sum(breakdown.values())
        breakdown_text = _format_breakdown(breakdown)

        print(
            f"{table_name:<36} | {total_rows:>10,} | {rows_passed:>11,} | "
            f"{pct_passed:>7.2f}% | {issues_caught:>13,} | {breakdown_text}"
        )

        expected = EXPECTED_ISSUE_COUNTS.get(table_name, {})
        if expected:
            print(f"  Expected injected issues for {table_name}:")
            for code in sorted(expected):
                caught = breakdown.get(code, 0)
                target = expected[code]
                status = "OK" if caught == target else "MISMATCH"
                print(f"    {code}: caught={caught}, expected={target} [{status}]")


def create_silver_tables(spark):
    """
    Read Bronze tables, apply quality modules 01-05, and write Silver Delta tables.

    Every Bronze row is preserved in Silver with an evaluated quality_check_result.
    """
    completeness_mod = _load_quality_module(
        "01_quality_completeness.py",
        "quality_completeness_mod",
    )
    uniqueness_mod = _load_quality_module(
        "02_quality_uniqueness.py",
        "quality_uniqueness_mod",
    )
    type_validation_mod = _load_quality_module(
        "03_quality_type_validation.py",
        "quality_type_validation_mod",
    )
    referential_mod = _load_quality_module(
        "04_quality_referential_integrity.py",
        "quality_referential_integrity_mod",
    )
    business_logic_mod = _load_quality_module(
        "05_quality_business_logic.py",
        "quality_business_logic_mod",
    )

    bronze_customers = spark.read.table("workspace.default.bronze_customers")
    bronze_orders = spark.read.table("workspace.default.bronze_orders")
    bronze_products = spark.read.table("workspace.default.bronze_products")

    print("Building Silver tables from Bronze inputs...")
    print(f"bronze_customers rows: {bronze_customers.count():,}")
    print(f"bronze_orders rows: {bronze_orders.count():,}")
    print(f"bronze_products rows: {bronze_products.count():,}")

    silver_customers = build_silver_customers(
        bronze_customers,
        completeness_mod,
        uniqueness_mod,
        type_validation_mod,
    )
    silver_orders = build_silver_orders(
        bronze_orders,
        bronze_customers,
        bronze_products,
        completeness_mod,
        uniqueness_mod,
        type_validation_mod,
        referential_mod,
        business_logic_mod,
    )
    silver_products = build_silver_products(
        bronze_products,
        uniqueness_mod,
        business_logic_mod,
    )

    silver_customers.write.format("delta").mode("overwrite").saveAsTable(
        "workspace.default.silver_customers"
    )
    silver_orders.write.format("delta").mode("overwrite").saveAsTable(
        "workspace.default.silver_orders"
    )
    silver_products.write.format("delta").mode("overwrite").saveAsTable(
        "workspace.default.silver_products"
    )

    silver_tables = {
        "workspace.default.silver_customers": silver_customers,
        "workspace.default.silver_orders": silver_orders,
        "workspace.default.silver_products": silver_products,
    }

    print("\nSilver tables written:")
    for table_name, silver_df in silver_tables.items():
        print(f"  {table_name}: {silver_df.count():,} rows")

    print_quality_metrics_report(silver_tables)
    return silver_tables


if __name__ == "__main__":
    create_silver_tables(spark)
