"""Data quality test tier — validates materialized Silver table output."""

from __future__ import annotations

from pyspark.sql.functions import col, trim

try:
    from pyspark.errors.exceptions.captured import AnalysisException
except ImportError:  # pragma: no cover - older PySpark layouts
    from pyspark.sql.utils import AnalysisException  # type: ignore[no-redef]

SILVER_CUSTOMERS_TABLE = "workspace.default.silver_customers"
SILVER_ORDERS_TABLE = "workspace.default.silver_orders"
SILVER_PRODUCTS_TABLE = "workspace.default.silver_products"

EXPECTED_SILVER_ROW_COUNTS = {
    SILVER_CUSTOMERS_TABLE: 10_000,
    SILVER_ORDERS_TABLE: 100_000,
    SILVER_PRODUCTS_TABLE: 500,
}

EXPECTED_INJECTED_ISSUE_COUNTS = {
    SILVER_CUSTOMERS_TABLE: {
        "FAIL_NULL_EMAIL": 50,
        "FAIL_DUPLICATE_CUSTOMER_ID": 10,
    },
    SILVER_ORDERS_TABLE: {
        "FAIL_NULL_CUSTOMER_ID": 100,
        "FAIL_NULL_PRODUCT_ID": 200,
        "FAIL_ORPHAN_CUSTOMER_ID": 50,
        "FAIL_ORPHAN_PRODUCT_ID": 30,
        "FAIL_DUPLICATE_ORDER_ID": 20,
    },
}


def _read_silver_table(spark, table_name: str):
    """
    Read a Silver Delta table, surfacing a clear error when it is missing.

    Assumes Silver was already materialized by create_silver_tables.py; this test
    validates persisted output rather than re-running the Silver pipeline.
    """
    try:
        return spark.read.table(table_name)
    except AnalysisException as exc:
        raise RuntimeError(
            f"Silver table '{table_name}' not found — run "
            "src/silver/create_silver_tables.py first."
        ) from exc
    except Exception as exc:
        message = str(exc).lower()
        if "not found" in message or "table_or_view" in message:
            raise RuntimeError(
                f"Silver table '{table_name}' not found — run "
                "src/silver/create_silver_tables.py first."
            ) from exc
        raise


def _count_rows_for_code(df, failure_code: str) -> int:
    """Count rows whose quality_check_result contains a specific failure code."""
    return df.filter(col("quality_check_result").contains(failure_code)).count()


def _assert_exact_count(
    label: str,
    actual: int,
    expected: int,
) -> None:
    """Assert an exact row count and print a PASS line on success."""
    if actual != expected:
        raise AssertionError(
            f"{label}: expected {expected:,}, got {actual:,}"
        )
    print(f"PASS {label}: expected={expected:,}, actual={actual:,}")


def test_silver_quality_checks(spark) -> None:
    """
    Validate Silver data-quality flags against known injected-issue ground truth.

    Reads already-materialized Silver tables (does not re-run create_silver_tables),
    checks per-failure-code counts, row preservation, regression guards, and that
    every row has a non-empty quality_check_result.
    """
    silver_customers = _read_silver_table(spark, SILVER_CUSTOMERS_TABLE)
    silver_orders = _read_silver_table(spark, SILVER_ORDERS_TABLE)
    silver_products = _read_silver_table(spark, SILVER_PRODUCTS_TABLE)

    silver_tables = {
        SILVER_CUSTOMERS_TABLE: silver_customers,
        SILVER_ORDERS_TABLE: silver_orders,
        SILVER_PRODUCTS_TABLE: silver_products,
    }

    for table_name, silver_df in silver_tables.items():
        for failure_code, expected_count in EXPECTED_INJECTED_ISSUE_COUNTS.get(
            table_name, {}
        ).items():
            actual_count = _count_rows_for_code(silver_df, failure_code)
            _assert_exact_count(
                f"{table_name} {failure_code}",
                actual_count,
                expected_count,
            )

    for table_name, silver_df in silver_tables.items():
        actual_rows = silver_df.count()
        expected_rows = EXPECTED_SILVER_ROW_COUNTS[table_name]
        _assert_exact_count(
            f"{table_name} total rows",
            actual_rows,
            expected_rows,
        )

    both_null_and_orphan_customer = silver_orders.filter(
        col("quality_check_result").contains("FAIL_NULL_CUSTOMER_ID")
        & col("quality_check_result").contains("FAIL_ORPHAN_CUSTOMER_ID")
    ).count()
    _assert_exact_count(
        "silver_orders rows with BOTH FAIL_NULL_CUSTOMER_ID and FAIL_ORPHAN_CUSTOMER_ID",
        both_null_and_orphan_customer,
        0,
    )

    both_null_and_orphan_product = silver_orders.filter(
        col("quality_check_result").contains("FAIL_NULL_PRODUCT_ID")
        & col("quality_check_result").contains("FAIL_ORPHAN_PRODUCT_ID")
    ).count()
    _assert_exact_count(
        "silver_orders rows with BOTH FAIL_NULL_PRODUCT_ID and FAIL_ORPHAN_PRODUCT_ID",
        both_null_and_orphan_product,
        0,
    )

    products_with_fail_codes = silver_products.filter(
        col("quality_check_result").contains("FAIL_")
    ).count()
    _assert_exact_count(
        "silver_products rows with any FAIL_* code",
        products_with_fail_codes,
        0,
    )

    passed_products = silver_products.filter(
        col("quality_check_result") == "PASSED"
    ).count()
    _assert_exact_count(
        "silver_products rows with quality_check_result = 'PASSED'",
        passed_products,
        500,
    )

    for table_name, silver_df in silver_tables.items():
        invalid_quality = silver_df.filter(
            col("quality_check_result").isNull()
            | (trim(col("quality_check_result")) == "")
        ).count()
        _assert_exact_count(
            f"{table_name} rows with NULL or empty quality_check_result",
            invalid_quality,
            0,
        )

    print("\nALL DATA QUALITY CHECKS PASSED")


if __name__ == "__main__":
    test_silver_quality_checks(spark)
