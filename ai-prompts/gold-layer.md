# AI Prompts — Gold Layer

## Session 1 — Initial draft assembled from design decisions
**Tool / mode:** Claude (spec drafting), not yet sent to Cursor.
Locked several judgment calls before drafting the prompt, since the source
requirements don't specify them: which Silver rows feed Gold (PASSED only,
both sides of any join), which order_status counts toward revenue
(Completed only), how to define the four customer segmentation tiers
(High-Value/Repeat/One-Time/Inactive — new derived tiers, not the existing
customer_segment column), and how create_gold_tables.py should relate to
the .sql files (.sql files hold the real queries, .py orchestrates and
executes them via spark.sql(), matching the Silver orchestrator's own
pattern).

## Session 2 — Pre-emptive hardening (before running, not after failing)
Before sending the prompt to Cursor, walked through the SQL logic for
bugs specific to this dataset's shape (still-present flagged/duplicate
rows in Silver, zero-activity products/customers that must not be
silently dropped):

1. **LEFT JOIN silently becoming an INNER JOIN** — if quality_check_result
   or order_status filters are applied in a WHERE clause after a LEFT JOIN
   instead of inside a pre-join CTE, NULL rows from the LEFT JOIN (for
   zero-activity products/customers) get filtered out by
   `NULL = 'PASSED'` evaluating to NULL/false, defeating the entire
   purpose of the LEFT JOIN. Fixed by mandating a pre-filter CTE pattern
   (passed_parent / passed_orders) for every join, with all filtering
   happening inside the CTEs, never in a post-join WHERE.
2. **SUM() returns NULL, not 0, for zero-match LEFT JOIN rows** — a
   zero-order product's SUM(total_amount) would show NULL instead of the
   spec's required 0.00. Fixed by requiring COALESCE(SUM(...), 0)
   everywhere.
3. **Percentile threshold diluted by zero-revenue customers** — computing
   PERCENTILE_CONT(0.8) over all customers (including Inactive/zero-order
   ones) would drag the High-Value cutoff down artificially. Fixed by
   requiring the percentile to be computed only over customers with
   total_orders > 0, while still assigning/outputting the Inactive segment
   for zero-order customers in the final result.

## Session 3 — Final prompt sent to Cursor
**Tool / mode:** Cursor, Agent mode.

**Prompt (verbatim):**

Write the Gold layer aggregation queries and table creation pipeline per tool-specific/cursor-workflow/spec.md section 4 and .cursorrules layer boundaries. Databricks PySpark, for a notebook (Free Edition, serverless compute, Unity Catalog three-level namespace: catalog.schema.table).

SOURCE TABLES (workspace.default — read directly via Spark SQL):
- workspace.default.silver_customers
- workspace.default.silver_orders
- workspace.default.silver_products

TARGET TABLES (catalog "workspace", schema "default" — do NOT create or alter catalog/schema):
- workspace.default.gold_sales_by_product
- workspace.default.gold_revenue_by_customer
- workspace.default.gold_daily_weekly_trends
- workspace.default.gold_customer_segmentation

READ PATTERN — every .sql file's FROM clause references Silver tables directly by full name (e.g. FROM workspace.default.silver_orders). No spark.read.table() calls inside the .sql files themselves — create_gold_tables.py loads each .sql file's text and executes it with spark.sql(query_text).

WRITE PATTERN — use exactly this for all Gold tables, from create_gold_tables.py:
result_df.write.format("delta").mode("overwrite").saveAsTable("workspace.default.gold_<name>")

GLOBAL FILTERING RULE — applies to every query below:
- Only rows with quality_check_result = 'PASSED' from Silver may participate, on BOTH sides of any join (parent and child) — filter before joining, not after, since duplicate-flagged rows are still physically present in Silver (flagged, not deleted) and would re-explode a join if left unfiltered on either side.
- Only orders with order_status = 'Completed' count toward revenue/order metrics in every query below (Pending isn't realized revenue, Cancelled is reversed). Add a "-- ASSUMPTION:" SQL comment noting this filter, since it is not explicitly specified in the source requirements.

MANDATORY CTE PATTERN for queries 1, 2, and 4 (prevents a LEFT JOIN silently becoming an INNER JOIN, and prevents ambiguous quality_check_result column errors when both tables being joined have a column with that same name):

  WITH passed_parent AS (
    SELECT * FROM workspace.default.silver_<products|customers>
    WHERE quality_check_result = 'PASSED'
  ),
  passed_orders AS (
    SELECT * FROM workspace.default.silver_orders
    WHERE quality_check_result = 'PASSED' AND order_status = 'Completed'
  )
  SELECT ...
  FROM passed_parent p
  LEFT JOIN passed_orders o ON p.<key> = o.<key>
  GROUP BY ...

Filtering must happen INSIDE each CTE, never in a WHERE clause applied after the LEFT JOIN — a post-join WHERE on o.quality_check_result or o.order_status would silently drop every zero-activity row (NULL = 'PASSED' evaluates to NULL/false) and turn the LEFT JOIN into an INNER JOIN, defeating the entire purpose of including zero-activity products/customers.

FILES TO CREATE:

1. src/gold/01_sales_by_product.sql — Aggregation "Sales by Product". Columns: product_id, product_name, category, total_orders, total_revenue, avg_order_value.
   - Use the mandatory CTE pattern: passed_parent = silver_products (PASSED only), passed_orders = silver_orders (PASSED + Completed only).
   - LEFT JOIN passed_parent to passed_orders on product_id, so products with zero completed orders still appear.
   - total_orders = COUNT(o.order_id) (correctly returns 0 for no match).
   - total_revenue = COALESCE(SUM(o.total_amount), 0) — SUM returns NULL, not 0, for zero-match rows after a LEFT JOIN, so this must be explicit.
   - avg_order_value = total_revenue / NULLIF(total_orders, 0) — NULL when zero orders, not a divide-by-zero error.
   - Round total_revenue and avg_order_value to 2 decimal places.

2. src/gold/02_revenue_by_customer.sql — Aggregation "Revenue by Customer". Columns: customer_id, customer_name, customer_segment, total_orders, total_revenue, avg_order_value, lifetime_value_actual.
   - Use the mandatory CTE pattern: passed_parent = silver_customers (PASSED only), passed_orders = silver_orders (PASSED + Completed only).
   - LEFT JOIN passed_parent to passed_orders on customer_id, so customers with zero completed orders still appear.
   - total_orders = COUNT(o.order_id).
   - total_revenue = COALESCE(SUM(o.total_amount), 0).
   - lifetime_value_actual = COALESCE(SUM(o.total_amount), 0) recomputed from actual Completed orders — distinct from the customers.lifetime_value input column, which is a separate existing field, left untouched.
   - avg_order_value = total_revenue / NULLIF(total_orders, 0).
   - Round total_revenue, avg_order_value, lifetime_value_actual to 2 decimal places.

3. src/gold/03_daily_weekly_trends.sql — Time-series trend view. Columns: order_date, order_week (Monday-start week, via date_trunc('week', order_date)), total_orders, total_revenue.
   - FROM a single filtered CTE: silver_orders WHERE quality_check_result = 'PASSED' AND order_status = 'Completed'. No join needed against customers/products, so the LEFT JOIN pattern above does not apply here.
   - GROUP BY order_date, order_week.
   - total_orders = COUNT(order_id), total_revenue = COALESCE(SUM(total_amount), 0).
   - Round total_revenue to 2 decimal places.
   - ASSUMPTION: grain is one row per calendar day, with an order_week column included so the same table supports both daily and weekly rollups in the dashboard (weekly = GROUP BY order_week on top of this table).

4. src/gold/04_customer_segmentation.sql — Aggregation "Customer Segmentation". Columns: segment_type, customer_count, avg_revenue, total_revenue.
   - Base CTE (per_customer): use the mandatory CTE pattern — passed_parent = silver_customers (PASSED only) LEFT JOIN passed_orders = silver_orders (PASSED + Completed only) on customer_id, GROUP BY customer_id to get each customer's total_orders (COUNT(o.order_id)) and total_revenue (COALESCE(SUM(o.total_amount), 0)).
   - Percentile CTE: compute PERCENTILE_CONT(0.8) WITHIN GROUP (ORDER BY total_revenue) ONLY over rows from per_customer WHERE total_orders > 0 — do NOT include zero-order customers in this calculation, since a mass of zero-revenue Inactive customers would artificially drag the High-Value threshold down. Inactive customers are still included in the final segment_type assignment/output — only the percentile calculation itself excludes them.
   - Assign segment_type per customer using this exact priority order (first match wins):
     1. 'High-Value' — total_revenue >= the 80th percentile threshold
     2. 'Repeat' — total_orders >= 2
     3. 'One-Time' — total_orders = 1
     4. 'Inactive' — total_orders = 0
   - Final SELECT groups by segment_type: customer_count = COUNT(*), avg_revenue = AVG(total_revenue), total_revenue = SUM(total_revenue).
   - Round avg_revenue and total_revenue to 2 decimal places.
   - ASSUMPTION: 80th percentile chosen as the High-Value cutoff since no fixed threshold was specified in the source requirements; note this clearly so it's easy to tune later.

5. src/gold/create_gold_tables.py — Main entry point script.
   - Reads each .sql file's text from disk relative to this script's own directory, using Path(__file__).resolve().parent — do NOT hardcode a Databricks Repos path (same pattern as SILVER_DIR/BRONZE_DIR in the existing Silver/Bronze orchestrators).
   - Executes each query via spark.sql(query_text) to produce a DataFrame.
   - Writes each result to its target Gold table using the exact WRITE PATTERN above.
   - After writing, PRINTs a summary table showing: Gold Table Name | Row Count | top 3 rows by total_revenue (or by customer_count for the segmentation table).
   - Every function needs a docstring.

HARD RULES:
- Every Gold table must be built ONLY from Silver rows where quality_check_result = 'PASSED' (filtered inside a CTE on both sides of any join, never via a post-join WHERE clause), and ONLY from orders where order_status = 'Completed'.
- Use LEFT JOIN (not INNER JOIN) from the parent entity (products/customers) in queries 1, 2, and 4 so zero-activity entities are not silently dropped.
- Wrap every SUM(...) in COALESCE(SUM(...), 0) so zero-activity rows show 0.00 instead of NULL for revenue columns.
- Guard every division with NULLIF(denominator, 0) to prevent divide-by-zero errors.
- Round all currency columns to 2 decimal places consistently.
- In query 4, compute the High-Value percentile threshold only over customers with total_orders > 0, but still assign and output the 'Inactive' segment for customers with total_orders = 0.
- Each script must be runnable in a Databricks notebook cell using the active spark session (create_gold_tables.py is the entry point; the .sql files are not directly executable on their own, they are read as text).
- Use "-- ASSUMPTION:" SQL comments (or "# ASSUMPTION:" in the .py file) only for judgment calls not covered by this prompt (thresholds, grain, order_status filter — already flagged above, but note in the actual file if you materially deviate).

Do not touch any other files.

**Result:** Accepted on first generation, no fix-iteration needed (one
cosmetic indentation adjustment inside create_gold_tables.py, no logic
change). Code review confirmed all 3 hardening requirements were correctly
implemented across all 4 SQL files and the orchestrator.

## Validation
Ran create_gold_tables(spark) in Databricks (serverless compute) via the
same runpy invocation pattern used for Bronze/Silver. Printed Gold Layer
Summary:

| Table | Row Count |
|---|---|
| gold_sales_by_product | 500 |
| gold_revenue_by_customer | 9,940 |
| gold_daily_weekly_trends | 974 |
| gold_customer_segmentation | 4 |

Cross-checked the results mathematically rather than just confirming they
ran without error:
- **gold_sales_by_product = 500** matches the full PASSED product count
  from Silver (500/500 passed) — confirms the LEFT JOIN kept every
  product, not just ones with completed orders.
- **gold_revenue_by_customer = 9,940** matches Silver's PASSED customer
  count exactly (10,000 total minus 60 flagged) — confirms no drops, no
  join-induced duplication.
- **gold_customer_segmentation** breaks down as Repeat=7,923,
  High-Value=1,987, One-Time=25, Inactive=5 (summing to 9,940).
  Inactive being nonzero is direct proof the LEFT JOIN correctly retained
  zero-order customers rather than silently dropping them (the exact
  failure mode hardening fix #1 was written to prevent).
- **High-Value = 1,987 out of 9,935 customers with total_orders > 0**
  computes to exactly 1987/9935 = 0.2000 — precisely the 80th percentile
  cutoff, confirming the percentile-dilution fix (hardening fix #3)
  produced the intended exact 20% split rather than a skewed one.
- Repeat + One-Time (7,923 + 25 = 7,948) equals 9,935 − 1,987 exactly,
  confirming the priority-ordered CASE assignment is internally
  consistent with no double-counting or gaps.

## Root cause / lesson
The three hardening fixes weren't just theoretical risk — the
Inactive=5 and exact-20% percentile split are concrete evidence they were
necessary and correctly implemented. Pre-empting join/aggregation
failure modes specific to "keep zero-activity rows visible" requirements
(rather than discovering a silently-wrong row count after the fact) again
avoided a second Cursor session, consistent with the same lesson from
Bronze and Silver.

## Status: ACCEPTED (1 code session, 0 logic fix-iterations, row counts and percentile math independently verified consistent)
