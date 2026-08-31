# Seed Data Notes

This document describes how the local seed CSVs map onto the Bronze layer schema. It covers **what** each file contains and **where** it lands before ingestion — not **why** specific quality issues were injected. For the rationale behind each intentional defect, see [DATA_GENERATION_NOTES.md](../src/data_generation/DATA_GENERATION_NOTES.md).

## Reproducibility

`src/data_generation/generate_sample_data.py` uses a fixed random seed (`RANDOM_SEED = 42`). Re-running the generator produces identical CSVs every time, which keeps Silver-layer quality-check tests deterministic.

## Seed file destination

After generation, upload the three CSVs from the repo-root `data/` folder to the Unity Catalog Volume:

```
/Volumes/workspace/default/raw_data/
```

This is a Unity Catalog Volume path — not a DBFS mount path. The Bronze ingestion scripts read from this location.

---

## customers.csv

| Column | Bronze type | Notes |
|--------|-------------|-------|
| `customer_id` | `INT` | |
| `customer_name` | `STRING` | |
| `email` | `STRING` | Empty string in CSV becomes `NULL` on ingest |
| `country` | `STRING` | |
| `signup_date` | `DATE` | ISO-8601 date string in CSV |
| `customer_segment` | `STRING` | Values: Premium, Standard, Basic |
| `lifetime_value` | `DECIMAL(10,2)` | |

**Source row count:** 10,000

**Target Bronze table:** `workspace.default.bronze_customers`

---

## orders.csv

| Column | Bronze type | Notes |
|--------|-------------|-------|
| `order_id` | `INT` | |
| `customer_id` | `INT` | Empty string in CSV becomes `NULL` on ingest |
| `order_date` | `DATE` | ISO-8601 date string in CSV |
| `product_id` | `INT` | Empty string in CSV becomes `NULL` on ingest |
| `quantity` | `INT` | |
| `unit_price` | `DECIMAL(10,2)` | |
| `total_amount` | `DECIMAL(10,2)` | |
| `order_status` | `STRING` | Values: Pending, Completed, Cancelled |
| `payment_date` | `DATE` | Empty string in CSV becomes `NULL` on ingest |

**Source row count:** 100,000

**Target Bronze table:** `workspace.default.bronze_orders`

---

## products.csv

| Column | Bronze type | Notes |
|--------|-------------|-------|
| `product_id` | `INT` | |
| `product_name` | `STRING` | |
| `category` | `STRING` | |
| `price` | `DECIMAL(10,2)` | |
| `cost` | `DECIMAL(10,2)` | |
| `stock_quantity` | `INT` | |
| `reorder_level` | `INT` | |

**Source row count:** 500

**Target Bronze table:** `workspace.default.bronze_products`

---

## Related documentation

- [DATA_GENERATION_NOTES.md](../src/data_generation/DATA_GENERATION_NOTES.md) — why each data-quality issue exists and how counts are verified
- [schema.sql](./schema.sql) — full DDL reference for all 10 pipeline tables
- [setup-notes.md](./setup-notes.md) — step-by-step instructions to populate the tables from these seed files
