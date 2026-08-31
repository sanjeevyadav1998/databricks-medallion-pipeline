# Data Layer Setup Notes

Step-by-step instructions to stand up the 10 pipeline tables (3 Bronze, 3 Silver, 4 Gold) from scratch. This guide is narrower in scope than the top-level [README.md](../README.md), which additionally covers Dashboard and account setup.

For the resulting table shapes, see [schema.sql](./schema.sql). That file is a **reference** for what these steps produce — it is not an alternative or additional setup step, and no project script executes it.

---

## 1. Generate seed CSVs (local)

Run from your local machine:

```bash
python src/data_generation/generate_sample_data.py
```

This writes three CSVs to the repo-root `data/` folder:

- `customers.csv` (10,000 rows)
- `orders.csv` (100,000 rows)
- `products.csv` (500 rows)

Skip this step if the CSVs already exist and you want to keep the current seed data unchanged. The fixed random seed (`42`) means re-running produces identical output anyway.

See [seed-data-notes.md](./seed-data-notes.md) for column-to-Bronze-schema mapping.

---

## 2. Prerequisites (Databricks)

The following must already exist before running the pipeline scripts. **None of the project scripts create or alter these objects programmatically.**

| Object | Name / path |
|--------|-------------|
| Unity Catalog | `workspace` |
| Schema | `workspace.default` |
| Volume | `/Volumes/workspace/default/raw_data/` |

If the Volume does not exist, create it via **Catalog Explorer** in the Databricks workspace UI (Catalog → `workspace` → `default` → Create Volume → `raw_data`).

---

## 3. Upload seed CSVs to the Volume

Upload all three files from the local `data/` folder to:

```
/Volumes/workspace/default/raw_data/
```

Expected files after upload:

- `/Volumes/workspace/default/raw_data/customers.csv`
- `/Volumes/workspace/default/raw_data/orders.csv`
- `/Volumes/workspace/default/raw_data/products.csv`

---

## 4. Run Bronze ingestion

```python
# Databricks notebook or job — requires an active SparkSession
%run ./src/bronze/ingest_all.py
```

Or invoke `ingest_all(spark)` from a notebook that already has a `spark` session.

**Creates:** `workspace.default.bronze_customers`, `workspace.default.bronze_orders`, `workspace.default.bronze_products`

---

## 5. Run Silver layer

```python
%run ./src/silver/create_silver_tables.py
```

**Depends on:** Bronze tables from step 4.

**Creates:** `workspace.default.silver_customers`, `workspace.default.silver_orders`, `workspace.default.silver_products` (each with a `quality_check_result` column appended).

---

## 6. Run Gold layer

```python
%run ./src/gold/create_gold_tables.py
```

**Depends on:** Silver tables from step 5.

**Creates:** `workspace.default.gold_sales_by_product`, `workspace.default.gold_revenue_by_customer`, `workspace.default.gold_daily_weekly_trends`, `workspace.default.gold_customer_segmentation`

---

## 7. Verify (optional)

```bash
python tests/run_all_tests.py
```

Runs unit and integration tests end-to-end. The integration tier re-executes Bronze, Silver, and Gold ingestion (steps 4–6) as part of the test suite.

---

## Quick reference

| Step | Script | Tables created |
|------|--------|----------------|
| 4 | `src/bronze/ingest_all.py` | 3 Bronze |
| 5 | `src/silver/create_silver_tables.py` | 3 Silver |
| 6 | `src/gold/create_gold_tables.py` | 4 Gold |

**Total:** 10 tables in `workspace.default`, all created by pipeline scripts via `.saveAsTable(...)` — not by running `database/schema.sql`.
