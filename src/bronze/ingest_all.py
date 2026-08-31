"""Orchestrate all Bronze layer ingestion scripts."""

from __future__ import annotations

import importlib.util
from pathlib import Path

BRONZE_DIR = Path(__file__).resolve().parent


def _load_ingest_module(filename: str, module_name: str):
    """
    Load a Bronze ingestion script as a module.

    Numeric filename prefixes (01_, 02_, etc.) are not valid Python import names,
    so importlib is used to load them by file path instead.
    """
    path = BRONZE_DIR / filename
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def ingest_all(spark):
    """
    Run customers, orders, and products Bronze ingestion in sequence.

    Prints a consolidated summary with row counts, ingestion timestamps, and
    date-null-check results for each table.
    """
    customers_mod = _load_ingest_module("01_ingest_customers.py", "ingest_customers_mod")
    orders_mod = _load_ingest_module("02_ingest_orders.py", "ingest_orders_mod")
    products_mod = _load_ingest_module("03_ingest_products.py", "ingest_products_mod")

    results = [
        customers_mod.ingest_customers(spark),
        orders_mod.ingest_orders(spark),
        products_mod.ingest_products(spark),
    ]

    print("\n=== Bronze ingestion summary ===")
    print("table name | row count | ingestion timestamp | date-null-check result")
    for result in results:
        print(
            f"{result['table_name']} | {result['row_count']} | "
            f"{result['ingestion_timestamp']} | {result['date_null_check']}"
        )

    return results


if __name__ == "__main__":
    ingest_all(spark)
