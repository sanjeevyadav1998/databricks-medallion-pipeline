# AI Prompts — Silver Layer

## Session 1 — Style mismatch, corrected before sending
**Tool / mode:** Claude (spec drafting), not yet sent to Cursor.
First draft targeted a local/pandas dual-run execution model (CSV folder
paths, Pandas/PySpark fallback), which didn't match the Databricks Unity
Catalog pattern already established in Bronze (`workspace.default.bronze_*`
tables, `spark.read.table(...)` / `saveAsTable(...)`). Caught and rewritten
before ever reaching Cursor, to match Bronze's exact prompt template:
SOURCE TABLES / TARGET TABLES / READ PATTERN / WRITE PATTERN / FILES TO
CREATE / HARD RULES sections.

## Session 2 — Pre-emptive hardening (before running, not after failing)
Before sending anything to Cursor, walked through the Silver logic for
latent PySpark bugs specific to this dataset's known injected-issue shape,
and patched the prompt proactively instead of discovering them via a failed
run:

1. **Numeric-prefix import trap** — fixed by requiring `importlib.util`.
2. **Orphan vs. NULL FK double-counting** — fixed by requiring the
   referential check to only evaluate non-null FK values.
3. **Join row-explosion** — fixed by requiring joins against
   `.select(...).distinct()` parent keys.
4. **Empty-string vs. 'PASSED' fallback** — fixed by requiring explicit
   empty/whitespace/NULL → `'PASSED'` mapping.
5. **NULL-unsafe business logic** — fixed by requiring all business-rule
   inputs to be non-null before evaluating.

## Session 3 — Final prompt sent to Cursor
**Tool / mode:** Cursor, Agent mode.

**Prompt (verbatim):**

Write the Silver layer quality validation scripts and table creation pipeline per tool-specific/cursor-workflow/spec.md section 3 and .cursorrules layer boundaries. Databricks PySpark, for a notebook (Free Edition, serverless compute, Unity Catalog three-level namespace: catalog.schema.table).

SOURCE TABLES (workspace.default — read directly via Spark):
- workspace.default.bronze_customers
- workspace.default.bronze_orders
- workspace.default.bronze_products

TARGET TABLES (catalog "workspace", schema "default" — do NOT create or alter catalog/schema):
- workspace.default.silver_customers
- workspace.default.silver_orders
- workspace.default.silver_products

READ PATTERN — use exactly this for all inputs:
df = spark.read.table("workspace.default.bronze_<entity>")

WRITE PATTERN — use exactly this for all Silver tables:
df.write.format("delta").mode("overwrite").saveAsTable("workspace.default.silver_<entity>")

EXACT COLUMN ADDITION TO ALL SILVER TABLES:
Every Silver table must include all original Bronze columns PLUS exactly one new column appended at the end:
`quality_check_result` (STRING)

VALUE CONVENTION FOR `quality_check_result`:
- Set to `'PASSED'` if the row satisfies all quality checks.
- If one or more checks fail, set to a pipe-delimited string of failure codes (e.g., `'FAIL_NULL_EMAIL'`, `'FAIL_DUPLICATE_ID'`, or `'FAIL_NULL_CUSTOMER_ID|FAIL_ORPHAN_CUSTOMER_ID'`).

FILES TO CREATE:

1. `src/silver/01_quality_completeness.py` — Exposes functions/expressions to check for NULL values in critical fields (`email` in customers; `customer_id` and `product_id` in orders). Assigns failure code `'FAIL_NULL_EMAIL'`, `'FAIL_NULL_CUSTOMER_ID'`, or `'FAIL_NULL_PRODUCT_ID'`.

2. `src/silver/02_quality_uniqueness.py` — Exposes functions to detect duplicate primary keys (`customer_id` in customers; `order_id` in orders). Assigns failure code `'FAIL_DUPLICATE_CUSTOMER_ID'` or `'FAIL_DUPLICATE_ORDER_ID'`.

3. `src/silver/03_quality_type_validation.py` — Exposes functions to validate data formats (e.g., valid email format containing `@`, valid date ranges). Assigns failure code `'FAIL_INVALID_EMAIL_FORMAT'` or `'FAIL_INVALID_DATE'`.

4. `src/silver/04_quality_referential_integrity.py` — Exposes functions taking `orders`, `customers`, and `products` DataFrames to verify foreign key existence. Assigns failure code `'FAIL_ORPHAN_CUSTOMER_ID'` or `'FAIL_ORPHAN_PRODUCT_ID'`.

5. `src/silver/05_quality_business_logic.py` — Exposes domain validation rules (`total_amount ≈ quantity * unit_price` within 0.01 margin, `quantity > 0`, `price >= cost`). Assigns failure code `'FAIL_CALCULATION_MISMATCH'` or `'FAIL_INVALID_QUANTITY'`.

6. `src/silver/create_silver_tables.py` — Main entry point script.
   - IMPORTS NOTE: Because module filenames start with numbers (e.g., `01_...`), use `importlib.util.spec_from_file_location()` or append `src/silver` to `sys.path` to dynamically import modules `01` through `05` without syntax errors.
   - Reads Bronze tables using the exact READ PATTERN.
   - Runs modules `01` through `05` sequentially to construct the consolidated `quality_check_result` column for `silver_customers`, `silver_orders`, and `silver_products`.
   - Writes all three Silver tables using the exact WRITE PATTERN.
   - Calculates and PRINTs a Data Quality Metrics Report formatted as a clean text table showing:
     Table Name | Total Rows | Rows Passed | % Passed | Total Issues Injected/Caught | Breakdown per Check Code

HARD RULES:
- NEVER DELETE OR DROP BAD ROWS. Every row from Bronze must be written to Silver with its evaluated `quality_check_result` status.
- No schema changes to original columns — only append `quality_check_result STRING`.
- PREVENT JOIN ROW-EXPLOSION: In `04_quality_referential_integrity.py`, always join `orders` against distinct parent key DataFrames (`customers.select("customer_id").distinct()` and `products.select("product_id").distinct()`) so duplicate keys in parent tables do not duplicate rows in `orders`.
- SKIP NULL FKS IN REFERENTIAL INTEGRITY: In `04_quality_referential_integrity.py`, evaluate referential integrity only on non-null foreign key values so missing fields are caught by completeness and not double-counted as orphan records.
- FLAG CONCATENATION FALLBACK: Ensure `quality_check_result` explicitly evaluates to `'PASSED'` whenever no failure flags are generated (e.g., when the concatenated flag string is empty, whitespace, or NULL).
- NULL SAFETY IN BUSINESS LOGIC: In `05_quality_business_logic.py`, ensure calculations (e.g., `total_amount ≈ quantity * unit_price`) handle NULL inputs gracefully so missing values are not misflagged as calculation mismatches.
- Each script must be runnable in a Databricks notebook cell using the active `spark` session.
- Every function needs a docstring explaining the check logic and flag assigned.
- Target issue counts to catch and report:
  * customers: exactly 50 NULL emails, 10 duplicate customer_ids
  * orders: exactly 100 NULL customer_ids, 200 NULL product_ids, 50 orphaned customer_ids, 30 orphaned product_ids, 20 duplicate order_ids
- Use `# ASSUMPTION:` comments only if something arises not covered by this prompt.

Do not touch any other files.

**Result:** Accepted on first generation, no fix-iteration needed. Code
review confirmed all 5 hardening requirements were correctly implemented,
plus every Bronze row preserved in Silver with no drops.

## Validation
Ran `create_silver_tables(spark)` in Databricks (serverless compute) via
`runpy`. Printed Data Quality Metrics Report matched all 7 injected-issue
target counts exactly:

| Check | Caught | Expected | Result |
|---|---|---|---|
| FAIL_NULL_EMAIL (customers) | 50 | 50 | OK |
| FAIL_DUPLICATE_CUSTOMER_ID (customers) | 10 | 10 | OK |
| FAIL_NULL_CUSTOMER_ID (orders) | 100 | 100 | OK |
| FAIL_NULL_PRODUCT_ID (orders) | 200 | 200 | OK |
| FAIL_ORPHAN_CUSTOMER_ID (orders) | 50 | 50 | OK |
| FAIL_ORPHAN_PRODUCT_ID (orders) | 30 | 30 | OK |
| FAIL_DUPLICATE_ORDER_ID (orders) | 20 | 20 | OK |

`silver_products`: 500/500 rows passed (100%), no injected issues targeted
there. Row counts preserved exactly: 10,000 / 100,000 / 500 in, same
counts out.

## Root cause / lesson
Pre-empting known PySpark join/null-handling failure modes before writing
the final prompt avoided burning a second Cursor session on Silver — the
entire layer passed in one Agent-mode generation.

## Status: ACCEPTED (1 code session, 0 fix-iterations, all 7 target counts verified exact)
