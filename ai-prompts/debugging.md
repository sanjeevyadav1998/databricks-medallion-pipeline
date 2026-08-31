# AI Prompts — Debugging (Test Suite, Task 9)

Per task-breakdown.md, Task 9 (test suite) logs here rather than a
separate ai-prompts/tests.md file, since only the 7 activity files named
in the exercise brief's required structure exist.

## Session 1 — Design decisions locked before drafting
**Tool / mode:** Claude (spec drafting), not yet sent to Cursor.
Task 9 was the one genuinely open design question left in the whole
project — task-breakdown.md had flagged the test location as "TBD" since
the exercise brief's required repository structure has no tests/ folder
listed anywhere, only "at least one meaningful test tier (data quality
tests, pipeline tests)" as a checklist requirement with no location or
framework specified. Locked three decisions before drafting the prompt:
1. **Location:** `tests/` at repo root, sibling to `src/` — not in the
   required file tree, but the brief says "follow this structure as
   closely as possible," not exclusively, so adding a conventional
   top-level folder for a required-but-unspecified artifact doesn't
   violate anything.
2. **Framework:** no pytest — plain `.py` scripts using `assert`,
   runnable via `runpy` with an injected `spark` session, matching every
   other script in the repo (Bronze/Silver/Gold all use this exact
   pattern already). Introducing pytest would mean a new dependency and a
   different invocation model (command-line `pytest`, not a notebook cell)
   inconsistent with everything else built so far.
3. **Scope:** both tiers the brief names — data quality tests (re-verify
   the 7 injected-issue counts, formalized as assertions rather than just
   printed report comparisons) and pipeline integration tests (Bronze →
   Silver → Gold end-to-end, asserting no exceptions and expected row
   counts at each stage).

## Session 2 — Pre-emptive hardening (2 review passes before running)
Reviewed the prompt twice before sending it to Cursor:

**Pass 1 — 3 gaps found:**
1. No input-validation/error-handling for missing Silver tables — a test
   run before Silver ever materializes would throw a raw, unhelpful Spark
   "table not found" exception. Fixed by requiring a try/except around
   each `spark.read.table(...)` call that re-raises a clear, actionable
   message naming which script to run first. This also directly
   demonstrates the brief's separately-graded checklist item "Input
   validation and error handling."
2. No warning that the integration test overwrites live tables — since
   `test_pipeline_integration.py` re-runs Bronze/Silver/Gold, it silently
   overwrites the exact `workspace.default.*` tables backing the already-
   published Dashboard. Fixed by requiring an explicit printed warning
   before any pipeline stage runs (safe/idempotent given the fixed random
   seed, but a real side effect worth surfacing, not hiding).
3. Inefficient row-count retrieval — left unspecified, Cursor could have
   re-queried tables via `spark.read.table(...).count()` immediately after
   writing them, when each orchestrator (`ingest_all`, `create_silver_
   tables`, `create_gold_tables`) already returns row counts or DataFrames
   directly. Fixed by requiring reuse of each stage's own return value.

**Pass 2 — 2 additional regression-invariant checks added:**
4. Nothing protected the "skip NULL FKs in referential integrity" fix from
   Silver (the hardening fix that prevented NULL-customer_id rows from
   being double-counted as orphans). Added an explicit assertion that zero
   rows in silver_orders carry BOTH `FAIL_NULL_CUSTOMER_ID` and
   `FAIL_ORPHAN_CUSTOMER_ID` simultaneously (and the same pair for
   product_id) — this protects the actual design invariant, not just a
   count that happens to be correct today.
5. Nothing protected Gold's LEFT JOIN correctness structurally — only the
   raw Gold row counts were checked. Added an assertion that
   `SUM(customer_count)` across all 4 `gold_customer_segmentation` rows
   equals the Silver PASSED customer count exactly — a structural
   invariant that would catch a future regression (e.g. the join
   silently dropping or duplicating customers) even if the sample data
   were regenerated with different absolute figures.

## Session 3 — Final prompt sent to Cursor
**Tool / mode:** Cursor, Agent mode.

**Prompt (verbatim):**

Write the test suite for this project per .cursorrules layer boundaries. Databricks PySpark, for a notebook (Free Edition, serverless compute, Unity Catalog three-level namespace: catalog.schema.table). No pytest — match the existing repo pattern: standalone .py scripts using `assert`, runnable via runpy with an injected `spark` session, same as src/bronze/ingest_all.py and src/silver/create_silver_tables.py.

TARGET DIRECTORY (does not exist yet, not in the doc's required file tree, but a required "at least one meaningful test tier" per the exercise brief — create it fresh):
- tests/

SOURCE TABLES (read-only — this suite does not write any table itself, though the integration test invokes the existing pipeline scripts which do):
- workspace.default.bronze_customers / bronze_orders / bronze_products
- workspace.default.silver_customers / silver_orders / silver_products
- workspace.default.gold_sales_by_product / gold_revenue_by_customer / gold_daily_weekly_trends / gold_customer_segmentation

KNOWN GROUND-TRUTH VALUES (from generate_sample_data.py's fixed seed — these are deterministic and reproducible on every regeneration, use them as hardcoded expected values, not approximations):
- Row counts: customers.csv 10,000 / orders.csv 100,000 / products.csv 500
- Injected issue counts: 50 NULL email, 10 duplicate customer_id (customers); 100 NULL customer_id, 200 NULL product_id, 50 orphan customer_id, 30 orphan product_id, 20 duplicate order_id (orders)
- Silver PASSED counts (derived): silver_customers 9,940/10,000 passed; silver_products 500/500 passed
- Gold row counts (derived): gold_sales_by_product 500 rows; gold_revenue_by_customer 9,940 rows; gold_customer_segmentation exactly 4 rows (segment_type values High-Value/Repeat/One-Time/Inactive)

FILES TO CREATE:

1. `tests/test_data_quality.py` — Data quality test tier.
   - Exposes a function `test_silver_quality_checks(spark)` that:
     a. Reads `workspace.default.silver_customers`, `workspace.default.silver_orders`, `workspace.default.silver_products` directly via `spark.read.table(...)` (does NOT call create_silver_tables again — assumes Silver already ran; this test validates the materialized Silver output, not the pipeline execution).
     a2. INPUT VALIDATION: wrap each `spark.read.table(...)` call in a try/except `AnalysisException` (or catch a broad exception if the specific type isn't reliably importable), and re-raise a clear, actionable error such as "Silver table 'workspace.default.silver_customers' not found — run src/silver/create_silver_tables.py first." Do not let a missing-table error surface as a raw Spark stack trace with no guidance.
     b. Asserts each of the 7 known injected-issue counts is caught EXACTLY (not approximately) by counting rows where `quality_check_result` contains the matching failure code string: `FAIL_NULL_EMAIL` = 50, `FAIL_DUPLICATE_CUSTOMER_ID` = 10, `FAIL_NULL_CUSTOMER_ID` = 100, `FAIL_NULL_PRODUCT_ID` = 200, `FAIL_ORPHAN_CUSTOMER_ID` = 50, `FAIL_ORPHAN_PRODUCT_ID` = 30, `FAIL_DUPLICATE_ORDER_ID` = 20.
     b2. Asserts total row counts are preserved (Silver drops nothing): silver_customers = 10,000 rows, silver_orders = 100,000 rows, silver_products = 500 rows.
     b3. REGRESSION CHECK (protects the NULL-vs-orphan hardening fix): asserts ZERO rows in silver_orders have BOTH `FAIL_NULL_CUSTOMER_ID` AND `FAIL_ORPHAN_CUSTOMER_ID` in quality_check_result simultaneously (and separately, zero rows with BOTH `FAIL_NULL_PRODUCT_ID` AND `FAIL_ORPHAN_PRODUCT_ID`). This protects against a future regression where referential-integrity checks stop excluding NULL foreign keys and start double-counting them as orphans.
     b4. REGRESSION CHECK: asserts silver_products has zero rows with any FAIL_* code in quality_check_result (i.e., 500/500 rows = 'PASSED' exactly) — no quality issues were intentionally injected into products.csv, so any failure here indicates an unexpected schema or generation change worth investigating.
     c. Asserts `quality_check_result` is never NULL or an empty string for any row in any of the 3 Silver tables (every row must resolve to either 'PASSED' or a pipe-delimited failure list).
     d. On any assertion failure, raise a clear `AssertionError` with the expected vs. actual counts in the message (not just "assert failed") so a failing test is immediately diagnosable.
     e. On success, PRINT a "PASS" line per check with expected/actual values shown, plus a final "ALL DATA QUALITY CHECKS PASSED" line.
   - `if __name__ == "__main__": test_silver_quality_checks(spark)`.

2. `tests/test_pipeline_integration.py` — Pipeline integration test tier.
   - Exposes a function `test_pipeline_end_to_end(spark)` that:
     a0. WARNING: before doing anything else, PRINT an explicit warning that this test re-runs the full pipeline and will OVERWRITE the live workspace.default.bronze_*/silver_*/gold_* tables (the same tables backing the published Dashboard) — this is safe/idempotent given the fixed random seed in generate_sample_data.py, but is a real side effect the caller should be aware of, not a silent mutation.
     a. Dynamically imports and calls, IN SEQUENCE, the three existing orchestrators using the same `importlib.util.spec_from_file_location` pattern already used in create_silver_tables.py / create_gold_tables.py (do not reinvent a different import mechanism): `src/bronze/ingest_all.py` → `ingest_all(spark)`, `src/silver/create_silver_tables.py` → `create_silver_tables(spark)`, `src/gold/create_gold_tables.py` → `create_gold_tables(spark)`.
     a1. EFFICIENT ROW COUNTS: `ingest_all(spark)` already returns a list of dicts containing `row_count` per table — use those values directly rather than re-querying via `spark.read.table(...).count()`. `create_silver_tables(spark)` and `create_gold_tables(spark)` return dicts of `{table_name: DataFrame}` — call `.count()` on those returned DataFrames directly rather than a fresh `spark.read.table()` call, since the DataFrame is already in hand from the return value.
     b. After each stage, asserts the row counts match the known ground-truth values above (Bronze: 10,000/100,000/500; Silver: 10,000/100,000/500 preserved; Gold: 500/9,940/974/4 — for the Gold daily/weekly trend row count, assert it is > 0 and treat the exact 974 figure as informational/logged rather than a hard assertion, since that count depends on the sample data's date range rather than an injected-issue spec value).
     c. Asserts no exception propagates from any of the three stage calls — if one raises, let it propagate up so the test script fails loudly rather than being silently swallowed.
     d. PRINTs a per-stage "PASS" summary (stage name, row count, expected) and a final "PIPELINE INTEGRATION TEST PASSED" line.
     e. REGRESSION CHECK (protects Gold's LEFT JOIN correctness structurally, not via a hardcoded magic number): asserts that SUM(customer_count) across all 4 rows of gold_customer_segmentation equals the total row count of silver_customers where quality_check_result = 'PASSED'. This catches a regression where the Gold segmentation join silently drops or duplicates customers, even if the sample data is regenerated with different absolute figures in the future.
   - Resolve the three script paths the same way SILVER_DIR/BRONZE_DIR/GOLD_DIR do in the existing orchestrators — relative to this test file's own location via `Path(__file__).resolve().parent.parent`, not a hardcoded Databricks Repos path.
   - `if __name__ == "__main__": test_pipeline_end_to_end(spark)`.

3. `tests/run_all_tests.py` — Test suite orchestrator, mirrors the style of `src/bronze/ingest_all.py` and `src/silver/create_silver_tables.py`.
   - Dynamically imports both test modules above (same importlib pattern).
   - Runs `test_silver_quality_checks(spark)` then `test_pipeline_end_to_end(spark)`, in that order (data quality first since it's cheaper/faster; integration test re-runs the whole pipeline and is more expensive).
   - Wraps each in a try/except so BOTH tests run and report even if one fails first — do not let the first test's failure hide whether the second one would have passed. Collect pass/fail per test.
   - PRINTs a final summary table: Test Name | Status (PASS/FAIL) | Notes.
   - Exits/returns a nonzero-equivalent signal (e.g. raise a final AssertionError summarizing which tests failed) if ANY test failed, so this can be used as a real pass/fail gate, not just informational output.
   - `if __name__ == "__main__": run_all_tests(spark)`.

HARD RULES:
- No pytest, no new dependencies — plain Python + PySpark only, matching every other script in this repo.
- test_data_quality.py must NOT call create_silver_tables again — it reads the already-materialized Silver tables only, so it tests the actual persisted output, not a fresh in-memory recomputation that could mask a write-time bug.
- test_data_quality.py must catch missing-table errors and re-raise them with an actionable message (which script to run first) — never let a raw "table or view not found" Spark exception be the only signal.
- test_pipeline_integration.py DOES re-run the full pipeline (Bronze, Silver, Gold orchestrators) since that's what "integration" means here — do not skip stages or read pre-existing tables instead.
- test_pipeline_integration.py must print the live-table-overwrite warning before running any pipeline stage.
- Every assertion failure message must include both the expected and actual value — never a bare `assert condition` with no message.
- Every function needs a docstring.
- Use `# ASSUMPTION:` comments only for judgment calls not covered by this prompt.

Do not touch any other files.

**Result:** Accepted on first generation, no fix-iteration needed. Code
review confirmed all 3 files matched the prompt exactly, including a
nice unrequested touch — `run_all_tests.py` calls `traceback.print_exc()`
on a failing test before continuing, giving full stack-trace visibility
without needing to re-run a failing test in isolation.

## Validation
Ran `tests/run_all_tests.py` in Databricks (serverless compute) via the
same `runpy` invocation pattern used for every other layer. Both tiers
passed on the first execution:

**Data quality tier (17 assertions, all PASS):**
- All 7 injected-issue counts exact (50/10/100/200/50/30/20).
- Row preservation exact (10,000/100,000/500).
- Both regression guards clean: zero NULL+orphan overlap on customer_id
  and product_id; silver_products 500/500 PASSED with zero FAIL_* codes.
- `quality_check_result` never NULL/empty across all 3 tables.

**Pipeline integration tier — a genuine reproducibility test, not just a
smoke test:** this re-ran the entire pipeline from scratch (Bronze →
Silver → Gold), and every figure matched the original manual validation
runs exactly, including the same top-3 preview rows in Gold (e.g.
"Deluxe Backpack 469" / "Lucas Dubois" appearing in the same rank
position with the same revenue figures). This confirms the fixed random
seed in generate_sample_data.py produces fully deterministic output
end-to-end, not just at the data-generation step — an unplanned but
valuable confirmation beyond what the test was originally designed to
prove.
- Bronze: 10,000/100,000/500 — PASS.
- Silver: 10,000/100,000/500 preserved, same issue breakdown as every
  prior run — PASS.
- Gold: 500/9,940/974(informational)/4 — PASS.
- Segmentation regression: SUM(customer_count) = 9,940 = silver_customers
  PASSED — PASS.

**Final summary:** `test_silver_quality_checks` PASS, `test_pipeline_end_to_end` PASS.

## Root cause / lesson
The two most valuable checks in this suite weren't the ones re-confirming
already-known numbers — they were the two regression-invariant checks
(NULL-vs-orphan mutual exclusivity, Gold segmentation sum) added in the
second hardening pass, since those are the only assertions that would
actually catch someone re-introducing a previously-fixed bug months later,
rather than just re-proving today's numbers are still today's numbers.
Treating the test suite as "what would catch a regression of a bug we
already found," not just "re-run everything and check nothing crashed,"
produced a meaningfully stronger test tier for the same amount of Cursor
budget.

## Status: ACCEPTED (1 code session, 0 fix-iterations, both test tiers verified passing, full pipeline reproducibility confirmed as an unplanned bonus finding)
