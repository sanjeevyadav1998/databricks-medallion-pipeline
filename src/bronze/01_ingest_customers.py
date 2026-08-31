"""Bronze ingestion: raw customers CSV to Delta table."""

from datetime import datetime

SOURCE_PATH = "/Volumes/workspace/default/raw_data/customers.csv"
TARGET_TABLE = "workspace.default.bronze_customers"


def ingest_customers(spark):
    """
    Read customers.csv from the Unity Catalog volume and write to bronze_customers.

    Raw ingestion only — no cleaning, filtering, or transformation. Prints row count,
    ingestion timestamp, and signup_date NULL count to detect date-parsing mismatches.
    """
    df = spark.read.format("csv").option("header", "true").schema(
        "customer_id INT, customer_name STRING, email STRING, country STRING, "
        "signup_date DATE, customer_segment STRING, lifetime_value DECIMAL(10,2)"
    ).load(SOURCE_PATH)

    df.write.format("delta").mode("overwrite").saveAsTable(TARGET_TABLE)

    row_count = df.count()
    ingestion_timestamp = datetime.now()
    signup_date_null_count = df.filter("signup_date IS NULL").count()

    print(f"Table: {TARGET_TABLE}")
    print(f"Row count: {row_count}")
    print(f"Ingestion timestamp: {ingestion_timestamp}")
    print(f"signup_date NULL count: {signup_date_null_count}")

    return {
        "table_name": TARGET_TABLE,
        "row_count": row_count,
        "ingestion_timestamp": ingestion_timestamp,
        "date_null_check": signup_date_null_count,
    }


if __name__ == "__main__":
    ingest_customers(spark)
