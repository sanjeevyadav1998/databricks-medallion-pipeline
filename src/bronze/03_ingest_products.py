"""Bronze ingestion: raw products CSV to Delta table."""

from datetime import datetime

SOURCE_PATH = "/Volumes/workspace/default/raw_data/products.csv"
TARGET_TABLE = "workspace.default.bronze_products"


def ingest_products(spark):
    """
    Read products.csv from the Unity Catalog volume and write to bronze_products.

    Raw ingestion only — no cleaning, filtering, or transformation. Prints row count
    and ingestion timestamp after the Delta table is written.
    """
    df = spark.read.format("csv").option("header", "true").schema(
        "product_id INT, product_name STRING, category STRING, price DECIMAL(10,2), "
        "cost DECIMAL(10,2), stock_quantity INT, reorder_level INT"
    ).load(SOURCE_PATH)

    df.write.format("delta").mode("overwrite").saveAsTable(TARGET_TABLE)

    row_count = df.count()
    ingestion_timestamp = datetime.now()

    print(f"Table: {TARGET_TABLE}")
    print(f"Row count: {row_count}")
    print(f"Ingestion timestamp: {ingestion_timestamp}")

    return {
        "table_name": TARGET_TABLE,
        "row_count": row_count,
        "ingestion_timestamp": ingestion_timestamp,
        "date_null_check": "N/A",
    }


if __name__ == "__main__":
    ingest_products(spark)
