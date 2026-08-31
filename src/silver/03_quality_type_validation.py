"""Silver type and format validation checks."""

from pyspark.sql import DataFrame
from pyspark.sql.functions import col, lit, trim, when


def invalid_email_format_flag():
    """
    Flag customers whose email is present but does not contain '@'.

    NULL and blank emails are skipped so completeness owns those failures.
    Assigns FAIL_INVALID_EMAIL_FORMAT.
    """
    return when(
        col("email").isNotNull()
        & (trim(col("email")) != "")
        & ~col("email").contains("@"),
        lit("FAIL_INVALID_EMAIL_FORMAT"),
    )


def invalid_signup_date_flag():
    """
    Flag customers whose signup_date could not be parsed to a valid DATE in Bronze.

    Assigns FAIL_INVALID_DATE.
    """
    return when(col("signup_date").isNull(), lit("FAIL_INVALID_DATE"))


def invalid_order_date_flag():
    """
    Flag orders whose order_date could not be parsed to a valid DATE in Bronze.

    Assigns FAIL_INVALID_DATE.
    """
    return when(col("order_date").isNull(), lit("FAIL_INVALID_DATE"))


def apply_customer_type_checks(df: DataFrame) -> DataFrame:
    """
    Add format/type flag columns for the customers entity.

    Returns the input DataFrame with _flag_invalid_email_format and
    _flag_invalid_signup_date columns appended.
    """
    return (
        df.withColumn("_flag_invalid_email_format", invalid_email_format_flag())
        .withColumn("_flag_invalid_signup_date", invalid_signup_date_flag())
    )


def apply_order_type_checks(df: DataFrame) -> DataFrame:
    """
    Add format/type flag columns for the orders entity.

    payment_date is intentionally excluded because cancelled orders may legitimately
    have no payment date. Returns the input DataFrame with _flag_invalid_order_date.
    """
    return df.withColumn("_flag_invalid_order_date", invalid_order_date_flag())
