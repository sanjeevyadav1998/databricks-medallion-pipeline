"""Orchestrate Gold-layer SQL aggregations and materialize business-ready Delta tables."""

from __future__ import annotations

from pathlib import Path

from pyspark.sql import DataFrame, SparkSession

GOLD_DIR = Path(__file__).resolve().parent

# Each entry: (sql filename, target table, column for top-N preview ordering).
GOLD_TABLE_SPECS: list[tuple[str, str, str]] = [
    ("01_sales_by_product.sql", "workspace.default.gold_sales_by_product", "total_revenue"),
    (
        "02_revenue_by_customer.sql",
        "workspace.default.gold_revenue_by_customer",
        "total_revenue",
    ),
    (
        "03_daily_weekly_trends.sql",
        "workspace.default.gold_daily_weekly_trends",
        "total_revenue",
    ),
    (
        "04_customer_segmentation.sql",
        "workspace.default.gold_customer_segmentation",
        "customer_count",
    ),
]


def load_sql_query(filename: str) -> str:
    """
    Read a Gold SQL file from disk relative to this script's directory.

    SQL files are not executed directly; their text is passed to spark.sql() so
    Silver tables are referenced by full Unity Catalog name inside the query.
    """
    sql_path = GOLD_DIR / filename
    return sql_path.read_text(encoding="utf-8")


def run_gold_query(spark: SparkSession, filename: str) -> DataFrame:
    """
    Load and execute one Gold aggregation query against the active Spark session.

    Returns the aggregation result without writing; the caller materializes the
    Delta table so write mode and table naming stay centralized.
    """
    query_text = load_sql_query(filename)
    return spark.sql(query_text)


def write_gold_table(result_df: DataFrame, table_name: str) -> None:
    """
    Overwrite the target Gold Delta table with the aggregation result.

    Uses the project-standard Unity Catalog three-level name and overwrite mode
    so re-runs replace prior Gold snapshots idempotently.
    """
    result_df.write.format("delta").mode("overwrite").saveAsTable(table_name)


def _format_preview_rows(preview_df: DataFrame) -> str:
    """Format up to three preview rows as a compact, single-line string."""
    rows = preview_df.collect()
    if not rows:
        return "(no rows)"

    # ASSUMPTION: str(row.asDict()) is sufficient for notebook logging; dashboard
    # consumers read the Delta tables directly, not this preview text.
    return " | ".join(str(row.asDict()) for row in rows)


def print_gold_summary(spark: SparkSession, table_specs: list[tuple[str, str, str]]) -> None:
    """
    Print row counts and top-3 preview rows for each materialized Gold table.

    Revenue-oriented tables are ranked by total_revenue; segmentation uses
    customer_count so the largest segments surface first in the summary.
    """
    print("\n=== Gold Layer Summary ===")
    header = f"{'Gold Table Name':<45} | {'Row Count':>9} | Top 3 Rows (by sort column)"
    print(header)
    print("-" * len(header))

    for _sql_file, table_name, sort_column in table_specs:
        gold_df = spark.read.table(table_name)
        row_count = gold_df.count()
        preview_df = gold_df.orderBy(sort_column, ascending=False).limit(3)
        preview_text = _format_preview_rows(preview_df)
        print(f"{table_name:<45} | {row_count:>9,} | {preview_text}")


def create_gold_tables(spark: SparkSession) -> dict[str, DataFrame]:
    """
    Execute all Gold SQL aggregations against Silver and write Delta tables.

    Only PASSED Silver rows and Completed orders participate; filtering is
    enforced inside each .sql file's CTEs, not in this orchestrator.
    """
    gold_tables: dict[str, DataFrame] = {}

    print("Building Gold tables from Silver inputs...")
    for sql_file, table_name, _sort_column in GOLD_TABLE_SPECS:
        print(f"  Running {sql_file} -> {table_name}")
        result_df = run_gold_query(spark, sql_file)
        write_gold_table(result_df, table_name)
        gold_tables[table_name] = result_df
        print(f"    wrote {result_df.count():,} rows")

    print_gold_summary(spark, GOLD_TABLE_SPECS)
    return gold_tables


if __name__ == "__main__":
    create_gold_tables(spark)
