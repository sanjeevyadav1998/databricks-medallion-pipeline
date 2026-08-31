"""Silver referential integrity checks: foreign keys must exist in parent tables."""

from pyspark.sql import DataFrame
from pyspark.sql.functions import col, lit, when


def add_orphan_customer_id_flag(orders_df: DataFrame, customers_df: DataFrame) -> DataFrame:
    """
    Flag orders whose non-null customer_id is absent from the customers table.

    Joins against distinct parent keys only to prevent row explosion when parent
    tables contain duplicate primary keys. NULL customer_ids are skipped so
    completeness owns those failures. Assigns FAIL_ORPHAN_CUSTOMER_ID.
    """
    valid_customers = customers_df.select("customer_id").distinct()
    enriched = orders_df.join(
        valid_customers.withColumn("_customer_exists", lit(1)),
        on="customer_id",
        how="left",
    )
    return enriched.withColumn(
        "_flag_orphan_customer_id",
        when(
            col("customer_id").isNotNull() & col("_customer_exists").isNull(),
            lit("FAIL_ORPHAN_CUSTOMER_ID"),
        ),
    ).drop("_customer_exists")


def add_orphan_product_id_flag(orders_df: DataFrame, products_df: DataFrame) -> DataFrame:
    """
    Flag orders whose non-null product_id is absent from the products table.

    Joins against distinct parent keys only to prevent row explosion when parent
    tables contain duplicate primary keys. NULL product_ids are skipped so
    completeness owns those failures. Assigns FAIL_ORPHAN_PRODUCT_ID.
    """
    valid_products = products_df.select("product_id").distinct()
    enriched = orders_df.join(
        valid_products.withColumn("_product_exists", lit(1)),
        on="product_id",
        how="left",
    )
    return enriched.withColumn(
        "_flag_orphan_product_id",
        when(
            col("product_id").isNotNull() & col("_product_exists").isNull(),
            lit("FAIL_ORPHAN_PRODUCT_ID"),
        ),
    ).drop("_product_exists")


def apply_order_referential_checks(
    orders_df: DataFrame,
    customers_df: DataFrame,
    products_df: DataFrame,
) -> DataFrame:
    """
    Add referential-integrity flag columns for the orders entity.

    Runs customer and product foreign-key checks sequentially.
    """
    with_customer_check = add_orphan_customer_id_flag(orders_df, customers_df)
    return add_orphan_product_id_flag(with_customer_check, products_df)
