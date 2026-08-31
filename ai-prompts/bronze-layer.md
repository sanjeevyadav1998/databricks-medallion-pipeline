# AI Prompts — Bronze Layer

## Session 1 — Ingestion scripts
**Tool / mode:** Cursor, Agent mode
**Prompt (verbatim):**

Write the Bronze layer ingestion scripts per tool-specific/cursor-workflow/spec.md section 2 and .cursorrules layer boundaries. Databricks PySpark, for a notebook (Free Edition, serverless compute, Unity Catalog three-level namespace: catalog.schema.table).

SOURCE FILES (exact paths, use literally):
- /Volumes/workspace/default/raw_data/customers.csv
- /Volumes/workspace/default/raw_data/orders.csv
- /Volumes/workspace/default/raw_data/products.csv

Do NOT use dbutils.fs or /dbfs mount-style paths.

TARGET TABLES (catalog "workspace", schema "default" — both already exist, do NOT create or alter the catalog/schema):
- workspace.default.bronze_customers
- workspace.default.bronze_orders
- workspace.default.bronze_products

READ PATTERN — use exactly this, with the DDL schema string given below, no inferSchema:
df = spark.read.format("csv").option("header", "true").schema("<ddl string>").load("<volume path>")

EXACT DDL SCHEMA STRINGS TO USE:

customers.csv:
"customer_id INT, customer_name STRING, email STRING, country STRING, signup_date DATE, customer_segment STRING, lifetime_value DECIMAL(10,2)"

orders.csv:
"order_id INT, customer_id INT, order_date DATE, product_id INT, quantity INT, unit_price DECIMAL(10,2), total_amount DECIMAL(10,2), order_status STRING, payment_date DATE"

products.csv:
"product_id INT, product_name STRING, category STRING, price DECIMAL(10,2), cost DECIMAL(10,2), stock_quantity INT, reorder_level INT"

WRITE PATTERN — use exactly this, for all three:
df.write.format("delta").mode("overwrite").saveAsTable("workspace.default.bronze_<entity>")

FILES TO CREATE:

1. src/bronze/01_ingest_customers.py — reads customers.csv with the exact read pattern and schema above, writes to workspace.default.bronze_customers with the exact write pattern above. After writing: PRINT (do not add as a table column) the row count, current timestamp, and the count of NULLs in signup_date specifically (this column should have zero legitimate nulls — a non-zero count signals a date-parsing mismatch, not a real data issue).

2. src/bronze/02_ingest_orders.py — same pattern, orders.csv → workspace.default.bronze_orders. Also print the count of NULLs in order_date specifically (same reasoning — should always be zero).

3. src/bronze/03_ingest_products.py — same pattern, products.csv → workspace.default.bronze_products. No date columns here, so no extra null check needed.

4. src/bronze/ingest_all.py — imports and calls the three ingestion functions in sequence, then prints one consolidated summary: table name | row count | ingestion timestamp | date-null-check result, for all three (products shows "N/A" for the date check).

HARD RULES:
- No cleaning, filtering, deduplication, or NULL-handling of any kind. Rows with NULL customer_id, NULL product_id, duplicate order_id, etc. must all be written to Bronze exactly as they are in the source.
- Table schema must exactly match the DDL schema strings above — no extra columns.
- Each script runnable standalone in a Databricks notebook cell, using the `spark` session already available.
- Every function needs a docstring.
- Use `# ASSUMPTION:` comments only if something arises not covered by this prompt.

Do not touch any other files.

**Result:** Accepted, no code-logic fixes needed. Cursor correctly:
- Used `importlib` to load the numeric-prefixed `01_`/`02_`/`03_` files as
  modules from `ingest_all.py` (correct Python workaround, not something
  the prompt specified — a good judgment call).
- Followed the exact DDL schema, write pattern, and "no extra columns"
  rule with no deviation.
- Exposed each script as an `ingest_<entity>(spark)` function with a
  docstring and a standalone `__main__` entry point, per `.cursorrules`.

## Debugging — running the scripts (not a code bug)
Two environment/tooling issues surfaced when actually running the
generated code, neither caused by Cursor's code:

1. **`%run` failed** — `%run` is a Databricks-notebook-specific magic
   command; it only works on notebooks, not plain `.py` files. Since the
   scripts were correctly written as standalone Python (per spec), `%run`
   was the wrong invocation method. **Root cause:** a gap in *my*
   environment knowledge, not a prompt or code issue. **Fix:** used
   `runpy.run_path(...)` with `init_globals={"spark": spark}` instead,
   which executes a plain script file while sharing the notebook's
   existing Spark session.

2. **Empty file content on first run** — after fixing the `%run` issue,
   `ingest_all.py` executed but produced zero output, with no error.
   Root cause: the Databricks Git folder had not fully synced the latest
   commit despite showing the correct branch/commit reference in the UI —
   an explicit manual "Pull" was required before the file content matched
   what was actually on GitHub. **Lesson:** don't trust a Git folder's
   apparent sync state after creation; explicitly pull and spot-check
   file content before running, especially right after linking a new
   Git folder.

## Validation
Ran `ingest_all.py` via `runpy` in a Databricks notebook (serverless
compute). Output:
- `workspace.default.bronze_customers`: 10,000 rows, signup_date NULL
  count = 0
- `workspace.default.bronze_orders`: 100,000 rows, order_date NULL
  count = 0
- `workspace.default.bronze_products`: 500 rows, N/A (no date column)

All row counts match the source CSVs exactly (10,000 / 100,000 / 500),
confirming Bronze ingested every row with no silent drops, and the
date-null tripwire confirms no schema/parsing mismatch.

## Status: ACCEPTED (1 code session, 2 environment/tooling fixes, 0 code fixes)