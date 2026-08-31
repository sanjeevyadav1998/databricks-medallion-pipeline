"""Silver completeness checks: NULL or blank values in critical fields."""

from pyspark.sql import DataFrame
from pyspark.sql.functions import col, lit, trim, when


def null_email_flag():
    """
    Flag customers whose email is NULL or blank after trimming.

    Blank CSV values remain as empty strings in Bronze; both NULL and empty
    are treated as missing. Assigns FAIL_NULL_EMAIL.
    """
    return when(
        col("email").isNull() | (trim(col("email")) == ""),
        lit("FAIL_NULL_EMAIL"),
    )


def null_customer_id_flag():
    """
    Flag orders whose customer_id is NULL.

    Missing foreign keys are caught here so referential integrity can skip NULLs.
    Assigns FAIL_NULL_CUSTOMER_ID.
    """
    return when(col("customer_id").isNull(), lit("FAIL_NULL_CUSTOMER_ID"))


def null_product_id_flag():
    """
    Flag orders whose product_id is NULL.

    Missing foreign keys are caught here so referential integrity can skip NULLs.
    Assigns FAIL_NULL_PRODUCT_ID.
    """
    return when(col("product_id").isNull(), lit("FAIL_NULL_PRODUCT_ID"))


def apply_customer_completeness_checks(df: DataFrame) -> DataFrame:
    """
    Add completeness flag columns for the customers entity.

    Returns the input DataFrame with a _flag_null_email column appended.
    """
    return df.withColumn("_flag_null_email", null_email_flag())


def apply_order_completeness_checks(df: DataFrame) -> DataFrame:
    """
    Add completeness flag columns for the orders entity.

    Returns the input DataFrame with _flag_null_customer_id and
    _flag_null_product_id columns appended.
    """
    return (
        df.withColumn("_flag_null_customer_id", null_customer_id_flag())
        .withColumn("_flag_null_product_id", null_product_id_flag())
    )
