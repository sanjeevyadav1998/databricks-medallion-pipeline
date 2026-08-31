# Specification — Medallion Pipeline

This is the design spec the project is built against. Each Cursor prompt
references the relevant section here instead of re-explaining requirements
from scratch.

## 1. Architecture

```
S3/DBFS CSVs → Bronze (raw Delta tables) → Silver (validated, flagged) →
Gold (aggregated Delta tables) → Dashboard (SQL queries + visualizations)
```

- Storage format: Delta Lake tables at each layer.
- Each layer reads only from the layer directly below it.
- Bronze is idempotent-ingest (re-running shouldn't duplicate rows silently —
  log if it would).

## 2. Bronze Layer

| Script | Responsibility |
|---|---|
| `01_ingest_customers.py` | Read `customers.csv` → `bronze_customers` Delta table |
| `02_ingest_orders.py` | Read `orders.csv` → `bronze_orders` Delta table |
| `03_ingest_products.py` | Read `products.csv` → `bronze_products` Delta table |
| `ingest_all.py` | Orchestrates the three, logs row counts + timestamp per table |

Rules: schema inference/explicit schema on read, no cleaning, no dropped
rows, metadata logging only (row count, ingestion timestamp).

## 3. Silver Layer

| Script | Responsibility |
|---|---|
| `01_quality_completeness.py` | NULL checks on `email`, `customer_id`, `product_id` |
| `02_quality_uniqueness.py` | Duplicate checks on `order_id`, `customer_id` |
| `03_quality_type_validation.py` | Type/format validation (e.g. valid email format, valid date ranges) |
| `04_quality_referential_integrity.py` | FK existence checks (customer_id, product_id) |
| `05_quality_business_logic.py` | Domain rules (e.g. `total_amount` ≈ `quantity × unit_price`, no negative quantities) |
| `create_silver_tables.py` | Runs 01–05, merges results into `silver_customers` / `silver_orders` / `silver_products` with a `quality_check_result` column, and emits a quality metrics report (% passed per check) |

Rules: never delete bad rows — flag them. Report must show % passed per
check per table.

## 4. Gold Layer

| Script | Responsibility |
|---|---|
| `01_sales_by_product.sql` | Aggregation A (see project-context.md) |
| `02_revenue_by_customer.sql` | Aggregation B |
| `03_daily_weekly_trends.sql` | Time-series trend view (supports dashboard) |
| `04_customer_segmentation.sql` | Aggregation C |
| `create_gold_tables.py` | Runs the SQL above against Silver tables, materializes `gold_*` Delta tables |

Only rows that passed Silver quality checks feed Gold aggregations, unless a
specific prompt says to analyze all rows including flagged ones.

## 5. Dashboard

- `dashboard_queries.sql` — the 3+ queries backing the visualizations.
- `DASHBOARD_GUIDE.md` — how to wire these into a Databricks SQL Dashboard
  (tile config, filters).

## 6. Testing

- At least one meaningful test tier: data quality tests (do the Silver
  checks actually catch the intentionally-injected issues — assert counts
  match the ~700 injected rows) and/or pipeline integration tests (does
  Bronze → Silver → Gold run end-to-end without error on the sample data).

## 7. Out of scope (do not build unless explicitly asked later)
- Streaming ingestion, orchestration tooling (Airflow/Step Functions),
  multi-environment config, auth/secrets management, CI/CD.
