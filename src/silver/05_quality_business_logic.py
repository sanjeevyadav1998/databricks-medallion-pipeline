"""Silver business-logic validation checks."""

from pyspark.sql import DataFrame
from pyspark.sql.functions import abs as spark_abs
from pyspark.sql.functions import col, lit, when


# ASSUMPTION: prompt names FAIL_CALCULATION_MISMATCH and FAIL_INVALID_QUANTITY only;
# price < cost uses FAIL_PRICE_BELOW_COST because no explicit code was provided.
FAIL_PRICE_BELOW_COST = "FAIL_PRICE_BELOW_COST"


def calculation_mismatch_flag():
    """
    Flag orders where total_amount differs from quantity * unit_price by more than 0.01.

    NULL inputs are skipped so missing values are not misflagged as mismatches.
    Assigns FAIL_CALCULATION_MISMATCH.
    """
    expected_total = col("quantity") * col("unit_price")
    return when(
        col("quantity").isNotNull()
        & col("unit_price").isNotNull()
        & col("total_amount").isNotNull()
        & (spark_abs(col("total_amount") - expected_total) > lit(0.01)),
        lit("FAIL_CALCULATION_MISMATCH"),
    )


def invalid_quantity_flag():
    """
    Flag orders whose quantity is present but not strictly greater than zero.

    NULL quantity is skipped so completeness or upstream parsing owns missing values.
    Assigns FAIL_INVALID_QUANTITY.
    """
    return when(
        col("quantity").isNotNull() & (col("quantity") <= 0),
        lit("FAIL_INVALID_QUANTITY"),
    )


def price_below_cost_flag():
    """
    Flag products whose price is present but strictly less than cost.

    NULL price or cost is skipped to avoid false positives on incomplete rows.
    Assigns FAIL_PRICE_BELOW_COST.
    """
    return when(
        col("price").isNotNull()
        & col("cost").isNotNull()
        & (col("price") < col("cost")),
        lit(FAIL_PRICE_BELOW_COST),
    )


def apply_order_business_checks(df: DataFrame) -> DataFrame:
    """
    Add business-logic flag columns for the orders entity.

    Returns the input DataFrame with _flag_calculation_mismatch and
    _flag_invalid_quantity columns appended.
    """
    return (
        df.withColumn("_flag_calculation_mismatch", calculation_mismatch_flag())
        .withColumn("_flag_invalid_quantity", invalid_quantity_flag())
    )


def apply_product_business_checks(df: DataFrame) -> DataFrame:
    """
    Add business-logic flag columns for the products entity.

    Returns the input DataFrame with a _flag_price_below_cost column appended.
    """
    return df.withColumn("_flag_price_below_cost", price_below_cost_flag())
