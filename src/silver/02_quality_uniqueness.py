"""Silver uniqueness checks: duplicate primary keys."""

from pyspark.sql import DataFrame, Window
from pyspark.sql.functions import col, lit, monotonically_increasing_id, row_number, when


def duplicate_customer_id_flag(df: DataFrame):
    """
    Flag customer rows that reuse a customer_id already seen earlier in the table.

    Only non-first occurrences are flagged so injected duplicate counts match the
    data-generation spec (10 rows, not 20). Assigns FAIL_DUPLICATE_CUSTOMER_ID.
    """
    window = Window.partitionBy("customer_id").orderBy(monotonically_increasing_id())
    return when(row_number().over(window) > 1, lit("FAIL_DUPLICATE_CUSTOMER_ID"))


def duplicate_order_id_flag(df: DataFrame):
    """
    Flag order rows that reuse an order_id already seen earlier in the table.

    Only non-first occurrences are flagged so injected duplicate counts match the
    data-generation spec (20 rows). Assigns FAIL_DUPLICATE_ORDER_ID.
    """
    window = Window.partitionBy("order_id").orderBy(monotonically_increasing_id())
    return when(row_number().over(window) > 1, lit("FAIL_DUPLICATE_ORDER_ID"))


def duplicate_product_id_flag(df: DataFrame):
    """
    Flag product rows that reuse a product_id already seen earlier in the table.

    Only non-first occurrences are flagged. Assigns FAIL_DUPLICATE_PRODUCT_ID.
    """
    window = Window.partitionBy("product_id").orderBy(monotonically_increasing_id())
    return when(row_number().over(window) > 1, lit("FAIL_DUPLICATE_PRODUCT_ID"))


def apply_customer_uniqueness_checks(df: DataFrame) -> DataFrame:
    """
    Add uniqueness flag columns for the customers entity.

    Returns the input DataFrame with a _flag_duplicate_customer_id column appended.
    """
    return df.withColumn("_flag_duplicate_customer_id", duplicate_customer_id_flag(df))


def apply_order_uniqueness_checks(df: DataFrame) -> DataFrame:
    """
    Add uniqueness flag columns for the orders entity.

    Returns the input DataFrame with a _flag_duplicate_order_id column appended.
    """
    return df.withColumn("_flag_duplicate_order_id", duplicate_order_id_flag(df))


def apply_product_uniqueness_checks(df: DataFrame) -> DataFrame:
    """
    Add uniqueness flag columns for the products entity.

    Returns the input DataFrame with a _flag_duplicate_product_id column appended.
    """
    return df.withColumn("_flag_duplicate_product_id", duplicate_product_id_flag(df))
