# AI Prompts — Documentation (Database Schema, Task 10)

## Session 1 — Design decisions locked before drafting
**Tool / mode:** Claude (spec drafting), not yet sent to Cursor.
"Database schema" needed interpretation for this project, since it uses
Databricks Unity Catalog / Delta Lake rather than a traditional RDBMS —
all 10 tables (3 Bronze, 3 Silver, 4 Gold) are already created implicitly
by the pipeline scripts via `.saveAsTable(...)`, not by any standalone DDL
script. Locked before drafting: `database/schema.sql` would be a
REFERENCE/documentation artifact describing the resulting schema, not a
script meant to be run as part of setup — and `seed-data-notes.md` /
`setup-notes.md` would be scoped narrowly (seed-to-schema mapping;
step-by-step data-layer setup) to avoid duplicating
`DATA_GENERATION_NOTES.md` or the top-level `README.md`.

## Session 2 — Pre-emptive hardening (3 review passes before running)
Reviewed the prompt three separate times before sending it to Cursor:

**Pass 1 — schema-mismatch risk found:** Bronze and Silver column types are
known with 100% certainty (literal DDL strings already used in the
ingestion scripts), safe to write as real executable `CREATE TABLE`
statements. Gold's computed columns (SUM/ROUND/division results) have
Spark-inferred DECIMAL precision/scale that can't be confirmed without
querying the live tables — writing these as executable DDL with a guessed
precision could cause a real Delta schema-mismatch error if
`create_gold_tables.py`'s later `.saveAsTable(mode="overwrite")` write
didn't exactly match the guess (no `overwriteSchema` option is used
there). Fixed by requiring the Gold section to be written as a fully
commented-out reference block instead of executable DDL — documents the
expected shape without any risk of it ever actually breaking a real run.

**Pass 2 — two misrepresentation risks found:**
1. No guard against `NOT NULL` constraints — the data intentionally
   contains NULLs (email, customer_id, product_id) as injected quality
   issues; a NOT NULL constraint would misrepresent the real data and
   could break ingestion if the schema were ever actually applied first.
2. No guard against `PRIMARY KEY`/`FOREIGN KEY` constraints — the data
   intentionally contains duplicate PKs and orphaned FKs as injected
   quality issues; declaring these constraints (even as Unity Catalog's
   non-enforced informational constraints) would be factually incorrect
   documentation of what the tables actually contain.
Both fixed by adding explicit HARD RULES prohibiting either constraint
type anywhere in schema.sql.

**Pass 3 — two missing setup-notes.md gaps found:**
3. The original step list started at "upload the seed CSVs," with no step
   explaining how those CSVs get created in the first place. Fixed by
   adding a first step to run `generate_sample_data.py` locally.
4. The Unity Catalog Volume path
   (`/Volumes/workspace/default/raw_data/`) was treated as already
   existing without ever being stated as a prerequisite, unlike the
   catalog/schema which were explicitly called out. Fixed by adding the
   Volume to the same prerequisite bullet as the catalog and schema, with
   a note on how to create it via Catalog Explorer if missing.

## Session 3 — Final prompt sent to Cursor
**Tool / mode:** Cursor, Agent mode.

**Prompt (verbatim):**

Write the database schema and setup documentation for this project per .cursorrules layer boundaries. Databricks PySpark, Unity Catalog three-level namespace: catalog.schema.table (catalog "workspace", schema "default").

CONTEXT: This project uses Databricks Delta Lake / Unity Catalog, not a traditional RDBMS. All 10 tables (3 Bronze, 3 Silver, 4 Gold) are actually created by their respective pipeline scripts via `.saveAsTable(...)`, NOT by running database/schema.sql directly. schema.sql is a REFERENCE/DOCUMENTATION artifact describing the resulting schema for a reviewer, not a script that gets executed as part of the pipeline. Do not imply anywhere that running this file is a required or normal step — the pipeline scripts already create these tables.

EXACT KNOWN SCHEMAS (Bronze — copy exactly, these are the literal DDL strings used in src/bronze/01_ingest_customers.py / 02_ingest_orders.py / 03_ingest_products.py, do not alter):

bronze_customers:
customer_id INT, customer_name STRING, email STRING, country STRING, signup_date DATE, customer_segment STRING, lifetime_value DECIMAL(10,2)

bronze_orders:
order_id INT, customer_id INT, order_date DATE, product_id INT, quantity INT, unit_price DECIMAL(10,2), total_amount DECIMAL(10,2), order_status STRING, payment_date DATE

bronze_products:
product_id INT, product_name STRING, category STRING, price DECIMAL(10,2), cost DECIMAL(10,2), stock_quantity INT, reorder_level INT

SILVER SCHEMAS: identical to the corresponding Bronze table above, PLUS exactly one appended column: `quality_check_result STRING` (never NULL, value is either 'PASSED' or a pipe-delimited list of FAIL_* codes).

GOLD SCHEMAS (column names/order are exact and known; DECIMAL precision/scale for computed SUM/ROUND/division columns is Spark-inferred at write time and NOT guaranteed to match a hand-written guess exactly — use DECIMAL(38,2) as a safe wide default for these columns and mark each one with an inline SQL comment "-- ASSUMPTION: exact precision/scale may differ from live table; verify via DESCRIBE TABLE workspace.default.<table> if byte-exact matching is required"):

gold_sales_by_product:
product_id INT, product_name STRING, category STRING, total_orders BIGINT, total_revenue DECIMAL(38,2), avg_order_value DECIMAL(38,2)

gold_revenue_by_customer:
customer_id INT, customer_name STRING, customer_segment STRING, total_orders BIGINT, total_revenue DECIMAL(38,2), avg_order_value DECIMAL(38,2), lifetime_value_actual DECIMAL(38,2)

gold_daily_weekly_trends:
order_date DATE, order_week TIMESTAMP, total_orders BIGINT, total_revenue DECIMAL(38,2)

gold_customer_segmentation:
segment_type STRING, customer_count BIGINT, avg_revenue DECIMAL(38,2), total_revenue DECIMAL(38,2)

FILES TO CREATE (all 3 already exist as empty stub files — fill them in, do not change their names or locations):

1. `database/schema.sql` — DDL reference for all 10 tables above.
   - BRONZE and SILVER (6 tables): use real, executable `CREATE TABLE IF NOT EXISTS workspace.default.<table_name> (...) USING DELTA;` statements — these types are known exactly (literal DDL strings already used by the pipeline scripts), so it is safe for this SQL to actually run without risk of conflicting with what `.saveAsTable(mode="overwrite")` later writes.
   - GOLD (4 tables): DO NOT write these as executable `CREATE TABLE` statements. Write them as a commented-out reference block instead (e.g. prefixed with `-- ` on every line, under a header comment "-- GOLD LAYER (reference only — DO NOT run this section)"). Reason: the DECIMAL precision/scale shown for Gold's computed SUM/ROUND/division columns is a best-effort guess, not a confirmed exact match to what Spark actually infers at write time. If someone ran this as real DDL and the guessed precision differs even slightly from what `create_gold_tables.py` later tries to write, the subsequent `.saveAsTable(mode="overwrite")` call (which does not use `overwriteSchema`) could fail with a Delta schema-mismatch error. Keeping Gold as commented-out reference text avoids ever creating that failure mode while still documenting the expected shape.
   - Group into 3 clearly commented sections: "-- BRONZE LAYER (raw ingest, no transformation)", "-- SILVER LAYER (validated + quality_check_result appended)", "-- GOLD LAYER (business aggregations, PASSED+Completed orders only) (reference only — DO NOT run this section)".
   - Add a header comment at the top of the file explicitly stating this is reference documentation of the schema the pipeline scripts create, not a script meant to be run as a setup step — and specifically that the Bronze/Silver sections are safe to run standalone if desired, but the Gold section is intentionally commented out and must never be uncommented and run before create_gold_tables.py has established the real column types.
   - Include the ASSUMPTION comments on Gold's computed decimal columns as specified above, inside the commented-out block.

2. `database/seed-data-notes.md` — documents how the seed CSVs map onto the Bronze schema (distinct scope from src/data_generation/DATA_GENERATION_NOTES.md, which already covers WHY each quality issue exists — do not duplicate that content here).
   - A table per source file (customers.csv/orders.csv/products.csv): column name, Bronze column type, source row count.
   - Note the fixed random seed (42) used in generate_sample_data.py makes the seed data fully reproducible.
   - Note where the seed CSVs land before Bronze ingestion: /Volumes/workspace/default/raw_data/*.csv (Unity Catalog Volume, not a DBFS mount path).
   - Cross-reference (link, don't repeat) DATA_GENERATION_NOTES.md for the intentional data-quality-issue rationale.

3. `database/setup-notes.md` — step-by-step instructions to stand up the data layer from scratch, narrower in scope than the top-level README.md (which will additionally cover Dashboard/account setup) — focus ONLY on getting the 10 tables populated and queryable:
   a. Run `python src/data_generation/generate_sample_data.py` locally to produce the 3 seed CSVs (customers.csv, orders.csv, products.csv) in the repo-root `data/` folder. Skip this step if the CSVs already exist and you want to keep the existing seed data unchanged (the fixed random seed makes re-running it produce identical output anyway).
   b. Prerequisite: the `workspace` catalog, `default` schema, AND the `/Volumes/workspace/default/raw_data/` Unity Catalog Volume must all already exist (create the Volume via Catalog Explorer if it does not — this project does not create or alter the catalog, schema, or Volume programmatically anywhere in its scripts).
   c. Upload the 3 seed CSVs from the local `data/` folder to the Unity Catalog Volume path /Volumes/workspace/default/raw_data/.
   d. Run `src/bronze/ingest_all.py` (creates the 3 Bronze tables).
   e. Run `src/silver/create_silver_tables.py` (creates the 3 Silver tables, depends on Bronze existing).
   f. Run `src/gold/create_gold_tables.py` (creates the 4 Gold tables, depends on Silver existing).
   g. Optionally run `tests/run_all_tests.py` to verify the whole pipeline end-to-end (note: this re-runs steps d-f as part of the integration test tier).
   h. Note that `database/schema.sql` is a reference for what these steps produce, not an alternative or additional setup step.

HARD RULES:
- Do not write any code that actually executes schema.sql — it is documentation only.
- Do not add NOT NULL constraints on any column in schema.sql. The data intentionally contains NULLs in email/customer_id/product_id as injected quality issues — a NOT NULL constraint would misrepresent the real data shape, and if the Bronze/Silver sections were ever actually run before ingestion, it could cause inserts of legitimately-null data to fail.
- Do not declare PRIMARY KEY or FOREIGN KEY constraints (enforced or informational) on any table in schema.sql. The data intentionally contains duplicate customer_id/order_id values and orphaned FK references as injected quality issues — declaring these constraints would be factually incorrect documentation of what the tables actually contain.
- Do not duplicate DATA_GENERATION_NOTES.md's content in seed-data-notes.md — link/reference it instead.
- Do not restate the full pipeline logic in setup-notes.md — reference the script names and what they do in one line each, not their internals.
- Use `-- ASSUMPTION:` (SQL) or `<!-- ASSUMPTION: -->`/plain-text `ASSUMPTION:` (Markdown) comments only for judgment calls not already resolved by this prompt.

Do not touch any other files.

**Result:** Accepted on first generation, no fix-iteration needed. Code
review confirmed all 3 files matched the prompt exactly: Bronze/Silver DDL
byte-for-byte matches the actual ingestion script schemas, the entire Gold
section is genuinely commented out with the ASSUMPTION notes inline, no
NOT NULL or PK/FK constraints anywhere, and setup-notes.md correctly
includes both the data-generation step and the Volume prerequisite added
during hardening.

## Validation
Read all 3 files directly from the repo and cross-checked column-by-column
against the actual pipeline scripts (not just against the prompt text):
- `schema.sql` Bronze/Silver DDL confirmed to match
  `src/bronze/01_ingest_customers.py` / `02_ingest_orders.py` /
  `03_ingest_products.py`'s literal schema strings exactly, including
  column order.
- `quality_check_result STRING` confirmed appended as the last column on
  all 3 Silver tables, matching `create_silver_tables.py`'s actual output
  schema.
- Gold section confirmed fully commented out (every line prefixed `--`),
  with the exact ASSUMPTION wording specified.
- `seed-data-notes.md` confirmed to link to (not duplicate)
  `DATA_GENERATION_NOTES.md`, with correct row counts and Volume path.
- `setup-notes.md` confirmed to include the Volume-creation prerequisite
  and the `generate_sample_data.py` step from the hardening passes, and to
  correctly frame `schema.sql` as reference-only throughout.

This is a documentation-only artifact with no executable pipeline logic
of its own, so validation here means static cross-referencing against the
real code (confirming the documented schema is accurate), rather than
running anything new in Databricks.

## Root cause / lesson
The most valuable review pass wasn't confirming the known Bronze/Silver
schemas were copied correctly — it was recognizing that Gold's computed
column types are fundamentally *unknowable* without live introspection,
and that presenting a guess as executable, run-safe DDL in a supposedly
authoritative "database schema" document would have been actively
misleading, not just imprecise. Treating "I don't actually know this
exactly" as a reason to change the *shape* of the artifact (commented
reference vs. real DDL) rather than just adding a disclaimer, produced a
more honest and safer final document for the same prompt-writing effort.

## Status: ACCEPTED (1 code session, 0 fix-iterations, all 3 files verified column-by-column against the real pipeline scripts)
