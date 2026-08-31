"""Bronze ingestion: raw orders CSV to Delta table."""

from datetime import datetime

SOURCE_PATH = "/Volumes/workspace/default/raw_data/orders.csv"
TARGET_TABLE = "workspace.default.bronze_orders"


def ingest_orders(spark):
    """
    Read orders.csv from the Unity Catalog volume and write to bronze_orders.

    Raw ingestion only — no cleaning, filtering, or transformation. Prints row count,
    ingestion timestamp, and order_date NULL count to detect date-parsing mismatches.
    """
    df = spark.read.format("csv").option("header", "true").schema(
        "order_id INT, customer_id INT, order_date DATE, product_id INT, quantity INT, "
        "unit_price DECIMAL(10,2), total_amount DECIMAL(10,2), order_status STRING, "
        "payment_date DATE"
    ).load(SOURCE_PATH)

    df.write.format("delta").mode("overwrite").saveAsTable(TARGET_TABLE)

    row_count = df.count()
    ingestion_timestamp = datetime.now()
    order_date_null_count = df.filter("order_date IS NULL").count()

    print(f"Table: {TARGET_TABLE}")
    print(f"Row count: {row_count}")
    print(f"Ingestion timestamp: {ingestion_timestamp}")
    print(f"order_date NULL count: {order_date_null_count}")

    return {
        "table_name": TARGET_TABLE,
        "row_count": row_count,
        "ingestion_timestamp": ingestion_timestamp,
        "date_null_check": order_date_null_count,
    }


if __name__ == "__main__":
    ingest_orders(spark)
